"""
Test de integración para verificar que el endpoint devuelve correctamente el campo discarded_at.

Estos tests verifican que el campo discarded_at se incluye en las respuestas
del endpoint cuando se obtienen las cartas de una partida.
"""

import pytest
from datetime import datetime, date
from uuid import uuid4

from app.cards.models import Card, Match_Card, Card_Type
from app.player.models import Player, Match_Player
from app.matches.models import Match, MatchStatus
from app.matches.services import MatchService


class TestDiscardedAtEndpointIntegration:
    """Tests de integración para verificar que el endpoint maneja correctamente discarded_at"""

    @pytest.fixture
    def setup_match_with_discarded_cards(self, db):
        """Setup que crea una partida con cartas descartadas y no descartadas"""
        # Crear owner
        owner = Player(
            name="Owner Player",
            avatar="owner_avatar", 
            birthday=date(2000, 1, 1)
        )
        db.add(owner)
        
        # Crear otro jugador
        other_player = Player(
            name="Other Player", 
            avatar="other_avatar", 
            birthday=date(2000, 1, 2)
        )
        db.add(other_player)
        db.commit()

        # Crear match
        match = Match(
            name="Test Match",
            status=MatchStatus.IN_PROGRESS,
            owner_id=owner.id
        )
        db.add(match)
        db.commit()

        # Agregar jugadores a la partida
        match_players = [
            Match_Player(player_id=owner.id, match_id=match.id, order=1),
            Match_Player(player_id=other_player.id, match_id=match.id, order=2)
        ]
        db.add_all(match_players)

        # Crear cartas
        cards = []
        for i in range(5):
            card = Card(
                name=f"Test Card {i}",
                type=Card_Type.EVENT,
                description=f"Test card description {i}"
            )
            cards.append(card)
        
        db.add_all(cards)
        db.commit()

        # Crear match_cards con diferentes estados
        match_cards = []
        
        # Carta del owner (no descartada)
        match_cards.append(Match_Card(
            card_id=cards[0].id,
            match_id=match.id,
            player_id=owner.id,
            is_discarded=False,
            discarded_at=None
        ))
        
        # Carta del otro jugador (no descartada)
        match_cards.append(Match_Card(
            card_id=cards[1].id,
            match_id=match.id,
            player_id=other_player.id,
            is_discarded=False,
            discarded_at=None
        ))
        
        # Carta descartada (con timestamp)
        discard_time = datetime(2024, 1, 15, 10, 30, 45)
        match_cards.append(Match_Card(
            card_id=cards[2].id,
            match_id=match.id,
            player_id=None,
            is_discarded=True,
            discarded_at=discard_time
        ))
        
        # Carta en el mazo (no asignada, no descartada)
        match_cards.append(Match_Card(
            card_id=cards[3].id,
            match_id=match.id,
            player_id=None,
            is_discarded=False,
            discarded_at=None
        ))
        
        # Otra carta descartada (con timestamp diferente)
        other_discard_time = datetime(2024, 1, 16, 14, 20, 30)
        match_cards.append(Match_Card(
            card_id=cards[4].id,
            match_id=match.id,
            player_id=None,
            is_discarded=True,
            discarded_at=other_discard_time
        ))
        
        db.add_all(match_cards)
        db.commit()

        return {
            'owner': owner,
            'other_player': other_player,
            'match': match,
            'cards': cards,
            'match_cards': match_cards,
            'discard_time': discard_time,
            'other_discard_time': other_discard_time
        }

    def test_match_service_get_cards_includes_discarded_at_field(self, setup_match_with_discarded_cards):
        """Test que verifica que MatchService.get_cards_by_match incluye el campo discarded_at"""
        setup = setup_match_with_discarded_cards
        match_id = setup['match'].id
        db = setup_match_with_discarded_cards['match'].__dict__['_sa_instance_state'].session
        
        service = MatchService(db)
        cards_data = service.get_cards_by_match(match_id)
        
        # Verificar que tenemos 5 cartas
        assert len(cards_data) == 5
        
        # Verificar que todas las cartas tienen el campo discarded_at
        for card in cards_data:
            assert "discarded_at" in card
        
        # Buscar cartas específicas por su estado
        discarded_cards = [c for c in cards_data if c["is_discarded"]]
        non_discarded_cards = [c for c in cards_data if not c["is_discarded"]]
        
        # Debe haber 2 cartas descartadas y 3 no descartadas
        assert len(discarded_cards) == 2
        assert len(non_discarded_cards) == 3
        
        # Las cartas descartadas deben tener discarded_at no nulo
        for card in discarded_cards:
            assert card["discarded_at"] is not None
            assert isinstance(card["discarded_at"], datetime)
        
        # Las cartas no descartadas deben tener discarded_at nulo
        for card in non_discarded_cards:
            assert card["discarded_at"] is None

    def test_schema_validation_with_discarded_at(self, setup_match_with_discarded_cards):
        """Test que verifica que el schema valida correctamente el campo discarded_at"""
        from app.matches.schemas import Cards_by_Match_Schema
        
        setup = setup_match_with_discarded_cards
        match_card = setup['match_cards'][2]  # Carta descartada
        
        # Crear datos como los devuelve el servicio
        card_data = {
            "id": match_card.id,
            "card_id": match_card.card_id,
            "match_id": match_card.match_id,
            "player_id": match_card.player_id,
            "is_discarded": match_card.is_discarded,
            "discarded_at": match_card.discarded_at,
            "name": "Test Card 2",
            "type": Card_Type.EVENT,
            "description": "Test card description 2"
        }
        
        # Crear schema desde los datos
        schema = Cards_by_Match_Schema(**card_data)
        
        # Verificar que el schema incluye todos los campos esperados
        assert hasattr(schema, 'id')
        assert hasattr(schema, 'card_id')
        assert hasattr(schema, 'match_id')
        assert hasattr(schema, 'player_id')
        assert hasattr(schema, 'is_discarded')
        assert hasattr(schema, 'discarded_at')
        assert hasattr(schema, 'name')
        assert hasattr(schema, 'type')
        assert hasattr(schema, 'description')
        
        # Verificar los valores específicos
        assert schema.is_discarded is True
        assert schema.discarded_at is not None
        assert schema.player_id is None
        
        # Verificar serialización
        schema_dict = schema.model_dump()
        assert 'discarded_at' in schema_dict
        assert schema_dict['discarded_at'] == setup['discard_time']

    # def test_service_preserves_existing_discarded_at_timestamps(self, setup_match_with_discarded_cards):
    #     """Test que verifica que el servicio preserva timestamps existentes de cartas ya descartadas"""
    #     setup = setup_match_with_discarded_cards
    #     match_id = setup['match'].id
    #     original_discard_time = setup['discard_time']
    #     db = setup_match_with_discarded_cards['match'].__dict__['_sa_instance_state'].session
        
    #     service = MatchService(db)
    #     cards_data = service.get_cards_by_match(match_id)
        
    #     # Buscar la carta que ya estaba descartada
    #     already_discarded = next(c for c in cards_data 
    #                            if c["is_discarded"] and c["discarded_at"] is not None)
        
    #     # Verificar que el timestamp se preservó correctamente
    #     assert already_discarded["discarded_at"] == original_discard_time