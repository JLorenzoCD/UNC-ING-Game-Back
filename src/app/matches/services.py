from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.cards.models import Match_Card
from app.events.models import EventosDeTurno
from app.matches import schemas as match_schemas
from app.matches.models import Match, MatchStatus
from app.messages.models import MatchMessage
from app.matches.schemas import MatchOut
from app.matches.utils import db_match_2_match_schema
from app.player.models import Match_Player, Player
from app.repositories.match_repository import MatchRepository
from app.secrets.models import Match_Secret
from app.sets.models import Match_Set
from app.ws_events.models import WsEvent

from app.matches.exceptions import MatchNotFound, MatchValidationError, OwnerNotFound, PlayersInMatchNotFound, MatchInvalidAction


class MatchService:
    """Service class for core match operations."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db
        self._repository = MatchRepository(db)

    def _delete_match_completely(self, match_id: UUID) -> None:
        """Delete a match and all its related data from the database."""
        try:
            self._db.query(WsEvent).filter(
                WsEvent.match_id == match_id).delete()
            self._db.query(EventosDeTurno).filter(
                EventosDeTurno.match_id == match_id
            ).delete()
            self._db.query(Match_Secret).filter(
                Match_Secret.match_id == match_id
            ).delete()
            self._db.query(Match_Card).filter(
                Match_Card.match_id == match_id).delete()
            self._db.query(Match_Set).filter(
                Match_Set.match_id == match_id).delete()
            self._db.query(Match_Player).filter(
                Match_Player.match_id == match_id
            ).delete()
            self._db.query(MatchMessage).filter(
                MatchMessage.match_id == match_id).delete()
            self._db.query(Match).filter(Match.id == match_id).delete()
            self._db.commit()
        except SQLAlchemyError as exception:
            print(f"Error deleting match {match_id}: {exception}")
            self._db.rollback()
            raise exception

    def cancel_match(self, match_id: UUID, owner_id: UUID) -> MatchOut:
        """Cancel match.

        Args:
            match_id: Parameter match_id.
            owner_id: Parameter owner_id.

        Returns:
            Return value."""

        match: Match = self.get_match_by_id(match_id)

        if match.owner_id != owner_id:
            raise MatchValidationError(
                "Solo el propietario de la partida puede cancelarla."
            )
        if match.status != MatchStatus.WAITING:
            raise MatchValidationError(
                "Solo se pueden cancelar partidas en estado 'waiting'."
            )
        match_out = db_match_2_match_schema(match)
        self._delete_match_completely(match_id)
        return match_out

    def count_players_by_match(self, match_id: UUID) -> int:
        """Count the number of players in a match."""
        return (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .count()
        )

    def create(self, match_dto: match_schemas.MatchDTO) -> match_schemas.MatchOut:
        """Create a new match."""
        if match_dto.min_players < 2 or match_dto.max_players > 6:
            raise MatchValidationError("Incorrect number of players")
        owner: Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()
        new_match = Match(
            name=match_dto.name,
            password=match_dto.password,
            min_players=match_dto.min_players,
            max_players=match_dto.max_players,
            owner_id=owner.id,
            timer_turn=datetime.now(timezone.utc),
        )

        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        try:
            match_player = Match_Player(
                match_id=new_match.id, player_id=owner.id)
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        match_out = db_match_2_match_schema(new_match)
        return match_out

    def extended_match(
        self, match: Match
    ) -> match_schemas.Match_number_of_Player | None:
        """Create an extended match schema with player count."""
        match_out = db_match_2_match_schema(match)
        player_count = self.count_players_by_match(match.id)
        extended_match = match_schemas.Match_number_of_Player(
            **match_out.model_dump(),
            current_player_count=player_count,
            password=match_out.password,
        )
        return extended_match

    def get_active_matches_ids_player(self, player_id: UUID) -> List[UUID]:
        """Get active matches ids player.

        Args:
            player_id: Parameter player_id.

        Returns:
            Return value."""
        try:
            match_players = (
                self._db.query(Match_Player)
                .join(Match, Match_Player.match_id == Match.id)
                .filter(
                    Match_Player.player_id == player_id,
                    Match.status == MatchStatus.IN_PROGRESS,
                )
                .all()
            )
            return [mp.match_id for mp in match_players]
        except SQLAlchemyError:
            self._db.rollback()
            raise
        except Exception:
            raise

    def get_all(self) -> List[match_schemas.Match_number_of_Player]:
        """Get all matches with player count."""

        try:
            matches = self._db.query(Match).all()

            combined = []
            for match in matches:
                match_out = db_match_2_match_schema(match)
                player_count = self.count_players_by_match(match.id)

                print("=========================", match_out)
                extended_match = match_schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count,
                    password=match_out.password
                )
                combined.append(extended_match)
            return combined
        except Exception:
            self._db.rollback()
            raise

    def get_cards_by_match(
        self, match_id: UUID
    ) -> List[match_schemas.Cards_by_Match_Schema]:
        """Get all cards in a match with detailed information (uses repository)."""
        return self._repository.get_cards_with_details(match_id)

    def get_extended_cards_by_match(
        self, match_id: UUID, ids: List[UUID]
    ):
        """Get extended card information for specific cards in a match."""
        from app.cards.models import Card

        result = (
            self._db.query(
                Match_Card.id,
                Match_Card.card_id,
                Match_Card.match_id,
                Match_Card.player_id,
                Match_Card.is_discarded,
                Match_Card.discarded_at,
                Card.name,
                Card.type,
                Card.description,
            )
            .join(Card, Match_Card.card_id == Card.id)
            .filter(Match_Card.match_id == match_id, Match_Card.id.in_(ids))
            .all()
        )
        return result

    def get_match_by_id(self, match_id: UUID) -> Match:
        """Get a match by its ID."""
        match: Match = self._db.query(Match).filter(
            Match.id == match_id).first()

        if not match:
            raise MatchNotFound()

        return match

    def get_ongoing_matches_of_player(self, player_id: UUID) -> List[match_schemas.Match_number_of_Player]:

        try:
            matches = (
                self._db.query(Match)
                .join(Match_Player, Match_Player.match_id == Match.id)
                .filter(
                    Match_Player.player_id == player_id,
                    Match.status != MatchStatus.COMPLETED,
                )
                .all()
            )

            combined = []
            for match in matches:
                match_out = db_match_2_match_schema(match)
                player_count = self.count_players_by_match(match.id)

                extended_match = match_schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count,
                    password=match_out.password,
                )
                combined.append(extended_match)
            return combined
        except Exception:
            self._db.rollback()
            raise

    def get_players_by_match(
        self, match_id: UUID
    ) -> List[match_schemas.Players_by_Match_Schema]:
        """Get all players in a match."""

        match = self._db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise MatchNotFound()

        result = []
        try:
            for mp in match.match_players:
                result.append(
                    {
                        "id": mp.player.id,
                        "player_id": mp.player.id,
                        "match_id": mp.match.id,
                        "role": mp.role.value if mp.role else None,
                        "order": mp.order,
                        "name": mp.player.name,
                        "avatar": mp.player.avatar,
                        "birthday": mp.player.birthday,
                    }
                )
        except SQLAlchemyError:
            raise PlayersInMatchNotFound()
        except Exception:
            raise

        return result

    def get_players_from_match(self, match_id: UUID) -> list[Match_Player]:
        """Get all players from a match."""
        return list(
            self._db.query(Match_Player).filter(
                Match_Player.match_id == match_id).all()
        )

    def get_secrets_by_match(self, match_id: UUID):
        """Get all secrets in a match with detailed information (uses repository)."""
        return self._repository.get_secrets_with_details(match_id)

    def update_status_match(self, match_id: UUID, new_status: str) -> None:
        """Update the status of a match."""
        match: Match = self.get_match_by_id(match_id)
        if not match:
            raise MatchNotFound()
        match.status = new_status
        try:
            self._db.commit()
            self._db.refresh(match)
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception

    def is_timeout(self, match_id: UUID) -> bool:

        time_now = datetime.now(timezone.utc)
        match = self.get_match_by_id(match_id)
        if not match.timer_turn:
            raise MatchInvalidAction("El timer de la partida no está activo.")

        time_diff = (time_now - match.timer_turn).total_seconds()
        if time_diff <= 60:
            return False

        return True
