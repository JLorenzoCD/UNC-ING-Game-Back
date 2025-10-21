"""
Defines data transfer objects for Match (DTO)
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass
class MatchDTO:
    name:        str
    min_players: int
    max_players: int
    owner_id:    UUID