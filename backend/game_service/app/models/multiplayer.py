from dataclasses import dataclass
from enum import IntEnum

@dataclass(slots=True)
class Player:
    player_id: str
    name: str

@dataclass(slots=True)
class LeaderboardEntry:
    player_id: str
    name: str
    score: int

class SaveAnswerResult(IntEnum):
    ROOM_NOT_FOUND = 0
    SAVED = 1
    QUESTION_CLOSED = 2
    ALREADY_SUBMITTED = 3