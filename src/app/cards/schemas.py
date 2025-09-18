from uuid import UUID
from pydantic import BaseModel, ConfigDict

class Card_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    name:str
    description:str


class Match_Card_Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    card_id:UUID
    match_id:UUID
    player_id:UUID
    is_discarded:bool