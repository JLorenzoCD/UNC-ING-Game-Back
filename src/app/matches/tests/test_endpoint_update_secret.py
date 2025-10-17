import pytest
import json
from uuid import UUID, uuid4
from unittest.mock import patch, AsyncMock
from app.sets.models import Match_Set, SetType
from app.player.models import Player
from app.matches.models import Match
from app.cards.models import Card, Match_Card, Card_Type
from app.secrets.models import Secret, Secret_Type, Match_Secret, Secret_action
from app.secrets import services as secret_services
from app.matches.tests.conftest import setup_match_and_players, jsonable_encoder

def create_match_cards_for_set(db_session, card_names: list[str], match_id: UUID, player_id: UUID) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = db_session.query(Card).filter(Card.name == name).first()
        assert card is not None, f"Card with name '{name}' not found in test setup."

        match_card = Match_Card(
            card_id=card.id,
            match_id=match_id,
            player_id=player_id
        )
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    
    return card_ids

def create_match_secrets(db_session, secret: Secret, is_revealed:bool, match_id: UUID, player_ids: list[UUID]) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=is_revealed
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids

@pytest.mark.parametrize("action, expected_state", [
    #Reveal
    (Secret_action.REVEAL, True),
    (Secret_action.HIDE, False),
])
def test__hide_reveal_secret(db_session, client, action, expected_state):
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        match_secret_ids = create_match_secrets(db_session, secret_base, (not expected_state), match_id, [owner_id, player2_id])
        target_secret_id: UUID = match_secret_ids[1] # Jugador 2
        str_secret_id = str(target_secret_id)
        
        set_data = {
            "target_player_id" : player2_id,
            "action" : action
        }
        
        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response['is_revealed'] == expected_state
        
@pytest.mark.parametrize("action, expected_state", [
    #Reveal
    (Secret_action.REVEAL, True),
    (Secret_action.HIDE, False),
])
def test_hide_reveal_secret_invalid(db_session, client, action, expected_state):
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        match_secret_ids = create_match_secrets(db_session, secret_base, expected_state, match_id, [owner_id, player2_id])
        target_secret_id: UUID = match_secret_ids[1] # Jugador 2
        str_secret_id = str(target_secret_id)
        
        set_data = {
            "target_player_id" : player2_id,
            "action" : action
        }
        
        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 404
        assert f"Secret is already {action}" in response.json()["detail"]
 
 
def test_steal_secret(db_session, client):
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        match_secret_ids = create_match_secrets(db_session, secret_base, False, match_id, [owner_id, player2_id])
        target_secret_id: UUID = match_secret_ids[1] # Jugador 2
        str_secret_id = str(target_secret_id)
        
        set_data = {
            "target_player_id" : owner_id,
            "action" : Secret_action.STEAL
        }

        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response['player_id'] == str(owner_id)
        
def test_steal_secret_invalid_players(db_session, client):
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']        
        fake_player = uuid4()

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        match_secret_ids = create_match_secrets(db_session, secret_base, False, match_id, [owner_id, player2_id])
        target_secret_id: UUID = match_secret_ids[1] # Jugador 2
        str_secret_id = str(target_secret_id)
        
        set_data = {
            "target_player_id" : fake_player,
            "action" : Secret_action.STEAL
        }

        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 404, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert f"Players are not in the same match" in response.json()["detail"]
        

@pytest.mark.parametrize("action1, expected_state, action2, action3", [
    #Reveal
    (Secret_action.REVEAL, True, Secret_action.HIDE, Secret_action.STEAL),
    (Secret_action.HIDE, False, Secret_action.REVEAL, Secret_action.STEAL),
])
def test__multi_action_secret(db_session, client, action1, expected_state, action2, action3):
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        match_secret_ids = create_match_secrets(db_session, secret_base, (not expected_state), match_id, [owner_id, player2_id])
        target_secret_id: UUID = match_secret_ids[1] # Jugador 2
        str_secret_id = str(target_secret_id)
        
        
        set_data = {
            "target_player_id" : player2_id,
            "action" : action1
        }
        
        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response['is_revealed'] == expected_state
        
        set_data = {
            "target_player_id" : player2_id,
            "action" : action2
        }
        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response['is_revealed'] == (not expected_state)
        
        set_data = {
            "target_player_id" : player2_id,
            "action" : action3
        }
        response = client.put(f"/matches/{match_str_id}/secrets/{str_secret_id}", json=jsonable_encoder(set_data))
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response['is_revealed'] == (not expected_state)