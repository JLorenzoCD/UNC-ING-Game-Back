"""
Test específicos para el campo discarded_at del modelo Match_Card.

Estos tests verifican que el nuevo campo discarded_at se actualice
correctamente cuando se descartan cartas.
"""

import pytest
from datetime import datetime, date
from uuid import uuid4
from unittest.mock import patch

from app.cards.models import Card, Match_Card, Card_Type
from app.player.models import Player
from app.matches.models import Match, MatchStatus
from app.matches.services import PileService


class TestMatchCardDiscardedAt:
    """Tests para verificar el comportamiento del campo discarded_at"""

    @pytest.fixture
    def setup_data(self, db):
        """Setup básico: crea player, match y cards para los tests"""
        # Crear player
        player = Player(
            name="Test Player", 
            avatar="test_avatar", 
            birthday=date(2000, 1, 1)
        )
        db.add(player)
        db.commit()
        db.refresh(player)

        # Crear match
        match = Match(
            name="Test Match",
            status=MatchStatus.IN_PROGRESS,
            owner_id=player.id
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        # Crear cartas
        cards = []
        for i in range(3):
            card = Card(
                name=f"Test Card {i}",
                type=Card_Type.EVENT,
                description=f"Test card description {i}"
            )
            cards.append(card)
        
        db.add_all(cards)
        db.commit()

        # Crear match_cards asignadas al jugador
        match_cards = []
        for card in cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=match.id,
                player_id=player.id,
                is_discarded=False,
                discarded_at=None
            )
            match_cards.append(match_card)
        
        db.add_all(match_cards)
        db.commit()

        return {
            'player': player,
            'match': match,
            'cards': cards,
            'match_cards': match_cards,
            'db': db
        }

    def test_match_card_created_with_null_discarded_at(self, setup_data):
        """Test que verifica que las nuevas match_cards tienen discarded_at=None"""
        match_cards = setup_data['match_cards']
        
        for match_card in match_cards:
            assert match_card.discarded_at is None
            assert match_card.is_discarded is False

    def test_discard_cards_sets_discarded_at(self, setup_data):
        """Test que verifica que discard_cards actualiza el campo discarded_at"""
        db = setup_data['db']
        player = setup_data['player']
        match_cards = setup_data['match_cards']
        
        # Crear PileService
        pile_service = PileService(db)
        
        # Obtener algunas cartas para descartar
        cards_to_discard = [match_cards[0].id, match_cards[1].id]
        
        # Timestamp antes de descartar
        before_discard = datetime.now()
        
        # Descartar cartas
        pile_service.discard_cards(player.id, cards_to_discard)
        
        # Timestamp después de descartar
        after_discard = datetime.now()
        
        # Verificar que las cartas descartadas tienen discarded_at actualizado
        db.refresh(match_cards[0])
        db.refresh(match_cards[1])
        db.refresh(match_cards[2])
        
        # Cartas descartadas deben tener discarded_at
        assert match_cards[0].discarded_at is not None
        assert match_cards[1].discarded_at is not None
        assert match_cards[0].is_discarded is True
        assert match_cards[1].is_discarded is True
        assert match_cards[0].player_id is None
        assert match_cards[1].player_id is None
        
        # Carta no descartada debe seguir con discarded_at=None
        assert match_cards[2].discarded_at is None
        assert match_cards[2].is_discarded is False
        assert match_cards[2].player_id == player.id
        
        # Verificar que el timestamp está en el rango esperado
        assert before_discard <= match_cards[0].discarded_at <= after_discard
        assert before_discard <= match_cards[1].discarded_at <= after_discard

    def test_discard_cards_with_specific_datetime(self, setup_data):
        """Test que verifica que discarded_at se asigna correctamente con datetime mock"""
        db = setup_data['db']
        player = setup_data['player']
        match_cards = setup_data['match_cards']
        
        # Mock datetime para tener un timestamp específico
        mock_datetime = datetime(2024, 1, 15, 10, 30, 45)
        
        with patch('app.matches.services.datetime') as mock_dt:
            mock_dt.now.return_value = mock_datetime
            
            pile_service = PileService(db)
            pile_service.discard_cards(player.id, [match_cards[0].id])
        
        # Verificar que el timestamp es exactamente el mockeado
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at == mock_datetime
        assert match_cards[0].is_discarded is True
        assert match_cards[0].player_id is None

    def test_discard_cards_only_own_cards(self, setup_data):
        """Test que verifica que solo se pueden descartar cartas propias"""
        db = setup_data['db']
        player = setup_data['player']
        match_cards = setup_data['match_cards']
        
        # Crear otro jugador
        other_player = Player(
            name="Other Player", 
            avatar="other_avatar", 
            birthday=date(2000, 1, 2)
        )
        db.add(other_player)
        db.commit()
        
        pile_service = PileService(db)
        
        # Intentar descartar carta de otro jugador (cambiamos owner primero)
        match_cards[0].player_id = other_player.id
        db.commit()
        
        # Intentar descartar con el player original (no debería funcionar)
        pile_service.discard_cards(player.id, [match_cards[0].id])
        
        # Verificar que la carta NO se descartó
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at is None
        assert match_cards[0].is_discarded is False
        assert match_cards[0].player_id == other_player.id

    def test_discard_cards_multiple_times_updates_timestamp(self, setup_data):
        """Test que verifica que re-descartar una carta actualiza el timestamp"""
        db = setup_data['db']
        player = setup_data['player']
        match_cards = setup_data['match_cards']
        
        pile_service = PileService(db)
        
        # Primera descarte
        first_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        with patch('app.matches.services.datetime') as mock_dt:
            mock_dt.now.return_value = first_timestamp
            pile_service.discard_cards(player.id, [match_cards[0].id])
        
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at == first_timestamp
        
        # Simular que la carta vuelve al jugador
        match_cards[0].player_id = player.id
        match_cards[0].is_discarded = False
        db.commit()
        
        # Segunda descarte con timestamp diferente
        second_timestamp = datetime(2024, 1, 2, 12, 0, 0)
        with patch('app.matches.services.datetime') as mock_dt:
            mock_dt.now.return_value = second_timestamp
            pile_service.discard_cards(player.id, [match_cards[0].id])
        
        # Verificar que el timestamp se actualizó
        db.refresh(match_cards[0])
        assert match_cards[0].discarded_at == second_timestamp
        assert match_cards[0].is_discarded is True

    def test_match_card_schema_includes_discarded_at(self, setup_data):
        """Test que verifica que el schema incluye el campo discarded_at"""
        from app.cards.schemas import Match_Card_Schema
        
        db = setup_data['db']
        match_card = setup_data['match_cards'][0]
        
        # Asignar un timestamp
        test_timestamp = datetime(2024, 1, 15, 14, 30, 0)
        match_card.discarded_at = test_timestamp
        db.commit()
        db.refresh(match_card)
        
        # Crear schema desde el modelo
        schema = Match_Card_Schema.model_validate(match_card)
        
        # Verificar que el campo está incluido
        assert hasattr(schema, 'discarded_at')
        assert schema.discarded_at == test_timestamp
        
        # Verificar serialización
        schema_dict = schema.model_dump()
        assert 'discarded_at' in schema_dict
        assert schema_dict['discarded_at'] == test_timestamp