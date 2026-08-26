import asyncio
import pytest
from unittest.mock import create_autospec, AsyncMock, patch
from app.services.quiz_engine import QuizEngine
from app.services.redis.redis_client import RedisClient
from app.schemas.multiplayer import Question, RoomAnswer, RoomStatus

@pytest.fixture
def mock_redis():
    return create_autospec(RedisClient, instance=True)

@pytest.fixture
def events_map():
    return {}

@pytest.fixture
def sample_question():
    return [
        Question(id="q1", question_text="Question 1", options=["A", "B", "C", "D"], correct_option="A"),
        Question(id="q2", question_text="Question 2", options=["A", "B", "C", "D"], correct_option="B")
    ]

@pytest.fixture
def engine(mock_redis, events_map):
    return QuizEngine(
        room_id="room_123",
        redis_client=mock_redis,
        events_map=events_map
    )

@pytest.mark.asyncio
async def test_lifecycle_aborts_if_no_questions_found(engine, mock_redis):
    mock_redis.get_questions.return_value = None

    await engine.run_lifecycle()

    mock_redis.get_questions.assert_called_with("room_123")
    mock_redis.publish_room_message.assert_not_called()

@pytest.mark.asyncio
async def test_complete_successful_lifecycle(
        engine,
        mock_redis,
        sample_question
):
    mock_redis.get_questions.return_value = sample_question
    mock_redis.get_answers.return_value = {}
    mock_redis.get_players.return_value = []

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch.object(engine, "_wait_for_answers_or_timeout", new_callable=AsyncMock) as mock_wait:
        await engine.run_lifecycle()

        assert mock_wait.call_count == len(sample_question)
        assert mock_sleep.call_count > 0

    assert mock_redis.update_room_status.call_count == 1
    assert mock_redis.update_room_progress.call_count == 2

    for idx, q in enumerate(sample_question):
        mock_redis.publish_room_message.assert_any_call(
            engine.room_id,
            {
                "type": "question",
                "question": q.model_dump(mode="json"),
                "index": idx,
            }
        )

@pytest.mark.asyncio
async def test_process_answers_with_linear_score_decay(engine, mock_redis):
    question = Question(id="q1", question_text="Question 1", options=["A", "B", "C", "D"], correct_option="A")
    question_idx = 0

    mock_redis.get_answers.return_value = {
        "p1": RoomAnswer(answer="A", timestamp=100.0),
        "p2": RoomAnswer(answer="A", timestamp=114.0),
        "p3": RoomAnswer(answer="B", timestamp=101.0)
    }

    with patch("time.time", return_value=100.0):
        await engine._process_answers(question, question_idx, 100.0)

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
async def test_lifecycle_exception_sets_room_status_to_error(engine, mock_redis):
    mock_redis.get_questions.side_effect = RuntimeError()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError):
            await engine.run_lifecycle()

            mock_redis.update_room_status.assert_called_with(
                engine.room_id,
                status=RoomStatus.ERROR,
            )