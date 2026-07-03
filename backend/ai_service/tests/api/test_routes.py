import pytest
from fastapi import FastAPI, status
from starlette.testclient import TestClient
from app.api.routes import router
from app.exception import AIProviderError, DomainError
from app.exception_handlers import domain_error_handler
from app.schemas.generation import QuizGenerateResponse
from app.services.quiz_generator_service import QuizGeneratorService
from unittest.mock import create_autospec
from app.dependencies import get_quiz_service

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(DomainError, domain_error_handler)
    return app

@pytest.fixture
def mock_quiz_generator_service():
    return create_autospec(QuizGeneratorService)

@pytest.fixture
def client(test_app, mock_quiz_generator_service):
    test_app.dependency_overrides[get_quiz_service] = lambda: mock_quiz_generator_service

    with TestClient(app=test_app) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()

@pytest.fixture
def valid_payload():
    return {
        "topic": "FastAPI Testing",
        "num_questions": 3,
        "difficulty": "medium"
    }

def test_generate_quiz_success(client, mock_quiz_generator_service, valid_payload):
    mock_response_data = {
        "title": "Quiz",
        "description": None,
        "questions": [
            {"question_text": "Question text", "options": ["A", "B", "C", "D"], "correct_answer": "A"}
        ]
    }

    mock_quiz_generator_service.generate_quiz_preview.return_value = QuizGenerateResponse(**mock_response_data)

    response = client.post("/v1/ai/generate", json=valid_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_response_data

    mock_quiz_generator_service.generate_quiz_preview.assert_called_once()

def test_generate_quiz_invalid_request_schema(client):
    bad_payload = {"difficulty": "hard"}

    response = client.post("/v1/ai/generate", json=bad_payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_generate_quiz_propagates_domain_errors(client, mock_quiz_generator_service, valid_payload):
    mock_quiz_generator_service.generate_quiz_preview.side_effect = AIProviderError(
        status_code=status.HTTP_502_BAD_GATEWAY,
        title="AI Provider Failure",
        detail="The upstream AI engine failed to process the request."
    )

    response = client.post("/v1/ai/generate", json=valid_payload)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY