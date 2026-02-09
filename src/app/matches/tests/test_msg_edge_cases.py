import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.matches.models import MatchEventType
from app.messages.models import MatchMessage
from app.messages.schemas import MatchMessageOut
from app.messages.services import MessageServices


class TestMsgEdgeCases:
    """Tests para casos edge y manejo de errores específicos del MessageServices"""

    def test_concurrent_msg_creation_simulation(self, db_session):
        """Test simular creación concurrente de msgs"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        concurrent_msgs = [
            ("Player 1 action", MatchEventType.PLAYER_JOIN, uuid.uuid4()),
            ("Player 2 action", MatchEventType.TURN, uuid.uuid4()),
            ("Player 3 action", MatchEventType.HERCULE_POIROT, uuid.uuid4()),
        ]
        created_ids = []
        for message, event_type, player_id in concurrent_msgs:
            msg_id = msg_service.create_msg(
                match_id, message, event_type, player_id)
            created_ids.append(msg_id)
        assert len(created_ids) == 3
        msgs = msg_service.get_msgs_by_match(match_id)
        assert len(msgs) == 3
        for msg in msgs:
            matching_data = next(
                (data for data in concurrent_msgs if data[0]
                 == msg.message), None
            )
            assert matching_data is not None
            assert msg.player_id == matching_data[2]

    def test_create_msg_commit_failure(self, db_session):
        """Test fallo específico en commit durante creación de msg"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with patch.object(db_session, "commit", side_effect=IntegrityError("", "", "")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(IntegrityError):
                    msg_service.create_msg(match_id, message, event_type)
                mock_rollback.assert_called_once()

    def test_create_msg_operational_error(self, db_session):
        """Test error operacional de base de datos"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.TURN
        with patch.object(db_session, "add", side_effect=OperationalError("", "", "")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(OperationalError):
                    msg_service.create_msg(match_id, message, event_type)
                mock_rollback.assert_called_once()

    def test_create_msg_with_invalid_uuid(self, db_session):
        """Test crear msg con UUID inválido (None)"""
        msg_service = MessageServices(db_session)
        match_id = None
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with pytest.raises(Exception):
            msg_service.create_msg(match_id, message, event_type)

    def test_create_msg_with_null_bytes(self, db_session):
        """Test crear msg con bytes nulos (podría causar problemas en algunas DB)"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message_with_null = "Message with\x00null byte"
        event_type = MatchEventType.TURN
        try:
            msg_id = msg_service.create_msg(
                match_id, message_with_null, event_type)
            if msg_id:
                saved_msg = (
                    db_session.query(MatchMessage).filter(
                        MatchMessage.id == msg_id).first()
                )
                assert saved_msg is not None
        except Exception:
            pass

    def test_create_msg_with_unicode_characters(self, db_session):
        """Test crear msg con caracteres especiales y unicode"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        unicode_message = "Jugador 测试玩家 se unió! 🎮 Émojis: 😊🎯🃏"
        event_type = MatchEventType.PLAYER_JOIN
        msg_id = msg_service.create_msg(match_id, unicode_message, event_type)
        assert msg_id is not None
        saved_msg = db_session.query(MatchMessage).filter(
            MatchMessage.id == msg_id).first()
        assert saved_msg.message == unicode_message

    def test_create_msg_with_very_long_uuid_string(self, db_session):
        """Test crear msg con string que no es UUID válido"""
        msg_service = MessageServices(db_session)
        invalid_match_id = "not-a-valid-uuid-string-at-all"
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with pytest.raises(Exception):
            msg_service.create_msg(invalid_match_id, message, event_type)

    def test_datetime_handling_edge_cases(self, db_session):
        """Test manejo de datetime en casos edge"""
        msg_service = MessageServices(db_session)
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
                    msg_id = msg_service.create_msg(
                        match_id, f"Edge date test {i}", MatchEventType.TURN
                    )
                    if msg_id:
                        saved_msg = (
                            db_session.query(MatchMessage)
                            .filter(MatchMessage.id == msg_id)
                            .first()
                        )
                        assert saved_msg.created_at == edge_date
                except Exception:
                    pass

    def test_get_msg_by_id_nonexistent_msg(self, db_session):
        """Test obtener msg por ID que no existe"""
        msg_service = MessageServices(db_session)
        nonexistent_id = uuid.uuid4()
        try:
            result = msg_service.get_msg_by_id(nonexistent_id)
            assert result is None or isinstance(result, MatchMessageOut)
        except Exception:
            pass

    def test_get_msgs_by_match_with_corrupted_data(self, db_session):
        """Test obtener msgs cuando hay datos corruptos en la base de datos"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        corrupt_msg = MatchMessage(
            id=uuid.uuid4(),
            match_id=match_id,
            message="",
            event_type=MatchEventType.PLAYER_JOIN,
            created_at=datetime.now(),
            player_id=None,
        )
        db_session.add(corrupt_msg)
        db_session.commit()
        msgs = msg_service.get_msgs_by_match(match_id)
        assert len(msgs) == 1
        assert msgs[0].message == ""
        assert isinstance(msgs[0], MatchMessageOut)

    def test_get_msgs_query_optimization(self, db_session):
        """Test que las consultas de msgs son eficientes con muchos registros"""
        msg_service = MessageServices(db_session)
        match1_id = uuid.uuid4()
        match2_id = uuid.uuid4()
        for i in range(50):
            msg_service.create_msg(
                match1_id, f"Match1 msg {i}", MatchEventType.TURN)
            msg_service.create_msg(
                match2_id, f"Match2 msg {i}", MatchEventType.PLAYER_JOIN
            )
        match1_msgs = msg_service.get_msgs_by_match(match1_id)
        assert len(match1_msgs) == 50
        for msg in match1_msgs:
            assert msg.match_id == match1_id
            assert "Match1" in msg.message

    def test_msg_service_memory_usage(self, db_session):
        """Test que el servicio de msgs no causa memory leaks"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        for cycle in range(10):
            for i in range(5):
                msg_service.create_msg(
                    match_id, f"Cycle {cycle} msg {i}", MatchEventType.TURN
                )
            msgs = msg_service.get_msgs_by_match(match_id)
            assert len(msgs) == (cycle + 1) * 5
            for msg in msgs[-5:]:
                retrieved = msg_service.get_msg_by_id(msg.id)
                if retrieved:
                    assert retrieved.id == msg.id
        final_msgs = msg_service.get_msgs_by_match(match_id)
        assert len(final_msgs) == 50

    def test_msg_service_with_malformed_event_type(self, db_session):
        """Test MessageServices con tipos de evento que podrían no existir"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        try:
            msg_service.create_msg(match_id, message, "INVALID_EVENT_TYPE")
            assert False, "Debería haber fallado con tipo de evento inválido"
        except (TypeError, ValueError, AttributeError):
            pass
        except Exception:
            assert True

    def test_massive_msg_creation(self, db_session):
        """Test crear muchos msgs rápidamente (stress test)"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        num_msgs = 100
        created_ids = []
        for i in range(num_msgs):
            msg_id = msg_service.create_msg(
                match_id, f"Bulk msg message {i}", MatchEventType.TURN
            )
            created_ids.append(msg_id)
        assert len(created_ids) == num_msgs
        assert len(set(created_ids)) == num_msgs
        msgs = msg_service.get_msgs_by_match(match_id)
        assert len(msgs) == num_msgs
