import json
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class WSEvent(str, Enum):
    """Class WSEvent."""

    MATCH = "match"
    PLAYER_JOIN = "player_join"
    PLAYER_QUIT = "player_quit"
    TURN = "turn"
    CARDS = "cards"
    MATCH_COMPLETED = "match_completed"
    SET = "set"
    SECRET = "secret"
    PLAYER_SECRET_REVEAL = "player_secret_reveal"
    CARDS_DELETE = "cards_delete"
    CANCELLATION_WINDOW_OPEN = "cancellation_window_open"
    EVENT_CANCELLED = "event_cancelled"
    PENDING_TARGET_RESPONSE = "pending_target_response"
    CARD_EVENT = "card_event"
    LOG = "new_log"


def custom_encoder(o):
    """Custom encoder.

    Args:
        o: Parameter o."""
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(
        f"Object of type {o.__class__.__name__} is not JSON serializable")


def make_ws_message(event: WSEvent, payload: Dict[str, Any] | int | str, match_id: Optional[UUID] = None) -> str:
    """Make ws message.

    Args:
        event: Parameter event.
        payload: Parameter payload.

    Returns:
        Return value."""

    event_to_send = event.value
    if not match_id is None:
        event_to_send = f"{event_to_send}/{match_id}"

    message = {"event": event_to_send, "payload": payload}
    return json.dumps(message, default=custom_encoder)
