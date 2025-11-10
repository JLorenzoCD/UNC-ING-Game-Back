import pytest
import json
from uuid import UUID, uuid4
from unittest.mock import patch, AsyncMock
from fastapi.encoders import jsonable_encoder

# Modelos de la App (Ajustar imports según tu estructura)
from app.sets.models import Match_Set, SetType
from app.player.models import Player
from app.matches.models import Match
from app.secrets.models import Secret, Secret_Type, Match_Secret, Secret_action
from app.events.models import EventosDeTurno, EventStatus

# Servicios (para verificar la DB)
from app.events import services as event_services
from app.secrets import services as secret_services

# Helpers de Tests (Asumiendo que están en 'app/matches/tests/conftest.py')
from app.matches.tests.conftest import setup_match_and_players

# --- Helpers Específicos para este Test (Copiados de otros tests) ---

def create_match_secrets(
    db_session, 
    secret_base: Secret, 
    match_id: UUID, 
    player_ids: list[UUID], 
    is_revealed: bool = False
) -> list[UUID]:
    """Helper para crear Match_Secret para jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret_base.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=is_revealed
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids

def create_existing_set(db_session, set_type: SetType, match_id: UUID, player_id: UUID) -> UUID:
    """Helper para crear un Match_Set ya existente en la BBDD."""
    match_set = Match_Set(
        type=set_type,
        match_id=match_id,
        player_id=player_id # El 'owner' del set
    )
    db_session.add(match_set)
    db_session.commit()
    db_session.refresh(match_set)
    return match_set.id

# --- Tests para PUT /{match_id}/sets/{set_id}/stolen ---

@pytest.mark.parametrize("set_type_to_rob, initial_reveal_state, expected_reveal_state, targetS", [
    # Caso 1: Robar Miss Marple (requiere secreto, lo revela)
    (SetType.MISS_MARPLE, False, True, True),
    
    # Caso 2: Robar Hercule Poirot (requiere secreto, lo revela)
    (SetType.HERCULE_POIROT, False, True, True),
    
    # Caso 3: Robar Parker Pyne (requiere secreto, lo esconde)
    (SetType.PARKER_PYNE, True, False, True),
    
    # Caso 4: Robar Lady Eileen (no requiere secreto, no cambia nada)
    (SetType.LADY_EILEEN, False, False, False),
    
    # Caso 5: Robar Two Beresford (no requiere secreto, no cambia nada)
    (SetType.TWO_BERESFORD, False, False, False),
])
def test_play_set_stolen_success(
    db_session, 
    client, 
    set_type_to_rob, 
    initial_reveal_state, 
    expected_reveal_state,
    targetS
):
    """
    Verifica que aplicar el efecto de un set robado funciona y 
    actualiza el estado del secreto en la BBDD.
    """
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        
        # 1. Setup Básico
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id'] # El que roba el set
        player2_id = setup_data['player2_id'] # El jugador target

        # 2. Setup del Set y Secreto
        set_id = create_existing_set(db_session, set_type_to_rob, match_id, owner_id)
        str_set_id = str(set_id)
        
        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()
        secret_ids_target = create_match_secrets(
            db_session, secret_base, match_id, [player2_id], is_revealed=initial_reveal_state
        )
        target_secret_id = secret_ids_target[0]
        
        # 3. Preparar Payload
        payload = {
            "player_id": str(owner_id),
            "target_player_id": str(player2_id),
            "target_secret_id": str(target_secret_id) if targetS else None
        }
        
        # 4. Llamar al Endpoint
        response = client.put(
            f"/matches/{match_str_id}/sets/{str_set_id}/stolen", 
            json=jsonable_encoder(payload)
        )

        # 5. Verificar Respuesta HTTP
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response["id"] == str(set_id)
        assert set_response["type"] == set_type_to_rob.value

        # 7. Verificar Estado de la Base de Datos (Secreto)
        db_secret = db_session.get(Match_Secret, target_secret_id)
        assert db_secret.is_revealed == expected_reveal_state
            
def test_play_set_stolen_invalid_set(db_session, client):
    """Verifica el error 422 si el set_id no existe."""
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        setup_data = setup_match_and_players(client, db_session)
        match_str_id = setup_data['match_str_id']
        player2_id = setup_data['player2_id']
        
        payload = {
            "target_player_id": str(player2_id),
            "target_secret_id": None
        }
        
        response = client.put(
            f"/matches/{match_str_id}/sets/{uuid4()}/stolen", 
            json=jsonable_encoder(payload)
        )
        
        assert response.status_code == 422 # InvalidSetError