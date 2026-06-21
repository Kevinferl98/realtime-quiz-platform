import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_quiz_service, get_current_user

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture
def mock_service():
    return MagicMock()

@pytest.fixture(autouse=True)
def setup_dependency_overrides(mock_service):
    app.dependency_overrides[get_quiz_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "user_123",
        "preferred_username": "test_user"
    }
    yield
    app.dependency_overrides = {}