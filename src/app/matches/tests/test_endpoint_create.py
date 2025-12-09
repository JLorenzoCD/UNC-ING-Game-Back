import uuid

import pytest

from app.player.models import Match_Player


@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_create_match(client, db_session, num_players):
    """Test create match.

    Args:
        client: Parameter client.
        db_session: Parameter db_session.
        num_players: Parameter num_players."""
    birthdates = [
        "2000-09-10",
        "2000-09-20",
        "2000-03-15",
        "2000-12-25",
        "2000-06-01",
        "2000-09-15",
    ]
    players = []
    for i in range(num_players):
        response = client.post(
            "/players",
            json={
                "name": f"Jugador{i + 1}",
                "avatar": f"avatar{i + 1}",
                "birthday": birthdates[i],
            },
        )
        assert response.status_code == 201
        players.append(response.json())
    match_post = {
        "name": f"Partida Test {num_players} jugadores",
        "min_players": 2,
        "max_players": 6,
        "owner_id": players[0]["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    match_uuid = uuid.UUID(match["id"])
    for order, player in enumerate(players[1:], start=1):
        mp = Match_Player(
            match_id=match_uuid, player_id=uuid.UUID(player["id"]), order=order
        )
        db_session.add(mp)
    db_session.commit()
    assert (
        db_session.query(Match_Player)
        .filter(Match_Player.match_id == match_uuid)
        .count()
        == num_players
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
