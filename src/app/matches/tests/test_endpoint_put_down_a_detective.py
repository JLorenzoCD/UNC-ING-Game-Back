import pytest
import json
from uuid import UUID
from unittest.mock import patch, AsyncMock
from fastapi.encoders import jsonable_encoder

from app.sets.models import Match_Set, SetType
from app.player.models import Player
from app.matches.models import Match
from app.cards.models import Card, Match_Card, Card_Type
from app.secrets.models import Secret, Secret_Type, Match_Secret
from app.events.models import EventosDeTurno, EventStatus

# Servicios (para verificar la DB)
from app.events import services as event_services

from app.matches.tests.conftest import setup_match_and_players

def create_match_cards_for_set(db_session, card_names: list[str], match_id: UUID, player_id: UUID) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = db_session.query(Card).filter(Card.name == name).first()
        assert card is not None, f"Carta con nombre '{name}' no encontrada. Asegúrate que la DB de test esté poblada."

        match_card = Match_Card(
            card_id=card.id,
            match_id=match_id,
            player_id=player_id,
            is_discarded=False
        )
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    
    return card_ids

def create_existing_set(db_session, set_type: SetType, match_id: UUID, player_id: UUID) -> UUID:
    """Helper para crear un Match_Set ya existente en la BBDD."""
    match_set = Match_Set(
        type=set_type,
        match_id=match_id,
        player_id=player_id
    )
    db_session.add(match_set)
    db_session.commit()
    db_session.refresh(match_set)
    return match_set.id

def create_match_secrets(db_session, secret: Secret, match_id: UUID, player_ids: list[UUID], revealed: bool) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=revealed
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids

@pytest.mark.parametrize("initial_set_type, card_to_play_name, expected_set_type, expected_discard, expected_event_status, requires_secret", [
    (SetType.MISS_MARPLE, "MISS MARPLE", SetType.MISS_MARPLE, True, EventStatus.PENDING, True),
    (SetType.PARKER_PYNE, "PARKER PYNE", SetType.PARKER_PYNE, True, EventStatus.PENDING, True),
    (SetType.TUPPENCE_BERESFORD, "TOMMY BERESFORD", SetType.TWO_BERESFORD, True, EventStatus.RESOLVED, False),
    (SetType.TOMMY_BERESFORD, "TUPPENCE BERESFORD", SetType.TWO_BERESFORD, True, EventStatus.RESOLVED, False),
    (SetType.LADY_EILEEN, "ARIADNE OLIVER", SetType.LADY_EILEEN, True, EventStatus.PENDING, True),
    (SetType.MISS_MARPLE, "ARIADNE OLIVER", SetType.MISS_MARPLE, True, EventStatus.PENDING, True),
])

def test_put_down_a_detective(
    db_session, 
    client, 
    initial_set_type, 
    card_to_play_name, 
    expected_set_type, 
    expected_discard, 
    expected_event_status,
    requires_secret
):
    """
    Verifica que añadir una carta a un set existente (PUT) funciona,
    manejando la lógica de descarte y los casos especiales.
    """
    with patch('app.matches.endpoints.manager') as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()

        # 1. Setup Básico
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data['match_id']
        match_str_id = setup_data['match_str_id']
        owner_id = setup_data['owner_id']
        player2_id = setup_data['player2_id'] # Target de ejemplo
        
        secret_base = db_session.query(Secret).filter(Secret.type == Secret_Type.INNOCENT).first()

        
        secret_ids_owner = create_match_secrets(db_session , secret_base, match_id, [owner_id], True)
        secret_ids_player2 = create_match_secrets(db_session , secret_base, match_id, [player2_id], False)

        # 2. Setup del Test
        
        # Crear el set que ya "existe" en la mesa
        set_id = create_existing_set(db_session, initial_set_type, match_id, owner_id)
        str_set_id = str(set_id)
        
        # Crear la carta que el jugador tiene en la mano y va a jugar
        card_ids_in_hand = create_match_cards_for_set(
            db_session, 
            [card_to_play_name], 
            match_id, 
            owner_id
        )
        card_to_play_id = card_ids_in_hand[0]
        
        secret_id_payload = None  # Empezar con None por defecto
        
        if requires_secret:
            if SetType.PARKER_PYNE == initial_set_type:
                # Parker Pyne se selecciona a sí mismo
                secret_id_payload = secret_ids_owner[0]
            elif card_to_play_name != SetType.ADRIADNE_OLIVER.value:
                # Otros detectives (Marple, Poirot) seleccionan al jugador 2
                secret_id_payload = secret_ids_player2[0]
            # (Si es Ariadne Oliver, secret_id_payload se queda como None,
            #  lo cual es correcto)
            elif SetType.MISS_MARPLE == initial_set_type:
                secret_id_payload = secret_ids_player2[0]


        # 3. Preparar el Payload (setIn: AddSetIn)
        set_in_payload = {
            "card_ids": card_ids_in_hand,
            "player_id": owner_id,
            "target_player_id": player2_id if SetType.PARKER_PYNE != initial_set_type else owner_id,
            "target_secret_id": secret_id_payload,
        }

        # 4. Llamar al Endpoint
        response = client.put(
            f"/matches/{match_str_id}/sets/{str_set_id}", 
            json=jsonable_encoder(set_in_payload)
        )

        # 5. Verificar Respuesta HTTP
        assert response.status_code == 200, f"Error {response.status_code}: {response.text}"
        
        set_response = response.json()
        assert set_response["id"] == str(set_id)
        assert set_response["type"] == expected_set_type.value # Verificar si se actualizó (Beresford)
        
        # 8. Verificar Estado de la Base de Datos (Evento Creado)
        
        # Si la carta es Oliver, el evento creado es de tipo OLIVER,
        # independientemente del set.
        if card_to_play_name == "ARIADNE OLIVER":
            expected_event_type = SetType.ADRIADNE_OLIVER.value
        else:
            expected_event_type = expected_set_type.value
            
        
        new_event = db_session.query(EventosDeTurno).filter(
            EventosDeTurno.match_id == match_id,
            EventosDeTurno.event_type == expected_event_type
        ).first()
        
        assert new_event is not None, "No se creó ningún evento"
        assert new_event.status == expected_event_status.value
        assert new_event.player_id == owner_id

        # Verificar payload del evento (que contenga los datos correctos)
        event_payload = new_event.payload
        
        # Para Lady Eileen (cuando NO crea set, sino que añade)
        if initial_set_type == SetType.LADY_EILEEN and card_to_play_name != "ARIADNE OLIVER":
            assert event_payload["is_create_set"] == False
            assert event_payload["set_id"] == str(set_id)