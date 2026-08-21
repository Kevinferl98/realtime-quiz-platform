import redis.asyncio as redis
import json
import uuid
import time
from app.schemas.multiplayer import Player
from app.core.config import config
from my_observability import get_logger
from pathlib import Path

logger = get_logger(__name__)

SCRIPTS_DIR = Path(__file__).parent / "redis_scripts"

ROOM_PREFIX = "room:"

INTERNAL_PLAYER_ID = "__room_meta__"

DEFAULT_ROOM_TTL = 3600
DEFAULT_LEADERBOARD_LIMIT = 5

class RedisClient:
    def __init__(self):
        self.redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        self._locks: dict[str, str] = {}
        self._create_room_script = self._register_script("create_room.lua")

    async def create_room(
            self,
            room_id: str,
            owner_id: str,
            quiz_id: str,
            questions: list[dict],
            ttl_seconds: int = DEFAULT_ROOM_TTL
    ) -> bool:
        room_key = self._room_key(room_id)

        result = await self._create_room_script(
            keys=[
                room_key,
                self._questions_key(room_id),
                self._players_key(room_id),
                self._scores_key(room_id)
            ],
            args=[
                room_id,
                owner_id,
                quiz_id,
                json.dumps(questions),
                ttl_seconds
            ]
        )

        return bool(result)

    async def update_room_progress(
            self,
            room_id: str,
            index: int,
            status: str | None = None
    ) -> None:
        mapping = {
            "current_question_index": index
        }

        if status:
            mapping["status"] = status

        await self.redis.hset(
            self._room_key(room_id),
            mapping=mapping
        )

    async def update_room_status(
            self,
            room_id: str,
            status: str
    ) -> None:
        await self.redis.hset(
            self._room_key(room_id),
            mapping={
                "status": status
            }
        )

    async def get_room_meta(self, room_id: str):
        data = await self.redis.hgetall(self._room_key(room_id))
        if not data:
            return None

        data["current_question_index"] = int(data.get("current_question_index", 0))
        return data
    
    async def get_all_questions(self, room_id: str) -> list[dict] | None:
        data = await self.redis.get(self._questions_key(room_id))
        if not data:
            return None
        
        return json.loads(data)

    async def add_player(
            self,
            room_id: str,
            player: Player,
    ) -> None:
        players_key = self._players_key(room_id)
        scores_key = self._scores_key(room_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(
                players_key,
                player.player_id,
                player.name
            )
            pipe.zadd(
                scores_key,
                {player.player_id: 0}
            )
            await pipe.execute()

    async def remove_player(self, room_id: str, player_id: str) -> None:
        players_key = self._players_key(room_id)
        scores_key = self._scores_key(room_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hdel(players_key, player_id)
            pipe.zrem(scores_key, player_id)
            await pipe.execute()

    async def get_players(self, room_id: str) -> list[dict]:
        players = await self.redis.hgetall(self._players_key(room_id))

        return [
            {
                "player_id": player_id,
                "name": name
            }
            for player_id, name in players.items()
            if player_id != INTERNAL_PLAYER_ID
        ]

    async def count_players(self, room_id: str) -> int:
        return max(
            0,
            await self.redis.hlen(self._players_key(room_id)) - 1,
        )

    async def get_leaderboard(self, room_id: str, limit: int = DEFAULT_LEADERBOARD_LIMIT):
        entries = await self.redis.zrevrange(
            self._scores_key(room_id),
            0,
            limit,
            withscores=True
        )

        entries = [
            (player_id, score)
            for player_id, score in entries
            if player_id != INTERNAL_PLAYER_ID
        ][:limit]

        if not entries:
            return []

        async with self.redis.pipeline(transaction=False) as pipe:
            for player_id, _score in entries:
                pipe.hget(self._players_key(room_id), player_id)

            names = await pipe.execute()

        return [
            {
                "player_id": player_id,
                "name": name,
                "score": int(score)
            }
            for (player_id, score), name in zip(entries, names)
            if name is not None
        ]
    
    async def save_answer(self, room_id: str, question_index: int, player_id: str, answer: str):
        answers_key = self._answers_key(room_id, question_index)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(
                answers_key,
                player_id,
                json.dumps({
                    "answer": answer,
                    "ts": time.time()
                })
            )
            pipe.expire(answers_key, 300, nx=True)
            await pipe.execute()

    async def get_answers(self, room_id: str, question_index: int):
        raw =  await self.redis.hgetall(self._answers_key(room_id, question_index))

        parsed = {}
        for pid, data in raw.items():
            parsed[pid] = json.loads(data)

        return parsed

    async def delete_answers(self, room_id: str, question_index: int):
        await self.redis.delete(self._answers_key(room_id, question_index))

    async def count_answers(self, room_id: str, question_index: int) -> int:
        return await self.redis.hlen(self._answers_key(room_id, question_index))

    async def increment_score(
            self,
            room_id: str,
            player_id: str,
            points: int = 1
    ) -> int:
        return await self.redis.zincrby(
            self._scores_key(room_id),
            points,
            player_id
        )
    
    async def publish_room_message(self, room_id: str, message: dict):
        try:
            await self.redis.publish(
                f"room_{room_id}",
                json.dumps(message)
            )
        except Exception as e:
            logger.warning(f"Error publishing to room {room_id}: {e}")

    async def subscribe_rooms(self, handler):
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("room_*")

        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                room_id = channel.split("_")[1]

                try:
                    data = json.loads(message["data"])
                    await handler(room_id, data)
                except Exception as e:
                    logger.warning(f"Error processing pubsub message: {e}")
    
    async def acquire_lock(self, key: str, ttl: int = 60) -> bool:
        lock_value = str(uuid.uuid4())
        acquired = await self.redis.set(key, lock_value, nx=True, ex=ttl)
        if acquired:
            self._locks[key] = lock_value
            logger.debug(f"Lock acquired: {key}")
            return True
        return False
    
    async def release_lock(self, key: str) -> bool:
        lock_value = self._locks.get(key)
        if not lock_value:
            logger.warning(f"Trying to release lock not owned: {key}")
            return False
        
        lua = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(lua, keys=[key], args=[lock_value])
        if result:
            logger.debug(f"Lock released: {key}")
            return True
        logger.warning(f"Lock not released, value mismatch: {key}")
        return False 
    
    async def set_question_start(self, room_id: str, ttl: int):
        await self.redis.set(
            f"room:{room_id}:question_start",
            time.time(),
            ex=ttl
        )

    async def get_question_start(self, room_id: str) -> float | None:
        value = await self.redis.get(f"room:{room_id}:question_start")
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _room_key(room_id: str) -> str:
        return f"{ROOM_PREFIX}{room_id}"

    @classmethod
    def _questions_key(cls, room_id: str) -> str:
        return f"{cls._room_key(room_id)}:questions"

    @classmethod
    def _players_key(cls, room_id: str) -> str:
        return f"{cls._room_key(room_id)}:players"

    @classmethod
    def _scores_key(cls, room_id: str) -> str:
        return f"{cls._room_key(room_id)}:scores"

    @classmethod
    def _answers_key(cls, room_id: str, question_index: int) -> str:
        return f"{cls._room_key(room_id)}:answers:{question_index}"

    def _register_script(self, filename: str):
        """Load and register a Lua script from the scripts directory."""
        script_path = SCRIPTS_DIR / filename
        script_content = script_path.read_text(encoding="utf-8")
        return self.redis.register_script(script_content)