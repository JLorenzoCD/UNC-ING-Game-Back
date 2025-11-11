import pytest
import uuid
from uuid import UUID
from unittest.mock import patch, AsyncMock, Mock


def test_quit_match_success(client):
    """Test que un jugador puede abandonar una partida exitosamente"""
    # Crear owner
    response = client.post("/players", json={
        "name": "Owner Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Crear partida
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Crear segundo jugador
    response = client.post("/players", json={
        "name": "Player Two",
        "avatar": "avatar2",
        "birthday": "2000-02-02"
    })
    assert response.status_code == 201
    player2 = response.json()

    # Unir segundo jugador a la partida
    response = client.post(f"/matches/{match['id']}/join", params={"player_id": player2['id']})
    assert response.status_code == 200

    # Verificar que hay 2 jugadores en la partida
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 2

    # El segundo jugador abandona la partida (con WebSocket mockeado)
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock) as mock_broadcast, \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock) as mock_quit:
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": player2['id']})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verificar que ahora solo hay 1 jugador en la partida
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 1
    assert players[0]["player_id"] == owner["id"]

    # Verificar que se llamaron los métodos de WebSocket
    mock_broadcast.assert_called_once()
    mock_quit.assert_called_once_with(UUID(player2['id']), UUID(match['id']))


def test_quit_match_player_not_found(client):
    """Test que falla cuando el jugador no existe"""
    # Crear owner
    response = client.post("/players", json={
        "name": "Owner Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Crear partida
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Intentar que un jugador inexistente abandone la partida
    fake_player_id = str(uuid.uuid4())
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": fake_player_id})
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"


def test_quit_match_player_not_in_match(client):
    """Test que falla cuando el jugador no está en la partida"""
    # Crear owner
    response = client.post("/players", json={
        "name": "Owner Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Crear partida
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Crear otro jugador que NO se une a la partida
    response = client.post("/players", json={
        "name": "External Player",
        "avatar": "avatar2",
        "birthday": "2000-02-02"
    })
    assert response.status_code == 201
    external_player = response.json()

    # Intentar que el jugador externo abandone la partida
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": external_player['id']})
    
    assert response.status_code == 404  # El servicio lanza HTTPException(404) para "Player not in match"


def test_quit_match_owner_can_quit(client):
    """Test que el owner también puede abandonar la partida"""
    # Crear owner
    response = client.post("/players", json={
        "name": "Owner Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Crear partida
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Crear segundo jugador
    response = client.post("/players", json={
        "name": "Player Two",
        "avatar": "avatar2",
        "birthday": "2000-02-02"
    })
    assert response.status_code == 201
    player2 = response.json()

    # Unir segundo jugador a la partida
    response = client.post(f"/matches/{match['id']}/join", params={"player_id": player2['id']})
    assert response.status_code == 200

    # El owner abandona la partida
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": owner['id']})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verificar que solo queda un jugador
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 1
    assert players[0]["player_id"] == player2["id"]


def test_quit_match_invalid_match_id(client):
    """Test que falla con un match_id inexistente"""
    # Crear jugador
    response = client.post("/players", json={
        "name": "Test Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    player = response.json()

    # Intentar abandonar una partida inexistente
    fake_match_id = str(uuid.uuid4())
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{fake_match_id}/quit", params={"player_id": player['id']})
    
    assert response.status_code == 404  # El servicio lanza HTTPException(404) para match inexistente


def test_quit_match_multiple_players(client):
    """Test con múltiples jugadores abandonando la partida"""
    # Crear owner
    response = client.post("/players", json={
        "name": "Owner Player",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()

    # Crear partida
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()

    # Crear y unir 3 jugadores más
    players = []
    for i in range(3):
        response = client.post("/players", json={
            "name": f"Player {i+2}",
            "avatar": f"avatar{i+2}",
            "birthday": f"200{i+1}-0{i+1}-0{i+1}"
        })
        assert response.status_code == 201
        player = response.json()
        players.append(player)
        
        # Unir a la partida
        response = client.post(f"/matches/{match['id']}/join", params={"player_id": player['id']})
        assert response.status_code == 200

    # Verificar que hay 4 jugadores total
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    all_players = response.json()
    assert len(all_players) == 4

    # Primer jugador abandona
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": players[0]['id']})
    
    assert response.status_code == 200

    # Verificar que quedan 3
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    remaining_players = response.json()
    assert len(remaining_players) == 3

    # Segundo jugador abandona
    with patch('app.matches.endpoints.manager.specificBroadcast', new_callable=AsyncMock), \
         patch('app.matches.endpoints.manager.quitMatch', new_callable=Mock):
        response = client.put(f"/matches/{match['id']}/quit", params={"player_id": players[1]['id']})
    
    assert response.status_code == 200

    # Verificar que quedan 2
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    remaining_players = response.json()
    assert len(remaining_players) == 2