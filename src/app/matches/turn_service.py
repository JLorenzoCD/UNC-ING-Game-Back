from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.matches.models import Match, MatchStatus
from app.player.models import Match_Player


class TurnService:
    """Service for turn management in matches."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def get_current_player_by_match(self, match_id: UUID) -> Optional[UUID]:
        """Get the current player ID based on current_player_order."""
        from app.matches.services import MatchService

        try:
            match = MatchService(self._db).get_match_by_id(match_id)
            if match.current_player_order is None:
                return None
            current_player = (
                self._db.query(Match_Player)
                .filter(
                    Match_Player.match_id == match_id,
                    Match_Player.order == match.current_player_order,
                )
                .first()
            )
            return current_player.player_id if current_player else None
        except Exception:
            return None

    def pass_turn_by_id(self, match_id: UUID):
        """Pass the turn to the next player."""
        from app.matches.services import MatchNotFound, MatchService

        try:
            match = MatchService(self._db).get_match_by_id(match_id)
        except Exception:
            raise MatchNotFound
        count_players = MatchService(self._db).count_players_by_match(match_id)
        if match.status != MatchStatus.IN_PROGRESS:
            raise ValueError("The match is not in progress")
        if match.current_player_order is None:
            raise ValueError("current_player_order Invalid")
        if match.current_player_order >= count_players:
            match.current_player_order = 1
        else:
            match.current_player_order = match.current_player_order + 1
        match.timer_turn = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(match)

        return match
