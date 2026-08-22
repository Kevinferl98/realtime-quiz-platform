import random
from app.services.redis.redis_client import RedisClient
from app.schemas.multiplayer import RoomCreateResponse
from app.services.quiz_grpc_client import QuizServiceClient
from my_observability import get_logger
from app.exception import QuizEmptyError, CreateRoomError

ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_TTL_SECONDS = 3600
MAX_RETRIES = 5

logger = get_logger(__name__)

def generate_room_code(length: int = 5) -> str:
    return "".join(random.choices(ROOM_CODE_CHARS, k=length))

async def create_room(redis: RedisClient, quiz_id: str, user_id: str, quiz_client: QuizServiceClient) -> RoomCreateResponse:
    quiz_data = await quiz_client.get_quiz_by_id(quiz_id)
    questions = quiz_data.get("questions", [])

    if not questions:
        raise QuizEmptyError()

    for _ in range(MAX_RETRIES):
        room_id = generate_room_code()

        created = await redis.create_room(
            room_id=room_id,
            owner_id=user_id,
            quiz_id=quiz_id,
            questions=questions,
            ttl_seconds=ROOM_TTL_SECONDS
        )

        if created:
            return RoomCreateResponse(room_id=room_id)

    logger.error("Unable to generate a unique room_id after multiple attempts")
    raise CreateRoomError()