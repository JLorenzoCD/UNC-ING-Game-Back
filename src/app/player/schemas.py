from pydantic import BaseModel
from datetime import date


class PlayerIn(BaseModel):
    name: str
    avatar: str
    birthday: date


class PlayerOut(BaseModel):
    id: int
    name: str
    avatar: str
    birthday: date

    class Config:
        orm_mode = True