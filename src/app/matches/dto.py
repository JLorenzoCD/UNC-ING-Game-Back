"""" Defines data transfer objecs for Match (DTO) """
from dataclasses import dataclass
from uuid import UUID

@dataclass
class MatchDTO:
    name: str
    min_player: int
    max_player: int
    owner_id: UUID
    