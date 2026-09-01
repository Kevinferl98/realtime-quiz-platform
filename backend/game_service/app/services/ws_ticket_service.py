import uuid
from typing import Any
from my_observability import get_logger
from app.schemas.auth import WSTicketResponse
from app.services.redis.redis_client import RedisClient

logger = get_logger(__name__)

TICKET_TTL_SECONDS = 10

async def create_ws_ticket(redis: RedisClient, user: dict[str, Any]) -> WSTicketResponse:
    """Generates a short-lived single-use ticket for WebSocket authentication."""
    ticket_id = str(uuid.uuid4())
    ticket_data = {
        "player_id": user["sub"],
        "username": user.get("preferred_username"),
        "user_payload": user
    }

    await redis.save_ticket(ticket_id, ticket_data)

    return WSTicketResponse(ticket=ticket_id, expires_in=TICKET_TTL_SECONDS)