import pytest
import uuid
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.cards.models import Card, Match_Card, Card_Type
from app.cards.schemas import Match_Card_Schema
from app.matches.models import Match


class TestEarlyTrainToPaddingtonEvent:
    """Tests unitarios para el evento Early Train to Paddington"""

    def setup_test_data(self, db, match_id, num_cards=6):
        """Crea cartas de prueba para el evento"""
        # Crear cartas base
        test_cards = []
        for i in range(num_cards):
            card = Card(
                id=uuid.uuid4(),
                name=f"Test Card {i+1}",
                type=Card_Type.DETECTIVE,
                description=f"Test card {i+1} description"
            )
            test_cards.append(card)
        
        db.add_all(test_cards)
        db.commit()
        
        # Crear match_cards asociadas al match (simulando cartas en el mazo)
        match_cards = []
        for card in test_cards:
            match_card = Match_Card(
                card_id=card.id,
                match_id=match_id,
                player_id=None,  # En el mazo, sin asignar
                is_discarded=False
            )
            match_cards.append(match_card)
        
        db.add_all(match_cards)
        db.commit()
        
        return match_cards

    @patch('app.matches.services.PileService')
    def test_early_train_to_paddington_success(self, mock_pile_service, db):
        """Test exitoso del evento Early Train to Paddington"""
        # Crear match de prueba
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        # Crear cartas de prueba
        match_cards = self.setup_test_data(db, match.id, 6)
        card_ids = [match_card.id for match_card in match_cards[:3]]  # Seleccionar 3 cartas
        
        # Configurar el mock
        mock_pile_instance = MagicMock()
        mock_pile_service.return_value = mock_pile_instance
        mock_pile_instance.discard_cards.return_value = None
        
        # Importar Cards_Services dentro del contexto del mock para evitar importación circular
        from app.cards.services import Cards_Services
        
        # Ejecutar el evento
        cards_service = Cards_Services(db)
        result = cards_service.early_train_to_paddington_event(match.id, card_ids)
        
        # Verificaciones
        assert len(result) == 3
        assert all(isinstance(card, Match_Card_Schema) for card in result)
        
        # Verificar que se llamó al discard_cards con los parámetros correctos
        mock_pile_instance.discard_cards.assert_called_once_with(match.id, card_ids)
        
        # Verificar que las cartas fueron procesadas
        for card_result in result:
            assert card_result.id in card_ids

    def test_early_train_to_paddington_empty_card_ids(self, db):
        """Test con lista vacía de card_ids"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar ValueError con lista vacía
        with pytest.raises(ValueError, match="Se requiere al menos una carta para descartar"):
            cards_service.early_train_to_paddington_event(match.id, [])

    def test_early_train_to_paddington_none_card_ids(self, db):
        """Test con None como card_ids"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar ValueError con None
        with pytest.raises(ValueError, match="Se requiere al menos una carta para descartar"):
            cards_service.early_train_to_paddington_event(match.id, None)

    def test_early_train_to_paddington_invalid_card_ids(self, db):
        """Test con card_ids que no existen en la partida"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        # IDs de cartas que no existen
        invalid_card_ids = [uuid.uuid4(), uuid.uuid4()]
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar ValueError por cartas inválidas
        with pytest.raises(ValueError, match="Una o más cartas no son válidas o no pertenecen a esta partida"):
            cards_service.early_train_to_paddington_event(match.id, invalid_card_ids)

    def test_early_train_to_paddington_partial_invalid_cards(self, db):
        """Test con mezcla de card_ids válidos e inválidos"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        # Crear una carta válida
        match_cards = self.setup_test_data(db, match.id, 1)
        valid_card_id = match_cards[0].id
        invalid_card_id = uuid.uuid4()
        
        # Mezclar válidos e inválidos
        mixed_card_ids = [valid_card_id, invalid_card_id]
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar ValueError por cartas inválidas
        with pytest.raises(ValueError, match="Una o más cartas no son válidas o no pertenecen a esta partida"):
            cards_service.early_train_to_paddington_event(match.id, mixed_card_ids)

    def test_early_train_to_paddington_wrong_match_id(self, db):
        """Test con match_id incorrecto"""
        # Crear match real
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        # Crear cartas para el match real
        match_cards = self.setup_test_data(db, match.id, 3)
        card_ids = [match_card.id for match_card in match_cards]
        
        # Usar un match_id diferente
        wrong_match_id = uuid.uuid4()
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar ValueError porque las cartas no pertenecen al match incorrecto
        with pytest.raises(ValueError, match="Una o más cartas no son válidas o no pertenecen a esta partida"):
            cards_service.early_train_to_paddington_event(wrong_match_id, card_ids)

    @patch('app.matches.services.PileService')
    def test_early_train_to_paddington_db_error(self, mock_pile_service, db):
        """Test manejo de errores de base de datos"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        match_cards = self.setup_test_data(db, match.id, 3)
        card_ids = [match_card.id for match_card in match_cards]
        
        # Configurar el mock para simular error de SQLAlchemy
        mock_pile_instance = MagicMock()
        mock_pile_service.return_value = mock_pile_instance
        mock_pile_instance.discard_cards.side_effect = SQLAlchemyError("DB Error")
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        
        # Debe lanzar SQLAlchemyError
        with pytest.raises(SQLAlchemyError, match="Error al ejecutar evento Early Train to Paddington"):
            cards_service.early_train_to_paddington_event(match.id, card_ids)

    @patch('app.matches.services.PileService')
    def test_early_train_to_paddington_single_card(self, mock_pile_service, db):
        """Test con una sola carta"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        match_cards = self.setup_test_data(db, match.id, 1)
        card_ids = [match_cards[0].id]
        
        # Configurar el mock
        mock_pile_instance = MagicMock()
        mock_pile_service.return_value = mock_pile_instance
        mock_pile_instance.discard_cards.return_value = None
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        result = cards_service.early_train_to_paddington_event(match.id, card_ids)
        
        # Verificaciones
        assert len(result) == 1
        assert isinstance(result[0], Match_Card_Schema)
        assert result[0].id == card_ids[0]

    @patch('app.matches.services.PileService')
    def test_early_train_to_paddington_max_cards(self, mock_pile_service, db):
        """Test con el máximo número de cartas (simulando las 6 del mazo)"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        match_cards = self.setup_test_data(db, match.id, 6)
        card_ids = [match_card.id for match_card in match_cards]  # Todas las 6 cartas
        
        # Configurar el mock
        mock_pile_instance = MagicMock()
        mock_pile_service.return_value = mock_pile_instance
        mock_pile_instance.discard_cards.return_value = None
        
        from app.cards.services import Cards_Services
        cards_service = Cards_Services(db)
        result = cards_service.early_train_to_paddington_event(match.id, card_ids)
        
        # Verificaciones
        assert len(result) == 6
        assert all(isinstance(card, Match_Card_Schema) for card in result)
        
        # Verificar que todas las cartas están en el resultado
        result_ids = [card.id for card in result]
        for card_id in card_ids:
            assert card_id in result_ids

    @patch('app.matches.services.PileService')
    def test_early_train_to_paddington_rollback_on_error(self, mock_pile_service, db):
        """Test que verifica el rollback en caso de error"""
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        match_cards = self.setup_test_data(db, match.id, 3)
        card_ids = [match_card.id for match_card in match_cards]
        
        # Configurar el mock para lanzar excepción
        mock_pile_instance = MagicMock()
        mock_pile_service.return_value = mock_pile_instance
        mock_pile_instance.discard_cards.side_effect = Exception("Generic error")
        
        # Mock para verificar que se llama rollback
        with patch.object(db, 'rollback') as mock_rollback:
            from app.cards.services import Cards_Services
            cards_service = Cards_Services(db)
            
            # Debe lanzar excepción y llamar rollback
            with pytest.raises(Exception):
                cards_service.early_train_to_paddington_event(match.id, card_ids)
            
            # Verificar que se llamó rollback
            mock_rollback.assert_called_once()

    def test_early_train_to_paddington_event_card_enum_exists(self, db):
        """Test que verifica que el evento existe en el enum Card_event"""
        from app.cards.services import Card_event
        
        # Verificar que el evento está definido en el enum
        assert hasattr(Card_event, 'EARLY_TRAIN_TO_PADDINGTON')
        assert Card_event.EARLY_TRAIN_TO_PADDINGTON.value == "EARLY TRAIN TO PADDINGTON"

    def test_early_train_to_paddington_card_description_matches_functionality(self, db):
        """Test que verifica que la descripción de la carta coincide con la funcionalidad"""
        # Este test valida que la lógica implementada coincide con la descripción de la carta
        # según el juego original: "Take the top six cards from the draw pile and place them face-up on the discard pile"
        
        match = Match(
            id=uuid.uuid4(),
            name="Test Match",
            min_players=2,
            max_players=6,
            owner_id=uuid.uuid4()
        )
        db.add(match)
        db.commit()
        
        # Crear exactamente 6 cartas como dice la descripción
        match_cards = self.setup_test_data(db, match.id, 6)
        card_ids = [match_card.id for match_card in match_cards]
        
        with patch('app.matches.services.PileService') as mock_pile_service:
            mock_pile_instance = MagicMock()
            mock_pile_service.return_value = mock_pile_instance
            mock_pile_instance.discard_cards.return_value = None
            
            from app.cards.services import Cards_Services
            cards_service = Cards_Services(db)
            result = cards_service.early_train_to_paddington_event(match.id, card_ids)
            
            # Verificar que se procesaron las 6 cartas como dice la descripción
            assert len(result) == 6
            # Verificar que se llamó al método para descartar las cartas
            mock_pile_instance.discard_cards.assert_called_once_with(match.id, card_ids)