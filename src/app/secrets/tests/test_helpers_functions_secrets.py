import uuid
import pytest

from conftest import setup_match_and_players
from app.secrets.services import Secrets_Services
from app.player.models import Match_Player
from app.secrets.models import Match_Secret,Secret,Secret_Type
from app.matches.ending import MatchEndedReason,MatchStatus, handle_match_ended

def test_get_murderer_id_success(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #inicia la partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    murderer_id = svc.get_murderer_id(match_id)

    assert murderer_id is not None

    #verificamos que murderer_id esté entre los player_id del match
    players = [mp.player_id for mp in db_session.query(Match_Player).filter_by(match_id=match_id).all()]
    assert murderer_id in players


def test_get_accomplice_id_none_when_not_present(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #inicia la partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    accomplice = svc.get_accomplice_id(match_id)

    assert accomplice is None


def test_get_murderer_and_accomplice_names(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #inicia la partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    murderer_name = svc.get_murderer_name(match_id)
    accomplice_name = svc.get_accomplice_name(match_id)

    #devuelve el nombre del murderer y devuelve None para el nombre del complice ya que solo hay 2 players y no hay complice
    assert isinstance(murderer_name, str) and murderer_name != ""
    assert (accomplice_name is None) or (isinstance(accomplice_name, str) and accomplice_name != "")

def test_is_murderer_revealed_none_before_reveal(db_session, client):
    #ningun secreto fue revelado
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]

    svc = Secrets_Services(db_session)
    result = svc.is_murderer_revealed(match_id)
    assert result is None


def test_is_murderer_revealed_after_reveal(db_session, client):
    #el secreto fue revelado devuelve el nombre del murder y None para el complice
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #inicia partida
    client.post(f"/matches/{match_str_id}/start")

    svc = Secrets_Services(db_session)

    secret = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Secret.type == Secret_Type.MURDERER)
        .first()
    )
    assert secret is not None

    # Revelamos el secreto
    svc.reveal_secret(secret.id)

    result = svc.is_murderer_revealed(match_id)
    assert result is not None
    assert result["secret_id"] == secret.id
    assert isinstance(result["murderer_name"], str)

