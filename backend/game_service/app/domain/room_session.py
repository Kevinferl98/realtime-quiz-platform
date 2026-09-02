from typing import Optional
from app.schemas.auth import AccessTokenPayload

class RoomSession:
    def __init__(self, player_id: str, role: str, username: Optional[str] = None, user_payload: Optional[AccessTokenPayload] = None):
        self.player_id = player_id
        self.username = username
        self.role = role
        self.user_payload = user_payload

    @property
    def is_host(self) -> bool:
        return self.role == "host"
    
    @property
    def is_authenticated(self) -> bool:
        return self.user_payload is not None
    
    @property
    def is_guest(self) -> bool:
        return not self.is_authenticated
    
    def set_username(self, username: str) -> None:
        self.username = username