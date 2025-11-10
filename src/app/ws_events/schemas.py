
import datetime

from pydantic import BaseModel, ConfigDict

class WsEventOut (BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    payload: dict
    send_at: datetime.datetime