from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.cards.models import Card, Match_Card
from app.events import services as event_services
from app.matches.tests.conftest import jsonable_encoder, setup_match_and_players
from app.secrets import services as secret_services
from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.sets.models import SetType


def create_match_cards_for_set(
    db_session, card_names: list[str], match_id: UUID, player_id: UUID
) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = db_session.query(Card).filter(Card.name == name).first()
        assert card is not None, f"Card with name '{name}' not found in test setup."
        match_card = Match_Card(
            card_id=card.id, match_id=match_id, player_id=player_id)
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    return card_ids


def create_match_secrets(
    db_session, secret: Secret, match_id: UUID, player_ids: list[UUID]
) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=False,
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids


@pytest.mark.parametrize(
    "set_type, card_names, quins_count_expected",
    [
        (SetType.LADY_EILEEN, ["LADY EILEEN", "LADY EILEEN"], 0),
        (SetType.LADY_EILEEN, ["LADY EILEEN", "HARLEY QUIN WILDCARD"], 1),
    ],
)
def test_endpoint_play_Eileen(
    db_session, client, set_type, card_names, quins_count_expected
):
    """Verifica que los sets de Eileen, hermanos Beresford y Mr. Satterthwaite no realicen accion pero creen el set."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        match_secret_ids = create_match_secrets(
            db_session, secret_base, match_id, [owner_id, player2_id]
        )
        target_secret_id = match_secret_ids[0]
        secret_services.SecretsServices(
            db_session).reveal_secret(target_secret_id)
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": None,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert (
            response.status_code == 201
        ), f"Error {response.status_code}: {response.text}"
        set_data_payload = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": None,
        }
        event_payload = {
            "type": jsonable_encoder(set_type),
            "card_ids": jsonable_encoder(match_card_ids),
            "player_id": jsonable_encoder(owner_id),
            "target_player_id": jsonable_encoder(owner_id),
            "target_secret_id": None,
            "is_create_set": True,
            "set_data": jsonable_encoder(set_data_payload),
        }
        new_event = event_services.EventServices(db_session).create_event(
            match_id,
            owner_id,
            SetType.LADY_EILEEN.value,
            None,
            jsonable_encoder(event_payload),
        )
        assert new_event is not None
        resutl = event_services.EventServices(
            db_session).resolve_event(new_event)
        accion_set = resutl["accion_set"]
        assert accion_set["target_player_id"] == str(owner_id)
        assert resutl["type"] == SetType.LADY_EILEEN.value
        data = resutl["data_set"]
        assert data is not None
        assert data["deleted_cards"] == [str(card) for card in match_card_ids]
        assert resutl["type"] == SetType.LADY_EILEEN.value


@pytest.mark.parametrize(
    "set_type, card_names, quins_count_expected",
    [
        (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TUPPENCE BERESFORD"], 0),
        (SetType.MR_SATTERTHWAITE, [
         "MR SATTERTHWAITE", "MR SATTERTHWAITE"], 0),
        (SetType.MR_SATTERTHWAITE, [
         "MR SATTERTHWAITE", "HARLEY QUIN WILDCARD"], 1),
    ],
)
def test_endpoint_play_Eileen_Beresford_Satterthwaitte(
    db_session, client, set_type, card_names, quins_count_expected
):
    """Verifica que los sets de Eileen, hermanos Beresford y Mr. Satterthwaite no realicen accion pero creen el set."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        match_secret_ids = create_match_secrets(
            db_session, secret_base, match_id, [owner_id, player2_id]
        )
        target_secret_id = match_secret_ids[0]
        secret_services.SecretsServices(
            db_session).reveal_secret(target_secret_id)
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": None,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert (
            response.status_code == 201
        ), f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response["type"] == set_type.value
        assert set_response["player_id"] == str(owner_id)
        assert set_response["quin_count"] == quins_count_expected


@pytest.mark.parametrize(
    "set_type, card_names",
    [
        (SetType.LADY_EILEEN, ["LADY EILEEN", "LADY EILEEN"]),
        (SetType.LADY_EILEEN, ["LADY EILEEN", "HARLEY QUIN WILDCARD"]),
        (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TUPPENCE BERESFORD"]),
        (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "MR SATTERTHWAITE"]),
        (SetType.MR_SATTERTHWAITE, [
         "MR SATTERTHWAITE", "HARLEY QUIN WILDCARD"]),
    ],
)
def test_endpoint_play_Eileen_Beresford_Satterthwaitte_invalid_combination(
    db_session, client, set_type, card_names
):
    """Verifica las excepciones de los sets LADY_EILEEN, TWO_BERESFORD y MR_SATTERTHWAITE."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        match_secret_ids = create_match_secrets(
            db_session, secret_base, match_id, [owner_id, player2_id]
        )
        target_secret_id = match_secret_ids[0]
        secret_services.SecretsServices(
            db_session).reveal_secret(target_secret_id)
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": owner_id,
            "target_secret_id": target_secret_id,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert (
            response.status_code == 400
        ), f"Error {response.status_code}: {response.text}"
        assert (
            "No se debería seleccionar secreto en este momento"
            in response.json()["detail"]
        )


@pytest.mark.parametrize(
    "set_type, card_names",
    [
        (SetType.PARKER_PYNE, ["PARKER PYNE", "PARKER PYNE"]),
        (SetType.PARKER_PYNE, ["PARKER PYNE", "HARLEY QUIN WILDCARD"]),
    ],
)
def test_endpoint_play_Pyne(db_session, client, set_type, card_names):
    """Verifica que el set de Pyne oculte un secreto correctamente."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        match_secret_ids = create_match_secrets(
            db_session, secret_base, match_id, [owner_id, player2_id]
        )
        target_secret_id = match_secret_ids[1]
        secret_services.SecretsServices(
            db_session).reveal_secret(target_secret_id)
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": target_secret_id,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert (
            response.status_code == 201
        ), f"Error {response.status_code}: {response.text}"
        set_response = response.json()
        assert set_response["type"] == set_type.value
        assert set_response["player_id"] == str(owner_id)
        new_event = event_services.EventServices(db_session).create_event(
            match_id, owner_id, set_response["type"], None, jsonable_encoder(
                set_in)
        )
        assert new_event is not None
        resutl = event_services.EventServices(
            db_session).resolve_event(new_event)
        assert new_event is not None
        assert resutl["is_revealed"] == False
        db_session.expire_all()
        match_secret_db = (
            db_session.query(Match_Secret)
            .filter(Match_Secret.id == target_secret_id)
            .first()
        )
        assert match_secret_db.is_revealed is False


@pytest.mark.parametrize(
    "set_type, card_names, quins",
    [
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HERCULE POIROT"],
            0,
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HARLEY QUIN WILDCARD"],
            1,
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
            2,
        ),
        (SetType.MISS_MARPLE, ["MISS MARPLE",
         "MISS MARPLE", "MISS MARPLE"], 0),
        (
            SetType.MISS_MARPLE,
            ["MISS MARPLE", "MISS MARPLE", "HARLEY QUIN WILDCARD"],
            1,
        ),
        (
            SetType.MISS_MARPLE,
            ["MISS MARPLE", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
            2,
        ),
    ],
)
def test_endpoint_play_set_Poirot_Marple(
    db_session, client, set_type, card_names, quins
):
    """Verifica que los sets de Poirot y Marple revelen un secreto correctamente."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        match_secret_ids = create_match_secrets(
            db_session, secret_base, match_id, [owner_id, player2_id]
        )
        target_secret_id = match_secret_ids[1]
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": target_secret_id,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert response.status_code == 201
        set_response = response.json()
        assert set_response["type"] == set_type.value
        assert set_response["player_id"] == str(owner_id)
        assert set_response["quin_count"] == quins
        db_session.expire_all()
        new_event = event_services.EventServices(db_session).create_event(
            match_id, owner_id, set_response["type"], None, jsonable_encoder(
                set_in)
        )
        assert new_event is not None
        resutl = event_services.EventServices(
            db_session).resolve_event(new_event)
        assert new_event is not None
        assert resutl["is_revealed"] == True
        match_secret_db = (
            db_session.query(Match_Secret)
            .filter(Match_Secret.id == target_secret_id)
            .first()
        )
        assert match_secret_db.is_revealed is True


@pytest.mark.parametrize(
    "set_type, card_names",
    [
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HERCULE POIROT"],
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HARLEY QUIN WILDCARD"],
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
        ),
        (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "MISS MARPLE"]),
        (SetType.MISS_MARPLE, ["MISS MARPLE",
         "MISS MARPLE", "HARLEY QUIN WILDCARD"]),
        (
            SetType.MISS_MARPLE,
            ["MISS MARPLE", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
        ),
    ],
)
def test_endpoint_play_set_target_secret_required(
    db_session, client, set_type, card_names
):
    """Test para verificar que Poirot/Marple requieren un secreto objetivo."""
    with patch("app.matches.endpoints.manager") as mock_manager:
        mock_manager.specificBroadcast = AsyncMock()
        mock_manager.waiting_room_broadcast = AsyncMock()
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_id"]
        match_str_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_id"]
        player2_id = setup_data["player2_id"]
        secret_base = (
            db_session.query(Secret).filter(
                Secret.type == Secret_Type.INNOCENT).first()
        )
        match_card_ids = create_match_cards_for_set(
            db_session, card_names, match_id, owner_id
        )
        create_match_secrets(db_session, secret_base,
                             match_id, [owner_id, player2_id])
        set_in = {
            "type": set_type,
            "card_ids": match_card_ids,
            "player_id": owner_id,
            "target_player_id": player2_id,
            "target_secret_id": None,
        }
        response = client.post(
            f"/matches/{match_str_id}/sets", json=jsonable_encoder(set_in)
        )
        assert response.status_code == 400
        assert "No hay secreto seleccionado" in response.json()["detail"]
