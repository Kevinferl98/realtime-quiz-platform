import asyncio
from typing import Dict, List
from fastapi import WebSocket
from my_observability import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """Manages active WebSocket connections grouped by room IDs."""
    def __init__(self):
        self._room_connections: Dict[str, List[WebSocket]] = {}

    async def add_connection(self, room_id: str, websocket: WebSocket) -> None:
        """Registers a new WebSocket connection into the specified room."""
        self._room_connections.setdefault(room_id, []).append(websocket)

    async def remove_connection(self, room_id: str, websocket: WebSocket) -> int:
        """
        Unregisters a WebSocket connection from a room and performs cleanup if empty.
        Returns the count of remaining active connections in the room.
        Returns 0 if the room is now empty and has been deallocated.
        """
        connections = self._room_connections.get(room_id, [])
        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self._room_connections.pop(room_id, None)
            return 0

        return len(connections)

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict,
        timeout_seconds: float = 2.0
    ) -> List[WebSocket]:
        """
        Broadcast a JSON message concurrently to all active web sockets in a room.
        Returns a list of stale/inactive WebSocket connections that failed
        during transmission and should be scheduled for disconnection.
        """
        # Create a shallow copy before awaiting network I/O.
        connections = list(self._room_connections.get(room_id, []))

        if not connections:
            return []

        async def send_safe(websocket: WebSocket) -> tuple[WebSocket, bool]:
            try:
                await asyncio.wait_for(websocket.send_json(message), timeout=timeout_seconds)
                return websocket, True
            except asyncio.TimeoutError:
                logger.warning(
                    "WebSocket broadcast timed out", room_id=room_id)
                return websocket, False
            except Exception as e:
                logger.warning("WebSocket broadcast failed", room_id=room_id, error=str(e))
                return websocket, False

        results = await asyncio.gather(
            *(send_safe(ws) for ws in connections)
        )

        return [websocket for websocket, success in results if not success]