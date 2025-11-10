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


def test_get_full_info_basic(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    #inicia la partida
    client.post(f"/matches/{match_str_id}/start")

    svc = Secrets_Services(db_session)
    info = svc.get_full_info(match_id)

    assert info is not None
    assert "murderer_secret_id" in info
    assert "murderer_name" in info
    assert "accomplice_secret_id" in info
    assert "accomplice_name" in info

    #no hay accomplice porque no tiene suficientes jugadores
    assert info['accomplice_name'] is None

def test_get_full_info_without_murderer(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]

    svc = Secrets_Services(db_session)
    info = svc.get_full_info(match_id)

    #nunca se inicio la partida, debe devolver None ya que no hay murderer
    assert info is None

def test_is_everyone_in_social_disgrace_false_when_match_not_started(db_session, client):
    """Test que verifica que no hay desgracia social cuando la partida no empezó"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]

    svc = Secrets_Services(db_session)
    result = svc.is_everyone_in_social_disgrace(match_id)
    
    # Debe devolver False porque no hay murderer asignado
    assert result is False

def test_is_everyone_in_social_disgrace_false_when_some_innocent_secrets_hidden(db_session, client):
    """Test que verifica que no hay desgracia social cuando algunos secretos inocentes no están revelados"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    # Iniciar partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    
    # Obtener todos los secretos inocentes
    innocent_secrets = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Match_Secret.match_id == match_id)
        .filter(Secret.type == Secret_Type.INNOCENT)
        .filter(Match_Secret.player_id.isnot(None))
    ).all()
    
    # Revelar solo algunos secretos inocentes (no todos)
    if len(innocent_secrets) > 1:
        svc.reveal_secret(innocent_secrets[0].id)
    
    result = svc.is_everyone_in_social_disgrace(match_id)
    
    # Debe devolver False porque no todos los secretos inocentes están revelados
    assert result is False

def test_is_everyone_in_social_disgrace_true_when_all_innocent_secrets_revealed(db_session, client):
    """Test que verifica que hay desgracia social cuando todos los secretos inocentes están revelados"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    # Iniciar partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    
    # Obtener todos los secretos inocentes
    innocent_secrets = (
        db_session.query(Match_Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Match_Secret.match_id == match_id)
        .filter(Secret.type == Secret_Type.INNOCENT)
        .filter(Match_Secret.player_id.isnot(None))
    ).all()
    
    # Revelar todos los secretos inocentes
    for secret in innocent_secrets:
        svc.reveal_secret(secret.id)
    
    result = svc.is_everyone_in_social_disgrace(match_id)
    
    # Debe devolver True porque todos los secretos inocentes están revelados
    assert result is True

def test_is_everyone_in_social_disgrace_two_players_scenario(db_session, client):
    """Test que verifica el escenario específico de 2 jugadores donde el inocente queda en desgracia social"""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    owner_id = setup["owner_id"]
    player2_id = setup["player2_id"]

    # Iniciar partida
    resp = client.post(f"/matches/{match_str_id}/start")
    assert resp.status_code == 200

    svc = Secrets_Services(db_session)
    
    # Obtener el ID del murderer
    murderer_id = svc.get_murderer_id(match_id)
    
    # Determinar quién es el inocente
    innocent_id = player2_id if murderer_id == owner_id else owner_id
    
    # Obtener todos los secretos del jugador inocente
    innocent_secrets = (
        db_session.query(Match_Secret)
        .filter(Match_Secret.match_id == match_id)
        .filter(Match_Secret.player_id == innocent_id)
    ).all()
    
    # Revelar todos los secretos del jugador inocente
    for secret in innocent_secrets:
        svc.reveal_secret(secret.id)
    
    result = svc.is_everyone_in_social_disgrace(match_id)
    
    # Debe devolver True porque el jugador inocente tiene todos sus secretos revelados
    # independientemente de si quedan secretos INNOCENT sin revelar que pertenecen al murderer
    assert result is True