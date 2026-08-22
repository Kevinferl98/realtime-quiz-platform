from dataclasses import dataclass

@dataclass(slots=True)
class Player:
    player_id: str
    name: str

@dataclass(slots=True)
class LeaderboardEntry:
    player_id: str
    name: str
    score: int