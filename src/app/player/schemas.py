from pydantic import BaseModel, ConfigDict
from datetime import date
import uuid

class Player_Schema_in(BaseModel):
    name: str
    avatar: str
    birthday: date


class Player_Schema_out(BaseModel):
    id: uuid.UUID
    name: str
    avatar: str
    birthday: date

    model_config = ConfigDict(from_attributes=True)