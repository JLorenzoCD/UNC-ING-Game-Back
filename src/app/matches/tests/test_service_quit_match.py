import pytest
import uuid
from uuid import UUID
from unittest.mock import MagicMock
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from datetime import date

from app.matches.services import MatchService, PlayerNotInMatch
from app.player.models import Match_Player, Player


def test_quit_match_service_success(db_session):
    """Test que el servicio quit_match elimina correctamente la relación match-player"""
    # Crear jugador en la DB
    player = Player(
        id=uuid.uuid4(),
        name="Test Player",
        avatar="avatar1",
        birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()

    # Crear match_player en la DB
    match_id = uuid.uuid4()
    match_player = Match_Player(
        match_id=match_id,
        player_id=player.id,
        order=1
    )
    db_session.add(match_player)
    db_session.commit()

    # Verificar que existe la relación
    assert db_session.query(Match_Player).filter(
        Match_Player.match_id == match_id,
        Match_Player.player_id == player.id
    ).first() is not None

    # Ejecutar quit_match
    service = MatchService(db_session)
    service.quit_match(match_id, player.id)

    # Verificar que se eliminó la relación
    assert db_session.query(Match_Player).filter(
        Match_Player.match_id == match_id,
        Match_Player.player_id == player.id
    ).first() is None


def test_quit_match_service_player_not_in_match(db_session):
    """Test que quit_match lanza PlayerNotInMatch cuando el jugador no está en la partida"""
    match_id = uuid.uuid4()
    player_id = uuid.uuid4()

    # Ejecutar quit_match sin que exista la relación match_player
    service = MatchService(db_session)
    
    with pytest.raises(PlayerNotInMatch):
        service.quit_match(match_id, player_id)


def test_quit_match_service_database_error(db_session):
    """Test que quit_match maneja errores de base de datos correctamente"""
    # Crear jugador en la DB
    player = Player(
        id=uuid.uuid4(),
        name="Test Player",
        avatar="avatar1",
        birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()

    # Crear match_player en la DB
    match_id = uuid.uuid4()
    match_player = Match_Player(
        match_id=match_id,
        player_id=player.id,
        order=1
    )
    db_session.add(match_player)
    db_session.commit()

    # Mockear la sesión de DB para que falle en commit
    service = MatchService(db_session)
    original_commit = db_session.commit
    original_rollback = db_session.rollback

    def mock_commit():
        raise SQLAlchemyError("Database connection error")

    db_session.commit = mock_commit
    db_session.rollback = MagicMock()

    # Ejecutar quit_match y verificar que maneja el error
    with pytest.raises(SQLAlchemyError):
        service.quit_match(match_id, player.id)

    # Verificar que se llamó rollback
    db_session.rollback.assert_called_once()

    # Restaurar métodos originales
    db_session.commit = original_commit
    db_session.rollback = original_rollback


def test_quit_match_service_multiple_players_same_match(db_session):
    """Test quit_match con múltiples jugadores en la misma partida"""
    match_id = uuid.uuid4()
    
    # Crear dos jugadores
    player1 = Player(
        id=uuid.uuid4(),
        name="Player 1",
        avatar="avatar1",
        birthday=date(2000, 1, 1)
    )
    player2 = Player(
        id=uuid.uuid4(),
        name="Player 2",
        avatar="avatar2",
        birthday=date(2000, 2, 2)
    )
    db_session.add_all([player1, player2])
    db_session.commit()

    # Crear relaciones match_player para ambos
    match_player1 = Match_Player(
        match_id=match_id,
        player_id=player1.id,
        order=1
    )
    match_player2 = Match_Player(
        match_id=match_id,
        player_id=player2.id,
        order=2
    )
    db_session.add_all([match_player1, match_player2])
    db_session.commit()

    # Verificar que ambos jugadores están en la partida
    assert db_session.query(Match_Player).filter(Match_Player.match_id == match_id).count() == 2

    # Player1 abandona la partida
    service = MatchService(db_session)
    service.quit_match(match_id, player1.id)

    # Verificar que solo quedó player2
    remaining_players = db_session.query(Match_Player).filter(Match_Player.match_id == match_id).all()
    assert len(remaining_players) == 1
    assert remaining_players[0].player_id == player2.id

    # Player2 también abandona
    service.quit_match(match_id, player2.id)

    # Verificar que no quedan jugadores
    assert db_session.query(Match_Player).filter(Match_Player.match_id == match_id).count() == 0


def test_quit_match_service_player_in_different_matches(db_session):
    """Test quit_match cuando un jugador está en múltiples partidas"""
    player = Player(
        id=uuid.uuid4(),
        name="Multi Player",
        avatar="avatar1",
        birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()

    # Crear dos partidas diferentes
    match_id1 = uuid.uuid4()
    match_id2 = uuid.uuid4()

    # Agregar el jugador a ambas partidas
    match_player1 = Match_Player(
        match_id=match_id1,
        player_id=player.id,
        order=1
    )
    match_player2 = Match_Player(
        match_id=match_id2,
        player_id=player.id,
        order=1
    )
    db_session.add_all([match_player1, match_player2])
    db_session.commit()

    # Verificar que el jugador está en ambas partidas
    assert db_session.query(Match_Player).filter(
        Match_Player.player_id == player.id
    ).count() == 2

    # El jugador abandona solo la primera partida
    service = MatchService(db_session)
    service.quit_match(match_id1, player.id)

    # Verificar que sigue en la segunda partida pero no en la primera
    assert db_session.query(Match_Player).filter(
        Match_Player.match_id == match_id1,
        Match_Player.player_id == player.id
    ).first() is None

    assert db_session.query(Match_Player).filter(
        Match_Player.match_id == match_id2,
        Match_Player.player_id == player.id
    ).first() is not None


def test_quit_match_service_with_existing_order(db_session):
    """Test quit_match preserva los datos correctos y no afecta otros campos"""
    player = Player(
        id=uuid.uuid4(),
        name="Test Player",
        avatar="avatar1",
        birthday=date(2000, 1, 1)
    )
    db_session.add(player)
    db_session.commit()

    match_id = uuid.uuid4()
    match_player = Match_Player(
        match_id=match_id,
        player_id=player.id,
        order=5,
        role=None  # Esto podría ser un enum en el modelo real
    )
    db_session.add(match_player)
    db_session.commit()

    # Ejecutar quit_match
    service = MatchService(db_session)
    service.quit_match(match_id, player.id)

    # Verificar que el registro específico fue eliminado
    assert db_session.query(Match_Player).filter(
        Match_Player.match_id == match_id,
        Match_Player.player_id == player.id
    ).first() is None