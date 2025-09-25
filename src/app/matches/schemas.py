from uuid import UUID
from app.matches.models import MatchStatus
from pydantic import BaseModel, ConfigDict
from app.matches.dto import MatchDTO

class MatchIn(BaseModel):
    name: str
    min_players: int
    max_players: int
    owner_id: UUID
    
    def to_dto(self) -> MatchDTO:
        return MatchDTO(
            name = self.name,
            min_players = self.min_players,
            max_players = self.max_players,
            owner_id = self.owner_id
        )

class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    status: MatchStatus
    min_players: int
    max_players: int
    owner_id: UUID
    current_player_order: int
    
class MatchResponse(BaseModel):
    id: UUID

class Match_Player_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    player_id: UUID
    match_id: UUID
    role: str
    order: int