import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.matches.services import MatchService, PlayerNotInMatch
from app.matches.lifecycle_service import MatchLifecycleService
from app.player.models import Match_Player, Player


def test_quit_match_service_database_error(db_session):
    """Test que quit_match maneja errores de base de datos correctamente"""
    player = Player(
        id=uuid.uuid4(), name="Test Player", avatar="avatar1", birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()
    match_id = uuid.uuid4()
    match_player = Match_Player(match_id=match_id, player_id=player.id, order=1)
    db_session.add(match_player)
    db_session.commit()
    service = MatchLifecycleService(db_session)
    original_commit = db_session.commit
    original_rollback = db_session.rollback

    def mock_commit():
        """Mock commit."""
        raise SQLAlchemyError("Database connection error")

    db_session.commit = mock_commit
    db_session.rollback = MagicMock()
    with pytest.raises(SQLAlchemyError):
        service.quit_match(match_id, player.id)
    db_session.rollback.assert_called_once()
    db_session.commit = original_commit
    db_session.rollback = original_rollback


def test_quit_match_service_multiple_players_same_match(db_session):
    """Test quit_match con múltiples jugadores en la misma partida"""
    match_id = uuid.uuid4()
    player1 = Player(
        id=uuid.uuid4(), name="Player 1", avatar="avatar1", birthday=date(2000, 1, 1)
    )
    player2 = Player(
        id=uuid.uuid4(), name="Player 2", avatar="avatar2", birthday=date(2000, 2, 2)
    )
    db_session.add_all([player1, player2])
    db_session.commit()
    match_player1 = Match_Player(match_id=match_id, player_id=player1.id, order=1)
    match_player2 = Match_Player(match_id=match_id, player_id=player2.id, order=2)
    db_session.add_all([match_player1, match_player2])
    db_session.commit()
    assert (
        db_session.query(Match_Player).filter(Match_Player.match_id == match_id).count()
        == 2
    )
    service = MatchLifecycleService(db_session)
    service.quit_match(match_id, player1.id)
    remaining_players = (
        db_session.query(Match_Player).filter(Match_Player.match_id == match_id).all()
    )
    assert len(remaining_players) == 1
    assert remaining_players[0].player_id == player2.id
    service.quit_match(match_id, player2.id)
    assert (
        db_session.query(Match_Player).filter(Match_Player.match_id == match_id).count()
        == 0
    )


def test_quit_match_service_player_in_different_matches(db_session):
    """Test quit_match cuando un jugador está en múltiples partidas"""
    player = Player(
        id=uuid.uuid4(),
        name="Multi Player",
        avatar="avatar1",
        birthday=date(2000, 1, 1),
    )
    db_session.add(player)
    db_session.commit()
    match_id1 = uuid.uuid4()
    match_id2 = uuid.uuid4()
    match_player1 = Match_Player(match_id=match_id1, player_id=player.id, order=1)
    match_player2 = Match_Player(match_id=match_id2, player_id=player.id, order=1)
    db_session.add_all([match_player1, match_player2])
    db_session.commit()
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.player_id == player.id)
        .count()
        == 2
    )
    service = MatchLifecycleService(db_session)
    service.quit_match(match_id1, player.id)
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_id1, Match_Player.player_id == player.id)
        .first()
        is None
    )
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_id2, Match_Player.player_id == player.id)
        .first()
        is not None
    )


def test_quit_match_service_player_not_in_match(db_session):
    """Test que quit_match lanza PlayerNotInMatch cuando el jugador no está en la partida"""
    match_id = uuid.uuid4()
    player_id = uuid.uuid4()
    service = MatchLifecycleService(db_session)
    with pytest.raises(PlayerNotInMatch):
        service.quit_match(match_id, player_id)


def test_quit_match_service_success(db_session):
    """Test que el servicio quit_match elimina correctamente la relación match-player"""
    player = Player(
        id=uuid.uuid4(), name="Test Player", avatar="avatar1", birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()
    match_id = uuid.uuid4()
    match_player = Match_Player(match_id=match_id, player_id=player.id, order=1)
    db_session.add(match_player)
    db_session.commit()
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_id, Match_Player.player_id == player.id)
        .first()
        is not None
    )
    service = MatchLifecycleService(db_session)
    service.quit_match(match_id, player.id)
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_id, Match_Player.player_id == player.id)
        .first()
        is None
    )


def test_quit_match_service_with_existing_order(db_session):
    """Test quit_match preserva los datos correctos y no afecta otros campos"""
    player = Player(
        id=uuid.uuid4(), name="Test Player", avatar="avatar1", birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()
    match_id = uuid.uuid4()
    match_player = Match_Player(
        match_id=match_id, player_id=player.id, order=5, role=None
    )
    db_session.add(match_player)
    db_session.commit()
    service = MatchLifecycleService(db_session)
    service.quit_match(match_id, player.id)
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_id, Match_Player.player_id == player.id)
        .first()
        is None
    )
