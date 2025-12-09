from uuid import UUID

import pytest

from app.cards.models import Card, Card_Type, Match_Card
from app.sets.models import SetType
from app.sets.schemas import MatchSetOut
from app.sets.services import InvalidSetError, SetService
from app.sets.tests.conftest import setup_match_and_players


def create_match_cards_for_set(
    db_session, card_names: list[str], match_id: UUID, player_id: UUID
) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = (
            db_session.query(Card)
            .filter(Card.name == name, Card.type == Card_Type.DETECTIVE)
            .first()
        )
        match_card = Match_Card(card_id=card.id, match_id=match_id, player_id=player_id)
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    return card_ids


@pytest.mark.parametrize(
    "set_type, card_names",
    [
        (SetType.PARKER_PYNE, ["PARKER PYNE"]),
        (SetType.LADY_EILEEN, ["LADY EILEEN", "PARKER PYNE"]),
        (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TOMMY BERESFORD"]),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "MISS MARPLE", "HARLEY QUIN WILDCARD"],
        ),
        (SetType.MISS_MARPLE, ["MISS MARPLE"]),
    ],
)
def test_create_set_invalid_combinations(db_session, client, set_type, card_names):
    """Verifica que se lance InvalidSetError con combinaciones de cartas inválidas."""
    setup_data = setup_match_and_players(client, db_session)
    match_id = setup_data["match_id"]
    owner_id = setup_data["owner_id"]
    match_card_ids = create_match_cards_for_set(
        db_session, card_names, match_id, owner_id
    )
    set_data = {
        "type": set_type,
        "card_ids": match_card_ids,
        "player_id": owner_id,
        "match_id": match_id,
    }
    set_service = SetService(db_session)
    with pytest.raises(
        InvalidSetError, match="Combinación inválida de cartas para el tipo de set"
    ):
        set_service.create_set(set_data)


@pytest.mark.parametrize(
    "set_type, card_names, quin_play_expected, quin_count_expected",
    [
        (SetType.PARKER_PYNE, ["PARKER PYNE", "PARKER PYNE"], False, 0),
        (SetType.PARKER_PYNE, ["PARKER PYNE", "HARLEY QUIN WILDCARD"], True, 1),
        (SetType.LADY_EILEEN, ["LADY EILEEN", "LADY EILEEN"], False, 0),
        (SetType.LADY_EILEEN, ["LADY EILEEN", "HARLEY QUIN WILDCARD"], True, 1),
        (SetType.TWO_BERESFORD, ["TOMMY BERESFORD", "TUPPENCE BERESFORD"], False, 0),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HERCULE POIROT"],
            False,
            0,
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HERCULE POIROT", "HARLEY QUIN WILDCARD"],
            True,
            1,
        ),
        (
            SetType.HERCULE_POIROT,
            ["HERCULE POIROT", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
            True,
            2,
        ),
        (SetType.MISS_MARPLE, ["MISS MARPLE", "MISS MARPLE", "MISS MARPLE"], False, 0),
        (
            SetType.MISS_MARPLE,
            ["MISS MARPLE", "MISS MARPLE", "HARLEY QUIN WILDCARD"],
            True,
            1,
        ),
        (
            SetType.MISS_MARPLE,
            ["MISS MARPLE", "HARLEY QUIN WILDCARD", "HARLEY QUIN WILDCARD"],
            True,
            2,
        ),
        (SetType.MR_SATTERTHWAITE, ["MR SATTERTHWAITE", "MR SATTERTHWAITE"], False, 0),
        (
            SetType.MR_SATTERTHWAITE,
            ["MR SATTERTHWAITE", "HARLEY QUIN WILDCARD"],
            True,
            1,
        ),
    ],
)
def test_create_set_valid_combinations(
    db_session, client, set_type, card_names, quin_play_expected, quin_count_expected
):
    """Verifica la creación exitosa de sets con combinaciones válidas."""
    setup_data = setup_match_and_players(client, db_session)
    match_id = setup_data["match_id"]
    owner_id = setup_data["owner_id"]
    match_card_ids = create_match_cards_for_set(
        db_session, card_names, match_id, owner_id
    )
    set_data = {
        "type": set_type,
        "card_ids": match_card_ids,
        "player_id": owner_id,
        "match_id": match_id,
    }
    set_service = SetService(db_session)
    new_set = set_service.create_set(set_data)
    assert isinstance(new_set, MatchSetOut)
    assert new_set.type == set_type
    assert new_set.player_id == owner_id
    assert new_set.match_id == match_id
    assert new_set.quin_play == quin_play_expected
    assert new_set.quin_count == quin_count_expected
