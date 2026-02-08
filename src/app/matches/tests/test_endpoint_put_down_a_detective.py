from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder

from app.cards.models import Card, Match_Card
from app.events.models import EventosDeTurno, EventStatus
from app.matches.tests.conftest import setup_match_and_players
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.sets.models import Match_Set, SetType


def create_existing_set(
    db_session, set_type: SetType, match_id: UUID, player_id: UUID
) -> UUID:
    """Helper para crear un Match_Set ya existente en la BBDD."""
    match_set = Match_Set(
        type=set_type, match_id=match_id, player_id=player_id)
    db_session.add(match_set)
    db_session.commit()
    db_session.refresh(match_set)
    return match_set.id


def create_match_cards_for_set(
    db_session, card_names: list[str], match_id: UUID, player_id: UUID
) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = db_session.query(Card).filter(Card.name == name).first()
        assert (
            card is not None
        ), f"Carta con nombre '{name}' no encontrada. Asegúrate que la DB de test esté poblada."
        match_card = Match_Card(
            card_id=card.id, match_id=match_id, player_id=player_id, is_discarded=False
        )
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    return card_ids


def create_match_secrets(
    db_session, secret: Secret, match_id: UUID, player_ids: list[UUID], revealed: bool
) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=revealed,
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids


@pytest.mark.parametrize(
    "initial_set_type, card_to_play_name, expected_set_type, expected_discard, expected_event_status, requires_secret",
    [
        (
            SetType.MISS_MARPLE,
            "MISS MARPLE",
            SetType.MISS_MARPLE,
            True,
            EventStatus.PENDING,
            True,
        ),
        (
            SetType.PARKER_PYNE,
            "PARKER PYNE",
            SetType.PARKER_PYNE,
            True,
            EventStatus.PENDING,
            True,
        ),
        (
            SetType.TUPPENCE_BERESFORD,
            "TOMMY BERESFORD",
            SetType.TWO_BERESFORD,
            True,
            EventStatus.RESOLVED,
            False,
        ),
        (
            SetType.TOMMY_BERESFORD,
            "TUPPENCE BERESFORD",
            SetType.TWO_BERESFORD,
            True,
            EventStatus.RESOLVED,
            False,
        ),
        (
            SetType.LADY_EILEEN,
            "ARIADNE OLIVER",
            SetType.LADY_EILEEN,
            True,
            EventStatus.PENDING,
            True,
        ),
        (
            SetType.MISS_MARPLE,
            "ARIADNE OLIVER",
            SetType.MISS_MARPLE,
            True,
            EventStatus.PENDING,
            True,
        ),
    ],
)
def test_put_down_a_detective(
    db_session,
    client,
    initial_set_type,
    card_to_play_name,
    expected_set_type,
    expected_discard,
    expected_event_status,
    requires_secret,
):
    """
    Verifica que añadir una carta a un set existente (PUT) funciona,
    manejando la lógica de descarte y los casos especiales.
    """
    with patch("app.matches.endpoints.manager") as mock_manager, patch("app.matches.endpoints.MessageServices.send_player_put_down_a_detective", new_callable=AsyncMock):
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        mock_manager.waiting_room_to_specific_player = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        secret_ids_owner = create_match_secrets(
            db_session, secret_base, match_id, [owner_id], True
        )
        secret_ids_player2 = create_match_secrets(
            db_session, secret_base, match_id, [player2_id], False
        )
        set_id = create_existing_set(
            db_session, initial_set_type, match_id, owner_id)
        str_set_id = str(set_id)
        card_ids_in_hand = create_match_cards_for_set(
            db_session, [card_to_play_name], match_id, owner_id
        )
        card_ids_in_hand[0]
        secret_id_payload = None
        if requires_secret:
            if SetType.PARKER_PYNE == initial_set_type:
                secret_id_payload = secret_ids_owner[0]
            elif card_to_play_name != SetType.ADRIADNE_OLIVER.value:
                secret_id_payload = secret_ids_player2[0]
            elif SetType.MISS_MARPLE == initial_set_type:
                secret_id_payload = secret_ids_player2[0]
        set_in_payload = {
            "card_ids": card_ids_in_hand,
            "player_id": owner_id,
            "target_player_id": (
                player2_id if SetType.PARKER_PYNE != initial_set_type else owner_id
            ),
            "target_secret_id": secret_id_payload,
        }
        response = client.put(
            f"/matches/{match_str_id}/sets/{str_set_id}",
            json=jsonable_encoder(set_in_payload),
        )
        assert (
            response.status_code == 200
        ), f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response["id"] == str(set_id)
        assert set_response["type"] == expected_set_type.value
        if card_to_play_name == "ARIADNE OLIVER":
            expected_event_type = SetType.ADRIADNE_OLIVER.value
        else:
            expected_event_type = expected_set_type.value
        new_event = (
            db_session.query(EventosDeTurno)
            .filter(
                EventosDeTurno.match_id == match_id,
                EventosDeTurno.event_type == expected_event_type,
            )
            .first()
        )
        assert new_event is not None, "No se creó ningún evento"
        assert new_event.status == expected_event_status.value
        assert new_event.player_id == owner_id
        event_payload = new_event.payload
        if (
            initial_set_type == SetType.LADY_EILEEN
            and card_to_play_name != "ARIADNE OLIVER"
        ):
            assert event_payload["is_create_set"] == False
            assert event_payload["set_id"] == str(set_id)
