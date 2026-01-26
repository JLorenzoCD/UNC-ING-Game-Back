from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.encoders import jsonable_encoder

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


def create_match_secrets(
    db_session,
    secret_base: Secret,
    match_id: UUID,
    player_ids: list[UUID],
    is_revealed: bool = False,
) -> list[UUID]:
    """Helper para crear Match_Secret para jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret_base.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=is_revealed,
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids


def test_play_set_stolen_invalid_set(db_session, client):
    """Verifica el error 422 si el set_id no existe."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        mock_manager.waiting_room_to_specific_player = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_str_id = setup_data["match_str_id"]
        player2_id = setup_data["player2_id"]
        payload = {"target_player_id": str(
            player2_id), "target_secret_id": None}
        response = client.put(
            f"/matches/{match_str_id}/sets/{uuid4()}/stolen",
            json=jsonable_encoder(payload),
        )
        assert response.status_code == 422


@pytest.mark.parametrize(
    "set_type_to_rob, initial_reveal_state, expected_reveal_state, targetS",
    [
        (SetType.MISS_MARPLE, False, True, True),
        (SetType.HERCULE_POIROT, False, True, True),
        (SetType.PARKER_PYNE, True, False, True),
        (SetType.LADY_EILEEN, False, False, False),
        (SetType.TWO_BERESFORD, False, False, False),
    ],
)
def test_play_set_stolen_success(
    db_session,
    client,
    set_type_to_rob,
    initial_reveal_state,
    expected_reveal_state,
    targetS,
):
    """
    Verifica que aplicar el efecto de un set robado funciona y
    actualiza el estado del secreto en la BBDD.
    """
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        mock_manager.waiting_room_to_specific_player = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        set_id = create_existing_set(
            db_session, set_type_to_rob, match_id, owner_id)
        str_set_id = str(set_id)
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        secret_ids_target = create_match_secrets(
            db_session,
            secret_base,
            match_id,
            [player2_id],
            is_revealed=initial_reveal_state,
        )
        target_secret_id = secret_ids_target[0]
        payload = {
            "player_id": str(owner_id),
            "target_player_id": str(player2_id),
            "target_secret_id": str(target_secret_id) if targetS else None,
        }
        response = client.put(
            f"/matches/{match_str_id}/sets/{str_set_id}/stolen",
            json=jsonable_encoder(payload),
        )
        assert (
            response.status_code == 200
        ), f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response["id"] == str(set_id)
        assert set_response["type"] == set_type_to_rob.value
        db_secret = db_session.get(Match_Secret, target_secret_id)
        assert db_secret.is_revealed == expected_reveal_state
