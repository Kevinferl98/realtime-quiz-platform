from pydantic import BaseModel
from enum import StrEnum

class RoomCreateResponse(BaseModel):
    room_id: str

class RoomStatus(StrEnum):
    CREATED = "CREATED"
    STARTED = "STARTED"
    CANCELLED = "CANCELLED"
    FINISHED = "FINISHED"
    ERROR = "ERROR"

class Room(BaseModel):
    room_id: str
    owner_id: str
    quiz_id: str
    current_question_index: int
    status: RoomStatus

class Question(BaseModel):
    id: int
    question_text: str
    options: list[str]
    correct_option: str

class RoomAnswer(BaseModel):
    answer: str
    timestamp: float