import random
import logging
from app.exception import QuizNotFoundError
from app.services.redis_client import RedisClient
from app.schemas.multiplayer import RoomCreateResponse
from app.services.quiz_grpc_client import QuizServiceClient
from fastapi import HTTPException

CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_TTL_SECONDS = 3600
MAX_RETRIES = 5

logger = logging.getLogger(__name__)

def generate_room_code(length: int = 5) -> str:
    return "".join(random.choices(CHARS, k=length))

async def reserve_room_id(redis: RedisClient, room_id: str, ttl: int) -> bool:
    return await redis.set_if_not_exists(
        key=f"room:{room_id}:lock",
        value="1",
        ttl=ttl
    )

async def generate_unique_room_id(redis: RedisClient) -> str:
    for _ in range(MAX_RETRIES):
        room_id = generate_room_code()

        reserved = await reserve_room_id(redis, room_id, ttl=ROOM_TTL_SECONDS)
        if reserved:
            return room_id

    raise RuntimeError("Unable to generate a unique room_id after multiple attempts")

async def create_room(redis: RedisClient, quiz_id: str, user_id: str, quiz_client: QuizServiceClient) -> RoomCreateResponse:
    try:
        quiz_data = await quiz_client.get_quiz_by_id(quiz_id)
    except QuizNotFoundError:
        logger.warning(f"Quiz {quiz_id} not found via gRPC")
        raise HTTPException(status_code=404, detail="Quiz not found")
    except Exception:
        logger.error(f"Failed to fetch quiz {quiz_id} due to upstream error")
        raise HTTPException(status_code=502, detail="Upstream quiz service unavailable")

    room_id = await generate_unique_room_id(redis)

    await redis.save_room_meta(
        room_id=room_id,
        owner_id=user_id,
        quiz_id=quiz_id,
        started=False,
        current_question_index=0,
        ttl_seconds=ROOM_TTL_SECONDS
    )

    await redis.save_questions(
        room_id=room_id,
        questions=quiz_data.get("questions", []),
        ttl_seconds=ROOM_TTL_SECONDS
    )

    return RoomCreateResponse(room_id=room_id)