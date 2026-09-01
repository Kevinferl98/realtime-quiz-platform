from pydantic import BaseModel

class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 10

class AccessTokenPayload(BaseModel):
    sub: str
    preferred_username: str | None = None

    iss: str | None = None
    aud: str | list[str] | None = None
    exp: int | None = None

    email: str | None = None

    model_config = {
        "extra": "allow"
    }

class WSTicket(BaseModel):
    player_id: str
    username: str | None = None
    user_payload: AccessTokenPayload | None
    room_id: str