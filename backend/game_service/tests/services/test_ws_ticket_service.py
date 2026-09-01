import pytest
from unittest.mock import create_autospec
from app.services.redis.redis_client import RedisClient
from app.services.ws_ticket_service import create_ws_ticket
from app.schemas.auth import WSTicketResponse, AccessTokenPayload, WSTicket

@pytest.fixture
def mock_redis() -> RedisClient:
    return create_autospec(RedisClient, instance=True)

@pytest.mark.asyncio
async def test_create_ws_ticket_success(mock_redis: RedisClient):
    user_payload = AccessTokenPayload(
        sub="user-123",
        preferred_username="John",
        email="john@email.com",
    )

    result = await create_ws_ticket(redis=mock_redis, user=user_payload, room_id="room-123")

    assert isinstance(result, WSTicketResponse)
    assert result.expires_in == 10

    expected_ticket = WSTicket(
        player_id="user-123",
        username="John",
        user_payload=user_payload,
        room_id="room-123"
    )

    mock_redis.save_ticket.assert_called_once_with(
        result.ticket,
        expected_ticket
    )