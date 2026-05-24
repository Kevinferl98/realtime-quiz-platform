import asyncio
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """Manages active WebSocket connections grouped by room IDs."""
    def __init__(self):
        self._room_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add_connection(self, room_id: str, websocket: WebSocket) -> None:
        """Registers a new WebSocket connection into the specified room."""
        async with self._lock:
            self._room_connections.setdefault(room_id, []).append(websocket)

    async def remove_connection(self, room_id: str, websocket: WebSocket) -> int:
        """
        Unregisters a WebSocket connection from a room and performs cleanup if empty.
        Returns the count of remaining active connections in the room.
        Returns 0 if the room is now empty and has been deallocated.
        """
        async with self._lock:
            connections = self._room_connections.get(room_id, [])
            if websocket in connections:
                connections.remove(websocket)

            if not connections:
                self._room_connections.pop(room_id, None)
                return 0

            return len(connections)

    async def broadcast_to_room(self, room_id: str, message: dict) -> List[WebSocket]:
        """
        Broadcast a JSON message concurrently to all active web sockets in a room.
        Returns a list of stale/inactive WebSocket connections that failed
        during transmission and should be scheduled for disconnection.
        """
        async with self._lock:
            # Create a shallow copy of the list to iterate outside the lock.
            connections = list(self._room_connections.get(room_id, []))

        if not connections:
            return []

        inactive_connections: List[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                # Track broken connections.
                inactive_connections.append(ws)

        return inactive_connections