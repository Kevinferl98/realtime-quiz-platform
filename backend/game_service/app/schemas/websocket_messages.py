from pydantic import BaseModel, Field
from typing import Annotated, Literal, Union

# FE -> BE
class JoinAction(BaseModel):
    type: Literal["join"]
    name: str

class StartAction(BaseModel):
    type: Literal["start"]

class AnswerAction(BaseModel):
    type: Literal["answer"]
    answer: str

ClientMessage = Annotated[
    Union[JoinAction, StartAction, AnswerAction],
    Field(discriminator="type")
]

# BE -> FE
class RoleMessage(BaseModel):
    type: Literal["role"] = "role"
    role: str
    player_id: str

class PlayerJoinedMessage(BaseModel):
    type: Literal["player_joined"] = "player_joined"
    players: list[str]

class PlayerLeftMessage(BaseModel):
    type: Literal["player_left"] = "player_left"
    players: list[str]

class AnswerSubmittedMessage(BaseModel):
    type: Literal["answer_submitted"] = "answer_submitted"
    current_question_index: int
    player_id: str

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str