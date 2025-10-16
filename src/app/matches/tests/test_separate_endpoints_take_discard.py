import uuid
import pytest
from datetime import date
from sqlalchemy import func
from unittest.mock import patch, MagicMock, AsyncMock
from conftest import setup_match_and_players

from app.cards.models import Card, Match_Card, Card_Type
from app.player.models import Player
from app.matches.models import Match


class TestTakeCardsEndpoint:
    """Tests para el endpoint PUT /matches/{match_id}/cards/take"""

    def create_deck_cards(self, db_session, setup_data, deck_cards_count=3):
        """Crea cartas disponibles en el mazo (descartadas o sin asignar)"""
        match_id = setup_data['match_id']
        cards = setup_data['cards']
        
        match_cards = []
        
        # Cartas del mazo (disponibles para tomar)
        for i in range(deck_cards_count):
            match_card = Match_Card(
                card_id=cards[i].id,
                match_id=match_id,
                player_id=None,
                is_discarded=False
            )
            match_cards.append(match_card)
        
        db_session.add_all(match_cards)
        db_session.commit()
        
        return match_cards

    def test_take_cards_success(self, client, db_session):
        """Test tomar cartas exitosamente"""
        setup_data = setup_match_and_players(client, db_session)
        deck_cards = self.create_deck_cards(db_session, setup_data, 3)
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(deck_cards[0].id), str(deck_cards[1].id)]
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/take",
                json=request_data
            )
            
            assert response.status_code == 200

    def test_take_cards_empty_list(self, client, db_session):
        """Test tomar lista vacía de cartas"""
        setup_data = setup_match_and_players(client, db_session)
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": []
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/take",
                json=request_data
            )
            
            assert response.status_code == 200

    def test_take_cards_more_than_6_fails(self, client, db_session):
        """Test error: intentar tomar más de 6 cartas"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Crear 7 cartas en el mazo
        cards_to_take = [
            Card(id=uuid.uuid4(), name=f"Take Card {i}", type=Card_Type.EVENT, 
                 description=f"Card to take {i}") for i in range(7)
        ]
        db_session.add_all(cards_to_take)
        db_session.commit()
        
        match_cards_to_take = []
        for card in cards_to_take:
            match_card = Match_Card(
                card_id=card.id,
                match_id=setup_data['match_id'],
                player_id=None,
                is_discarded=False
            )
            match_cards_to_take.append(match_card)
        
        db_session.add_all(match_cards_to_take)
        db_session.commit()
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(mc.id) for mc in match_cards_to_take]  # 7 cartas
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/take",
            json=request_data
        )
        
        assert response.status_code == 400

    def test_take_cards_exceed_hand_limit_fails(self, client, db_session):
        """Test error: tomar cartas excedería el límite de 6 cartas en mano"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Crear 4 cartas que ya tiene el jugador
        existing_cards = [
            Card(id=uuid.uuid4(), name=f"Existing Card {i}", type=Card_Type.EVENT, 
                 description=f"Existing card {i}") for i in range(4)
        ]
        db_session.add_all(existing_cards)
        
        # Crear 4 cartas en el mazo para tomar
        deck_cards = [
            Card(id=uuid.uuid4(), name=f"Deck Card {i}", type=Card_Type.EVENT, 
                 description=f"Deck card {i}") for i in range(4)
        ]
        db_session.add_all(deck_cards)
        db_session.commit()
        
        # Match cards que ya tiene el jugador
        player_match_cards = []
        for card in existing_cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=setup_data['match_id'],
                player_id=setup_data['owner_id'],
                is_discarded=False
            )
            player_match_cards.append(match_card)
        
        # Match cards en el mazo
        deck_match_cards = []
        for card in deck_cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=setup_data['match_id'],
                player_id=None,
                is_discarded=False
            )
            deck_match_cards.append(match_card)
        
        db_session.add_all(player_match_cards + deck_match_cards)
        db_session.commit()
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(mc.id) for mc in deck_match_cards]  # 4 cartas + 4 existentes = 8 > 6
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/take",
            json=request_data
        )
        
        assert response.status_code == 400

    def test_take_cards_player_not_in_match_fails(self, client, db_session):
        """Test error: jugador no está en la partida"""
        setup_data = setup_match_and_players(client, db_session)
        deck_cards = self.create_deck_cards(db_session, setup_data, 2)
        
        # Usar un jugador que no está en la partida
        fake_player_id = str(uuid.uuid4())
        
        request_data = {
            "player_id": fake_player_id,
            "card_ids": [str(deck_cards[0].id)]
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/take",
            json=request_data
        )
        
        assert response.status_code == 404

    def test_take_cards_malformed_request(self, client, db_session):
        """Test con request malformada"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Faltan campos requeridos
        request_data = {
            "player_id": setup_data['owner_str_id'],
            # Falta card_ids
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/take",
            json=request_data
        )
        
        assert response.status_code == 422  # Validation error

    def test_take_cards_invalid_uuid_format(self, client, db_session):
        """Test con UUIDs con formato inválido"""
        setup_data = setup_match_and_players(client, db_session)
        
        request_data = {
            "player_id": "invalid-uuid-format",
            "card_ids": ["also-invalid", "not-a-uuid"]
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/take",
            json=request_data
        )
        
        assert response.status_code == 422  # Validation error


class TestDiscardCardsEndpoint:
    """Tests para el endpoint PUT /matches/{match_id}/cards/discard"""

    def create_player_cards(self, db_session, setup_data, player_cards_count=3):
        """Crea cartas que pertenecen al jugador"""
        match_id = setup_data['match_id']
        owner_id = setup_data['owner_id']
        cards = setup_data['cards']
        
        match_cards = []
        
        # Cartas del jugador (para descartar)
        for i in range(player_cards_count):
            match_card = Match_Card(
                card_id=cards[i].id,
                match_id=match_id,
                player_id=owner_id,
                is_discarded=False
            )
            match_cards.append(match_card)
        
        db_session.add_all(match_cards)
        db_session.commit()
        
        return match_cards

    def test_discard_cards_success(self, client, db_session):
        """Test descartar cartas exitosamente"""
        setup_data = setup_match_and_players(client, db_session)
        player_cards = self.create_player_cards(db_session, setup_data, 3)
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(player_cards[0].id), str(player_cards[1].id)]
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/discard",
                json=request_data
            )
            
            assert response.status_code == 200

    def test_discard_cards_empty_list(self, client, db_session):
        """Test descartar lista vacía de cartas"""
        setup_data = setup_match_and_players(client, db_session)
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": []
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/discard",
                json=request_data
            )
            
            assert response.status_code == 200

    def test_discard_more_cards_than_owned_fails(self, client, db_session):
        """Test error: intentar descartar más cartas de las que se tienen"""
        setup_data = setup_match_and_players(client, db_session)
        player_cards = self.create_player_cards(db_session, setup_data, 2)  # Solo 2 cartas
        
        # Intentar descartar 3 cartas cuando solo tiene 2
        fake_card_id = str(uuid.uuid4())
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(player_cards[0].id), str(player_cards[1].id), fake_card_id]  # 3 cartas
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/discard",
            json=request_data
        )
        
        assert response.status_code == 400

    def test_discard_cards_player_not_in_match_fails(self, client, db_session):
        """Test error: jugador no está en la partida"""
        setup_data = setup_match_and_players(client, db_session)
        player_cards = self.create_player_cards(db_session, setup_data, 2)
        
        # Usar un jugador que no está en la partida
        fake_player_id = str(uuid.uuid4())
        
        request_data = {
            "player_id": fake_player_id,
            "card_ids": [str(player_cards[0].id)]
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/discard",
            json=request_data
        )
        
        assert response.status_code == 404

    def test_discard_cards_not_owned_by_player(self, client, db_session):
        """Test que no se pueden descartar cartas que no pertenecen al jugador"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Primero darle una carta al jugador principal para que tenga al menos una
        player_cards = self.create_player_cards(db_session, setup_data, 1)
        
        # Crear otro jugador
        other_player = Player(
            name="Other Player",
            avatar="other_avatar",
            birthday=date(2000, 1, 2)
        )
        db_session.add(other_player)
        db_session.commit()
        
        # Crear carta que pertenece al otro jugador
        card = Card(
            id=uuid.uuid4(),
            name="Other's Card",
            type=Card_Type.EVENT,
            description="Card belonging to other player"
        )
        db_session.add(card)
        db_session.commit()
        
        other_match_card = Match_Card(
            card_id=card.id,
            match_id=setup_data['match_id'],
            player_id=other_player.id,
            is_discarded=False
        )
        db_session.add(other_match_card)
        db_session.commit()
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(other_match_card.id)]
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/discard",
                json=request_data
            )
            
            # Debería devolver 200 ya que el endpoint maneja las cartas que no son del jugador silenciosamente
            assert response.status_code == 200
            
            # Verificar que la carta no se descartó
            db_session.refresh(other_match_card)
            assert other_match_card.is_discarded is False
            assert other_match_card.player_id == other_player.id

    def test_discard_cards_sets_discarded_at(self, client, db_session):
        """Test que verifica que se establece el campo discarded_at"""
        setup_data = setup_match_and_players(client, db_session)
        player_cards = self.create_player_cards(db_session, setup_data, 2)
        
        request_data = {
            "player_id": setup_data['owner_str_id'],
            "card_ids": [str(player_cards[0].id)]
        }
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/discard",
                json=request_data
            )
            
            assert response.status_code == 200
            
            # Verificar que la carta fue descartada correctamente
            db_session.refresh(player_cards[0])
            assert player_cards[0].is_discarded is True
            assert player_cards[0].player_id is None
            assert player_cards[0].discarded_at is not None

    def test_discard_cards_malformed_request(self, client, db_session):
        """Test con request malformada"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Faltan campos requeridos
        request_data = {
            "player_id": setup_data['owner_str_id'],
            # Falta card_ids
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/discard",
            json=request_data
        )
        
        assert response.status_code == 422  # Validation error

    def test_discard_cards_invalid_uuid_format(self, client, db_session):
        """Test con UUIDs con formato inválido"""
        setup_data = setup_match_and_players(client, db_session)
        
        request_data = {
            "player_id": "invalid-uuid-format",
            "card_ids": ["also-invalid", "not-a-uuid"]
        }
        
        response = client.put(
            f"/matches/{setup_data['match_str_id']}/cards/discard",
            json=request_data
        )
        
        assert response.status_code == 422  # Validation error


class TestCombinedTakeDiscardScenarios:
    """Tests para escenarios que combinan tomar y descartar cartas"""

    def test_take_and_discard_workflow(self, client, db_session):
        """Test workflow: jugador descarta cartas y luego toma otras"""
        setup_data = setup_match_and_players(client, db_session)
        
        # Crear cartas que tiene el jugador
        player_cards = [
            Card(id=uuid.uuid4(), name=f"Player Card {i}", type=Card_Type.EVENT, 
                 description=f"Player card {i}") for i in range(3)
        ]
        db_session.add_all(player_cards)
        
        # Crear cartas en el mazo
        deck_cards = [
            Card(id=uuid.uuid4(), name=f"Deck Card {i}", type=Card_Type.EVENT, 
                 description=f"Deck card {i}") for i in range(3)
        ]
        db_session.add_all(deck_cards)
        db_session.commit()
        
        # Match cards del jugador
        player_match_cards = []
        for card in player_cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=setup_data['match_id'],
                player_id=setup_data['owner_id'],
                is_discarded=False
            )
            player_match_cards.append(match_card)
        
        # Match cards del mazo
        deck_match_cards = []
        for card in deck_cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=setup_data['match_id'],
                player_id=None,
                is_discarded=False
            )
            deck_match_cards.append(match_card)
        
        db_session.add_all(player_match_cards + deck_match_cards)
        db_session.commit()
        
        async def mock_broadcast(*args, **kwargs):
            return None
        
        with patch('app.matches.endpoints.manager') as mock_manager:
            mock_manager.specificBroadcast = mock_broadcast
            
            # Paso 1: Descartar 2 cartas
            discard_data = {
                "player_id": setup_data['owner_str_id'],
                "card_ids": [str(player_match_cards[0].id), str(player_match_cards[1].id)]
            }
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/discard",
                json=discard_data
            )
            
            assert response.status_code == 200
            
            # Paso 2: Tomar 2 cartas del mazo
            take_data = {
                "player_id": setup_data['owner_str_id'],
                "card_ids": [str(deck_match_cards[0].id), str(deck_match_cards[1].id)]
            }
            
            response = client.put(
                f"/matches/{setup_data['match_str_id']}/cards/take",
                json=take_data
            )
            
            assert response.status_code == 200
            
            # Verificar el estado final
            db_session.refresh(player_match_cards[0])
            db_session.refresh(player_match_cards[1])
            db_session.refresh(deck_match_cards[0])
            db_session.refresh(deck_match_cards[1])
            
            # Cartas descartadas
            assert player_match_cards[0].is_discarded is True
            assert player_match_cards[0].player_id is None
            assert player_match_cards[1].is_discarded is True
            assert player_match_cards[1].player_id is None
            
            # Cartas tomadas
            assert deck_match_cards[0].player_id == setup_data['owner_id']
            assert deck_match_cards[1].player_id == setup_data['owner_id']