import pytest
from uuid import uuid4
from datetime import date

from app.matches.models import MatchStatus, Match
from app.matches.services import MatchService
from app.matches.schemas import MatchDTO
from app.player.models import Player, Match_Player


def test_cancel_match_success(client, db_session):
    """Test successful match cancellation and deletion by owner."""
    # Create a test player
    owner = Player(name="Owner", avatar="avatar.png", birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    
    # Create a test match
    match_dto = MatchDTO(
        name="Test Match",
        min_players=2,
        max_players=4,
        owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    
    # Verify match exists
    assert db_session.query(Match).filter(Match.id == match.id).first() is not None
    
    # Cancel the match
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "Match cancelled and deleted successfully"
    assert response.json()["match_id"] == str(match.id)
    
    # Verify match was completely deleted from database
    deleted_match = db_session.query(Match).filter(Match.id == match.id).first()
    assert deleted_match is None
    
    # Verify Match_Player entries were also deleted
    match_players = db_session.query(Match_Player).filter(Match_Player.match_id == match.id).all()
    assert len(match_players) == 0


def test_cancel_match_not_owner(client, db_session):
    """Test that non-owner cannot cancel match."""
    # Create test players
    owner = Player(name="Owner", avatar="avatar.png", birthday=date(2000, 1, 1))
    other_player = Player(name="Other", avatar="avatar2.png", birthday=date(2000, 1, 2))
    db_session.add_all([owner, other_player])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other_player)
    
    # Create a test match
    match_dto = MatchDTO(
        name="Test Match",
        min_players=2,
        max_players=4,
        owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    
    # Try to cancel with different player
    response = client.post(f"/matches/{match.id}/cancel?owner_id={other_player.id}")
    
    assert response.status_code == 400
    assert "Solo el propietario de la partida puede cancelarla." in response.json()["detail"]
    
    # Verify match still exists
    existing_match = db_session.query(Match).filter(Match.id == match.id).first()
    assert existing_match is not None


def test_cancel_match_not_found(client, db_session):
    """Test cancelling non-existent match."""
    fake_match_id = uuid4()
    fake_owner_id = uuid4()
    
    response = client.post(f"/matches/{fake_match_id}/cancel?owner_id={fake_owner_id}")
    
    assert response.status_code == 404
    assert "Match not found" in response.json()["detail"]


def test_cancel_started_match(client, db_session):
    """Test that started matches (IN_PROGRESS) cannot be cancelled."""
    # Create a test player
    owner = Player(name="Owner", avatar="avatar.png", birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    
    # Create a test match
    match_dto = MatchDTO(
        name="Test Match",
        min_players=2,
        max_players=4,
        owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    
    # Start the match (change status to IN_PROGRESS)
    match_service.update_status_match(match.id, MatchStatus.IN_PROGRESS)
    
    # Try to cancel started match
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    
    assert response.status_code == 400
    assert "Solo se pueden cancelar partidas en estado 'waiting'." in response.json()["detail"]
    
    # Verify match still exists and is still in progress
    existing_match = db_session.query(Match).filter(Match.id == match.id).first()
    assert existing_match is not None
    assert existing_match.status == MatchStatus.IN_PROGRESS


def test_cancel_completed_match(client, db_session):
    """Test that completed matches cannot be cancelled."""
    # Create a test player
    owner = Player(name="Owner", avatar="avatar.png", birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    
    # Create a test match
    match_dto = MatchDTO(
        name="Test Match",
        min_players=2,
        max_players=4,
        owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    
    # Complete the match
    match_service.update_status_match(match.id, MatchStatus.COMPLETED)
    
    # Try to cancel completed match
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    
    assert response.status_code == 400
    assert "Solo se pueden cancelar partidas en estado 'waiting'." in response.json()["detail"]
    
    # Verify match still exists and is still completed
    existing_match = db_session.query(Match).filter(Match.id == match.id).first()
    assert existing_match is not None
    assert existing_match.status == MatchStatus.COMPLETED


def test_cancel_match_with_multiple_players(client, db_session):
    """Test cancelling a match with multiple players deletes all related data."""
    # Create test players
    owner = Player(name="Owner", avatar="avatar.png", birthday=date(2000, 1, 1))
    player2 = Player(name="Player2", avatar="avatar2.png", birthday=date(2000, 1, 2))
    player3 = Player(name="Player3", avatar="avatar3.png", birthday=date(2000, 1, 3))
    db_session.add_all([owner, player2, player3])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(player2)
    db_session.refresh(player3)
    
    # Create a test match
    match_dto = MatchDTO(
        name="Test Match",
        min_players=2,
        max_players=4,
        owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    
    # Add other players to the match
    match_service.join(match.id, player2.id)
    match_service.join(match.id, player3.id)
    
    # Verify all players are in the match
    match_players = db_session.query(Match_Player).filter(Match_Player.match_id == match.id).all()
    assert len(match_players) == 3
    
    # Cancel the match
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    
    assert response.status_code == 200
    
    # Verify match was completely deleted
    deleted_match = db_session.query(Match).filter(Match.id == match.id).first()
    assert deleted_match is None
    
    # Verify all Match_Player entries were deleted
    remaining_match_players = db_session.query(Match_Player).filter(Match_Player.match_id == match.id).all()
    assert len(remaining_match_players) == 0