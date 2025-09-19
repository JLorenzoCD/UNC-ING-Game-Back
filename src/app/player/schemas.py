from pydantic import BaseModel, ConfigDict
from datetime import date
import uuid

class PlayerIn(BaseModel):
    name: str
    avatar: str
    birthday: date


class PlayerOut(BaseModel):
    id: uuid.UUID
    name: str
    avatar: str
    birthday: date

    model_config = ConfigDict(from_attributes=True)