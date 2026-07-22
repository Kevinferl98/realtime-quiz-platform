import pytest
from unittest.mock import AsyncMock, patch, create_autospec
from app.exception import QuizNotFoundError
from app.schemas.multiplayer import RoomCreateResponse
from app.services.quiz_grpc_client import QuizServiceClient
from app.services.redis_client import RedisClient
from app.services.room_service import create_room

@pytest.fixture
def mock_redis():
    redis = create_autospec(RedisClient, instance=True)
    redis.set_if_not_exists = AsyncMock(return_value=True)
    redis.save_room_meta = AsyncMock()
    redis.save_questions = AsyncMock()
    return redis

@pytest.fixture
def mock_quiz_client():
    quiz_client = create_autospec(QuizServiceClient, instance=True)
    quiz_client.get_quiz_by_id = AsyncMock()
    return quiz_client

@pytest.mark.asyncio
async def test_create_room_success(mock_redis, mock_quiz_client):
    quiz_id = "quiz_123"
    user_id = "user_456"
    expected_room_code = "ABCDE"

    quiz_data = {
        "quizId": quiz_id,
        "title": "Test Quiz",
        "questions": [{"q": "test"}]
    }
    mock_quiz_client.get_quiz_by_id.return_value = quiz_data

    with patch("app.services.room_service.generate_room_code", return_value="ABCDE"):
        result = await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

    assert isinstance(result, RoomCreateResponse)
    assert result.room_id == expected_room_code

    mock_quiz_client.get_quiz_by_id.assert_called_once_with(quiz_id)

    mock_redis.set_if_not_exists.assert_called_once_with(
        key=f"room:{expected_room_code}:lock",
        value="1",
        ttl=3600
    )

    mock_redis.save_room_meta.assert_called_once_with(
        room_id=expected_room_code,
        owner_id=user_id,
        quiz_id=quiz_id,
        started=False,
        current_question_index=0,
        ttl_seconds=3600
    )

    mock_redis.save_questions.assert_called_once_with(
        room_id=expected_room_code,
        questions=quiz_data["questions"],
        ttl_seconds=3600
    )

@pytest.mark.asyncio
async def test_create_room_with_empty_questions(mock_redis, mock_quiz_client):
    quiz_id = "quiz_empty"
    user_id = "user_456"
    expected_room_code = "EMPTY"

    quiz_data = {
        "quizId": quiz_id,
        "title": "Empty Quiz"
    }
    mock_quiz_client.get_quiz_by_id.return_value = quiz_data

    with patch("app.services.room_service.generate_room_code", return_value=expected_room_code):
        result = await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

    assert result.room_id == expected_room_code
    mock_redis.save_questions.assert_called_once_with(
        room_id=expected_room_code,
        questions=[],
        ttl_seconds=3600
    )

@pytest.mark.asyncio
async def test_create_room_raises_http_404_when_quiz_not_found(mock_redis, mock_quiz_client):
    quiz_id = "non_existent_quiz"
    user_id = "user_456"
    mock_quiz_client.get_quiz_by_id.side_effect = QuizNotFoundError()

    with pytest.raises(QuizNotFoundError) as exc_info:
        await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

    assert exc_info.value.status_code == 404
    assert "The requested quiz does not exist." in exc_info.value.detail

    mock_redis.set_if_not_exists.assert_not_called()
    mock_redis.save_room_meta.assert_not_called()

@pytest.mark.asyncio
async def test_create_room_raises_runtime_error_when_room_code_collision_occurs(mock_redis, mock_quiz_client):
    quiz_id = "quiz_123"
    user_id = "user_456"

    quiz_data = {
        "quizId": quiz_id,
        "questions": []
    }
    mock_quiz_client.get_quiz_by_id.return_value = quiz_data

    mock_redis.set_if_not_exists.return_value = False

    with pytest.raises(RuntimeError) as exc_info:
        await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

        assert "Unable to generate a unique room_id" in str(exc_info.value)
        assert mock_redis.set_if_not_exists.call_count == 5
        mock_redis.save_room_meta.assert_not_called()