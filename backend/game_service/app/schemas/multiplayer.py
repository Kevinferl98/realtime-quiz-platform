from pydantic import BaseModel

class RoomCreateResponse(BaseModel):
    room_id: str

class Room(BaseModel):
    room_id: str
    owner_id: str
    quiz_id: str
    current_question_index: int
    status: str

class Question(BaseModel):
    id: int
    question_text: str
    options: list[str]
    correct_option: str

class RoomAnswer(BaseModel):
    answer: str
    timestamp: float