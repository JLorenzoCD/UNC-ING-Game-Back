import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class Player_Schema_in(BaseModel):
    """Class Player_Schema_in."""

    name: str
    avatar: str
    birthday: date


class Player_Schema_out(BaseModel):
    """Class Player_Schema_out."""

    id: uuid.UUID
    name: str
    avatar: str
    birthday: date
    model_config = ConfigDict(from_attributes=True)
