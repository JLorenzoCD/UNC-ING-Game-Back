from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message

from app.matches import schemas as match_schemas
from app.logs.models import MatchLogs
from app.matches.utils import db_match_log_2_match_log_schema


class LogServices:
    """Service class for managing match logs."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def create_log(
        self,
        match_id: UUID,
        message: str,
        event_type: str,
        player_id: Optional[UUID] = None,
    ) -> UUID:
        """Create a new log entry for a match."""
        new_log = MatchLogs(
            match_id=match_id,
            message=message,
            event_type=event_type,
            player_id=player_id,
            created_at=datetime.now(),
        )
        try:
            self._db.add(new_log)
            self._db.commit()
            self._db.refresh(new_log)
            return new_log.id
        except Exception:
            self._db.rollback()
            raise

    def get_log_by_id(self, log_id: UUID) -> match_schemas.MatchLogOut:
        """Get a specific log by ID."""
        try:
            log = self._db.query(MatchLogs).filter(
                MatchLogs.id == log_id).first()
            return db_match_log_2_match_log_schema(log)
        except Exception:
            self._db.rollback()
            raise

    def get_logs_by_match(self, match_id: UUID) -> List[match_schemas.MatchLogOut]:
        """Get all logs for a match."""
        result = self._db.query(MatchLogs).filter(
            MatchLogs.match_id == match_id).all()
        return [db_match_log_2_match_log_schema(match_log) for match_log in result]

    async def create_and_propagate_log(
        self,
        match_id: UUID,
        message: str,
        event_type: str,
        player_id: Optional[UUID] = None,
    ):
        """Create a new log entry for a match and propagate by websockets"""

        new_log = MatchLogs(
            match_id=match_id,
            message=message,
            event_type=event_type,
            player_id=player_id,
            created_at=datetime.now(),
        )
        try:
            self._db.add(new_log)
            self._db.commit()
            self._db.refresh(new_log)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        log_out = db_match_log_2_match_log_schema(
            new_log).model_dump(mode="json")

        await manager.specificBroadcast(
            make_ws_message(WSEvent.LOG, log_out, match_id), match_id
        )
