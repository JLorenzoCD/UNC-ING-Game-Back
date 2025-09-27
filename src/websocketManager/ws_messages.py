import json
from enum import Enum
from typing import Any,Dict

class WSEvent(str, Enum):
    MATCH = "match"
    PLAYER_JOIN = "player_join"
    TURN = "turn"

def make_ws_message(event: WSEvent, payload: Dict[str, Any] | int | str) -> str:
    message = {
        "event": event,
        "payload": payload
    }
    return json.dumps(message)

