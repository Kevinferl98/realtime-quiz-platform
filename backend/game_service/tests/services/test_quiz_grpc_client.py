import grpc.aio
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.exception import QuizNotFoundError
from app.services.grpc_generated import quiz_service_pb2
from app.services.quiz_grpc_client import QuizServiceClient

@pytest.fixture
def initialized_client():
    client = QuizServiceClient(host="localhost:50051")
    client._channel = MagicMock(spec=grpc.aio.Channel)
    client._stub = MagicMock()
    return client

@pytest.mark.asyncio
async def test_get_quiz_by_id_success(initialized_client):
    quiz_id = "quiz1"

    mock_question = MagicMock()
    mock_question.id = "q1"
    mock_question.question_text = "Question text"
    mock_question.options = ["A", "B", "C", "D"]
    mock_question.correct_option = 1

    mock_response = MagicMock()
    mock_response.quizId = quiz_id
    mock_response.title = "Test Quiz"
    mock_response.questions = [mock_question]

    initialized_client._stub.GetQuizById = AsyncMock(return_value=mock_response)

    result = await initialized_client.get_quiz_by_id(quiz_id)

    assert result == {
        "quizId": "quiz1",
        "title": "Test Quiz",
        "questions": [
            {
                "id": "q1",
                "question_text": "Question text",
                "options": ["A", "B", "C", "D"],
                "correct_option": 1,
            }
        ]
    }

    initialized_client._stub.GetQuizById.assert_called_once()
    called_args, called_kwargs = initialized_client._stub.GetQuizById.call_args

    assert isinstance(called_args[0], quiz_service_pb2.GetQuizRequest)
    assert called_args[0].quizId == quiz_id
    assert called_kwargs["timeout"] == 5.0

@pytest.mark.asyncio
async def test_get_quiz_by_id_raises_runtime_error_if_not_started():
    quiz_id = "any_id"
    uninitialized_client = QuizServiceClient()

    with pytest.raises(RuntimeError) as exc_info:
        await uninitialized_client.get_quiz_by_id(quiz_id)

    assert "QuizServiceClient is not initialized" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_quiz_by_id_raises_domain_exception_on_grpc_not_found(initialized_client):
    quiz_id = "missing_quiz"

    gprc_error = grpc.aio.AioRpcError(
        code=grpc.StatusCode.NOT_FOUND,
        initial_metadata=grpc.aio.Metadata(),
        trailing_metadata=grpc.aio.Metadata(),
        details="Quiz entity not found in the target database."
    )
    initialized_client._stub.GetQuizById = AsyncMock(side_effect=gprc_error)

    with pytest.raises(QuizNotFoundError) as exc_info:
        await initialized_client.get_quiz_by_id(quiz_id)

    assert exc_info.value.quiz_id == quiz_id

@pytest.mark.asyncio
async def test_get_quiz_by_id_raises_generic_grpc_errors(initialized_client):
    quiz_id = "quiz1"

    generic_grpc_error = grpc.aio.AioRpcError(
        code=grpc.StatusCode.INTERNAL,
        initial_metadata=grpc.aio.Metadata(),
        trailing_metadata=grpc.aio.Metadata(),
        details="Internal server error."
    )
    initialized_client._stub.GetQuizById = AsyncMock(side_effect=generic_grpc_error)

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await initialized_client.get_quiz_by_id(quiz_id)

    assert exc_info.value.code() == grpc.StatusCode.INTERNAL