from uuid import UUID
from pydantic import BaseModel, ConfigDict

class MatchIn(BaseModel):
    name: str
    min_player: int
    max_player: int
    owner_id: UUID
    
    
class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    status: enumerate
    min_player: int
    max_player: int
    owner_id: UUID
    current_player_order: int
    
    