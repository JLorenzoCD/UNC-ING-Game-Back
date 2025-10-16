from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.secrets.models import Secret_Type, Secret_action

class Secret_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    type:Secret_Type
    content:str


class Match_Secret_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    secret_id:UUID
    match_id:UUID
    player_id:UUID
    is_revealed:bool
    
class SecretUpdate(BaseModel):
    target_player_id: UUID
    action: Secret_action