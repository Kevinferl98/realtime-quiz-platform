from pydantic import BaseModel
from typing import Optional

class Player(BaseModel):
    player_id: str
    name: str
    score: int = 0
    current_answer: Optional[str] = None

class RoomCreateResponse(BaseModel):
    room_id: str