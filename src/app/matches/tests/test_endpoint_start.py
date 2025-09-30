import uuid
import pytest
from unittest.mock import AsyncMock, patch
from app.matches.models import Match_Player, MatchStatus

@pytest.mark.parametrize("num_players", [2, 3, 4, 5, 6])
def test_endpoint_start_match(client, db_session, num_players):
    from app.matches.models import Match
    from app.cards.models import Card, Card_Type
    from app.secrets.models import Secret, Secret_Type
    from unittest.mock import MagicMock

    # Mock del WebSocket manager
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        mock_manager.enterMatch = MagicMock()
        
        # 1. Crear jugadores
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
        
        # 2. Crear partida
        match_post = {
            "name": f"Partida Test {num_players} jugadores",
            "min_players": 2,
            "max_players": 6,
            "owner_id": players[0]["id"],
        }
        response = client.post("/matches", json=match_post)
        assert response.status_code == 201
        match_id = response.json()["id"]
        match_uuid = uuid.UUID(match_id)
        
        # 3. Unir jugadores (excepto owner)
        for player in players[1:]:
            response = client.post(
                f"/matches/{match_id}/join",
                params={"player_id": player["id"]}
            )
            assert response.status_code == 200
        
        # Verificar que están todos en la partida
        assert db_session.query(Match_Player).filter(
            Match_Player.match_id == match_uuid
        ).count() == num_players
        
        # 4. Sembrar cartas y secretos necesarios
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
        
        # 5. Iniciar partida
        response_start = client.post(f"/matches/{match_id}/start")
        if response_start.status_code != 200:
            print(f"Error details: {response_start.json()}")
        assert response_start.status_code == 200
        
        # 6. Verificar que el estado cambió a IN_PROGRESS
        match_db = db_session.query(Match).filter(Match.id == match_uuid).first()
        assert match_db is not None
        assert match_db.status == MatchStatus.IN_PROGRESS
