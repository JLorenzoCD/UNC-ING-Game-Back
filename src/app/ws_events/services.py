from datetime import datetime

from sqlalchemy import UUID

from app.ws_events.models import WsEvent


class WsEventsService:
    """Class WsEventsService."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def create_event(self, match_id: UUID, message: str) -> WsEvent:
        """Create event.

        Args:
            match_id: Parameter match_id.
            message: Parameter message.

        Returns:
            Return value."""
        event = WsEvent(match_id=match_id, message=message,
                        send_at=datetime.now())
        self._db.add(event)
        self._db.commit()
        self._db.refresh(event)
        return event

    def get_last_match_event_no_log(self, match_id: UUID) -> WsEvent | None:
        """Get last match event. When last_event.message.event != "message"

        Args:
            match_id: Parameter match_id.

        Returns:
            Return value."""
        return (
            self._db.query(WsEvent)
            .filter(
                WsEvent.match_id == match_id,
                ~WsEvent.message.contains('"event": "message"')
            )
            .order_by(WsEvent.send_at.desc())
            .first()
        )
