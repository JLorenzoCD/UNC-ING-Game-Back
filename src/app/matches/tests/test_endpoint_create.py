import uuid
import pytest

from app.matches.services import MatchService
from app.cards.models import Card, Card_Type, Match_Card
<<<<<<< HEAD
from unittest.mock import MagicMock, patch
=======
>>>>>>> ff37ef6 (ING-22 Inicializamos todas las match_cards y pasamos los test)

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

    # 3. Convertir string UUID a UUID object
    match_uuid = uuid.UUID(match["id"])
    
    # 4. Insertar cartas base en la BD de test
    cartas_base = [
        {"id": "d572ba5c-20b8-4ee0-8bf5-f792887b0073", "name": "NOT SO FAST", "type": Card_Type.INSTANT},
        {"id": "a95eebac-9c02-4ea0-99fd-5bde7882ac79", "name": "PARKER PYNE", "type": Card_Type.DETECTIVE},
        {"id": "d314be48-bbd2-4093-b53f-4715515f6dd7", "name": "LADY EILEEN", "type": Card_Type.DETECTIVE},
        {"id": "7c4e65ec-4d73-43e2-bc46-e04c2eea5dc4", "name": "TOMMY BERESFORD", "type": Card_Type.DETECTIVE},
        {"id": "0092e2f1-78ee-4da7-8acb-1568c212d8c2", "name": "TUPPENCE BERESFORD", "type": Card_Type.DETECTIVE},
        {"id": "7531f174-7099-42dc-86f2-dd5aaccaa9af", "name": "HARLEY QUIN WILDCARD", "type": Card_Type.DETECTIVE},
        {"id": "8d5ddb79-4e52-4386-9a54-9f65664d67dc", "name": "ARIADNE OLIVER", "type": Card_Type.DETECTIVE},
        {"id": "f69ae2be-71a1-4248-a5ad-3293839a7ea7", "name": "HERCULE POIROT", "type": Card_Type.DETECTIVE},
        {"id": "527aefd2-5580-4b25-9ff1-20c5a10eb5dc", "name": "MISS MARPLE", "type": Card_Type.DETECTIVE},
        {"id": "d71ca59e-451f-42f1-a7f0-1d3e2fef72d3", "name": "MR SATTERTHWAITE", "type": Card_Type.DETECTIVE},
        {"id": "8ba1f702-dba4-4486-aff9-b18a8849b7ae", "name": "CARDS OFF THE TABLE", "type": Card_Type.EVENT},
        {"id": "7cd5bf6d-de4b-4173-aef8-c611c30dbca5", "name": "ANOTHER VICTIM", "type": Card_Type.EVENT},
        {"id": "d9b822e5-1092-49e4-9f13-59369b40a6c2", "name": "DEAD CARD FOLLY", "type": Card_Type.EVENT},
        {"id": "62918044-f5e5-4380-91ba-4a3eacabc550", "name": "LOOK INTO THE ASHES", "type": Card_Type.EVENT},
        {"id": "3eda241c-c47e-470d-832f-637f5cf635eb", "name": "CARD TRADE", "type": Card_Type.EVENT},
        {"id": "fefb72eb-12e4-4406-983e-8facccf3e4ca", "name": "AND THEN THERE WAS ONE MORE", "type": Card_Type.EVENT},
        {"id": "a4574f49-e28f-4c94-8a4e-b50d92448ae1", "name": "DELAY THE MURDERER ESCAPE", "type": Card_Type.EVENT},
        {"id": "70318b8d-62b4-4f76-bf30-4a183b35b354", "name": "EARLY TRAIN TO PADDINGTON", "type": Card_Type.EVENT},
        {"id": "c6a66530-b11c-4eb7-8d1f-c84a261252e5", "name": "POINT YOUR SUSPICIONS", "type": Card_Type.EVENT},
        {"id": "43322138-0471-4beb-a00c-0089758f261e", "name": "BLACKMAILED", "type": Card_Type.DEVIOUS},
        {"id": "6dac86f0-0e23-499f-993a-40460d7fa090", "name": "SOCIAL FAUX PAS", "type": Card_Type.DEVIOUS},
    ]

    for carta_data in cartas_base:
        carta = Card(
            id=uuid.UUID(carta_data["id"]),   # ✅ conversión a UUID
            name=carta_data["name"],
            type=carta_data["type"],
            description=f"Description for {carta_data['name']}"
        )
        db_session.add(carta)

    db_session.commit()
    print("\n" + "-" * 50)
    print(f"Insertadas {len(cartas_base)} cartas base en la BD de test")

    # 5. Llamar a iniciar_partida con el servicio de matches
    MatchService(db_session).iniciar_partida(match_uuid)
    db_session.commit()

    # 6. Verificar cartas creadas para la partida
    cartas_con_info = (
        db_session.query(Match_Card, Card)
        .join(Card, Match_Card.card_id == Card.id)
        .filter(Match_Card.match_id == match_uuid)
        .all()
    )

    print("\n" + "-" * 50)
    print(f"\nCARTAS CREADAS ({len(cartas_con_info)} total):")
    print("\n" + "-" * 50)

    for match_card, card in cartas_con_info:
        jugador = f"P:{match_card.player_id}" if match_card.player_id else "Sin asignar"
        print(f"• {card.name} ({card.type.value}) | {jugador}")
>>>>>>> ff37ef6 (ING-22 Inicializamos todas las match_cards y pasamos los test)
