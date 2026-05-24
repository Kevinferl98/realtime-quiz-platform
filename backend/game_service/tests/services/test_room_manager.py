import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from app.services.connection_manager import ConnectionManager
from app.services.redis_client import RedisClient
from app.services.room_manager import QUIZ_LOCK_TTL, RoomManager

@pytest.fixture
def mock_redis():
    client = MagicMock(spec=RedisClient)
    client.acquire_lock = AsyncMock(return_value=True)
    client.release_lock = AsyncMock()
    client.remove_player = AsyncMock()
    client.get_players = AsyncMock(return_value=[{"name": "Player1"}, {"name": "Player2"}])
    client.publish_room_message = AsyncMock()
    client.subscribe_rooms = AsyncMock()
    client.count_answers = AsyncMock(return_value=2)
    return client

@pytest.fixture
def mock_websocket():
    return MagicMock(spec=WebSocket)

@pytest.fixture
def mock_connection_manager():
    manager = MagicMock(spec=ConnectionManager)
    manager.add_connection = AsyncMock()
    manager.remove_connection = AsyncMock(return_value=1)
    manager.broadcast_to_room = AsyncMock(return_value=[])
    return manager

@pytest.fixture
async def room_manager(mock_redis, mock_connection_manager):
    manager = RoomManager(redis_client=mock_redis, connection_manager=mock_connection_manager)
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_start_successfully(room_manager):
    await room_manager.start()

    assert room_manager._running is True
    assert room_manager._subscribe_task is not None
    assert isinstance(room_manager._subscribe_task, asyncio.Task)

@pytest.mark.asyncio
async def test_start_is_idempotent(room_manager, mock_redis):
    await room_manager.start()
    first_task = room_manager._subscribe_task

    await room_manager.start()
    await asyncio.sleep(0)

    assert room_manager._subscribe_task is first_task
    mock_redis.subscribe_rooms.assert_awaited_once()

@pytest.mark.asyncio
async def test_stop_cancels_subscribe_and_quiz_tasks(room_manager):
    await room_manager.start()

    blocker = asyncio.Event()

    async def never_ending():
        await blocker.wait()

    task = asyncio.create_task(never_ending())
    room_manager._quiz_tasks["room_123"] = task

    await room_manager.stop()

    assert room_manager._running is False
    assert task.cancelled() is True
    assert room_manager._quiz_tasks == {}

@pytest.mark.asyncio
async def test_connect_delegates_to_connection_manager(room_manager, mock_websocket, mock_connection_manager):
    await room_manager.connect("room_1", mock_websocket)

    mock_connection_manager.add_connection.assert_awaited_once_with("room_1", mock_websocket)

@pytest.mark.asyncio
async def test_register_player_ws_maps_socket_to_player(room_manager, mock_websocket):
    await room_manager.register_player_ws(mock_websocket, "player_abc")

    assert room_manager._ws_to_player[mock_websocket] == "player_abc"

@pytest.mark.asyncio
async def test_disconnect_player_updates_state_and_notifies(room_manager, mock_websocket, mock_connection_manager, mock_redis):
    await room_manager.register_player_ws(mock_websocket, "player_123")

    await room_manager.disconnect("room_1", mock_websocket)

    assert mock_websocket not in room_manager._ws_to_player
    mock_connection_manager.remove_connection.assert_awaited_once_with("room_1", mock_websocket)
    mock_redis.remove_player.assert_awaited_once_with("room_1", "player_123")
    mock_redis.publish_room_message.assert_awaited_once_with(
        "room_1",
        {"type": "player_left", "players": ["Player1", "Player2"]},
    )

@pytest.mark.asyncio
async def test_disconnect_without_registered_player_does_not_touch_redis_player_state(
    room_manager, mock_websocket, mock_redis
):
    await room_manager.disconnect("room_1", mock_websocket)

    mock_redis.remove_player.assert_not_awaited()
    mock_redis.publish_room_message.assert_not_awaited()

@pytest.mark.asyncio
async def test_disconnect_empty_room_triggers_cleanup(room_manager, mock_websocket, mock_connection_manager):
    mock_connection_manager.remove_connection.return_value = 0
    room_manager._cleanup_room_resources = AsyncMock()

    await room_manager.disconnect("room_empty", mock_websocket)

    room_manager._cleanup_room_resources.assert_awaited_once_with("room_empty")

@pytest.mark.asyncio
async def test_start_quiz_lock_already_acquired_on_other_instance(room_manager):
    room_manager._redis.acquire_lock.return_value = False

    await room_manager.start_quiz("room_2")

    assert "room_2" not in room_manager._quiz_tasks
    room_manager._redis.release_lock.assert_not_awaited()

@pytest.mark.asyncio
async def test_start_quiz_already_running_locally_releases_lock(room_manager):
    blocker = asyncio.Event()

    async def never_ending():
        await blocker.wait()

    room_manager._quiz_tasks["room_3"] = asyncio.create_task(never_ending())

    await room_manager.start_quiz("room_3")

    room_manager._redis.release_lock.assert_awaited_once_with("quiz_lock:room_3")

@pytest.mark.asyncio
@patch("app.services.room_manager.QuizEngine")
async def test_start_quiz_success_spawns_background_task(mock_quiz_engine_cls, room_manager):
    mock_engine = mock_quiz_engine_cls.return_value
    mock_engine.lock_key = "quiz_lock:room_1"
    mock_engine.run_lifecycle = AsyncMock()

    await room_manager.start_quiz("room_1")

    room_manager._redis.acquire_lock.assert_awaited_once_with("quiz_lock:room_1", QUIZ_LOCK_TTL)
    mock_quiz_engine_cls.assert_called_once_with(
        "room_1", "quiz_lock:room_1", room_manager._redis, room_manager._answer_events
    )
    assert "room_1" in room_manager._quiz_tasks

    await asyncio.sleep(0)

    mock_engine.run_lifecycle.assert_awaited_once()
    room_manager._redis.release_lock.assert_awaited_once_with("quiz_lock:room_1")
    assert "room_1" not in room_manager._quiz_tasks

@pytest.mark.asyncio
async def test_wrapped_quiz_runner_releases_lock_and_removes_task_on_error(room_manager):
    room_id = "room_err"
    engine = MagicMock()
    engine.lock_key = "quiz_lock:room_err"
    engine.run_lifecycle = AsyncMock(side_effect=RuntimeError("boom"))
    room_manager._quiz_tasks[room_id] = asyncio.current_task()

    with pytest.raises(RuntimeError, match="boom"):
        await room_manager._wrapped_quiz_runner(room_id, engine)

    assert room_id not in room_manager._quiz_tasks
    room_manager._redis.release_lock.assert_awaited_once_with("quiz_lock:room_err")

@pytest.mark.asyncio
async def test_cleanup_room_resources_cancels_existing_task(room_manager):
    blocker = asyncio.Event()

    async def never_ending():
        await blocker.wait()

    task = asyncio.create_task(never_ending())
    room_manager._quiz_tasks["room_4"] = task

    await room_manager._cleanup_room_resources("room_4")

    assert task.cancelled() is True
    assert "room_4" not in room_manager._quiz_tasks

@pytest.mark.asyncio
async def test_handle_answer_submitted_unblocks_when_all_players_answered(room_manager):
    room_id = "room_99"
    q_idx = 3
    event_key = f"{room_id}:{q_idx}"
    early_event = asyncio.Event()
    room_manager._answer_events[event_key] = early_event

    room_manager._redis.get_players.return_value = [{"name": "P1"}, {"name": "P2"}]
    room_manager._redis.count_answers.return_value = 2

    message = {"type": "answer_submitted", "current_question_index": q_idx}

    await room_manager._handle_inbound_pubsub_msg(room_id, message)

    assert early_event.is_set() is True
    room_manager._connection_manager.broadcast_to_room.assert_awaited_once_with(room_id, message)

@pytest.mark.asyncio
async def test_handle_answer_submitted_does_not_unblock_when_answers_missing(room_manager):
    room_id = "room_100"
    q_idx = 1
    event_key = f"{room_id}:{q_idx}"
    early_event = asyncio.Event()
    room_manager._answer_events[event_key] = early_event

    room_manager._redis.get_players.return_value = [{"name": "P1"}, {"name": "P2"}, {"name": "P3"}]
    room_manager._redis.count_answers.return_value = 2

    message = {"type": "answer_submitted", "current_question_index": q_idx}

    await room_manager._handle_inbound_pubsub_msg(room_id, message)

    assert early_event.is_set() is False

@pytest.mark.asyncio
async def test_handle_pubsub_disconnects_stale_sockets(room_manager, mock_websocket):
    room_id = "room_1"
    message = {"type": "chat_message", "content": "Hello"}
    room_manager._connection_manager.broadcast_to_room.return_value = [mock_websocket]
    room_manager.disconnect = AsyncMock()

    await room_manager._handle_inbound_pubsub_msg(room_id, message)

    room_manager.disconnect.assert_awaited_once_with(room_id, mock_websocket)