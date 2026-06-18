from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.services import room_service
from app.auth import get_current_user
from app.dependencies import get_redis_client
from app.schemas.multiplayer import RoomCreateResponse
from my_observability import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/game", tags=["game"])

@router.post(
    "/{quiz_id}/create_room",
    status_code=status.HTTP_201_CREATED,
    response_model=RoomCreateResponse,
    summary="Create a new room based on a quiz",
)
async def create_room(quiz_id: str, request: Request, user=Depends(get_current_user), redis=Depends(get_redis_client)):
    if user is None:
        raise HTTPException(status_code=401, detail="User not logged in")

    quiz_client = request.app.state.quiz_client

    return await room_service.create_room(redis, quiz_id, user["sub"], quiz_client)