from uuid import UUID
from matches.models import MatchStatus
from pydantic import BaseModel, ConfigDict
from matches.dto import MatchDTO

class MatchIn(BaseModel):
    name: str
    min_player: int
    max_player: int
    owner_id: UUID
    
    def to_dto(self) -> MatchDTO:
        return MatchDTO(
            name = self.name,
            min_player = self.min_player,
            max_player = self.max_player,
            owner_id = self.owner_id
        )

class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    status: MatchStatus
    min_player: int
    max_player: int
    owner_id: UUID
    current_player_order: int
    
class MatchResponse(MatchOut):
    pass