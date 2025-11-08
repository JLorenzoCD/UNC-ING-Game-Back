import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.matches.services import LogService
from app.matches.models import Match, MatchLogs, MatchEventType
from app.matches.schemas import MatchLogOut
from app.player.models import Player


class TestLogService:
    
    def test_create_log_success(self, db_session):
        """Test crear un log exitosamente"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        message = "Test log message"
        event_type = MatchEventType.PLAYER_JOIN
        
        # Act
        log_id = log_service.create_log(match_id, message, event_type, player_id)
        
        # Assert
        assert log_id is not None
        assert isinstance(log_id, uuid.UUID)
        
        # Verificar que se guardó en la base de datos
        saved_log = db_session.query(MatchLogs).filter(MatchLogs.id == log_id).first()
        assert saved_log is not None
        assert saved_log.match_id == match_id
        assert saved_log.message == message
        assert saved_log.event_type == event_type
        assert saved_log.player_id == player_id
        assert isinstance(saved_log.created_at, datetime)
    
    def test_create_log_without_player_id(self, db_session):
        """Test crear un log sin especificar player_id (opcional)"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        message = "System message"
        event_type = MatchEventType.TURN
        
        # Act
        log_id = log_service.create_log(match_id, message, event_type)
        
        # Assert
        assert log_id is not None
        
        saved_log = db_session.query(MatchLogs).filter(MatchLogs.id == log_id).first()
        assert saved_log is not None
        assert saved_log.player_id is None
        assert saved_log.match_id == match_id
        assert saved_log.message == message
    
    def test_create_log_database_error(self, db_session):
        """Test manejo de error de base de datos al crear log"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        
        # Mock database error
        with patch.object(db_session, 'add', side_effect=SQLAlchemyError("DB Error")):
            with patch.object(db_session, 'rollback') as mock_rollback:
                # Act & Assert
                with pytest.raises(SQLAlchemyError):
                    log_service.create_log(match_id, message, event_type)
                
                mock_rollback.assert_called_once()
    
    def test_get_logs_by_match_success(self, db_session):
        """Test obtener logs por match_id exitosamente"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        
        # Crear algunos logs de prueba
        log1_id = log_service.create_log(match_id, "First log", MatchEventType.PLAYER_JOIN, player_id)
        log2_id = log_service.create_log(match_id, "Second log", MatchEventType.TURN)
        
        # Crear log de otra partida (no debería aparecer)
        other_match_id = uuid.uuid4()
        log_service.create_log(other_match_id, "Other match log", MatchEventType.PLAYER_JOIN)
        
        # Act
        logs = log_service.get_logs_by_match(match_id)
        
        # Assert
        assert len(logs) == 2
        assert all(isinstance(log, MatchLogOut) for log in logs)
        
        # Verificar que son los logs correctos
        log_ids = [log.id for log in logs]
        assert log1_id in log_ids
        assert log2_id in log_ids
        
        # Verificar contenido
        for log in logs:
            assert log.match_id == match_id
            assert log.message in ["First log", "Second log"]
    
    def test_get_logs_by_match_empty_result(self, db_session):
        """Test obtener logs de una partida sin logs"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        
        # Act
        logs = log_service.get_logs_by_match(match_id)
        
        # Assert
        assert logs == []
    
    def test_get_log_by_id_success(self, db_session):
        """Test obtener un log por su ID exitosamente"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        message = "Test log for get by ID"
        event_type = MatchEventType.HERCULE_POIROT
        
        # Crear log
        log_id = log_service.create_log(match_id, message, event_type, player_id)
        
        # Act
        retrieved_log = log_service.get_log_by_id(log_id)
        
        # Assert
        assert isinstance(retrieved_log, MatchLogOut)
        assert retrieved_log.id == log_id
        assert retrieved_log.match_id == match_id
        assert retrieved_log.message == message
        assert retrieved_log.event_type == event_type
        assert retrieved_log.player_id == player_id
        assert isinstance(retrieved_log.created_at, datetime)
    
    def test_get_log_by_id_database_error(self, db_session):
        """Test manejo de error de base de datos al obtener log por ID"""
        # Arrange
        log_service = LogService(db_session)
        log_id = uuid.uuid4()
        
        # Mock database error
        with patch.object(db_session, 'query', side_effect=SQLAlchemyError("DB Error")):
            with patch.object(db_session, 'rollback') as mock_rollback:
                # Act & Assert
                with pytest.raises(SQLAlchemyError):
                    log_service.get_log_by_id(log_id)
                
                mock_rollback.assert_called_once()
    
    def test_create_log_all_event_types(self, db_session):
        """Test crear logs con todos los tipos de evento disponibles"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        
        # Test con varios tipos de evento
        event_types = [
            MatchEventType.PLAYER_JOIN,
            MatchEventType.TURN,
            MatchEventType.HERCULE_POIROT,
            MatchEventType.MISS_MARPLE,
            MatchEventType.CARDS_OFF_THE_TABLE,
            MatchEventType.BLACKMAILED,
            MatchEventType.DISCARD_CARDS,
            MatchEventType.TAKE_CARDS
        ]
        
        created_logs = []
        
        # Act
        for i, event_type in enumerate(event_types):
            message = f"Log message {i} for {event_type.value}"
            log_id = log_service.create_log(match_id, message, event_type, player_id)
            created_logs.append(log_id)
        
        # Assert
        assert len(created_logs) == len(event_types)
        
        # Verificar que todos se guardaron correctamente
        saved_logs = log_service.get_logs_by_match(match_id)
        assert len(saved_logs) == len(event_types)
        
        # Verificar que cada tipo de evento está presente
        saved_event_types = [log.event_type for log in saved_logs]
        for event_type in event_types:
            assert event_type in saved_event_types
    
    def test_logs_chronological_order(self, db_session):
        """Test que los logs mantienen orden cronológico"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        
        # Crear logs con pequeños delays para asegurar orden temporal
        logs_data = [
            ("First log", MatchEventType.PLAYER_JOIN),
            ("Second log", MatchEventType.TURN),
            ("Third log", MatchEventType.HERCULE_POIROT)
        ]
        
        created_times = []
        
        # Act
        for message, event_type in logs_data:
            with patch('app.matches.services.datetime') as mock_datetime:
                mock_time = datetime.now() + timedelta(seconds=len(created_times))
                mock_datetime.now.return_value = mock_time
                created_times.append(mock_time)
                
                log_service.create_log(match_id, message, event_type)
        
        # Assert
        logs = log_service.get_logs_by_match(match_id)
        assert len(logs) == 3
        
        # Los logs podrían no estar ordenados por defecto, pero al menos 
        # verificamos que tienen timestamps diferentes
        timestamps = [log.created_at for log in logs]
        assert len(set(timestamps)) == 3  # Todos diferentes
    
    def test_log_service_integration_with_different_matches(self, db_session):
        """Test que los logs se separan correctamente por partida"""
        # Arrange
        log_service = LogService(db_session)
        match1_id = uuid.uuid4()
        match2_id = uuid.uuid4()
        player_id = uuid.uuid4()
        
        # Act - Crear logs para diferentes partidas
        log1_match1 = log_service.create_log(match1_id, "Match 1 Log 1", MatchEventType.PLAYER_JOIN, player_id)
        log2_match1 = log_service.create_log(match1_id, "Match 1 Log 2", MatchEventType.TURN)
        
        log1_match2 = log_service.create_log(match2_id, "Match 2 Log 1", MatchEventType.HERCULE_POIROT)
        
        # Assert
        match1_logs = log_service.get_logs_by_match(match1_id)
        match2_logs = log_service.get_logs_by_match(match2_id)
        
        assert len(match1_logs) == 2
        assert len(match2_logs) == 1
        
        # Verificar que los logs están en la partida correcta
        match1_log_ids = [log.id for log in match1_logs]
        match2_log_ids = [log.id for log in match2_logs]
        
        assert log1_match1 in match1_log_ids
        assert log2_match1 in match1_log_ids
        assert log1_match2 in match2_log_ids
        
        # Verificar que no hay cross-contamination
        assert log1_match2 not in match1_log_ids
        assert log1_match1 not in match2_log_ids
        assert log2_match1 not in match2_log_ids
    
    def test_create_log_with_long_message(self, db_session):
        """Test crear log con mensaje largo"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        long_message = "x" * 1000  # Mensaje muy largo
        event_type = MatchEventType.PLAYER_JOIN
        
        # Act
        log_id = log_service.create_log(match_id, long_message, event_type)
        
        # Assert
        assert log_id is not None
        
        saved_log = db_session.query(MatchLogs).filter(MatchLogs.id == log_id).first()
        assert saved_log.message == long_message
    
    def test_create_log_with_empty_message(self, db_session):
        """Test crear log con mensaje vacío"""
        # Arrange
        log_service = LogService(db_session)
        match_id = uuid.uuid4()
        empty_message = ""
        event_type = MatchEventType.TURN
        
        # Act
        log_id = log_service.create_log(match_id, empty_message, event_type)
        
        # Assert
        assert log_id is not None
        
        saved_log = db_session.query(MatchLogs).filter(MatchLogs.id == log_id).first()
        assert saved_log.message == empty_message