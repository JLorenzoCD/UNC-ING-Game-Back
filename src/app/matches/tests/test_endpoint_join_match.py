import pytest
import uuid


def test_join_match_success(client):
    # Creo player owner
    response = client.post("/players", json={
        "name":     "Owner",
        "avatar":   "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Creo partida
    match_post = {
        "name":        "Partida Test",
        "min_players": 2,
        "max_players": 4,
        "owner_id":    owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Crear otro player
    response = client.post("/players", json={
        "name":     "Jugador Nuevo",
        "avatar":   "avatar2",
        "birthday": "2000-02-02"
    })
    assert response.status_code == 201
    new_player = response.json()

    # Entro a la partida
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": new_player["id"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "match_id" in data
    assert data["match_id"] == match["id"]


def test_join_match_player_not_found(client):
    # Creo player owner
    response = client.post("/players", json={
        "name":     "Owner",
        "avatar":   "avatar1",
        "birthday": "2000-01-01"
    })
    owner = response.json()

    # Creo partida
    match_post = {
        "name":        "Partida Test",
        "min_players": 2,
        "max_players": 4,
        "owner_id":    owner["id"],
    }
    response = client.post("/matches", json=match_post)
    match = response.json()

    # UUID inexistente
    fake_player_id = str(uuid.uuid4())

    # Intenta unirse
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": fake_player_id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"


def test_join_match_same_player_twice(client):
    # Creo owner
    response = client.post("/players", json={
        "name":     "Owner3",
        "avatar":   "avatarZ",
        "birthday": "1990-03-03"
    })
    owner = response.json()

    # Creo partida
    response = client.post("/matches", json={
        "name":        "Partida Doble",
        "min_players": 2,
        "max_players": 4,
        "owner_id":    owner["id"],
    })
    match = response.json()

    # Creo otro jugador
    response = client.post("/players", json={
        "name":     "Jugador Repetido",
        "avatar":   "rep",
        "birthday": "1999-09-09"
    })
    new_player = response.json()

    # Primera vez - Bien
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": new_player["id"]}
    )
    assert response.status_code == 200

    # Segunda vez - Falla
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": new_player["id"]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Player already in"


def test_join_match_when_full(client):
    # Creo owner
    response = client.post("/players", json={
        "name":     "OwnerFull",
        "avatar":   "avatar2",
        "birthday": "1988-08-08"
    })
    owner = response.json()

    # Creo partida con máximo 2
    response = client.post("/matches", json={
        "name":        "Partida Llena",
        "min_players": 2,
        "max_players": 2,
        "owner_id":    owner["id"],
    })
    match = response.json()

    # Creo jugador 2
    response = client.post("/players", json={
        "name":     "Jugador2",
        "avatar":   "extra2",
        "birthday": "1992-02-02"
    })
    player2 = response.json()

    # Creo jugador 3
    response = client.post("/players", json={
        "name":     "Jugador3",
        "avatar":   "extra3",
        "birthday": "1993-03-03"
    })
    player3 = response.json()

    # Jugador 2 intenta entrar - Bien
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": player2["id"]}
    )
    assert response.status_code == 200

    # Jugador 3 intenta entrar - Falla porque ya está lleno
    response = client.post(
        f"/matches/{match['id']}/join",
        params={"player_id": player3["id"]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Match is full"
