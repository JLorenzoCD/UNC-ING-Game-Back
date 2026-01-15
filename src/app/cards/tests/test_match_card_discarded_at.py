from datetime import date, datetime
from unittest.mock import patch

import pytest

from app.cards.models import Card, Card_Type, Match_Card
from app.matches.models import Match, MatchStatus
from app.piles.services import PileServices
from app.player.models import Player

"\nTest específicos para el campo discarded_at del modelo Match_Card.\n\nEstos tests verifican que el nuevo campo discarded_at se actualice\ncorrectamente cuando se descartan cartas.\n"


class TestMatchCardDiscardedAt:
    """Tests para verificar el comportamiento del campo discarded_at"""

    @pytest.fixture
    def setup_data(self, db):
        """Setup básico: crea player, match y cards para los tests"""
        player = Player(
            name="Test Player", avatar="test_avatar", birthday=date(2000, 1, 1)
        )
        db.add(player)
        db.commit()
        db.refresh(player)
        match = Match(
            name="Test Match", status=MatchStatus.IN_PROGRESS, owner_id=player.id
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        cards = []
        for i in range(3):
            card = Card(
                name=f"Test Card {i}",
                type=Card_Type.EVENT,
                description=f"Test card description {i}",
            )
            cards.append(card)
        db.add_all(cards)
        db.commit()
        match_cards = []
        for card in cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=match.id,
                player_id=player.id,
                is_discarded=False,
                discarded_at=None,
            )
            match_cards.append(match_card)
        db.add_all(match_cards)
        db.commit()
        return {
            "player": player,
            "match": match,
            "cards": cards,
            "match_cards": match_cards,
            "db": db,
        }

    def test_discard_cards_multiple_times_updates_timestamp(self, setup_data):
        """Test que verifica que re-descartar una carta actualiza el timestamp"""
        db = setup_data["db"]
        player = setup_data["player"]
        match_cards = setup_data["match_cards"]
        pile_service = PileServices(db)
        first_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        with patch("app.piles.services.datetime") as mock_dt:
            mock_dt.now.return_value = first_timestamp
            pile_service.discard_cards(
                player.id, setup_data["match"].id, [match_cards[0].id]
            )
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at == first_timestamp
        match_cards[0].player_id = player.id
        match_cards[0].is_discarded = False
        db.commit()
        second_timestamp = datetime(2024, 1, 2, 12, 0, 0)
        with patch("app.piles.services.datetime") as mock_dt:
            mock_dt.now.return_value = second_timestamp
            pile_service.discard_cards(
                player.id, setup_data["match"].id, [match_cards[0].id]
            )
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at == second_timestamp
        assert match_cards[0].is_discarded is True

    def test_discard_cards_only_own_cards(self, setup_data):
        """Test que verifica que solo se pueden descartar cartas propias"""
        db = setup_data["db"]
        player = setup_data["player"]
        match_cards = setup_data["match_cards"]
        other_player = Player(
            name="Other Player", avatar="other_avatar", birthday=date(2000, 1, 2)
        )
        db.add(other_player)
        db.commit()
        pile_service = PileServices(db)
        match_cards[0].player_id = other_player.id
        db.commit()
        pile_service.discard_cards(
            player.id, setup_data["match"].id, [match_cards[0].id]
        )
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at is None
        assert match_cards[0].is_discarded is False
        assert match_cards[0].player_id == other_player.id

    def test_discard_cards_sets_discarded_at(self, setup_data):
        """Test que verifica que discard_cards actualiza el campo discarded_at"""
        db = setup_data["db"]
        player = setup_data["player"]
        match_cards = setup_data["match_cards"]
        pile_service = PileServices(db)
        cards_to_discard = [match_cards[0].id, match_cards[1].id]
        before_discard = datetime.now()
        pile_service.discard_cards(
            player.id, setup_data["match"].id, cards_to_discard)
        after_discard = datetime.now()
        db.refresh(match_cards[0])
        db.refresh(match_cards[1])
        db.refresh(match_cards[2])
        assert match_cards[0].discarded_at is not None
        assert match_cards[1].discarded_at is not None
        assert match_cards[0].is_discarded is True
        assert match_cards[1].is_discarded is True
        assert match_cards[0].player_id is None
        assert match_cards[1].player_id is None
        assert match_cards[2].discarded_at is None
        assert match_cards[2].is_discarded is False
        assert match_cards[2].player_id == player.id
        assert before_discard <= match_cards[0].discarded_at <= after_discard
        assert before_discard <= match_cards[1].discarded_at <= after_discard

    def test_match_card_created_with_null_discarded_at(self, setup_data):
        """Test que verifica que las nuevas match_cards tienen discarded_at=None"""
        match_cards = setup_data["match_cards"]
        for match_card in match_cards:
            assert match_card.discarded_at is None
            assert match_card.is_discarded is False
