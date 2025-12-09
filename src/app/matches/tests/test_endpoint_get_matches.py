import uuid


def test_get_matches(client, db_session):
    """Test get matches.

    Args:
        client: Parameter client.
        db_session: Parameter db_session."""
    created_matches = []
    for i in range(5):
        response = client.post(
            "/players",
            json={
                "name": f"Owner {i + 1}",
                "avatar": f"avatar{i + 1}",
                "birthday": f"2000-0{i + 1}-01",
            },
        )
        assert response.status_code == 201
        owner = response.json()
        match_post = {
            "name": f"Partida Test {i + 1}",
            "min_players": 2,
            "max_players": 4,
            "owner_id": owner["id"],
        }
        response = client.post("/matches", json=match_post)
        assert response.status_code == 201
        match = response.json()
        match_id = uuid.UUID(match["id"])
        response = client.post(
            "/players",
            json={
                "name": f"Jugador Nuevo {i + 1}",
                "avatar": f"avatar_jugador_{i + 1}",
                "birthday": f"2000-0{i + 1}-02",
            },
        )
        assert response.status_code == 201
        new_player = response.json()
        response = client.post(
            f"/matches/{match['id']}/join", params={"player_id": new_player["id"]}
        )
        assert response.status_code == 200
        created_matches.append(
            {
                "match_id": match_id,
                "match_data": match,
                "owner_id": uuid.UUID(owner["id"]),
                "player_id": uuid.UUID(new_player["id"]),
                "name": f"Partida Test {i + 1}",
            }
        )
    response = client.get("/matches")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    for match in data:
        assert (
            match["current_player_count"] == 2
        ), f"la cantidad de jugadores en {match['name']}: {match['current_player_count']}"
    for i in range(5):
        response = client.get(f"/matches/{created_matches[i]['match_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(
            created_matches[i]["match_id"]
        ), "ID de partida no coincide"
        assert (
            data["current_player_count"] == 2
        ), f"la cantidad de jugadores en {data['name']}: {data['current_player_count']}"
