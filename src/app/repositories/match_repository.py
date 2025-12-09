from typing import List
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.cards.models import Card, Match_Card
from app.matches import schemas as match_schemas
from app.secrets.models import Match_Secret, Secret


class MatchRepository:
    """Repository for complex match queries with joins."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def get_cards_with_details(
        self, match_id: UUID
    ) -> List[match_schemas.Cards_by_Match_Schema]:
        """Get all cards in a match with detailed information."""
        try:
            results = (
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
                .filter(Match_Card.match_id == match_id)
                .order_by(Match_Card.id)
                .all()
            )
            combined: List[match_schemas.Cards_by_Match_Schema] = []
            for r in results:
                combined.append(
                    {
                        "id": r.id,
                        "card_id": r.card_id,
                        "match_id": r.match_id,
                        "player_id": r.player_id,
                        "is_discarded": r.is_discarded,
                        "discarded_at": r.discarded_at,
                        "name": r.name,
                        "type": r.type,
                        "description": r.description,
                    }
                )
            return combined
        except SQLAlchemyError as e:
            raise Exception(f"Database error: {str(e)}")

    def get_secrets_with_details(self, match_id: UUID):
        """Get all secrets in a match with detailed information."""
        results = (
            self._db.query(Match_Secret, Secret)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .all()
        )
        combined = []
        for ms, s in results:
            combined.append(
                {
                    "id": ms.id,
                    "secret_id": ms.secret_id,
                    "match_id": ms.match_id,
                    "player_id": ms.player_id,
                    "is_revealed": ms.is_revealed,
                    "type": s.type,
                    "content": s.content,
                }
            )
        return combined
