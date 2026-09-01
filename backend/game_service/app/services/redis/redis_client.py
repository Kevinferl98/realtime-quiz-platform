import redis.asyncio as redis
import json
from app.schemas.multiplayer import Room, RoomAnswer, Question, RoomStatus
from app.models.multiplayer import Player, LeaderboardEntry
from app.core.config import config
from my_observability import get_logger
from pathlib import Path
from app.services.redis.keys import RedisKeys

logger = get_logger(__name__)

SCRIPTS_DIR = Path(__file__).parent / "scripts"

INTERNAL_PLAYER_ID = "__room_meta__"
DEFAULT_ROOM_TTL = 3600
DEFAULT_LEADERBOARD_LIMIT = 5
TICKET_TTL_SECONDS = 10

class RedisClient:
    def __init__(self):
        self.redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        self._create_room_script = self._load_script("create_room.lua")
        self._start_quiz_script = self._load_script("start_quiz.lua")
        self._add_player_script = self._load_script("add_player.lua")

    def _load_script(self, filename: str):
        script_path = SCRIPTS_DIR / filename
        script_content = script_path.read_text(encoding="utf-8")
        return self.redis.register_script(script_content)

    async def _get_redis_timestamp(self) -> float:
        seconds, microseconds = await self.redis.time()
        return seconds + (microseconds / 1_000_000)

    async def create_room(
            self,
            room_id: str,
            owner_id: str,
            quiz_id: str,
            questions: list[Question],
            ttl_seconds: int = DEFAULT_ROOM_TTL
    ) -> bool:
        result = await self._create_room_script(
            keys=[
                RedisKeys.room(room_id),
                RedisKeys.questions(room_id),
                RedisKeys.players(room_id),
                RedisKeys.scores(room_id)
            ],
            args=[
                room_id,
                owner_id,
                quiz_id,
                json.dumps([
                    question.model_dump(mode="json")
                    for question in questions
                ]),
                ttl_seconds
            ]
        )

        return bool(result)

    async def update_room_progress(
            self,
            room_id: str,
            index: int,
    ) -> None:
        start_timestamp = await self._get_redis_timestamp()

        await self.redis.hset(
            RedisKeys.room(room_id),
            mapping={
                "current_question_index": index,
                "question_start_timestamp": start_timestamp
            }
        )

    async def update_room_status(
            self,
            room_id: str,
            status: RoomStatus,
    ) -> None:
        await self.redis.hset(
            RedisKeys.room(room_id),
            mapping={"status": status.value}
        )

    async def get_room(self, room_id: str) -> Room | None:
        data = await self.redis.hgetall(RedisKeys.room(room_id))
        return Room.model_validate(data) if data else None

    async def get_question_start_timestamp(self, room_id: str) -> float | None:
        val = await self.redis.hget(RedisKeys.room(room_id), "question_start_timestamp")
        return float(val) if val else None

    async def try_start_room(self, room_id: str) -> bool:
        result = await self._start_quiz_script(
            keys=[RedisKeys.room(room_id)]
        )
        return bool(result)
    
    async def get_questions(self, room_id: str) -> list[Question] | None:
        data = await self.redis.get(RedisKeys.questions(room_id))
        if not data:
            return None

        raw_questions = json.loads(data)
        return [Question.model_validate(question) for question in raw_questions]

    async def add_player_if_not_exists(
            self,
            room_id: str,
            player: Player,
    ) -> bool:
        players_key = RedisKeys.players(room_id)
        scores_key = RedisKeys.scores(room_id)

        result = await self._add_player_script(
            keys=[players_key, scores_key],
            args=[player.player_id, player.name]
        )

        return result == 1

    async def remove_player(self, room_id: str, player_id: str) -> None:
        players_key = RedisKeys.players(room_id)
        scores_key = RedisKeys.scores(room_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hdel(players_key, player_id)
            pipe.zrem(scores_key, player_id)
            await pipe.execute()

    async def get_players(self, room_id: str) -> list[Player]:
        players = await self.redis.hgetall(RedisKeys.players(room_id))

        return [
            Player(player_id=player_id, name=name)
            for player_id, name in players.items()
            if player_id != INTERNAL_PLAYER_ID
        ]

    async def count_players(self, room_id: str) -> int:
        return max(
            0,
            await self.redis.hlen(RedisKeys.players(room_id)) - 1,
        )

    async def save_answer(
            self,
            room_id: str,
            question_index: int,
            player_id: str,
            answer: str
    ) -> bool:
        answers_key = RedisKeys.answers(room_id, question_index)
        current_timestamp = await self._get_redis_timestamp()
        room_answer = RoomAnswer(answer=answer, timestamp=current_timestamp)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hsetnx(
                answers_key,
                player_id,
                room_answer.model_dump_json()
            )
            pipe.expire(answers_key, 300, nx=True)
            results = await pipe.execute()

        return bool(results[0])

    async def get_answers(self, room_id: str, question_index: int) -> dict[str, RoomAnswer]:
        raw =  await self.redis.hgetall(RedisKeys.answers(room_id, question_index))

        return {
            player_id: RoomAnswer.model_validate_json(data)
            for player_id, data in raw.items()
        }

    async def delete_answers(self, room_id: str, question_index: int) -> None:
        await self.redis.delete(RedisKeys.answers(room_id, question_index))

    async def count_answers(self, room_id: str, question_index: int) -> int:
        return await self.redis.hlen(RedisKeys.answers(room_id, question_index))

    async def increment_score(
            self,
            room_id: str,
            player_id: str,
            points: int = 1
    ) -> int:
        return await self.redis.zincrby(
            RedisKeys.scores(room_id),
            points,
            player_id
        )

    async def get_leaderboard(
            self,
            room_id: str,
            limit: int = DEFAULT_LEADERBOARD_LIMIT
    ) -> list[LeaderboardEntry]:
        entries = await self.redis.zrevrange(
            RedisKeys.scores(room_id),
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
                pipe.hget(RedisKeys.players(room_id), player_id)

            names = await pipe.execute()

        return [
            LeaderboardEntry(
                player_id=player_id,
                name=name,
                score=int(score)
            )
            for (player_id, score), name in zip(entries, names)
            if name is not None
        ]
    
    async def publish_room_message(
            self,
            room_id: str,
            message: dict[str, object],
    ) -> None:
        try:
            await self.redis.publish(
                RedisKeys.room_channel(room_id),
                json.dumps(message)
            )
        except Exception as e:
            logger.exception(f"Error publishing to room {room_id}: {e}")
            raise

    async def subscribe_rooms(self, handler) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe(RedisKeys.room_channels_pattern())

        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                room_id = channel.split("_")[1]

                try:
                    data = json.loads(message["data"])
                    await handler(room_id, data)
                except Exception as e:
                    logger.warning(f"Error processing pubsub message: {e}")

    async def save_ticket(self, ticket_id: str, ticket_data: dict) -> None:
        await self.redis.setex(
            RedisKeys.ticket(ticket_id),
            TICKET_TTL_SECONDS,
            json.dumps(ticket_data)
        )