from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.cards.models import Match_Card


class PileService:
    """Service class for managing the card pile."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def discard_cards(self, player_id: UUID, match_id: UUID, cards: list[UUID], delete=False) -> None:
        """Discard cards from player to the pile."""
        try:
            for card in cards:
                match_card = (
                    self._db.query(Match_Card).filter(
                        Match_Card.id == card).first()
                )
                if match_card and match_card.match_id == match_id:
                    if player_id is None or match_card.player_id == player_id:
                        if not delete:
                            match_card.player_id = None
                            match_card.is_discarded = True
                            match_card.discarded_at = datetime.now()
                        else:
                            self._db.delete(match_card)
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise

    def get_count_cards_pile(self, match_id: UUID) -> int:
        """Get the count of available cards in the pile."""
        return (
            self._db.query(Match_Card)
            .filter(
                Match_Card.match_id == match_id,
                Match_Card.player_id.is_(None),
                Match_Card.is_discarded.is_(False),
            )
            .count()
        )

    def take_cards(
        self, player_id: UUID, match_id: UUID, cards: list[UUID]
    ) -> Optional[Match_Card]:
        """Take cards from the pile and assign to player."""
        try:
            if not cards:
                return
            for card in cards:
                match_card: Match_Card = (
                    self._db.query(Match_Card).filter(
                        Match_Card.id == card).first()
                )
                if match_card and (
                    match_card.player_id is None and match_card.match_id == match_id
                ):
                    match_card.player_id = player_id
                    match_card.is_discarded = False
                    match_card.discarded_at = None
            self._db.commit()
            self._db.refresh(match_card)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return match_card
