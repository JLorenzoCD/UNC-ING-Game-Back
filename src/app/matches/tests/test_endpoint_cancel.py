from datetime import date
from uuid import uuid4

from app.matches.models import Match, MatchStatus
from app.matches.schemas import MatchDTO
from app.matches.services import MatchService
from app.matches.lifecycle_service import MatchLifecycleServices
from app.player.models import Match_Player, Player


def test_cancel_completed_match(client, db_session):
    """Test that completed matches cannot be cancelled."""
    owner = Player(name="Owner", avatar="avatar.png",
                   birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    match_dto = MatchDTO(
        name="Test Match", min_players=2, max_players=4, owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    match_service.update_status_match(match.id, MatchStatus.COMPLETED)
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    assert response.status_code == 400
    assert (
        "Solo se pueden cancelar partidas en estado 'waiting'."
        in response.json()["detail"]
    )
    existing_match = db_session.query(
        Match).filter(Match.id == match.id).first()
    assert existing_match is not None
    assert existing_match.status == MatchStatus.COMPLETED


def test_cancel_match_not_found(client, db_session):
    """Test cancelling non-existent match."""
    fake_match_id = uuid4()
    fake_owner_id = uuid4()
    response = client.post(
        f"/matches/{fake_match_id}/cancel?owner_id={fake_owner_id}")
    assert response.status_code == 404
    assert "Match not found" in response.json()["detail"]


def test_cancel_match_not_owner(client, db_session):
    """Test that non-owner cannot cancel match."""
    owner = Player(name="Owner", avatar="avatar.png",
                   birthday=date(2000, 1, 1))
    other_player = Player(
        name="Other", avatar="avatar2.png", birthday=date(2000, 1, 2))
    db_session.add_all([owner, other_player])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(other_player)
    match_dto = MatchDTO(
        name="Test Match", min_players=2, max_players=4, owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    response = client.post(
        f"/matches/{match.id}/cancel?owner_id={other_player.id}")
    assert response.status_code == 400
    assert (
        "Solo el propietario de la partida puede cancelarla."
        in response.json()["detail"]
    )
    existing_match = db_session.query(
        Match).filter(Match.id == match.id).first()
    assert existing_match is not None


def test_cancel_match_success(client, db_session):
    """Test successful match cancellation and deletion by owner."""
    owner = Player(name="Owner", avatar="avatar.png",
                   birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    match_dto = MatchDTO(
        name="Test Match", min_players=2, max_players=4, owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    assert db_session.query(Match).filter(
        Match.id == match.id).first() is not None
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    assert response.status_code == 200
    assert response.json()[
        "status"] == "Match cancelled and deleted successfully"
    assert response.json()["match_id"] == str(match.id)
    deleted_match = db_session.query(
        Match).filter(Match.id == match.id).first()
    assert deleted_match is None
    match_players = (
        db_session.query(Match_Player).filter(
            Match_Player.match_id == match.id).all()
    )
    assert len(match_players) == 0


def test_cancel_match_with_multiple_players(client, db_session):
    """Test cancelling a match with multiple players deletes all related data."""
    owner = Player(name="Owner", avatar="avatar.png",
                   birthday=date(2000, 1, 1))
    player2 = Player(name="Player2", avatar="avatar2.png",
                     birthday=date(2000, 1, 2))
    player3 = Player(name="Player3", avatar="avatar3.png",
                     birthday=date(2000, 1, 3))
    db_session.add_all([owner, player2, player3])
    db_session.commit()
    db_session.refresh(owner)
    db_session.refresh(player2)
    db_session.refresh(player3)
    match_dto = MatchDTO(
        name="Test Match", min_players=2, max_players=4, owner_id=owner.id
    )
    match_service = MatchService(db_session)
    lifecycle_service = MatchLifecycleServices(db_session)
    match = match_service.create(match_dto)
    lifecycle_service.join(match.id, player2.id)
    lifecycle_service.join(match.id, player3.id)
    match_players = (
        db_session.query(Match_Player).filter(
            Match_Player.match_id == match.id).all()
    )
    assert len(match_players) == 3
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    assert response.status_code == 200
    deleted_match = db_session.query(
        Match).filter(Match.id == match.id).first()
    assert deleted_match is None
    remaining_match_players = (
        db_session.query(Match_Player).filter(
            Match_Player.match_id == match.id).all()
    )
    assert len(remaining_match_players) == 0


def test_cancel_started_match(client, db_session):
    """Test that started matches (IN_PROGRESS) cannot be cancelled."""
    owner = Player(name="Owner", avatar="avatar.png",
                   birthday=date(2000, 1, 1))
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    match_dto = MatchDTO(
        name="Test Match", min_players=2, max_players=4, owner_id=owner.id
    )
    match_service = MatchService(db_session)
    match = match_service.create(match_dto)
    match_service.update_status_match(match.id, MatchStatus.IN_PROGRESS)
    response = client.post(f"/matches/{match.id}/cancel?owner_id={owner.id}")
    assert response.status_code == 400
    assert (
        "Solo se pueden cancelar partidas en estado 'waiting'."
        in response.json()["detail"]
    )
    existing_match = db_session.query(
        Match).filter(Match.id == match.id).first()
    assert existing_match is not None
    assert existing_match.status == MatchStatus.IN_PROGRESS
