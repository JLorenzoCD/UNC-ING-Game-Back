from dataclasses import dataclass
from uuid import UUID

"\nDefines data transfer objects for Match (DTO)\n"


@dataclass
class MatchDTO:
    name: str
    min_players: int
    max_players: int
    owner_id: UUID
    password: str | None = None
