import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import WebSocket
from app.services.connection_manager import ConnectionManager

@pytest.fixture()
def manager():
    return ConnectionManager()

@pytest.fixture()
def mock_websocket():
    ws = MagicMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    return ws

@pytest.mark.asyncio
async def test_add_connection(manager, mock_websocket):
    room_id = "room_123"

    await manager.add_connection(room_id, mock_websocket)

    assert room_id in manager._room_connections
    assert manager._room_connections[room_id] == [mock_websocket]

@pytest.mark.asyncio
async def test_add_multiple_connections_to_same_room(manager):
    room_id = "room_123"
    ws1 = MagicMock(spec=WebSocket)
    ws2 = MagicMock(spec=WebSocket)

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    assert len(manager._room_connections[room_id]) == 2
    assert manager._room_connections[room_id] == [ws1, ws2]

@pytest.mark.asyncio
async def test_remove_connection_returns_remaining_count(manager):
    room_id = "room_123"
    ws1 = MagicMock(spec=WebSocket)
    ws2 = MagicMock(spec=WebSocket)

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    remaining = await manager.remove_connection(room_id, ws1)

    assert remaining == 1
    assert manager._room_connections[room_id] == [ws2]

@pytest.mark.asyncio
async def test_remove_last_connection_deallocates_room(manager, mock_websocket):
    room_id = "room_123"
    await manager.add_connection(room_id, mock_websocket)

    remaining = await manager.remove_connection(room_id, mock_websocket)

    assert remaining == 0
    assert room_id not in manager._room_connections

@pytest.mark.asyncio
async def test_remove_non_existent_connection(manager, mock_websocket):
    room_id = "empty_room"

    remaining = await manager.remove_connection(room_id, mock_websocket)

    assert remaining == 0
    assert room_id not in manager._room_connections

@pytest.mark.asyncio
async def test_broadcast_to_empty_room_returns_immediately(manager):
    inactive_sockets = await manager.broadcast_to_room("empty_room", {"data": "test"})
    assert inactive_sockets == []

@pytest.mark.asyncio
async def test_broadcast_success_to_all_clients(manager):
    room_id = "room_123"
    message = {"type": "test"}

    ws1 = MagicMock(spec=WebSocket)
    ws1.send_json = AsyncMock()
    ws2 = MagicMock(spec=WebSocket)
    ws2.send_json = AsyncMock()

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    inactive_sockets = await manager.broadcast_to_room(room_id, message)

    assert inactive_sockets == []
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_tracks_and_returns_inactive_connections(manager):
    room_id = "room_123"
    message = {"type": "test"}

    ws_healthy = MagicMock(spec=WebSocket)
    ws_healthy.send_json = AsyncMock()

    ws_inactive = MagicMock(spec=WebSocket)
    ws_inactive.send_json = AsyncMock(side_effect=RuntimeError("Connection lost"))

    await manager.add_connection(room_id, ws_healthy)
    await manager.add_connection(room_id, ws_inactive)

    inactive_sockets = await manager.broadcast_to_room(room_id, message)

    assert inactive_sockets == [ws_inactive]
    ws_healthy.send_json.assert_called_once_with(message)
    ws_inactive.send_json.assert_called_once_with(message)