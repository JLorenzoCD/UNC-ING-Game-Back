import uuid
import pytest
from app.matches.services import MatchService
from app.secrets.models import Secret,Secret_Type,Match_Secret
from unittest.mock import MagicMock, patch
from app.secrets import models
from sqlalchemy import func

def test_get_secrets(client, db_session):
    #creo player
    response = client.post("/players", json={
        "name": "creador",
        "avatar": "avatar1",
        "birthday": "2000-01-02"
    })
    assert response.status_code == 201
    owner = response.json()
    owner_id = uuid.UUID(owner["id"])

    #creo partida
    match_post = {
        "name": "partidaTest",
        "min_players": 2,
        "max_players": 4,
        "owner_id": owner["id"]
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code==201
    match = response.json()
    match_id = uuid.UUID(match["id"])

    #creo otro player
    response = client.post("/players", json={
        "name": "hernan",
        "avatar": "avatar1",
        "birthday": "2000-06-21"
    })
    assert response.status_code == 201
    new_player = response.json()
    new_player_id = uuid.UUID(new_player["id"])

    #entro a la partida
    response = client.post(f"/matches/{match['id']}/join", params={"player_id": new_player["id"]})
    assert response.status_code == 200

    #agrego los secretos

    db_session.add_all([
        #instanciar secretos
        Secret(id=uuid.uuid4(), type="MURDERER", content="You are the Murderer!"),
                Secret(id=uuid.uuid4(), type="ACCOMPLICE", content="You are the Accomplice!"),
                Secret(id=uuid.uuid4(), type="INNOCENT", content="You are Innocent!")
    ])
    db_session.commit()

    secret_count = db_session.query(Secret).count()
    assert secret_count==3

    secret1=db_session.query(models.Secret).order_by(func.random()).first()
    secret2=db_session.query(models.Secret).order_by(func.random()).first()
    secret3=db_session.query(models.Secret).order_by(func.random()).first()
    secret4=db_session.query(models.Secret).order_by(func.random()).first()
    secret5=db_session.query(models.Secret).order_by(func.random()).first()
    secret6=db_session.query(models.Secret).order_by(func.random()).first()

    if not(secret1 and secret2 and secret3 and secret4 and secret5 and secret6):
        pytest.fail("No se pudieron obtener todos los secretos necesarios")

    match_secret1 = Match_Secret(
        secret_id=secret1.id,
        match_id = match_id,
        player_id = owner_id
    )
    match_secret2 = Match_Secret(
        secret_id=secret2.id,
        match_id = match_id,
        player_id = owner_id
    )
    match_secret3 = Match_Secret(
        secret_id=secret3.id,
        match_id = match_id,
        player_id = owner_id
    )
    match_secret4 = Match_Secret(
        secret_id=secret4.id,
        match_id = match_id,
        player_id = owner_id
    )
    match_secret5 = Match_Secret(
        secret_id=secret5.id,
        match_id = match_id,
        player_id = owner_id
    )
    match_secret6 = Match_Secret(
        secret_id=secret6.id,
        match_id = match_id,
        player_id = owner_id
    )

    db_session.add_all([
        match_secret1,
        match_secret2,
        match_secret3,
        match_secret4,
        match_secret5,
        match_secret6
        ])
    db_session.commit()

    response_secret = client.get(f"/matches/{match['id']}/secrets")
    assert response_secret.status_code == 200
    data = response_secret.json()

    #verifica que es una lista y tiene elementos
    assert isinstance(data, list)
    assert len(data)==6

    for secret_data in data:
        #id es distinto al secret_id
        assert secret_data['id'] != secret_data['secret_id'], f"id y secret_id no deben ser iguales: {secret_data}"
        #match_id exista y sea el correcto
        assert 'match_id' in secret_data, "Falta campo match_id"
        assert secret_data['match_id'] == str(match_id), f"match_id incorrecto: {secret_data['match_id']}"




def test_get_secrets_empty_match(client, db_session):
    #creo un jugador
    response = client.post("/players", json={
        "name": "creador",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    owner = response.json()

    #creo partida
    response = client.post("/matches", json={
        "name": "PartidaSinSecretos",
        "min_players": 2,
        "max_players": 4,
        "owner_id": owner["id"]
    })
    match = response.json()

    #llamo al endpoint de secretos sin haber iniciado la partida ni nada
    response = client.get(f"/matches/{match['id']}/secrets")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 0  #no hay secretos todavía