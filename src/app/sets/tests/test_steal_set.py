import uuid
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.sets.models import Match_Set, SetType
from app.sets.schemas import MatchSetOut
from app.sets.services import InvalidSetError, SetServices
from app.sets.tests.conftest import setup_match_and_players


class TestStealSet:
    """Suite de pruebas para el método steal_set en SetServices"""

    def test_steal_set_database_error_rollback(self, db_session, client):
        """Prueba que los errores de base de datos se manejen correctamente con rollback"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.PARKER_PYNE,
            player_id=owner_id,
            match_id=match_id,
            quin_play=False,
            quin_count=0,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = original_set
        mock_db.commit.side_effect = SQLAlchemyError("Error de base de datos")
        mock_db.rollback = Mock()
        set_service = SetServices(mock_db)
        with pytest.raises(SQLAlchemyError):
            set_service.steal_set(original_set.id, player2_id)
        mock_db.rollback.assert_called_once()

    def test_steal_set_invalid_uuid_format(self, db_session, client):
        """Prueba el comportamiento cuando se proporciona un UUID que no existe"""
        setup_data = setup_match_and_players(client, db_session)
        player2_id = setup_data["player2_id"]
        set_service = SetServices(db_session)
        non_existent_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        with pytest.raises(InvalidSetError):
            set_service.steal_set(non_existent_uuid, player2_id)

    def test_steal_set_multiple_sets_independence(self, db_session, client):
        """Prueba que robar un set no afecta otros sets"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        set1 = Match_Set(
            type=SetType.PARKER_PYNE,
            player_id=owner_id,
            match_id=match_id,
            quin_play=False,
            quin_count=0,
        )
        set2 = Match_Set(
            type=SetType.LADY_EILEEN,
            player_id=owner_id,
            match_id=match_id,
            quin_play=True,
            quin_count=1,
        )
        db_session.add_all([set1, set2])
        db_session.commit()
        db_session.refresh(set1)
        db_session.refresh(set2)
        set_service = SetServices(db_session)
        result = set_service.steal_set(set1.id, player2_id)
        assert result.player_id == player2_id
        assert result.id == set1.id
        unchanged_set = (
            db_session.query(Match_Set).filter(Match_Set.id == set2.id).first()
        )
        assert unchanged_set.player_id == owner_id

    def test_steal_set_nonexistent_set_id(self, db_session, client):
        """Prueba que se lanza InvalidSetError al intentar robar un set inexistente"""
        setup_data = setup_match_and_players(client, db_session)
        player2_id = setup_data["player2_id"]
        fake_set_id = uuid.uuid4()
        set_service = SetServices(db_session)
        with pytest.raises(
            InvalidSetError, match=f"No se encontró el set con id {fake_set_id}"
        ):
            set_service.steal_set(fake_set_id, player2_id)

    def test_steal_set_preserves_all_original_properties(self, db_session, client):
        """Prueba que todas las propiedades originales se preservan excepto player_id"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.TOMMY_BERESFORD,
            player_id=owner_id,
            match_id=match_id,
            quin_play=True,
            quin_count=1,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        original_id = original_set.id
        original_type = original_set.type
        original_match_id = original_set.match_id
        original_quin_play = original_set.quin_play
        original_quin_count = original_set.quin_count
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player2_id)
        assert result.id == original_id
        assert result.type == original_type
        assert result.match_id == original_match_id
        assert result.quin_play == original_quin_play
        assert result.quin_count == original_quin_count
        assert result.player_id == player2_id

    def test_steal_set_same_player(self, db_session, client):
        """Prueba robar un set por el mismo jugador que ya lo posee"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        original_set = Match_Set(
            type=SetType.PARKER_PYNE,
            player_id=owner_id,
            match_id=match_id,
            quin_play=False,
            quin_count=0,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, owner_id)
        assert result.player_id == owner_id
        assert result.id == original_set.id

    def test_steal_set_success(self, db_session, client):
        """Prueba el robo exitoso de un set de un jugador a otro"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.PARKER_PYNE,
            player_id=owner_id,
            match_id=match_id,
            quin_play=False,
            quin_count=0,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player2_id)
        assert isinstance(result, MatchSetOut)
        assert result.id == original_set.id
        assert result.type == SetType.PARKER_PYNE
        assert result.player_id == player2_id
        assert result.match_id == match_id
        assert result.quin_play == False
        assert result.quin_count == 0
        updated_set = (
            db_session.query(Match_Set).filter(
                Match_Set.id == original_set.id).first()
        )
        assert updated_set.player_id == player2_id

    def test_steal_set_third_player(self, db_session, client):
        """Prueba el robo de un set que involucra a un tercer jugador"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        response = client.post(
            "/players",
            json={
                "name": "Tercer Jugador",
                "avatar": "avatar3",
                "birthday": "2000-03-03",
            },
        )
        assert response.status_code == 201
        player3 = response.json()
        player3_id = uuid.UUID(player3["id"])
        original_set = Match_Set(
            type=SetType.MISS_MARPLE,
            player_id=player2_id,
            match_id=match_id,
            quin_play=True,
            quin_count=1,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player3_id)
        assert result.player_id == player3_id
        assert result.type == SetType.MISS_MARPLE

    def test_steal_set_tommy_beresford_type(self, db_session, client):
        """Prueba específica para el tipo de set TOMMY_BERESFORD"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.TOMMY_BERESFORD,
            player_id=owner_id,
            match_id=match_id,
            quin_play=False,
            quin_count=0,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player2_id)
        assert result.type == SetType.TOMMY_BERESFORD
        assert result.player_id == player2_id

    def test_steal_set_tuppence_beresford_type(self, db_session, client):
        """Prueba específica para el tipo de set TUPPENCE_BERESFORD"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.TUPPENCE_BERESFORD,
            player_id=owner_id,
            match_id=match_id,
            quin_play=True,
            quin_count=1,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player2_id)
        assert result.type == SetType.TUPPENCE_BERESFORD
        assert result.player_id == player2_id
        assert result.quin_play == True
        assert result.quin_count == 1

    def test_steal_set_with_different_set_types(self, db_session, client):
        """Prueba el robo de sets de diferentes tipos"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        test_cases = [
            SetType.HERCULE_POIROT,
            SetType.MISS_MARPLE,
            SetType.LADY_EILEEN,
            SetType.TWO_BERESFORD,
            SetType.MR_SATTERTHWAITE,
        ]
        for set_type in test_cases:
            original_set = Match_Set(
                type=set_type,
                player_id=owner_id,
                match_id=match_id,
                quin_play=True,
                quin_count=1,
            )
            db_session.add(original_set)
            db_session.commit()
            db_session.refresh(original_set)
            set_service = SetServices(db_session)
            result = set_service.steal_set(original_set.id, player2_id)
            assert result.type == set_type
            assert result.player_id == player2_id
            assert result.quin_play == True
            assert result.quin_count == 1

    def test_steal_set_with_quin_properties(self, db_session, client):
        """Prueba que las propiedades quin se preservan al robar un set"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        original_set = Match_Set(
            type=SetType.HERCULE_POIROT,
            player_id=owner_id,
            match_id=match_id,
            quin_play=True,
            quin_count=2,
        )
        db_session.add(original_set)
        db_session.commit()
        db_session.refresh(original_set)
        set_service = SetServices(db_session)
        result = set_service.steal_set(original_set.id, player2_id)
        assert result.quin_play == True
        assert result.quin_count == 2
        assert result.player_id == player2_id
