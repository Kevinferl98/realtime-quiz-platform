import pytest
from unittest.mock import AsyncMock, create_autospec
from app.exception import AIProviderError
from app.prompts.prompt_manager import PromptTemplate, PromptManager
from app.schemas.generation import QuizGenerateRequest, QuizGenerateResponse
from app.services.quiz_generator_service import QuizGeneratorService
from ollama import ResponseError, RequestError
from fastapi import status

@pytest.fixture
def mock_ollama_client():
    return AsyncMock()

@pytest.fixture
def mock_prompt_template():
    template = create_autospec(PromptTemplate)
    template.system_prompt = "You are a helpful quiz generator."
    template.user_template = "Create a quiz about {topic} with {count} questions at {difficulty} level."
    return template

@pytest.fixture
def mock_prompt_manager(mock_prompt_template):
    manager = create_autospec(PromptManager)
    manager.get.return_value = mock_prompt_template
    return manager

@pytest.fixture
def quiz_service(mock_ollama_client, mock_prompt_manager):
    return QuizGeneratorService(
        ollama_client=mock_ollama_client,
        model_name="llama3",
        prompt_manager=mock_prompt_manager,
    )

@pytest.fixture
def valid_request():
    return QuizGenerateRequest(
        topic="Python Basics",
        num_questions=5,
        difficulty="easy"
    )

async def test_generate_quiz_preview_success(quiz_service, mock_ollama_client, valid_request):
    """
    Ensure a valid JSON response from Ollama is correctly
    parsed and returned as a QuizGenerateResponse instance.
    """
    mock_response_content = '{"title": "quiz", "questions": [{"question_text": "Question", "options": ["A", "B", "C", "D"], "correct_answer_index": 0}]}'

    mock_ollama_client.chat.return_value = {
        "message": {
            "content": mock_response_content
        }
    }

    result = await quiz_service.generate_quiz_preview(valid_request)

    assert isinstance(result, QuizGenerateResponse)
    mock_ollama_client.chat.assert_called_once_with(
        model="llama3",
        messages=[
            {"role": "system", "content": "You are a helpful quiz generator."},
            {"role": "user", "content": "Create a quiz about Python Basics with 5 questions at easy level."}
        ],
        options={"temperature": 0.7},
        stream=False,
        format=QuizGenerateResponse.model_json_schema()
    )

async def test_generate_quiz_preview_response_error(quiz_service, mock_ollama_client, valid_request):
    """
    Ensure ResponseError from Ollama raises a 502 Bad Gateway AIProviderError.
    """
    mock_ollama_client.chat.side_effect = ResponseError(
        error="Model not found",
        status_code=404
    )

    with pytest.raises(AIProviderError) as exc_info:
        await quiz_service.generate_quiz_preview(valid_request)

    assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc_info.value.title == "AI Provider Failure"

async def test_generate_quiz_preview_request_error(quiz_service, mock_ollama_client, valid_request):
    """
    Ensure RequestError (timeouts/network drops) raises a 504 Gateway Timeout AIProviderError.
    """
    mock_ollama_client.chat.side_effect = RequestError(
        error="Connection timed out"
    )

    with pytest.raises(AIProviderError) as exc_info:
        await quiz_service.generate_quiz_preview(valid_request)

    assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert exc_info.value.title == "AI Provider Timeout"

@pytest.mark.parametrize(
        "bad_ai_content",
        [
            "Not a JSON string at all",
            '{"invalid_field": "unrelated data"}',
            None
        ]
    )
async def test_generate_quiz_preview_parsing_and_validation_errors(quiz_service, mock_ollama_client, valid_request, bad_ai_content):
    """
    Ensure that broken JSON, invalid structures, or bad types from the LLM
    raise a 422 Unprocessable Entity AIProviderError.
    """
    mock_ollama_client.chat.return_value = {
        "message": {
            "content": bad_ai_content
        }
    }

    with pytest.raises(AIProviderError) as exc_info:
        await quiz_service.generate_quiz_preview(valid_request)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.title == "AI Validation Error"