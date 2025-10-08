from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.sets.models import SetType

class SetIn (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    player_id: UUID
    
class SetOut (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: SetType
    player_id: UUID
    match_id: UUID