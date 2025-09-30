from uuid import UUID
from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.matches.models import MatchStatus
from app.matches.dto import MatchDTO
from app.secrets.models import Secret_Type
from app.cards.models import Card_Type


class MatchIn(BaseModel):
    name:        str
    min_players: int
    max_players: int
    owner_id:    UUID

    def to_dto(self) -> MatchDTO:
        return MatchDTO(
            name        = self.name,
            min_players = self.min_players,
            max_players = self.max_players,
            owner_id    = self.owner_id
        )


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:                   UUID
    name:                 str
    status:               MatchStatus
    min_players:          int
    max_players:          int
    owner_id:             UUID
    current_player_order: int


class MatchResponse(BaseModel):
    id: UUID


class Match_Player_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    player_id: UUID
    match_id:  UUID
    role:      str
    order:     int


class Players_by_Match_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:        UUID
    player_id: UUID
    match_id:  UUID
    role:      Optional[str] = None
    order:     int
    name:      str
    avatar:    str
    birthday:  date


class Cards_by_Match_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:           UUID
    card_id:      UUID
    match_id:     UUID
    player_id:    Optional[UUID] = None
    is_discarded: bool
    name:         str
    type:         Card_Type
    description:  str


class Secrets_by_Match_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    secret_id:   UUID
    match_id:    UUID
    player_id:   Optional[UUID] = None
    is_revealed: bool
    type:        Secret_Type
    content:     str


class Match_number_of_Player(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id:                   UUID
    name:                 str
    status:               MatchStatus
    min_players:          int
    max_players:          int
    owner_id:             UUID
    current_player_order: int
    current_player_count: int