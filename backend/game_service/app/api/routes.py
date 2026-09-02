from fastapi import APIRouter, Depends, status, Request
from app.services import room_service
from app.dependencies import get_redis_client, get_current_user
from app.schemas.multiplayer import RoomCreateResponse
from my_observability import get_logger
from app.schemas.auth import WSTicketResponse
from app.services import ws_ticket_service

logger = get_logger(__name__)
router = APIRouter(prefix="/game", tags=["game"])

@router.post(
    "/{quiz_id}/create_room",
    status_code=status.HTTP_201_CREATED,
    response_model=RoomCreateResponse,
    summary="Create a new room based on a quiz",
)
async def create_room(quiz_id: str, request: Request, user=Depends(get_current_user), redis=Depends(get_redis_client)):
    quiz_client = request.app.state.quiz_client

    return await room_service.create_room(redis, quiz_id, user.sub, quiz_client)

@router.post(
    "/rooms/{room_id}/ws-ticket",
    response_model=WSTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a single-use ticket for WebSocket authentication",
)
async def create_ws_ticket(room_id: str, user = Depends(get_current_user), redis=Depends(get_redis_client)):
    return await ws_ticket_service.create_ws_ticket(redis, user, room_id)