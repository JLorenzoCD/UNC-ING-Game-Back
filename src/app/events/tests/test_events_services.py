from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.cards.services import Card_event
from app.events.models import EventStatus
from app.events.services import EventService

from app.events.exceptions import EventNotFound


def test_add_response_to_event(db: Session):
    """Test add response to event.

    Args:
        db: Parameter db."""
    event_service = EventService(db)
    target_player_id_str = str(uuid4())
    event = event_service.create_event(
        match_id=uuid4(),
        player_id=uuid4(),
        event_type_str=Card_event.CARD_TRADE.value,
        match_card_id=uuid4(),
        event_payload={"target_player_id": target_player_id_str},
    )
    event.status = EventStatus.PENDING_TARGET_RESPONSE.value
    db.commit()
    db.refresh(event)
    assert event.payload.get("responses") is None
    p1_card_id = uuid4()
    updated_event = event_service.update_info_event(
        event_id=event.id, player_id=event.player_id, info_from_endpoint=p1_card_id
    )
    assert "responses" in updated_event.payload
    assert len(updated_event.payload["responses"]) == 1
    assert updated_event.payload["responses"][0] == str(p1_card_id)
    p2_card_id = uuid4()
    updated_event_2 = event_service.update_info_event(
        event_id=event.id,
        player_id=UUID(target_player_id_str),
        info_from_endpoint=p2_card_id,
    )
    assert len(updated_event_2.payload["responses"]) == 2
    assert updated_event_2.payload["responses"][1] == str(p2_card_id)


def test_create_event_cancelable(db: Session):
    """
    Prueba que si no pasamos status, el evento se crea como PENDING
    y el timer es de 5+ segundos.
    """
    event_service = EventService(db)
    match_id = uuid4()
    player_id = uuid4()
    match_card_id = uuid4()
    new_event = event_service.create_event(
        match_id=match_id,
        player_id=player_id,
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=match_card_id,
        event_payload={"target_set_id": "..."},
    )
    assert new_event.status == EventStatus.PENDING.value
    assert new_event.nsf_count == 0
    assert new_event.resolve_at > datetime.now(
        timezone.utc).replace(tzinfo=None)


def test_create_event_instant_hachazo(db: Session):
    """
    Prueba crear un evento instantaneo con status resolved y tiempo pasado o presente
    """
    event_service = EventService(db)
    match_id = uuid4()
    player_id = uuid4()
    match_card_id = uuid4()
    new_event = event_service.create_event(
        match_id=match_id,
        player_id=player_id,
        event_type_str=Card_event.CARDS_OFF_THE_TABLE.value,
        match_card_id=match_card_id,
        event_payload={"target_player_id": "..."},
        status=EventStatus.RESOLVED,
    )
    assert new_event.status == EventStatus.RESOLVED.value
    assert new_event.resolve_at <= datetime.now(
        timezone.utc).replace(tzinfo=None)


def test_is_event_ready_to_resolve(db: Session):
    """
    Prueba tu servicio 'is_event_ready_to_resolve'.
    """
    event_service = EventService(db)
    target_player_id_str = str(uuid4())
    event = event_service.create_event(
        match_id=uuid4(),
        player_id=uuid4(),
        event_type_str=Card_event.CARD_TRADE.value,
        match_card_id=uuid4(),
        event_payload={"target_player_id": target_player_id_str},
    )
    event.status = EventStatus.PENDING_TARGET_RESPONSE.value
    db.commit()
    assert event_service.is_event_ready_to_resolve(event) == False
    event = event_service.update_info_event(event.id, event.player_id, uuid4())
    assert event_service.is_event_ready_to_resolve(event) == False
    event = event_service.update_info_event(
        event.id, UUID(target_player_id_str), uuid4()
    )
    assert event_service.is_event_ready_to_resolve(event) == True


def test_play_nsf_race_condition_fails(db: Session):
    """
    Prueba que la lógica atómica funciona (la "condición de carrera").
    """
    event_service = EventService(db)
    event = event_service.create_event(
        match_id=uuid4(),
        player_id=uuid4(),
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=uuid4(),
        event_payload={},
    )
    event_service.update_event_nsf(event_id=event.id, nsf_count=0)
    with pytest.raises(EventNotFound, match="alguien ya jugo not so fast"):
        event_service.update_event_nsf(event_id=event.id, nsf_count=0)


def test_play_nsf_success(db: Session):
    """
    Prueba que 'play_nsf_on_event' actualiza el
    contador y el timer.
    """
    event_service = EventService(db)
    event = event_service.create_event(
        match_id=uuid4(),
        player_id=uuid4(),
        event_type_str=Card_event.ANOTHER_VICTIM.value,
        match_card_id=uuid4(),
        event_payload={},
    )
    assert event.nsf_count == 0
    original_resolve_at = event.resolve_at
    updated_event = event_service.update_event_nsf(
        event_id=event.id, nsf_count=0)
    assert updated_event.nsf_count == 1
    assert updated_event.resolve_at > original_resolve_at
