import redis.asyncio as redis
import json
import uuid
import time
from app.schemas.multiplayer import Player
from app.core.config import config
from my_observability import get_logger

logger = get_logger(__name__)

class RedisClient:
    def __init__(self):
        self.redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        self._locks: dict[str, str] = {}

    async def save_room_meta(self, room_id: str, owner_id: str, quiz_id: str, 
                             started: bool = False, current_question_index: int = 0, ttl_seconds: int = 3600):
        await self.redis.hset(f"room:{room_id}", mapping={
            "room_id": room_id,
            "owner_id": owner_id,
            "quiz_id": quiz_id,
            "started": int(started),
            "current_question_index": current_question_index
        })
        await self.redis.expire(f"room:{room_id}", ttl_seconds)

    async def get_room_meta(self, room_id: str):
        data = await self.redis.hgetall(f"room:{room_id}")
        if not data:
            return None
        data["started"] = bool(int(data.get("started", 0)))
        data["current_question_index"] = int(data.get("current_question_index", 0))
        return data
    
    async def delete_room_meta(self, room_id: str):
        await self.redis.delete(f"room:{room_id}")

    async def save_questions(self, room_id: str, questions: list[dict], ttl_seconds: int = 3600):
        await self.redis.set(f"room:{room_id}:questions", json.dumps(questions), ex=ttl_seconds)
    
    async def get_question(self, room_id: str, index: int):
        data = await self.redis.get(f"room:{room_id}:questions")
        if not data:
            return None
        
        qlist = json.loads(data)
        
        if index < 0 or index >= len(qlist):
            return None
        
        return qlist[index]
    
    async def get_all_questions(self, room_id: str) -> list[dict] | None:
        data = await self.redis.get(f"room:{room_id}:questions")
        if not data:
            return None
        
        return json.loads(data)

    async def delete_questions(self, room_id: str):
        await self.redis.delete(f"room:{room_id}:questions")

    async def add_player(self, room_id: str, player: Player, ttl_seconds: int = 3600):
        await self.redis.sadd(f"room:{room_id}:players", player.player_id)
        await self.redis.hset(f"room:{room_id}:player:{player.player_id}", mapping={
            "name": player.name,
            "score": player.score
        })
        await self.redis.expire(f"room:{room_id}:player:{player.player_id}", ttl_seconds)

    async def remove_player(self, room_id: str, player_id: str):
        await self.redis.srem(f"room:{room_id}:players", player_id)
        await self.redis.delete(f"room:{room_id}:player:{player_id}")

    async def get_players(self, room_id: str) -> list[dict]:
        player_ids = await self.redis.smembers(f"room:{room_id}:players")
        players = []
        for pid in player_ids:
            pdata = await self.redis.hgetall(f"room:{room_id}:player:{pid}")
            if pdata:
                players.append({
                    "player_id": pid,
                    "name": pdata.get("name"),
                    "score": int(pdata.get("score", 0))
                })
        return players
    
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

    async def increment_score(self, room_id: str, player_id: str, points: int = 1):
        await self.redis.hincrby(f"room:{room_id}:player:{player_id}", "score", points)
    
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

    async def set_if_not_exists(self, key: str, value: str, ttl: int) -> bool:
        return await self.redis.set(key, value, ex=ttl, nx=True)

    async def count_answers(self, room_id: str, question_index: int) -> int:
        return await self.redis.hlen(f"room:{room_id}:answers:{question_index}")