import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.matches.models import MatchEventType
from app.messages.models import MatchMessage
from app.messages.schemas import MatchMessageOut
from app.messages.services import MessageServices


class TestMessageServices:
    """Class TestMessageServices."""

    def test_create_msg_all_event_types(self, db_session):
        """Test crear msgs con todos los tipos de evento disponibles"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        event_types = [
            MatchEventType.PLAYER_JOIN,
            MatchEventType.TURN,
            MatchEventType.HERCULE_POIROT,
            MatchEventType.MISS_MARPLE,
            MatchEventType.CARDS_OFF_THE_TABLE,
            MatchEventType.BLACKMAILED,
            MatchEventType.DISCARD_CARDS,
            MatchEventType.TAKE_CARDS,
        ]
        created_msgs = []
        for i, event_type in enumerate(event_types):
            message = f"Msg message {i} for {event_type.value}"
            msg_id = msg_service.create_msg(
                match_id, message, event_type, player_id)
            created_msgs.append(msg_id)
        assert len(created_msgs) == len(event_types)
        saved_msgs = msg_service.get_msgs_by_match(match_id)
        assert len(saved_msgs) == len(event_types)
        saved_event_types = [msg.event_type for msg in saved_msgs]
        for event_type in event_types:
            assert event_type in saved_event_types

    def test_create_msg_database_error(self, db_session):
        """Test manejo de error de base de datos al crear msg"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message = "Test message"
        event_type = MatchEventType.PLAYER_JOIN
        with patch.object(db_session, "add", side_effect=SQLAlchemyError("DB Error")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    msg_service.create_msg(match_id, message, event_type)
                mock_rollback.assert_called_once()

    def test_create_msg_success(self, db_session):
        """Test crear un msg exitosamente"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        message = "Test msg message"
        event_type = MatchEventType.PLAYER_JOIN
        msg_id = msg_service.create_msg(
            match_id, message, event_type, player_id)
        assert msg_id is not None
        assert isinstance(msg_id, uuid.UUID)
        saved_msg = db_session.query(MatchMessage).filter(
            MatchMessage.id == msg_id).first()
        assert saved_msg is not None
        assert saved_msg.match_id == match_id
        assert saved_msg.message == message
        assert saved_msg.event_type == event_type
        assert saved_msg.player_id == player_id
        assert isinstance(saved_msg.created_at, datetime)

    def test_create_msg_with_empty_message(self, db_session):
        """Test crear msg con mensaje vacío"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        empty_message = ""
        event_type = MatchEventType.TURN
        msg_id = msg_service.create_msg(match_id, empty_message, event_type)
        assert msg_id is not None
        saved_msg = db_session.query(MatchMessage).filter(
            MatchMessage.id == msg_id).first()
        assert saved_msg.message == empty_message

    def test_create_msg_with_long_message(self, db_session):
        """Test crear msg con mensaje largo"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        long_message = "x" * 1000
        event_type = MatchEventType.PLAYER_JOIN
        msg_id = msg_service.create_msg(match_id, long_message, event_type)
        assert msg_id is not None
        saved_msg = db_session.query(MatchMessage).filter(
            MatchMessage.id == msg_id).first()
        assert saved_msg.message == long_message

    def test_create_msg_without_player_id(self, db_session):
        """Test crear un msg sin especificar player_id (opcional)"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        message = "System message"
        event_type = MatchEventType.TURN
        msg_id = msg_service.create_msg(match_id, message, event_type)
        assert msg_id is not None
        saved_msg = db_session.query(MatchMessage).filter(
            MatchMessage.id == msg_id).first()
        assert saved_msg is not None
        assert saved_msg.player_id is None
        assert saved_msg.match_id == match_id
        assert saved_msg.message == message

    def test_get_msg_by_id_database_error(self, db_session):
        """Test manejo de error de base de datos al obtener msg por ID"""
        msg_service = MessageServices(db_session)
        msg_id = uuid.uuid4()
        with patch.object(db_session, "query", side_effect=SQLAlchemyError("DB Error")):
            with patch.object(db_session, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    msg_service.get_msg_by_id(msg_id)
                mock_rollback.assert_called_once()

    def test_get_msg_by_id_success(self, db_session):
        """Test obtener un msg por su ID exitosamente"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        message = "Test msg for get by ID"
        event_type = MatchEventType.HERCULE_POIROT
        msg_id = msg_service.create_msg(
            match_id, message, event_type, player_id)
        retrieved_msg = msg_service.get_msg_by_id(msg_id)
        assert isinstance(retrieved_msg, MatchMessageOut)
        assert retrieved_msg.id == msg_id
        assert retrieved_msg.match_id == match_id
        assert retrieved_msg.message == message
        assert retrieved_msg.event_type == event_type
        assert retrieved_msg.player_id == player_id
        assert isinstance(retrieved_msg.created_at, datetime)

    def test_get_msgs_by_match_empty_result(self, db_session):
        """Test obtener msgs de una partida sin msgs"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        msgs = msg_service.get_msgs_by_match(match_id)
        assert msgs == []

    def test_get_msgs_by_match_success(self, db_session):
        """Test obtener msgs por match_id exitosamente"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        msg1_id = msg_service.create_msg(
            match_id, "First msg", MatchEventType.PLAYER_JOIN, player_id
        )
        msg2_id = msg_service.create_msg(
            match_id, "Second msg", MatchEventType.TURN)
        other_match_id = uuid.uuid4()
        msg_service.create_msg(
            other_match_id, "Other match msg", MatchEventType.PLAYER_JOIN
        )
        msgs = msg_service.get_msgs_by_match(match_id)
        assert len(msgs) == 2
        assert all((isinstance(msg, MatchMessageOut) for msg in msgs))
        msg_ids = [msg.id for msg in msgs]
        assert msg1_id in msg_ids
        assert msg2_id in msg_ids
        for msg in msgs:
            assert msg.match_id == match_id
            assert msg.message in ["First msg", "Second msg"]

    def test_msg_service_integration_with_different_matches(self, db_session):
        """Test que los msgs se separan correctamente por partida"""
        msg_service = MessageServices(db_session)
        match1_id = uuid.uuid4()
        match2_id = uuid.uuid4()
        player_id = uuid.uuid4()
        msg1_match1 = msg_service.create_msg(
            match1_id, "Match 1 Msg 1", MatchEventType.PLAYER_JOIN, player_id
        )
        msg2_match1 = msg_service.create_msg(
            match1_id, "Match 1 Msg 2", MatchEventType.TURN
        )
        msg1_match2 = msg_service.create_msg(
            match2_id, "Match 2 Msg 1", MatchEventType.HERCULE_POIROT
        )
        match1_msgs = msg_service.get_msgs_by_match(match1_id)
        match2_msgs = msg_service.get_msgs_by_match(match2_id)
        assert len(match1_msgs) == 2
        assert len(match2_msgs) == 1
        match1_msg_ids = [msg.id for msg in match1_msgs]
        match2_msg_ids = [msg.id for msg in match2_msgs]
        assert msg1_match1 in match1_msg_ids
        assert msg2_match1 in match1_msg_ids
        assert msg1_match2 in match2_msg_ids
        assert msg1_match2 not in match1_msg_ids
        assert msg1_match1 not in match2_msg_ids
        assert msg2_match1 not in match2_msg_ids

    def test_msgs_chronological_order(self, db_session):
        """Test que los msgs mantienen orden cronológico"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        msgs_data = [
            ("First msg", MatchEventType.PLAYER_JOIN),
            ("Second msg", MatchEventType.TURN),
            ("Third msg", MatchEventType.HERCULE_POIROT),
        ]
        created_times = []
        for message, event_type in msgs_data:
            with patch("app.matches.services.datetime") as mock_datetime:
                mock_time = datetime.now() + timedelta(seconds=len(created_times))
                mock_datetime.now.return_value = mock_time
                created_times.append(mock_time)
                msg_service.create_msg(match_id, message, event_type)
        msgs = msg_service.get_msgs_by_match(match_id)
        assert len(msgs) == 3
        timestamps = [msg.created_at for msg in msgs]
        assert len(set(timestamps)) == 3
