from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.sets.models import SetType


class MatchSetIn(BaseModel):
    """Class MatchSetIn."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    player_id: UUID


class MatchSetOut(BaseModel):
    """Class MatchSetOut."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: SetType
    player_id: UUID
    match_id: UUID
    quin_play: bool
    quin_count: int


class SetIn(BaseModel):
    """Class SetIn."""

    type: SetType
    card_ids: List[UUID]
    player_id: UUID
    target_player_id: UUID
    target_secret_id: Optional[UUID] = None


class AddSetIn(BaseModel):
    """Class AddSetIn."""

    card_ids: List[UUID]
    player_id: UUID
    target_player_id: UUID
    target_secret_id: Optional[UUID] = None


class stoleSetIn(BaseModel):
    """Class stoleSetIn."""

    player_id: UUID
    target_player_id: UUID
    target_secret_id: Optional[UUID] = None
