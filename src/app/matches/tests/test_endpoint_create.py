import uuid
import pytest

from app.matches.services import MatchService
from app.cards.models import Card, Card_Type, Match_Card
from unittest.mock import MagicMock, patch

def test_iniciar_crear_partida(client, db_session):
    # 1. Crear player
    response = client.post("/players", json={
        "name": "Elian",
        "avatar": "avatar2",
        "birthday": "2000-04-21"
    })
    assert response.status_code == 201
    player = response.json()

    # 2. Crear match
    match_post = {
        "name": "Partida Test",
        "min_players": 2,
        "max_players": 6,
        "owner_id": player["id"],
    }
    response = client.post("/matches", json=match_post)
    match = response.json()
    assert response.status_code == 201
    
    # 3. Metedos GET 
    response = client.get("/matches")
    assert response.status_code == 200
    
    response = client.get(f"/matches/{match['id']}")
    assert response.status_code == 200
    
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200 