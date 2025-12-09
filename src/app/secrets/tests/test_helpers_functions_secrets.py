from conftest import setup_match_and_players

from app.player.models import Match_Player
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.secrets.services import Secrets_Services


def test_get_accomplice_id_none_when_not_present(db_session, client):
    """Test get accomplice id none when not present.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    accomplice = svc.get_accomplice_id(match_id)
    assert accomplice is None


def test_get_full_info_basic(db_session, client):
    """Test get full info basic.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    client.post(f"/matches/{match_str_id}/start")
    svc = Secrets_Services(db_session)
    info = svc.get_full_info(match_id)
    assert info is not None
    assert "murderer_secret_id" in info
    assert "murderer_name" in info
    assert "accomplice_secret_id" in info
    assert "accomplice_name" in info
    assert info["accomplice_name"] is None


def test_get_full_info_without_murderer(db_session, client):
    """Test get full info without murderer.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    svc = Secrets_Services(db_session)
    info = svc.get_full_info(match_id)
    assert info is None


def test_get_murderer_and_accomplice_names(db_session, client):
    """Test get murderer and accomplice names.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    murderer_name = svc.get_murderer_name(match_id)
    accomplice_name = svc.get_accomplice_name(match_id)
    assert isinstance(murderer_name, str) and murderer_name != ""
    assert accomplice_name is None or (
        isinstance(accomplice_name, str) and accomplice_name != ""
    )


def test_get_murderer_id_success(db_session, client):
    """Test get murderer id success.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    murderer_id = svc.get_murderer_id(match_id)
    assert murderer_id is not None
    players = [
        mp.player_id
        for mp in db_session.query(Match_Player).filter_by(match_id=match_id).all()
    ]
    assert murderer_id in players


def test_is_everyone_in_social_disgrace_false_when_match_not_started(
    db_session, client
):
    """Test que verifica que no hay desgracia social cuando la partida no empezó"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    svc = Secrets_Services(db_session)
    result = svc.is_everyone_in_social_disgrace(match_id)
    assert result is False


def test_is_everyone_in_social_disgrace_false_when_some_innocent_secrets_hidden(
    db_session, client
):
    """Test que verifica que no hay desgracia social cuando algunos secretos inocentes no están revelados"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    innocent_secrets = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Match_Secret.match_id == match_id)
        .filter(Secret.type == Secret_Type.INNOCENT)
        .filter(Match_Secret.player_id.isnot(None))
        .all()
    )
    if len(innocent_secrets) > 1:
        svc.reveal_secret(innocent_secrets[0].id)
    result = svc.is_everyone_in_social_disgrace(match_id)
    assert result is False


def test_is_everyone_in_social_disgrace_true_when_all_innocent_secrets_revealed(
    db_session, client
):
    """Test que verifica que hay desgracia social cuando todos los secretos inocentes están revelados"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    innocent_secrets = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Match_Secret.match_id == match_id)
        .filter(Secret.type == Secret_Type.INNOCENT)
        .filter(Match_Secret.player_id.isnot(None))
        .all()
    )
    for secret in innocent_secrets:
        svc.reveal_secret(secret.id)
    result = svc.is_everyone_in_social_disgrace(match_id)
    assert result is True


def test_is_everyone_in_social_disgrace_two_players_scenario(db_session, client):
    """Test que verifica el escenario específico de 2 jugadores donde el inocente queda en desgracia social"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    owner_id = setup["owner_id"]
    player2_id = setup["player2_id"]
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200
    svc = Secrets_Services(db_session)
    murderer_id = svc.get_murderer_id(match_id)
    innocent_id = player2_id if murderer_id == owner_id else owner_id
    innocent_secrets = (
        db_session.query(Match_Secret)
        .filter(Match_Secret.match_id == match_id)
        .filter(Match_Secret.player_id == innocent_id)
        .all()
    )
    for secret in innocent_secrets:
        svc.reveal_secret(secret.id)
    result = svc.is_everyone_in_social_disgrace(match_id)
    assert result is True


def test_is_murderer_revealed_after_reveal(db_session, client):
    """Test is murderer revealed after reveal.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    client.post(f"/matches/{match_str_id}/start")
    svc = Secrets_Services(db_session)
    secret = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Secret.type == Secret_Type.MURDERER)
        .first()
    )
    assert secret is not None
    svc.reveal_secret(secret.id)
    result = svc.is_murderer_revealed(match_id)
    assert result is not None
    assert result["secret_id"] == secret.id
    assert isinstance(result["murderer_name"], str)


def test_is_murderer_revealed_none_before_reveal(db_session, client):
    """Test is murderer revealed none before reveal.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    svc = Secrets_Services(db_session)
    result = svc.is_murderer_revealed(match_id)
    assert result is None
