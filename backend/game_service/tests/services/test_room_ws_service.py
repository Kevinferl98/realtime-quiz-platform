import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec
from app.services.redis.redis_client import RedisClient
from app.services.room_manager import RoomManager
from app.services.room_ws_service import RoomWebSocketService
from app.domain.room_session import RoomSession
from app.schemas.multiplayer import Room, RoomStatus
from app.models.multiplayer import Player
from app.schemas.websocket_messages import JoinAction, AnswerAction, ErrorMessage

@pytest.fixture
def mock_manager() -> RoomManager:
    return create_autospec(RoomManager, instance=True)

@pytest.fixture
def mock_redis() -> RedisClient:
    redis = create_autospec(RedisClient, instance=True)
    redis.get_room.return_value = Room(
        room_id="1",
        owner_id="host-id",
        quiz_id="1",
        current_question_index=0,
        status=RoomStatus.CREATED
    )
    redis.get_players.return_value=[Player(player_id="p1", name="John")]
    return redis

@pytest.fixture
def mock_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    ws.query_params = {}
    return ws

@pytest.fixture
def service(mock_manager: RoomManager, mock_redis: RedisClient) -> RoomWebSocketService:
    return RoomWebSocketService(mock_manager, mock_redis)

@pytest.mark.asyncio
async def test_initialize_session_as_host(service, mock_websocket):
    mock_websocket.query_params = {}

    session = await service._initialize_session(mock_websocket, "room1", None, "host-id", "John")

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

    action = JoinAction(type="join", name="John")

    await service._handle_join("room1", session, action, mock_websocket)

    assert session.username == "John"
    service.redis.add_player_if_not_exists.assert_called_once()

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
        "code": "FORBIDDEN",
        "message": "Only host can start the quiz"
    })

@pytest.mark.asyncio
async def test_handle_answer(service, mock_redis, mock_websocket):
    mock_redis.get_room.return_value = Room(
        room_id="1",
        owner_id="host-id",
        quiz_id="1",
        current_question_index=2,
        status=RoomStatus.STARTED
    )

    session = RoomSession(
        player_id="p1",
        role="player"
    )
    action = AnswerAction(type="answer", answer="A")

    await service._handle_answer(mock_websocket, "room1", session, action)

    mock_redis.save_answer.assert_called_once_with(
        "room1",
        2,
        "p1",
        "A"
    )

@pytest.mark.asyncio
async def test_room_not_found(service, mock_websocket, mock_redis):
    mock_redis.get_room.return_value = None

    with pytest.raises(Exception):
        await service._initialize_session(mock_websocket, "room1", None, "host-id", "John")

    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_room_already_started(service, mock_websocket, mock_redis):
    mock_redis.get_room.return_value = Room(
        room_id="1",
        owner_id="host-id",
        quiz_id="1",
        current_question_index=2,
        status=RoomStatus.STARTED
    )

    with pytest.raises(Exception):
        await service._initialize_session(mock_websocket, "room1", None, "host-id", "John")

    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_answer_when_already_submitted_sends_error_message(service, mock_redis, mock_websocket):
    mock_redis.get_room.return_value = Room(
        room_id="room1",
        owner_id="host-id",
        quiz_id="1",
        current_question_index=0,
        status=RoomStatus.STARTED
    )
    mock_redis.save_answer.return_value=False

    session = RoomSession(
        player_id="p1",
        role="player"
    )
    action = AnswerAction(type="answer", answer="A")

    await service._handle_answer(mock_websocket, "room1", session, action)

    mock_redis.save_answer.assert_called_once_with(
        "room1",
        0,
        "p1",
        "A"
    )

    mock_websocket.send_json.assert_called_once_with({
        "type": "error",
        "code": "ANSWER_ALREADY_SUBMITTED",
        "message": "You have already submitted an answer for this question"
    })

    mock_redis.publish_room_message.assert_not_called()

@pytest.mark.asyncio
async def test_initialize_session__when_player_already_connected__raises_exception_and_closes_socket(
        service, mock_websocket, mock_redis
):
    mock_redis.add_player_if_not_exists.return_value = False

    with pytest.raises(Exception, match="Player already connected"):
        await service._initialize_session(mock_websocket, "room1", None, "host-id", "John")

    mock_redis.add_player_if_not_exists.assert_called_once()
    mock_websocket.send_json.assert_called_with(
        ErrorMessage(
            code="PLAYER_ALREADY_CONNECTED",
            message="You are already connected to this room from another tab or device"
        ).model_dump()
    )
    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_join__when_guest_already_connected__raises_exception_and_closes_socket(
    service, mock_websocket, mock_redis
):
    mock_redis.add_player_if_not_exists.return_value = False
    session = RoomSession(
        player_id="guest-uuid-123",
        role="player",
        username=None,
        user_payload=None
    )
    action = JoinAction(type="join", name="GuestPlayer")

    with pytest.raises(Exception, match="Player already connected"):
        await service._handle_join("room1", session, action, mock_websocket)

    mock_websocket.send_json.assert_called_with(
        ErrorMessage(
            code="PLAYER_ALREADY_CONNECTED",
            message="You are already connected to this room from another tab or device"
        ).model_dump()
    )
    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_connection_when_ticket_invalid_or_expired__rejects_and_closes_socket(
    service, mock_websocket, mock_redis
):
    invalid_ticket = "invalid-or-expired-ticket"
    mock_redis.retrieve_and_delete_ticket.return_value = None

    await service.handle_connection(mock_websocket, "room1", invalid_ticket)

    mock_redis.retrieve_and_delete_ticket.assert_awaited_once_with(invalid_ticket)
    mock_websocket.close.assert_awaited_once()
    mock_websocket.accept.assert_not_called()