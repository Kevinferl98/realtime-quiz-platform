import uuid
from my_observability import get_logger
from app.schemas.auth import WSTicketResponse, AccessTokenPayload, WSTicket
from app.services.redis.redis_client import RedisClient

logger = get_logger(__name__)

TICKET_TTL_SECONDS = 10

async def create_ws_ticket(redis: RedisClient, user: AccessTokenPayload, room_id: str) -> WSTicketResponse:
    """Generates a short-lived single-use ticket for WebSocket authentication."""
    ticket_id = str(uuid.uuid4())
    ticket = WSTicket(
        player_id=user.sub,
        username=user.preferred_username,
        user_payload=user,
        room_id=room_id
    )

    await redis.save_ticket(ticket_id, ticket)

    return WSTicketResponse(ticket=ticket_id, expires_in=TICKET_TTL_SECONDS)