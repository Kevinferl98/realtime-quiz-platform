import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.room_ws_service import RoomWebSocketService
from app.domain.room_session import RoomSession

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.start_quiz = AsyncMock()
    return manager

@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.get_room_meta = AsyncMock(return_value={
        "owner_id": "host-id",
        "status": "CREATED"
    })
    redis.add_player = AsyncMock()
    redis.get_players = AsyncMock(return_value=[{"name": "John"}])
    redis.publish_room_message = AsyncMock()
    redis.save_answer = AsyncMock()
    return redis

@pytest.fixture
def mock_websocket():
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    ws.query_params = {}
    return ws

@pytest.fixture
def service(mock_manager, mock_redis):
    return RoomWebSocketService(mock_manager, mock_redis)

@pytest.mark.asyncio
async def test_initialize_session_as_host(service, mock_websocket):
    mock_websocket.query_params = {}

    service._resolve_identity = MagicMock(return_value=("host-id", "John"))

    session = await service._initialize_session(mock_websocket, "room1")

    assert isinstance(session, RoomSession)
    assert session.is_host is True
    mock_websocket.send_json.assert_called()

@pytest.mark.asyncio
async def test_handle_join_guest(service, mock_websocket):
    session = RoomSession(
        player_id="p1",
        role="player",
        username=None,
        user_payload=None
    )

    data = {"name": "John"}

    await service._handle_join(mock_websocket, "room1", session, data)

    assert session.username == "John"
    service.redis.add_player.assert_called_once()

@pytest.mark.asyncio
async def test_handle_join_without_name(service, mock_websocket):
    session = RoomSession(
        player_id="p1",
        role="player",
        username=None,
        user_payload=None
    )

    await service._handle_join(mock_websocket, "room1", session, {})

    mock_websocket.send_json.assert_called_with({
        "type": "error",
        "message": "Name required"
    })

@pytest.mark.asyncio
async def test_start_as_host(service, mock_websocket):
    session = RoomSession(
        player_id="host-id",
        role="host"
    )

    await service._handle_start(mock_websocket, "room1", session)

    service.manager.start_quiz.assert_called_once_with("room1")

@pytest.mark.asyncio
async def test_start_as_player_fails(service, mock_websocket):
    session = RoomSession(
        player_id="p1",
        role="player"
    )

    await service._handle_start(mock_websocket, "room1", session)

    mock_websocket.send_json.assert_called_with({
        "type": "error",
        "message": "Only host can start the quiz"
    })

@pytest.mark.asyncio
async def test_handle_answer(service, mock_redis):
    mock_redis.get_room_meta.return_value = {
        "owner_id": "host-id",
        "current_question_index": 2
    }

    session = RoomSession(
        player_id="p1",
        role="player"
    )

    await service._handle_answer("room1", session, {"answer": "A"})

    mock_redis.save_answer.assert_called_once_with(
        "room1",
        2,
        "p1",
        "A"
    )

@pytest.mark.asyncio
async def test_room_not_found(service, mock_websocket, mock_redis):
    mock_redis.get_room_meta.return_value = None

    with pytest.raises(Exception):
        await service._initialize_session(mock_websocket, "room1")

    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_room_already_started(service, mock_websocket, mock_redis):
    mock_redis.get_room_meta.return_value = {
        "owner_id": "host-id",
        "current_question_index": 2,
        "started": True
    }

    with pytest.raises(Exception):
        await service._initialize_session(mock_websocket, "room1")

    mock_websocket.close.assert_called_once()