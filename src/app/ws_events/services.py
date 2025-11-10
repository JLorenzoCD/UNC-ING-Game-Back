
from datetime import datetime
from sqlalchemy import UUID

from app.events.models import EventosDeTurno
from app.ws_events.models import WsEvent


class WsEventsService:
    def __init__(self, db):
        self._db = db

    def create_event(self, match_id: UUID, message: str) -> WsEvent:
        event = WsEvent(
            match_id = match_id,
            message  = message,
            send_at  = datetime.now(),
        )
        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)
        return event

    def get_last_match_event(self, match_id: UUID) -> WsEvent | None:
        return (
            self._db.query(WsEvent)
            .filter(WsEvent.match_id == match_id)
            .order_by(WsEvent.send_at.desc())
            .first()
        )
