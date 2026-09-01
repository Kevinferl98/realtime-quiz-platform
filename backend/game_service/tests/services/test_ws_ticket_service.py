import pytest
from unittest.mock import create_autospec
from app.services.redis.redis_client import RedisClient
from app.services.ws_ticket_service import create_ws_ticket
from app.schemas.auth import WSTicketResponse

@pytest.fixture
def mock_redis() -> RedisClient:
    return create_autospec(RedisClient, instance=True)

@pytest.mark.asyncio
async def test_create_ws_ticket_success(mock_redis: RedisClient):
    user_payload = {
        "sub": "user-123",
        "preferred_username": "John",
        "email": "john@email.com"
    }

    result = await create_ws_ticket(redis=mock_redis, user=user_payload)

    assert isinstance(result, WSTicketResponse)
    assert result.expires_in == 10

    mock_redis.save_ticket.assert_called_once_with(
        result.ticket,
        {
            "player_id": "user-123",
            "username": "John",
            "user_payload": user_payload
        }
    )

@pytest.mark.asyncio
async def test_create_ws_ticket_raises_key_error_when_sub_missing(mock_redis: RedisClient):
    user_payload = {"preferred_username": "John"}

    with pytest.raises(KeyError, match="sub"):
        await create_ws_ticket(redis=mock_redis, user=user_payload)

    mock_redis.save_ticket.assert_not_called()