import uuid
import pytest
from app.matches.models import Match_Player

<<<<<<< HEAD
from app.matches.services import MatchService
from app.cards.models import Card, Card_Type, Match_Card
<<<<<<< HEAD
from unittest.mock import MagicMock, patch
=======
>>>>>>> ff37ef6 (ING-22 Inicializamos todas las match_cards y pasamos los test)
=======
# 🔹 Parametrizamos para probar con distintas cantidades de jugadores
@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_crear_partida(client, db_session, num_players):
    from app.player.models import Player
    from app.matches.models import Match
    from app.matches.services import MatchService
>>>>>>> e26721f (ING-22 Terminamos el proceso de iniciar partida, tambien pasamos los test)

    # 1. Crear jugadores con diferentes fechas de nacimiento
    birthdates = [
        "2000-09-10", "2000-09-20", "2000-03-15",
        "2000-12-25", "2000-06-01", "2000-09-15"
    ]
    
    players = []
    for i in range(num_players):
        response = client.post("/players", json={
            "name": f"Jugador{i+1}",
            "avatar": f"avatar{i+1}",
            "birthday": birthdates[i]
        })
        assert response.status_code == 201
        players.append(response.json())

    # 2. Crear partida con el primer jugador como owner
    match_post = {
        "name": f"Partida Test {num_players} jugadores",
        "min_players": 2,
        "max_players": 6,
        "owner_id": players[0]["id"],
    }
    response = client.post("/matches", json=match_post)
    match = response.json()
    assert response.status_code == 201
<<<<<<< HEAD
    
    # 3. Metedos GET 
    response = client.get("/matches")
    assert response.status_code == 200
    
    response = client.get(f"/matches/{match['id']}")
    assert response.status_code == 200
    
    response = client.get(f"/matches/{match['id']}/players")
    assert response.status_code == 200 
=======
    match = response.json()
    match_uuid = uuid.UUID(match["id"])

    # 3. Asociar jugadores al match (excepto owner que ya fue agregado)
    for order, player in enumerate(players[1:], start=1):
        mp = Match_Player(
            match_id=match_uuid,
            player_id=uuid.UUID(player["id"]),
            order=order
        )
        db_session.add(mp)
    db_session.commit()

    assert db_session.query(Match_Player).filter(Match_Player.match_id == match_uuid).count() == num_players
    assert response.status_code == 201

<<<<<<< HEAD
    print("\n" + "-" * 50)
    print(f"\nCARTAS CREADAS ({len(cartas_con_info)} total):")
    print("\n" + "-" * 50)

    for match_card, card in cartas_con_info:
        jugador = f"P:{match_card.player_id}" if match_card.player_id else "Sin asignar"
        print(f"• {card.name} ({card.type.value}) | {jugador}")
>>>>>>> ff37ef6 (ING-22 Inicializamos todas las match_cards y pasamos los test)
=======
    body = response.json()
    assert "id" in body
>>>>>>> e26721f (ING-22 Terminamos el proceso de iniciar partida, tambien pasamos los test)
