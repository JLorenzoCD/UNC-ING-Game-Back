import pytest
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone

# --- Importaciones de tu app ---
from app.events.services import EventService
from app.events.models import EventosDeTurno, EventStatus
from app.cards.models import Card_event
from app.cards.services import Cards_Services # Para el setup

# (Helpers de test)
# ...

pytestmark = pytest.mark.asyncio

# --- Tests para create_event (El "Hachazo" vs. Cancelable) ---
def test_create_event_cancelable(db: Session):
    """
    Prueba que si NO pasamos status, el evento se crea como PENDING
    y el timer es de 5+ segundos.
    """
    event_service = EventService(db)
    
    # --- Setup ---
    match_id = uuid4()
    player_id = uuid4()
    match_card_id = uuid4()
    # (Aquí necesitarás crear un Match, Player y MatchCard reales
    #  para que las Foreign Keys no fallen, o mockearlos)
    
    # --- Acción ---
    new_event = event_service.create_event(
        match_id=match_id,
        player_id=player_id,
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=match_card_id,
        event_payload={"target_set_id": "..."}
        # ¡No pasamos 'status'!
    )
    
    # --- Assert ---
    assert new_event.status == EventStatus.PENDING.value
    assert new_event.nsf_count == 0
    assert new_event.resolve_at > datetime.now(timezone.utc)

def test_create_event_instant_hachazo(db: Session):
    """
    Prueba que si SÍ pasamos status=RESOLVED (el "hachazo"),
    el evento se crea como RESOLVED y el timer está en el pasado (o ahora).
    """
    event_service = EventService(db)
    # --- Setup ---
    match_id = uuid4(); player_id = uuid4(); match_card_id = uuid4()
    
    # --- Acción ---
    new_event = event_service.create_event(
        match_id=match_id,
        player_id=player_id,
        event_type_str=Card_event.CARDS_OFF_THE_TABLE.value,
        match_card_id=match_card_id,
        event_payload={"target_player_id": "..."},
        status = EventStatus.RESOLVED # ¡El Hachazo!
    )
    
    # --- Assert ---
    assert new_event.status == EventStatus.RESOLVED.value
    assert new_event.resolve_at <= datetime.now(timezone.utc)


# --- Tests para play_nsf_on_event (Ticket 3) ---
def test_play_nsf_success(db: Session):
    """
    Prueba que 'play_nsf_on_event' (Ticket 3) actualiza el
    contador y el timer.
    """
    event_service = EventService(db)
    # --- Setup: Creamos un evento PENDIENTE ---
    event = event_service.create_event(
        match_id=uuid4(), player_id=uuid4(),
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=uuid4(), event_payload={}
    )
    assert event.nsf_count == 0
    original_resolve_at = event.resolve_at
    
    # --- Acción ---
    updated_event = event_service.play_nsf_on_event(
        event_id=event.id,
        nsf_count=0 
    )

    # --- Assert ---
    assert updated_event.nsf_count == 1
    assert updated_event.resolve_at > original_resolve_at

def test_play_nsf_race_condition_fails(db: Session):
    """
    Prueba que la lógica atómica funciona (la "condición de carrera").
    """
    event_service = EventService(db)
    # --- Setup: Creamos un evento y ALGUIEN YA JUGÓ NSF ---
    event = event_service.create_event(
        match_id=uuid4(), player_id=uuid4(),
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=uuid4(), event_payload={}
    )
    event_service.play_nsf_on_event(event_id=event.id, nsf_count=0)
    
    # --- Acción ---
    with pytest.raises(ValueError, match="alguien ya jugo not so fast"):
        event_service.play_nsf_on_event(
            event_id=event.id,
            nsf_count=0 # ¡Incorrecto!
        )


# --- Tests para Eventos Compuestos (Fase 2) ---
def test_add_response_to_event(db: Session):
    """
    Prueba 'update_info_event' (la "puta lista" de UUIDs).
    """
    event_service = EventService(db)
    
    # --- Setup: Creamos un evento y lo ponemos en PENDING_TARGET_RESPONSE ---
    target_player_id_str = str(uuid4()) # Guardamos el UUID
    
    event = event_service.create_event(
        match_id=uuid4(), player_id=uuid4(),
        event_type_str=Card_event.CARD_TRADE.value,
        match_card_id=uuid4(), event_payload={"target_player_id": target_player_id_str}
    )
    event.status = EventStatus.PENDING_TARGET_RESPONSE.value
    db.commit()
    db.refresh(event)
    
    assert event.payload.get('responses') is None # La lista no existe
    
    # --- Acción (P1 añade su carta) ---
    p1_card_id = uuid4()
    updated_event = event_service.update_info_event(
        event_id=event.id,
        player_id=event.player_id,
        info_from_endpoint=p1_card_id
    )

    # --- Assert 1 ---
    assert 'responses' in updated_event.payload
    assert len(updated_event.payload['responses']) == 1
    assert updated_event.payload['responses'][0] == str(p1_card_id)

    # --- Acción (P2 añade su carta) ---
    p2_card_id = uuid4()
    
    updated_event_2 = event_service.update_info_event(
        event_id=event.id,
        player_id=UUID(target_player_id_str), 
        info_from_endpoint=p2_card_id
    )
    
    # --- Assert 2 ---
    assert len(updated_event_2.payload['responses']) == 2
    assert updated_event_2.payload['responses'][1] == str(p2_card_id)

def test_is_event_ready_to_resolve(db: Session):
    """
    Prueba tu servicio 'is_event_ready_to_resolve'.
    """
    event_service = EventService(db)
    
    # (Necesitarás un helper para esto, lo hardcodeamos)
    match_players_count = 2 
    target_player_id_str = str(uuid4()) 
    
    event = event_service.create_event(
        match_id=uuid4(), player_id=uuid4(),
        event_type_str=Card_event.CARD_TRADE.value,
        match_card_id=uuid4(), 
        event_payload={"target_player_id": target_player_id_str} 
    )
    event.status = EventStatus.PENDING_TARGET_RESPONSE.value
    db.commit()
    
    # --- Assert 1: No está listo (0 respuestas) ---
    assert event_service.is_event_ready_to_resolve(event, match_players_count) == False

    # --- Acción 1 (P1 responde) ---
    event = event_service.update_info_event(event.id, event.player_id, uuid4())

    # --- Assert 2: No está listo (1 respuesta) ---
    assert event_service.is_event_ready_to_resolve(event, match_players_count) == False
    
    # --- Acción 2 (P2 responde) ---
    event = event_service.update_info_event(event.id, UUID(target_player_id_str), uuid4())

    # --- Assert 3: ¡SÍ ESTÁ LISTO! (2 respuestas) ---
    assert event_service.is_event_ready_to_resolve(event, match_players_count) == True