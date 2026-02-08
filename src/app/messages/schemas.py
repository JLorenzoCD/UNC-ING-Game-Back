from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.matches.models import MatchEventType


class MatchMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    match_id: UUID
    message: str
    created_at: datetime
    player_id: Optional[UUID]
    event_type: MatchEventType
    is_system_msg: bool


class MatchMessageIn(BaseModel):
    message: str
    player_id: UUID
