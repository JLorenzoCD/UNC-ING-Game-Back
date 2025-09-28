import uuid
import pytest

from app.matches.services import MatchService
from app.cards.models import Card, Card_Type, Match_Card
from app.player.models import Player
from app.secrets.models import Secret, Secret_Type, Match_Secret
from app.matches.models import Match_Player


# 🔹 Parametrizamos para probar con distintas cantidades de jugadores
@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_iniciar_partida_con_varios_jugadores(client, db_session, num_players):
    # 1. Crear jugadores con diferentes fechas de nacimiento
    birthdates = [
        "2000-09-10",  # Muy cerca del 15 sep
        "2000-09-20",  # Cerca del 15 sep
        "2000-03-15",  # Lejos del 15 sep
        "2000-12-25",  # Navidad
        "2000-06-01",  # Junio
        "2000-09-15"   # Exactamente 15 sep
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
    assert response.status_code == 201
    match = response.json()
    match_uuid = uuid.UUID(match["id"])

    # 3. Asociar jugadores al match (incluyendo al owner que ya fue agregado en create)
    for order, player in enumerate(players[1:], start=1):
        mp = Match_Player(
            match_id=match_uuid,
            player_id=uuid.UUID(player["id"]),
            order=order
        )
        db_session.add(mp)

    # 4. Insertar cartas base
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
            id=uuid.UUID(carta_data["id"]),
            name=carta_data["name"],
            type=carta_data["type"],
            description=f"Description for {carta_data['name']}"
        )
        db_session.add(carta)

    # 5. Insertar secretos base
    secretos_base = [
        {"type": Secret_Type.INNOCENT, "content": "Eres un inocente"},
        {"type": Secret_Type.MURDERER, "content": "Eres el asesino"},
        {"type": Secret_Type.ACCOMPLICE, "content": "Eres el cómplice"},
    ]
    for secret_data in secretos_base:
        secret = Secret(
            id=uuid.uuid4(),
            type=secret_data["type"],
            content=secret_data["content"],
        )
        db_session.add(secret)

    db_session.commit()

    # 6. Iniciar partida
    MatchService(db_session).iniciar_partida(match_uuid)
    db_session.commit()

    # 7. Obtener cartas y secretos con información completa
    cartas_con_info = (
        db_session.query(Match_Card, Card)
        .join(Card, Match_Card.card_id == Card.id)
        .filter(Match_Card.match_id == match_uuid)
        .all()
    )
    
    secretos_con_info = (
        db_session.query(Match_Secret, Secret)
        .join(Secret, Match_Secret.secret_id == Secret.id)
        .filter(Match_Secret.match_id == match_uuid)
        .all()
    )
    
    # 8. Obtener match_players para mostrar roles y orden, junto con info de jugadores
    match_players_con_info = (
        db_session.query(Match_Player, Player)
        .join(Player, Match_Player.player_id == Player.id)
        .filter(Match_Player.match_id == match_uuid)
        .order_by(Match_Player.order)  # Ordenar por orden de juego
        .all()
    )

    # 9. Verificaciones
    assert len(cartas_con_info) > 0
    assert len(secretos_con_info) > 0

    # 10. Debug prints organizados por orden de juego
    print("\n" + "=" * 80)
    print(f"🔹 Test con {num_players} jugadores - Match: {match_uuid}")
    print("=" * 80)
    
    # Mostrar orden de juego
    print("\n🎯 ORDEN DE JUEGO (por cercanía al 15 de septiembre):")
    print("-" * 60)
    for match_player, player_info in match_players_con_info:
        role = match_player.role.value if match_player.role else "Sin rol"
        print(f"{match_player.order}° - {player_info.name} (Cumple: {player_info.birthday}) - ROL: {role}")
    
    # Mostrar información detallada por jugador
    print("\n📋 INFORMACIÓN DETALLADA:")
    for match_player, player_info in match_players_con_info:
        player_uuid = player_info.id
        role = match_player.role.value if match_player.role else "Sin rol"
        
        print(f"\n👤 [{match_player.order}°] {player_info.name} (Cumple: {player_info.birthday}) - ROL: {role}")
        print("-" * 60)
        
        # Cartas del jugador
        cartas_jugador = [
            (match_card, card) for match_card, card in cartas_con_info 
            if match_card.player_id == player_uuid
        ]
        print(f"📚 Cartas ({len(cartas_jugador)}):")
        for match_card, card in cartas_jugador:
            print(f"  • {card.name} ({card.type.value})")
        
        # Secretos del jugador
        secretos_jugador = [
            (match_secret, secret) for match_secret, secret in secretos_con_info 
            if match_secret.player_id == player_uuid
        ]
        print(f"🔐 Secretos ({len(secretos_jugador)}):")
        for match_secret, secret in secretos_jugador:
            revelado = "Revelado" if match_secret.is_revealed else "Oculto"
            print(f"  • {secret.type.value} - {revelado}")
    
    # Mostrar cartas sin asignar (en el mazo)
    cartas_sin_asignar = [
        (match_card, card) for match_card, card in cartas_con_info 
        if match_card.player_id is None
    ]
    print(f"\n🃏 Cartas en el mazo ({len(cartas_sin_asignar)}):")
    print("-" * 60)
    for match_card, card in cartas_sin_asignar:
        print(f"  • {card.name} ({card.type.value})")
    
    # Mostrar secretos sin asignar
    secretos_sin_asignar = [
        (match_secret, secret) for match_secret, secret in secretos_con_info 
        if match_secret.player_id is None
    ]
    if secretos_sin_asignar:
        print(f"\n🔐 Secretos sin asignar ({len(secretos_sin_asignar)}):")
        print("-" * 60)
        for match_secret, secret in secretos_sin_asignar:
            revelado = "Revelado" if match_secret.is_revealed else "Oculto"
            print(f"  • {secret.type.value} - {revelado}")
    
    # Resumen final
    total_cartas_asignadas = len(cartas_con_info) - len(cartas_sin_asignar)
    total_secretos_asignados = len(secretos_con_info) - len(secretos_sin_asignar)
    
    print(f"\n📊 RESUMEN:")
    print("-" * 60)
    print(f"Total jugadores: {num_players}")
    print(f"Cartas asignadas: {total_cartas_asignadas} | En mazo: {len(cartas_sin_asignar)}")
    print(f"Secretos asignados: {total_secretos_asignados} | Sin asignar: {len(secretos_sin_asignar)}")
    print("=" * 80)