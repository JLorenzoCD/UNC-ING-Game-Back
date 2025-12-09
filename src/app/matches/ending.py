from enum import Enum
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.matches.models import Match, MatchStatus


class MatchEndedReason(Enum):
    """Class MatchEndedReason."""

    DECK_FINISHED = "deck_finished"
    MURDERER_REVEALED = "murderer_revealed"
    SOCIAL_DISGRACE = "social_disgrace"


async def handle_match_ended(db, manager, match_id: UUID, reason: MatchEndedReason):
    """Handle match ended.

    Args:
        db: Parameter db.
        manager: Parameter manager.
        match_id: Parameter match_id.
        reason: Parameter reason."""
    from app.matches.services import MatchService
    from app.secrets.services import Secrets_Services
    from websocketManager.ws_messages import WSEvent, make_ws_message

    try:
        match_row = db.query(Match).filter(Match.id == match_id).first()
    except SQLAlchemyError as e:
        raise e
    if match_row is None:
        return None
    if match_row.status == MatchStatus.COMPLETED:
        return None
    info = Secrets_Services(db).get_full_info(match_id)
    try:
        MatchService(db).update_status_match(match_id, MatchStatus.COMPLETED)
    except SQLAlchemyError as e:
        raise e
    if not info:
        return None
    detailstmp = ""
    if reason == MatchEndedReason.MURDERER_REVEALED:
        if info["accomplice_name"]:
            detailstmp = f"The murderer was revealed. {info['murderer_name']} was the murderer and {info['accomplice_name']} was his accomplice"
        else:
            detailstmp = (
                f"The murderer was revealed. {info['murderer_name']} was the murderer"
            )
    elif reason == MatchEndedReason.SOCIAL_DISGRACE:
        if info["accomplice_name"]:
            detailstmp = f"Everyone is in social disgrace! The murderer {info['murderer_name']} wins with his accomplice {info['accomplice_name']}"
        else:
            detailstmp = f"Everyone is in social disgrace! The murderer {info['murderer_name']} wins"
    elif info["accomplice_name"]:
        detailstmp = f"The murderer {info['murderer_name']} escaped!. He was helped by his accomplice {info['accomplice_name']}"
    else:
        detailstmp = f"The murderer {info['murderer_name']} escaped!."
    payload = {
        "match_id": str(match_id),
        "secret_murderer_id": str(info["murderer_secret_id"]),
        "secret_accomplice_id": (
            str(info["accomplice_secret_id"]) if info["accomplice_secret_id"] else None
        ),
        "reason": reason.value,
        "details": detailstmp,
    }
    try:
        await manager.specificBroadcast(
            make_ws_message(WSEvent.MATCH_COMPLETED, payload), match_id
        )
    except Exception as e:
        print(f"Error al enviar WS: {e}")
    try:
        manager.close_match(match_id)
    except Exception as e:
        print(f"Error al cerrar la partida: {e}")
    return payload
