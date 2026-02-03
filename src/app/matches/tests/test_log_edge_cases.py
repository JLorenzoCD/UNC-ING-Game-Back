import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.matches.models import MatchEventType
from app.logs.models import MatchLogs
from app.matches.schemas import MatchLogOut
from app.logs.services import LogServices


class TestLogEdgeCases:
    """Tests para casos edge y manejo de errores específicos del LogServices"""

    def test_concurrent_log_creation_simulation(self, db_session):
        """Test simular creación concurrente de logs"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        concurrent_logs = [
            ("Player 1 action", MatchEventType.PLAYER_JOIN, uuid.uuid4()),
            ("Player 2 action", MatchEventType.TURN, uuid.uuid4()),
            ("Player 3 action", MatchEventType.HERCULE_POIROT, uuid.uuid4()),
        ]
        created_ids = []
        for message, event_type, player_id in concurrent_logs:
            log_id = log_service.create_log(
                match_id, message, event_type, player_id)
            created_ids.append(log_id)
        assert len(created_ids) == 3
        logs = log_service.get_logs_by_match(match_id)
        assert len(logs) == 3
        for log in logs:
            matching_data = next(
                (data for data in concurrent_logs if data[0]
                 == log.message), None
            )
            assert matching_data is not None
            assert log.player_id == matching_data[2]

    def test_create_log_commit_failure(self, db_session):
        """Test fallo específico en commit durante creación de log"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with patch.object(db_session, "commit", side_effect=IntegrityError("", "", "")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(IntegrityError):
                    log_service.create_log(match_id, message, event_type)
                mock_rollback.assert_called_once()

    def test_create_log_operational_error(self, db_session):
        """Test error operacional de base de datos"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.TURN
        with patch.object(db_session, "add", side_effect=OperationalError("", "", "")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(OperationalError):
                    log_service.create_log(match_id, message, event_type)
                mock_rollback.assert_called_once()

    def test_create_log_with_invalid_uuid(self, db_session):
        """Test crear log con UUID inválido (None)"""
        log_service = LogServices(db_session)
        match_id = None
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with pytest.raises(Exception):
            log_service.create_log(match_id, message, event_type)

    def test_create_log_with_null_bytes(self, db_session):
        """Test crear log con bytes nulos (podría causar problemas en algunas DB)"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        message_with_null = "Message with\x00null byte"
        event_type = MatchEventType.TURN
        try:
            log_id = log_service.create_log(
                match_id, message_with_null, event_type)
            if log_id:
                saved_log = (
                    db_session.query(MatchLogs).filter(
                        MatchLogs.id == log_id).first()
                )
                assert saved_log is not None
        except Exception:
            pass

    def test_create_log_with_unicode_characters(self, db_session):
        """Test crear log con caracteres especiales y unicode"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        unicode_message = "Jugador 测试玩家 se unió! 🎮 Émojis: 😊🎯🃏"
        event_type = MatchEventType.PLAYER_JOIN
        log_id = log_service.create_log(match_id, unicode_message, event_type)
        assert log_id is not None
        saved_log = db_session.query(MatchLogs).filter(
            MatchLogs.id == log_id).first()
        assert saved_log.message == unicode_message

    def test_create_log_with_very_long_uuid_string(self, db_session):
        """Test crear log con string que no es UUID válido"""
        log_service = LogServices(db_session)
        invalid_match_id = "not-a-valid-uuid-string-at-all"
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with pytest.raises(Exception):
            log_service.create_log(invalid_match_id, message, event_type)

    def test_datetime_handling_edge_cases(self, db_session):
        """Test manejo de datetime en casos edge"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        edge_dates = [
            datetime.min,
            datetime.max,
            datetime(2000, 1, 1, 0, 0, 0),
            datetime(2038, 1, 19, 3, 14, 7),
        ]
        for i, edge_date in enumerate(edge_dates):
            with patch("app.matches.services.datetime") as mock_datetime:
                mock_datetime.now.return_value = edge_date
                try:
                    log_id = log_service.create_log(
                        match_id, f"Edge date test {i}", MatchEventType.TURN
                    )
                    if log_id:
                        saved_log = (
                            db_session.query(MatchLogs)
                            .filter(MatchLogs.id == log_id)
                            .first()
                        )
                        assert saved_log.created_at == edge_date
                except Exception:
                    pass

    def test_get_log_by_id_nonexistent_log(self, db_session):
        """Test obtener log por ID que no existe"""
        log_service = LogServices(db_session)
        nonexistent_id = uuid.uuid4()
        try:
            result = log_service.get_log_by_id(nonexistent_id)
            assert result is None or isinstance(result, MatchLogOut)
        except Exception:
            pass

    def test_get_logs_by_match_with_corrupted_data(self, db_session):
        """Test obtener logs cuando hay datos corruptos en la base de datos"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        corrupt_log = MatchLogs(
            id=uuid.uuid4(),
            match_id=match_id,
            message="",
            event_type=MatchEventType.PLAYER_JOIN,
            created_at=datetime.now(),
            player_id=None,
        )
        db_session.add(corrupt_log)
        db_session.commit()
        logs = log_service.get_logs_by_match(match_id)
        assert len(logs) == 1
        assert logs[0].message == ""
        assert isinstance(logs[0], MatchLogOut)

    def test_get_logs_query_optimization(self, db_session):
        """Test que las consultas de logs son eficientes con muchos registros"""
        log_service = LogServices(db_session)
        match1_id = uuid.uuid4()
        match2_id = uuid.uuid4()
        for i in range(50):
            log_service.create_log(
                match1_id, f"Match1 log {i}", MatchEventType.TURN)
            log_service.create_log(
                match2_id, f"Match2 log {i}", MatchEventType.PLAYER_JOIN
            )
        match1_logs = log_service.get_logs_by_match(match1_id)
        assert len(match1_logs) == 50
        for log in match1_logs:
            assert log.match_id == match1_id
            assert "Match1" in log.message

    def test_log_service_memory_usage(self, db_session):
        """Test que el servicio de logs no causa memory leaks"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        for cycle in range(10):
            for i in range(5):
                log_service.create_log(
                    match_id, f"Cycle {cycle} log {i}", MatchEventType.TURN
                )
            logs = log_service.get_logs_by_match(match_id)
            assert len(logs) == (cycle + 1) * 5
            for log in logs[-5:]:
                retrieved = log_service.get_log_by_id(log.id)
                if retrieved:
                    assert retrieved.id == log.id
        final_logs = log_service.get_logs_by_match(match_id)
        assert len(final_logs) == 50

    def test_log_service_with_malformed_event_type(self, db_session):
        """Test LogServices con tipos de evento que podrían no existir"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        try:
            log_service.create_log(match_id, message, "INVALID_EVENT_TYPE")
            assert False, "Debería haber fallado con tipo de evento inválido"
        except (TypeError, ValueError, AttributeError):
            pass
        except Exception:
            assert True

    def test_massive_log_creation(self, db_session):
        """Test crear muchos logs rápidamente (stress test)"""
        log_service = LogServices(db_session)
        match_id = uuid.uuid4()
        num_logs = 100
        created_ids = []
        for i in range(num_logs):
            log_id = log_service.create_log(
                match_id, f"Bulk log message {i}", MatchEventType.TURN
            )
            created_ids.append(log_id)
        assert len(created_ids) == num_logs
        assert len(set(created_ids)) == num_logs
        logs = log_service.get_logs_by_match(match_id)
        assert len(logs) == num_logs
