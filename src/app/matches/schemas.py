from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, Field

from app.cards.models import Card_Type
from app.matches.dto import MatchDTO
from app.matches.models import MatchStatus
from app.secrets.models import Secret_Type


class MatchIn(BaseModel):
    """Class MatchIn."""

    name: str
    min_players: int
    max_players: int
    owner_id: UUID
    password: Optional[str] = None

    def to_dto(self) -> MatchDTO:
        return MatchDTO(
            name=self.name,
            min_players=self.min_players,
            max_players=self.max_players,
            owner_id=self.owner_id,
            password=self.password
        )


class MatchOut(BaseModel):
    """Class MatchOut."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: MatchStatus
    min_players: int
    max_players: int
    owner_id: UUID
    current_player_order: int
    timer_turn: Optional[datetime]

    # Campo que no se va a enviar
    password: Optional[str] = Field(exclude=True, default=None)

    @computed_field
    @property
    def is_private(self) -> bool:
        return self.password is not None


class MatchResponse(BaseModel):
    """Class MatchResponse."""

    id: UUID


class MatchJoinIn(BaseModel):
    password: Optional[str] = None


class Match_Player_Schema(BaseModel):
    """Class Match_Player_Schema."""

    model_config = ConfigDict(from_attributes=True)
    player_id: UUID
    match_id: UUID
    role: str
    order: int


class Players_by_Match_Schema(BaseModel):
    """Class Players_by_Match_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    player_id: UUID
    match_id: UUID
    role: Optional[str] = None
    order: int
    name: str
    avatar: str
    birthday: date


class Cards_by_Match_Schema(BaseModel):
    """Class Cards_by_Match_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    card_id: UUID
    match_id: UUID
    player_id: Optional[UUID] = None
    is_discarded: bool
    discarded_at: Optional[datetime] = None
    name: str
    type: Card_Type
    description: str


class Secrets_by_Match_Schema(BaseModel):
    """Class Secrets_by_Match_Schema."""

    model_config = ConfigDict(from_attributes=True)
    secret_id: UUID
    match_id: UUID
    player_id: Optional[UUID] = None
    is_revealed: bool
    type: Secret_Type
    content: str


class Match_number_of_Player(BaseModel):
    """Class Match_number_of_Player."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: MatchStatus
    min_players: int
    max_players: int
    owner_id: UUID
    current_player_order: int
    current_player_count: int
    timer_turn: Optional[datetime]

    # Campo que no se va a enviar
    password: Optional[str] = Field(exclude=True, default=None)

    @computed_field
    @property
    def is_private(self) -> bool:
        return self.password is not None
