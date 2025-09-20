from uuid import UUID
from pydantic import BaseModel, ConfigDict

class Secret_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    name:str
    content:str


class Match_Secret_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    secret_id:UUID
    match_id:UUID
    player_id:UUID
    is_revealed:bool