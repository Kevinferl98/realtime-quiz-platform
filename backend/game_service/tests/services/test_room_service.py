import pytest
from unittest.mock import patch, create_autospec
from app.exception import QuizNotFoundError, QuizEmptyError, CreateRoomError
from app.schemas.multiplayer import RoomCreateResponse
from app.services.quiz_grpc_client import QuizServiceClient
from app.services.redis_client import RedisClient
from app.services.room_service import create_room

@pytest.fixture
def mock_redis():
    return create_autospec(RedisClient, instance=True)

@pytest.fixture
def mock_quiz_client():
    return create_autospec(QuizServiceClient, instance=True)

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

    mock_redis.create_room.assert_called_once_with(
        room_id=expected_room_code,
        owner_id=user_id,
        quiz_id=quiz_id,
        questions=quiz_data["questions"],
        ttl_seconds=3600
    )

@pytest.mark.asyncio
async def test_create_room_with_empty_questions(mock_redis, mock_quiz_client):
    quiz_id = "quiz_empty"
    user_id = "user_456"

    quiz_data = {
        "quizId": quiz_id,
        "title": "Empty Quiz"
    }
    mock_quiz_client.get_quiz_by_id.return_value = quiz_data

    with pytest.raises(QuizEmptyError) as exc_info:
        result = await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

    assert exc_info.value.status_code == 500
    assert "The requested quiz has no questions." in exc_info.value.detail

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

@pytest.mark.asyncio
async def test_create_room_raises_runtime_error_when_room_code_collision_occurs(mock_redis, mock_quiz_client):
    quiz_id = "quiz_123"
    user_id = "user_456"

    quiz_data = {
        "quizId": quiz_id,
        "questions": [{"q": "test"}]
    }
    mock_quiz_client.get_quiz_by_id.return_value = quiz_data

    mock_redis.create_room.return_value = False

    with pytest.raises(CreateRoomError) as exc_info:
        await create_room(
            redis=mock_redis,
            quiz_id=quiz_id,
            user_id=user_id,
            quiz_client=mock_quiz_client
        )

        assert "Unable to create a room." in str(exc_info.value)