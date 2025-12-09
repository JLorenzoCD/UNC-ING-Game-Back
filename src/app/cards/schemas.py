from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.cards.models import Card_Type


class Card_Schema(BaseModel):
    """Class Card_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    type: Card_Type
    description: str


class Match_Card_Schema(BaseModel):
    """Class Match_Card_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    card_id: UUID
    match_id: UUID
    player_id: Optional[UUID]
    is_discarded: bool
    discarded_at: Optional[datetime]


class take_Match_Cards_in(BaseModel):
    """Class take_Match_Cards_in."""

    player_id: UUID
    card_ids: List[UUID]


class discard_Match_Cards_in(BaseModel):
    """Class discard_Match_Cards_in."""

    player_id: UUID
    card_ids: List[UUID]
