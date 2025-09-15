from pydantic import BaseModel
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

    class Config:
        orm_mode = True