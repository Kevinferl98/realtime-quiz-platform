import pytest
import jwt
from fastapi import HTTPException
from unittest.mock import patch
from fastapi.security import HTTPAuthorizationCredentials
from app.dependencies import get_current_user

def create_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

@patch("app.core.security.decode_access_token")
def test_get_current_user_invalid_token_format(mock_decode):
    mock_decode.side_effect = Exception("Invalid token format")

    creds = create_credentials("InvalidFormat token123")

    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or expired token"

@patch("app.dependencies.decode_access_token")
def test_get_current_user_success(mock_decode_token):
    expected_payload = {
        "sub": "user_123",
        "email": "test@example.com",
        "preferred_username": "john.doe"
    }
    mock_decode_token.return_value = expected_payload

    creds = create_credentials("fake-token-123")
    result = get_current_user(creds)

    assert result == expected_payload
    mock_decode_token.assert_called_once_with("fake-token-123")

@patch("app.dependencies.decode_access_token")
def test_get_current_user_jwks_error(mock_decode_token):
    mock_decode_token.side_effect = Exception("JWKS endpoint unreachable")

    creds = create_credentials("some-token")

    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or expired token"

@patch("app.dependencies.decode_access_token")
def test_get_current_user_expired_token(mock_decode_token):
    mock_decode_token.side_effect = jwt.ExpiredSignatureError("Token expired")

    creds = create_credentials("expired-token")

    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or expired token"