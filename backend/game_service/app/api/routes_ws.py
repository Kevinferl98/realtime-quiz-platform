from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.dependencies import get_room_manager, get_redis_client
from app.services.room_ws_service import RoomWebSocketService
from my_observability import get_logger

router_ws = APIRouter()
logger = get_logger(__name__)

@router_ws.websocket("/ws/rooms/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str, manager=Depends(get_room_manager), redis=Depends(get_redis_client)):
    service = RoomWebSocketService(manager, redis)

    try:
        await service.handle_connection(websocket, room_id)
    except WebSocketDisconnect:
        await service.handle_disconnect(websocket, room_id)