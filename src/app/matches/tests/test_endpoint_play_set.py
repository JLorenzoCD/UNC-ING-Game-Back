import pytest
import json
from uuid import UUID
from unittest.mock import patch, AsyncMock
from app.sets.models import Match_Set, SetType
from app.player.models import Player
from app.matches.models import Match
from app.cards.models import Card, Match_Card, Card_Type
from app.secrets.models import Secret, Secret_Type, Match_Secret
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

def create_match_secrets(db_session, secret: Secret, match_id: UUID, player_ids: list[UUID]) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=False
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids

@pytest.mark.parametrize("set_type, card_names, quins", [
    # HERCULE_POIROT
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HERCULE POIROT", "HERCULE POIROT"], 0),
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HERCULE POIROT", "HARLEY QUIN WILDCARD"], 1),
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"], 2),
    # MISS_MARPLE
    (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "MISS MARPLE"], 0),
    (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "HARLEY QUIN WILDCARD"], 1),
    (SetType.MISS_MARPLE, ["MISS MARPLE", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"], 2),
])
def test_endpoint_play_set_Poirot_Marple(db_session, client, set_type, card_names, quins):
    """Verifica que los sets de Poirot y Marple revelen un secreto correctamente."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        match_card_ids = create_match_cards_for_set(db_session, card_names, match_id, owner_id)
        match_secret_ids = create_match_secrets(db_session, secret_base, match_id, [owner_id, player2_id])
        
        target_secret_id = match_secret_ids[1] # El secreto del jugador 2

        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": target_secret_id
        }
        
        response = client.post(f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in))
        
        assert response.status_code == 201
        set_response = response.json()
        assert set_response['type'] == set_type.value
        assert set_response['player_id'] == str(owner_id)
        assert set_response['quin_count'] == quins
        
        db_session.expire_all() # Forzar la recarga desde la BD
        match_secret_db = db_session.query(Match_Secret).filter(Match_Secret.id == target_secret_id).first()
        assert match_secret_db.is_revealed is True
        
        is_cards_delete = db_session.query(Match_Card).filter(Match_Card.id.in_(match_card_ids)).all()
        assert is_cards_delete == []

     
@pytest.mark.parametrize("set_type, card_names", [
    # HERCULE_POIROT
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HERCULE POIROT", "HERCULE POIROT"]),
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HERCULE POIROT", "HARLEY QUIN WILDCARD"]),
    (SetType.HERCULE_POIROT, ["HERCULE POIROT", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"]),
    # MISS_MARPLE
    (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "MISS MARPLE"]),
    (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "HARLEY QUIN WILDCARD"]),
    (SetType.MISS_MARPLE, ["MISS MARPLE", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"]),
])
def test_endpoint_play_set_target_secret_required(db_session, client, set_type, card_names):
    """Test para verificar que Poirot/Marple requieren un secreto objetivo."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']
        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        
        match_card_ids = create_match_cards_for_set(db_session, card_names, match_id, owner_id)
        match_secret_ids = create_match_secrets(db_session, secret_base, match_id, [owner_id, player2_id])

        
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": None # Enviamos None cuando es requerido
        }

        response = client.post(f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in))

        assert response.status_code == 400
        assert "No hay secreto seleccionado" in response.json()["detail"]
        
@pytest.mark.parametrize("set_type, card_names", [
    # PARKER_PYNE
    (SetType.PARKER_PYNE, ["PARKER PYNE", "PARKER PYNE"]),
    (SetType.PARKER_PYNE, ["PARKER PYNE", "HARLEY QUIN WILDCARD"]),
])       
def test_endpoint_play_Pyne(db_session, client, set_type, card_names):
    """Verifica que el set de Pyne oculte un secreto correctamente."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        match_card_ids = create_match_cards_for_set(db_session, card_names, match_id, owner_id)
        match_secret_ids = create_match_secrets(db_session, secret_base, match_id, [owner_id, player2_id])
        
        target_secret_id = match_secret_ids[1] # El secreto del jugador 2
        secret_services.Secrets_Services(db_session).reveal_secret(target_secret_id)

        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": target_secret_id
        }
        
        response = client.post(f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in))
        
        assert response.status_code == 201, f"Error {response.status_code}: {response.text}"

        set_response = response.json()
        assert set_response['type'] == set_type.value
        assert set_response['player_id'] == str(owner_id)
        
        db_session.expire_all() # Forzar la recarga desde la BD
        match_secret_db = db_session.query(Match_Secret).filter(Match_Secret.id == target_secret_id).first()
        assert match_secret_db.is_revealed is False

@pytest.mark.parametrize("set_type, card_names, quins_count_expected", [
    # LADY_EILEEN
    (SetType.LADY_EILEEN, ["LADY EILEEN", "LADY EILEEN"], 0),
    (SetType.LADY_EILEEN, ["LADY EILEEN", "HARLEY QUIN WILDCARD"], 1),
    # TWO_BERESFORD
    (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TUPPENCE BERESFORD"], 0),
    # MR_SATTERTHWAITE
    (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "MR SATTERTHWAITE"], 0),
    (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "HARLEY QUIN WILDCARD"], 1),
])
def test_endpoint_play_Eileen_Beresford_Satterthwaitte(db_session, client, set_type, card_names, quins_count_expected):
    """Verifica que los sets de Eileen, hermanos Beresford y Mr. Satterthwaite no realicen accion pero creen el set."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        match_card_ids = create_match_cards_for_set(db_session, card_names, match_id, owner_id)
        match_secret_ids = create_match_secrets(db_session, secret_base, match_id, [owner_id, player2_id])
        
        target_secret_id = match_secret_ids[0] # El secreto del jugador 1
        secret_services.Secrets_Services(db_session).reveal_secret(target_secret_id)

        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": None
        }
        
        response = client.post(f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in))
        
        assert response.status_code == 201, f"Error {response.status_code}: {response.text}"

        set_response = response.json()
        assert set_response['type'] == set_type.value
        assert set_response['player_id'] == str(owner_id)
        assert set_response['quin_count'] == quins_count_expected

@pytest.mark.parametrize("set_type, card_names", [
    # LADY_EILEEN
    (SetType.LADY_EILEEN, ["LADY EILEEN", "LADY EILEEN"]),
    (SetType.LADY_EILEEN, ["LADY EILEEN", "HARLEY QUIN WILDCARD"]),
    # TWO_BERESFORD
    (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TUPPENCE BERESFORD"]),
    # MR_SATTERTHWAITE
    (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "MR SATTERTHWAITE"]),
    (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "HARLEY QUIN WILDCARD"]),
])
def test_endpoint_play_Eileen_Beresford_Satterthwaitte_invalid_combination(db_session, client, set_type, card_names):
    """Verifica las excepciones de los sets LADY_EILEEN, TWO_BERESFORD y MR_SATTERTHWAITE."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id']

        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        match_card_ids = create_match_cards_for_set(db_session, card_names, match_id, owner_id)
        match_secret_ids = create_match_secrets(db_session, secret_base, match_id, [owner_id, player2_id])
        
        target_secret_id = match_secret_ids[0] # El secreto del jugador 1
        secret_services.Secrets_Services(db_session).reveal_secret(target_secret_id)

        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": target_secret_id
        }
        
        response = client.post(f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in))
        
        assert response.status_code == 400, f"Error {response.status_code}: {response.text}"
        assert "No se debería seleccionar secreto en este momento" in response.json()["detail"]
        