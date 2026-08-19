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
_INTERNAL_PLAYER_ID = "__room_meta__"

class RedisClient:
    def __init__(self):
        self.redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        self._locks: dict[str, str] = {}

        lua_path = SCRIPTS_DIR / "create_room.lua"
        script_content = lua_path.read_text(encoding="utf-8")
        self._create_room_script = self.redis.register_script(script_content)

    async def create_room(
            self,
            room_id: str,
            owner_id: str,
            quiz_id: str,
            questions: list[dict],
            ttl_seconds: int = 3600
    ) -> bool:
        room_key = f"room:{room_id}"
        questions_key = f"{room_key}:questions"
        players_key = f"{room_key}:players"
        scores_key = f"{room_key}:scores"
        questions_json = json.dumps(questions)

        result = await self._create_room_script(
            keys=[room_key, questions_key, players_key, scores_key],
            args=[
                room_id,
                owner_id,
                quiz_id,
                questions_json,
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
        room_key = f"room:{room_id}"
        mapping = {
            "current_question_index": index
        }

        if status:
            mapping["started"] = status

        await self.redis.hset(
            room_key,
            mapping=mapping
        )

    async def update_room_status(
            self,
            room_id: str,
            status: str
    ) -> None:
        room_key = f"room:{room_id}"
        await self.redis.hset(
            room_key,
            mapping={
                "status": status
            }
        )

    async def get_room_meta(self, room_id: str):
        data = await self.redis.hgetall(f"room:{room_id}")
        if not data:
            return None

        data["current_question_index"] = int(data.get("current_question_index", 0))
        return data
    
    async def get_all_questions(self, room_id: str) -> list[dict] | None:
        data = await self.redis.get(f"room:{room_id}:questions")
        if not data:
            return None
        
        return json.loads(data)

    async def add_player(
            self,
            room_id: str,
            player: Player,
    ) -> None:
        players_key = f"room:{room_id}:players"
        scores_key = f"room:{room_id}:scores"

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
        players_key = f"room:{room_id}:players"
        scores_key = f"room:{room_id}:scores"

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hdel(players_key, player_id)
            pipe.zrem(scores_key, player_id)
            await pipe.execute()

    async def get_players(self, room_id: str) -> list[dict]:
        players_key = f"room:{room_id}:players"
        players = await self.redis.hgetall(players_key)

        return [
            {
                "player_id": player_id,
                "name": name
            }
            for player_id, name in players.items()
            if player_id != _INTERNAL_PLAYER_ID
        ]

    async def count_players(self, room_id: str) -> int:
        return max(
            0,
            await self.redis.hlen(f"room:{room_id}:players") - 1,
        )

    async def get_leaderboard(self, room_id: str, limit: int = 5):
        scores_key = f"room:{room_id}:scores"
        players_key = f"room:{room_id}:players"

        entries = await self.redis.zrevrange(
            scores_key,
            0,
            limit,
            withscores=True
        )

        entries = [
            (player_id, score)
            for player_id, score in entries
            if player_id != _INTERNAL_PLAYER_ID
        ][:limit]

        if not entries:
            return []

        async with self.redis.pipeline(transaction=False) as pipe:
            for player_id, _score in entries:
                pipe.hget(players_key, player_id)

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
        await self.redis.hset(
            f"room:{room_id}:answers:{question_index}",
            player_id, 
            json.dumps({
                "answer": answer,
                "ts": time.time()
            })
        )

    async def get_answers(self, room_id: str, question_index: int):
        raw =  await self.redis.hgetall(f"room:{room_id}:answers:{question_index}")

        parsed = {}
        for pid, data in raw.items():
            parsed[pid] = json.loads(data)

        return parsed

    async def delete_answers(self, room_id: str, question_index: int):
        await self.redis.delete(f"room:{room_id}:answers:{question_index}")

    async def increment_score(
            self,
            room_id: str,
            player_id: str,
            points: int = 1
    ) -> int:
        scores_key = f"room:{room_id}:scores"

        return await self.redis.zincrby(
            scores_key,
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

    async def count_answers(self, room_id: str, question_index: int) -> int:
        return await self.redis.hlen(f"room:{room_id}:answers:{question_index}")