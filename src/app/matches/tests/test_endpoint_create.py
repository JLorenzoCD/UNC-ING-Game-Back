import uuid
from app.matches.models import Match
from app.matches.schemas import MatchOut, MatchIn
from app.matches.dto import MatchDTO
from app.matches.models import MatchStatus
from app.player.models import Player
from datetime import date
        
def test_endpoint_matcher_POST(client):
        
    #Creamos Player
    response = client.post("/players", json={
        "name": "Elian",
        "avatar": "avatar2",
        "birthday": "2000-04-21"
    })
    assert response.status_code == 201
    data = response.json()

    # body request Match
    match_post = {
        "name": "Partida Test",
        "min_players": 2,
        "max_players": 6,
        "owner_id": data["id"],
    }
    # Llamada al endpoint
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201

    body = response.json()
    assert "id" in body