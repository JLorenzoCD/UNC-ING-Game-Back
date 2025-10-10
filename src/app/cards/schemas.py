from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.cards.models import Card_Type


class Card_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id          : UUID
    name        : str
    type        : Card_Type
    description : str


class Match_Card_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id           : UUID
    card_id      : UUID
    match_id     : UUID
    player_id    : Optional[UUID]
    is_discarded : bool
    discarded_at : Optional[datetime]

class take_discard_Match_Cards_in(BaseModel):
    player_id         : UUID
    taken_card_ids    : List[UUID]
    discarded_card_ids: List[UUID]