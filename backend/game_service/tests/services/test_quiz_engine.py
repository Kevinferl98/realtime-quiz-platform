import asyncio
import pytest
from unittest.mock import create_autospec, AsyncMock, patch
from app.services.quiz_engine import QuizEngine
from app.services.redis_client import RedisClient

@pytest.fixture
def mock_redis():
    redis = create_autospec(RedisClient, instance=True)
    redis.get_room_meta = AsyncMock()
    redis.get_all_questions = AsyncMock()
    redis.publish_room_message = AsyncMock()
    redis.set_question_start = AsyncMock()
    redis.get_question_start = AsyncMock()
    redis.get_answers = AsyncMock()
    redis.increment_score = AsyncMock()
    redis.delete_answers = AsyncMock()
    redis.get_players = AsyncMock()
    redis.save_room_meta = AsyncMock()
    return redis

@pytest.fixture
def events_map():
    return {}

@pytest.fixture
def sample_room_meta():
    return {
        "owner_id": "host_user",
        "quiz_id": "quiz_abc",
        "started": False,
        "current_question_index": 0
    }

@pytest.fixture
def sample_question():
    return [
        {"text": "Question 1", "correct_option": "A", "options": ["A", "B", "C"]},
        {"text": "Question 2", "correct_option": "B", "options": ["A", "B", "C"]}
    ]

@pytest.fixture
def engine(mock_redis, events_map):
    return QuizEngine(
        room_id="room_123",
        lock_key="quiz_lock:room_123",
        redis_client=mock_redis,
        events_map=events_map
    )

@pytest.mark.asyncio
async def test_lifecycle_aborts_if_no_room_metadata(engine, mock_redis):
    mock_redis.get_room_meta.return_value = None

    await engine.run_lifecycle()

    mock_redis.get_room_meta.assert_called_with("room_123")
    mock_redis.get_all_questions.assert_not_called()
    mock_redis.save_room_meta.assert_not_called()

@pytest.mark.asyncio
async def test_lifecycle_aborts_if_no_questions_found(engine, mock_redis, sample_room_meta):
    mock_redis.get_room_meta.return_value = sample_room_meta
    mock_redis.get_all_questions.return_value = None

    await engine.run_lifecycle()

    mock_redis.get_all_questions.assert_called_with("room_123")
    mock_redis.publish_room_message.assert_not_called()

@pytest.mark.asyncio
async def test_complete_successful_lifecycle(
        engine,
        mock_redis,
        sample_room_meta,
        sample_question
):
    mock_redis.get_room_meta.return_value = sample_room_meta
    mock_redis.get_all_questions.return_value = sample_question
    mock_redis.get_answers.return_value = {}
    mock_redis.get_players.return_value = []

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch.object(engine, "_wait_for_answers_or_timeout", new_callable=AsyncMock) as mock_wait:
        await engine.run_lifecycle()

        assert mock_wait.call_count == len(sample_question)
        assert mock_sleep.call_count > 0

    assert mock_redis.save_room_meta.call_count == 4

    for idx, q in enumerate(sample_question):
        mock_redis.publish_room_message.assert_any_call(
            engine.room_id, {"type": "question", "question": q, "index": idx}
        )

    mock_redis.save_room_meta.assert_called_with(
        engine.room_id,
        owner_id=sample_room_meta["owner_id"],
        quiz_id=sample_room_meta["quiz_id"],
        started=False,
        current_question_index=0
    )

@pytest.mark.asyncio
async def test_process_answers_with_linear_score_decay(engine, mock_redis):
    question = {"correct_option": "A"}
    question_idx = 0

    mock_redis.get_question_start.return_value = 100.0
    mock_redis.get_answers.return_value = {
        "p1": {"answer": "A", "ts": 100.0},
        "p2": {"answer": "A", "ts": 114.0},
        "p3": {"answer": "B", "ts": 101.0},
    }

    with patch("time.time", return_value=100.0):
        await engine._process_answers(question, question_idx)

    mock_redis.increment_score.assert_any_call(engine.room_id, "p1", 1000)
    mock_redis.increment_score.assert_any_call(engine.room_id, "p2", 200)

    assert "p3" not in [call.args[1] for call in mock_redis.increment_score.call_args_list]

@pytest.mark.asyncio
async def test_wait_for_answers_exits_early_on_event_signal(engine, events_map):
    question_idx = 5
    event_key = f"{engine.room_id}:{question_idx}"

    event = events_map.setdefault(event_key, asyncio.Event())
    event.set()

    await engine._wait_for_answers_or_timeout(question_idx)

    assert event_key not in events_map

@pytest.mark.asyncio
async def test_lifecycle_exception_guarantees_state_reset(engine, mock_redis, sample_room_meta):
    mock_redis.get_room_meta.return_value = sample_room_meta

    mock_redis.get_all_questions.side_effect = RuntimeError()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await engine.run_lifecycle()

    mock_redis.save_room_meta.assert_called_once_with(
        engine.room_id,
        owner_id=sample_room_meta["owner_id"],
        quiz_id=sample_room_meta["quiz_id"],
        started=False,
        current_question_index=0
    )