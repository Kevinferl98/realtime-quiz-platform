import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from fastapi import WebSocket
from app.services.connection_manager import ConnectionManager

@pytest.fixture()
def manager() -> ConnectionManager:
    return ConnectionManager()

def make_mock_ws(send_json_side_effect=None) -> MagicMock:
    """Helper factory to build a WebSocket mock with spec and custom behavior."""
    ws = MagicMock(spec=WebSocket)
    ws.send_json = AsyncMock(side_effect=send_json_side_effect)
    return ws

@pytest.mark.asyncio
async def test_add_connection(manager):
    room_id = "room_123"
    ws = make_mock_ws()

    await manager.add_connection(room_id, ws)

    assert room_id in manager._room_connections
    assert manager._room_connections[room_id] == [ws]

@pytest.mark.asyncio
async def test_add_multiple_connections_to_same_room(manager):
    room_id = "room_123"
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    assert len(manager._room_connections[room_id]) == 2
    assert manager._room_connections[room_id] == [ws1, ws2]

@pytest.mark.asyncio
async def test_remove_connection(manager):
    room_id = "room_123"
    ws1, ws2 = make_mock_ws(), make_mock_ws()

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    await manager.remove_connection(room_id, ws1)

    assert manager._room_connections[room_id] == [ws2]

@pytest.mark.asyncio
async def test_remove_last_connection_deallocates_room(manager):
    room_id = "room_123"
    ws = make_mock_ws()

    await manager.add_connection(room_id, ws)
    await manager.remove_connection(room_id, ws)

    assert room_id not in manager._room_connections

@pytest.mark.asyncio
async def test_remove_non_existent_connection(manager):
    room_id = "empty_room"
    ws = make_mock_ws()

    await manager.remove_connection(room_id, ws)

    assert room_id not in manager._room_connections

@pytest.mark.asyncio
async def test_broadcast_to_empty_room_returns_immediately(manager):
    inactive_sockets = await manager.broadcast_to_room("empty_room", {"data": "test"})
    assert inactive_sockets == []

@pytest.mark.asyncio
async def test_broadcast_success_to_all_clients(manager):
    room_id = "room_123"
    message = {"type": "test"}
    ws1, ws2 = make_mock_ws(), make_mock_ws()

    await manager.add_connection(room_id, ws1)
    await manager.add_connection(room_id, ws2)

    inactive_sockets = await manager.broadcast_to_room(room_id, message)

    assert inactive_sockets == []
    ws1.send_json.assert_called_once_with(message)
    ws2.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_tracks_failed_connections(manager: ConnectionManager):
    room_id = "room_123"
    message = {"type": "game_update"}

    ws_healthy = make_mock_ws()
    ws_broken = make_mock_ws(send_json_side_effect=RuntimeError("Socket closed"))

    await manager.add_connection(room_id, ws_healthy)
    await manager.add_connection(room_id, ws_broken)

    inactive_sockets = await manager.broadcast_to_room(room_id, message)

    assert inactive_sockets == [ws_broken]
    ws_healthy.send_json.assert_called_once_with(message)
    ws_broken.send_json.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_broadcast_timeout_returns_inactive(manager: ConnectionManager):
    room_id = "room_123"
    message = {"type": "ping"}

    async def slow_send(_: dict):
        await asyncio.sleep(0.5)

    ws_healthy = make_mock_ws()
    ws_slow = make_mock_ws(send_json_side_effect=slow_send)

    await manager.add_connection(room_id, ws_healthy)
    await manager.add_connection(room_id, ws_slow)

    inactive_sockets = await manager.broadcast_to_room(
        room_id, message, timeout_seconds=0.1
    )

    assert inactive_sockets == [ws_slow]
    ws_healthy.send_json.assert_called_once_with(message)