import uuid
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID


def test_quit_match_invalid_match_id(client):
    """Test que falla con un match_id inexistente"""
    response = client.post(
        "/players",
        json={"name": "Test Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    player = response.json()
    fake_match_id = str(uuid.uuid4())
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{fake_match_id}/quit", params={"player_id": player["id"]}
        )
    assert response.status_code == 404


def test_quit_match_multiple_players(client):
    """Test con múltiples jugadores abandonando la partida"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    players = []
    for i in range(3):
        response = client.post(
            "/players",
            json={
                "name": f"Player {i + 2}",
                "avatar": f"avatar{i + 2}",
                "birthday": f"200{i + 1}-0{i + 1}-0{i + 1}",
            },
        )
        assert response.status_code == 201
        player = response.json()
        players.append(player)
        response = client.post(
            f"/matches/{match['id']}/join", params={"player_id": player["id"]}
        )
        assert response.status_code == 200
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    all_players = response.json()
    assert len(all_players) == 4
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": players[0]["id"]}
        )
    assert response.status_code == 200
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    remaining_players = response.json()
    assert len(remaining_players) == 3
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": players[1]["id"]}
        )
    assert response.status_code == 200
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    remaining_players = response.json()
    assert len(remaining_players) == 2


def test_quit_match_owner_can_quit(client):
    """Test que el owner también puede abandonar la partida"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    response = client.post(
        "/players",
        json={"name": "Player Two", "avatar": "avatar2",
              "birthday": "2000-02-02"},
    )
    assert response.status_code == 201
    player2 = response.json()
    response = client.post(
        f"/matches/{match['id']}/join", params={"player_id": player2["id"]}
    )
    assert response.status_code == 200
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": owner["id"]}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 1
    assert players[0]["player_id"] == player2["id"]


def test_quit_match_player_not_found(client):
    """Test que falla cuando el jugador no existe"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    fake_player_id = str(uuid.uuid4())
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": fake_player_id}
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "The player is not in the match"


def test_quit_match_player_not_in_match(client):
    """Test que falla cuando el jugador no está en la partida"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    response = client.post(
        "/players",
        json={"name": "External Player",
              "avatar": "avatar2", "birthday": "2000-02-02"},
    )
    assert response.status_code == 201
    external_player = response.json()
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ), patch("app.matches.endpoints.manager.quitMatch", new_callable=Mock):
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": external_player["id"]}
        )
    assert response.status_code == 404


def test_quit_match_success(client):
    """Test que un jugador puede abandonar una partida exitosamente"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    response = client.post(
        "/players",
        json={"name": "Player Two", "avatar": "avatar2",
              "birthday": "2000-02-02"},
    )
    assert response.status_code == 201
    player2 = response.json()
    response = client.post(
        f"/matches/{match['id']}/join", params={"player_id": player2["id"]}
    )
    assert response.status_code == 200
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 2
    with patch(
        "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
    ) as mock_broadcast, patch(
        "app.matches.endpoints.manager.quitMatch", new_callable=Mock
    ) as mock_quit:
        response = client.put(
            f"/matches/{match['id']}/quit", params={"player_id": player2["id"]}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200
    players = response.json()
    assert len(players) == 1
    assert players[0]["player_id"] == owner["id"]
    mock_broadcast.assert_called()
    mock_quit.assert_called_once_with(UUID(player2["id"]), UUID(match["id"]))
