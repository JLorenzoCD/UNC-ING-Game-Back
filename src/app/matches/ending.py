from uuid import UUID
from enum import Enum
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from app.matches.models import MatchStatus

class MatchEndedReason(Enum):
    DECK_FINISHED = "deck_finished"
    MURDERER_REVEALED = "murderer_revealed"

class MatchEnded(Exception):
    def __init__(self, match_id: UUID, reason: MatchEndedReason,
                 murderer_name: str, accomplice_name: Optional[str] = None):
        self.match_id = match_id
        self.reason = reason
        self.murderer_name = murderer_name
        self.accomplice_name = accomplice_name

async def handle_match_ended(db, manager, match_id: UUID,
                             reason: MatchEndedReason,
                             murderer_name: str,
                             accomplice_name: Optional[str]):
    #imports locales para no destruir todo con dependencia circulares
    from app.matches.services import MatchService
    from websocketManager.ws_messages import WSEvent, make_ws_message

    try:
        MatchService(db).update_status_match(match_id, MatchStatus.COMPLETED)
    except SQLAlchemyError:
        pass
    if accomplice_name:
        payload = {
            "match_id": str(match_id),
            "reason": str(reason.value),
            "details": f"The murderer was {murderer_name} and the accomplice was {accomplice_name}"
        }
    else:
        payload = {
            "match_id": str(match_id),
            "reason": str(reason.value),
            "details": f"The murderer was {murderer_name}"
        }
    try:
        await manager.specificBroadcast(make_ws_message(WSEvent.MATCH_ENDED, payload), match_id)
    except Exception:
        pass

    try:
         manager.close_match(match_id)
    except Exception:
        pass
    
    return payload