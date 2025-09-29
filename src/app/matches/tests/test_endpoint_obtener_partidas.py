import uuid
import pytest
from app.cards.models import Card, Match_Card
from app.cards import models
from sqlalchemy import func

def test_obtener_cartas(client, db_session):
    # Lista para guardar información de las partidas creadas
    created_matches = []

    for i in range(5):
        #creo player owner
        response = client.post("/players", json={
            "name": f"Owner {i+1}",
            "avatar": f"avatar{i+1}",
            "birthday": f"2000-0{i+1}-01"
        })
        assert response.status_code == 201
        owner = response.json()

        #creo partida
        match_post = {
            "name": f"Partida Test {i+1}",
            "min_players": 2,
            "max_players": 4,
            "owner_id": owner["id"],
        }
        response = client.post("/matches", json=match_post)
        assert response.status_code == 201
        match = response.json()
        match_id = uuid.UUID(match['id'])
        
        #crear otro player
        response = client.post("/players", json={
            "name": f"Jugador Nuevo {i+1}",
            "avatar": f"avatar_jugador_{i+1}",
            "birthday": f"2000-0{i+1}-02"
        })
        assert response.status_code == 201
        new_player = response.json()
        
        #entro a la partida
        response = client.post(f"/matches/{match['id']}/join", params={"player_id": new_player["id"]})
        assert response.status_code == 200
        
        # Guardar información de la partida creada
        created_matches.append({
            "match_id": match_id,
            "match_data": match,
            "owner_id": uuid.UUID(owner['id']),
            "player_id": uuid.UUID(new_player['id']),
            "name": f"Partida Test {i+1}"
        })
    
    #Probamos metodos GET obtener todas las partidas
    response = client.get("/matches")
    assert response.status_code == 200
    data = response.json()
    #verificar que es una lista y tiene elementos
    assert isinstance(data, list)
    assert len(data) == 5
    for match in data:
        #1 Verificamos si la cantidad de players es la correcta
        assert match['current_player_count'] == 2, f"la cantidad de jugadores en {match['name']}: {match['current_player_count']}"
    
    #Probamos metodo obtener una partida
    for i in range(5):    
        response = client.get(f"/matches/{created_matches[i]['match_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(created_matches[i]['match_id']), f"ID de partida no coincide"
        assert data['current_player_count'] == 2, f"la cantidad de jugadores en {data['name']}: {data['current_player_count']}"
