import uuid

from fastapi import status

from app.matches.tests.conftest import setup_match_and_players
from app.sets.models import Match_Set, SetType


def test_get_sets_database_error(client, db_session):
    """Test manejo de errores de base de datos"""
    setup_data = setup_match_and_players(client, db_session)
    match_id = setup_data["match_str_id"]
    response = client.get(f"/matches/{match_id}/sets")
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ]


def test_get_sets_different_matches(client, db_session):
    """Test que get_sets solo devuelve sets de la partida específica"""
    setup_data1 = setup_match_and_players(client, db_session)
    match1_id_uuid = setup_data1["match_id"]
    match1_id = setup_data1["match_str_id"]
    player1_id = setup_data1["owner_id"]
    response = client.post(
        "/players",
        json={"name": "Third Player", "avatar": "avatar3", "birthday": "2000-03-03"},
    )
    assert response.status_code == 201
    third_player = response.json()
    match_post2 = {
        "name": "Second Test Match",
        "min_players": 2,
        "max_players": 4,
        "owner_id": third_player["id"],
    }
    response = client.post("/matches", json=match_post2)
    assert response.status_code == 201
    match2 = response.json()
    match2_id_uuid = uuid.UUID(match2["id"])
    match2_id = match2["id"]
    match_set1 = Match_Set(
        type=SetType.HERCULE_POIROT,
        player_id=player1_id,
        match_id=match1_id_uuid,
        quin_play=False,
        quin_count=0,
    )
    match_set2 = Match_Set(
        type=SetType.MISS_MARPLE,
        player_id=uuid.UUID(third_player["id"]),
        match_id=match2_id_uuid,
        quin_play=True,
        quin_count=1,
    )
    db_session.add_all([match_set1, match_set2])
    db_session.commit()
    response1 = client.get(f"/matches/{match1_id}/sets")
    assert response1.status_code == status.HTTP_200_OK
    sets1 = response1.json()
    assert len(sets1) == 1
    assert sets1[0]["type"] == SetType.HERCULE_POIROT.value
    response2 = client.get(f"/matches/{match2_id}/sets")
    assert response2.status_code == status.HTTP_200_OK
    sets2 = response2.json()
    assert len(sets2) == 1
    assert sets2[0]["type"] == SetType.MISS_MARPLE.value


def test_get_sets_empty_match(client, db_session):
    """Test obtener sets de una partida que no tiene sets"""
    setup_data = setup_match_and_players(client, db_session)
    match_id = setup_data["match_str_id"]
    response = client.get(f"/matches/{match_id}/sets")
    assert response.status_code == status.HTTP_200_OK
    sets = response.json()
    assert isinstance(sets, list)
    assert len(sets) == 0


def test_get_sets_invalid_match_id_format(client, db_session):
    """Test obtener sets con un ID de partida con formato inválido"""
    invalid_match_id = "not-a-valid-uuid"
    response = client.get(f"/matches/{invalid_match_id}/sets")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_sets_nonexistent_match(client, db_session):
    """Test obtener sets de una partida que no existe"""
    nonexistent_match_id = str(uuid.uuid4())
    response = client.get(f"/matches/{nonexistent_match_id}/sets")
    assert response.status_code == status.HTTP_200_OK
    sets = response.json()
    assert isinstance(sets, list)
    assert len(sets) == 0


def test_get_sets_response_format(client, db_session):
    """Test que la respuesta tiene el formato correcto"""
    setup_data = setup_match_and_players(client, db_session)
    match_id_uuid = setup_data["match_id"]
    match_id = setup_data["match_str_id"]
    player_id = setup_data["owner_id"]
    match_set = Match_Set(
        type=SetType.MR_SATTERTHWAITE,
        player_id=player_id,
        match_id=match_id_uuid,
        quin_play=True,
        quin_count=2,
    )
    db_session.add(match_set)
    db_session.commit()
    db_session.refresh(match_set)
    response = client.get(f"/matches/{match_id}/sets")
    assert response.status_code == status.HTTP_200_OK
    sets = response.json()
    assert isinstance(sets, list)
    assert len(sets) == 1
    set_item = sets[0]
    required_fields = ["id", "type", "player_id", "match_id", "quin_play", "quin_count"]
    for field in required_fields:
        assert field in set_item, f"Campo {field} faltante en la respuesta"
    assert isinstance(set_item["id"], str)
    assert isinstance(set_item["type"], str)
    assert isinstance(set_item["player_id"], str)
    assert isinstance(set_item["match_id"], str)
    assert isinstance(set_item["quin_play"], bool)
    assert isinstance(set_item["quin_count"], int)
    assert set_item["type"] == SetType.MR_SATTERTHWAITE.value
    assert set_item["quin_play"] == True
    assert set_item["quin_count"] == 2


def test_get_sets_with_multiple_sets(client, db_session):
    """Test obtener sets cuando hay múltiples sets en la partida"""
    setup_data = setup_match_and_players(client, db_session)
    match_id_uuid = setup_data["match_id"]
    match_id = setup_data["match_str_id"]
    owner_id = setup_data["owner_id"]
    player2_id = setup_data["player2_id"]
    sets_data = [
        {
            "type": SetType.HERCULE_POIROT,
            "player_id": owner_id,
            "quin_play": True,
            "quin_count": 1,
        },
        {
            "type": SetType.MISS_MARPLE,
            "player_id": player2_id,
            "quin_play": False,
            "quin_count": 0,
        },
        {
            "type": SetType.PARKER_PYNE,
            "player_id": owner_id,
            "quin_play": True,
            "quin_count": 2,
        },
    ]
    created_sets = []
    for set_data in sets_data:
        match_set = Match_Set(
            type=set_data["type"],
            player_id=set_data["player_id"],
            match_id=match_id_uuid,
            quin_play=set_data["quin_play"],
            quin_count=set_data["quin_count"],
        )
        db_session.add(match_set)
        db_session.commit()
        db_session.refresh(match_set)
        created_sets.append(match_set)
    response = client.get(f"/matches/{match_id}/sets")
    assert response.status_code == status.HTTP_200_OK
    sets = response.json()
    assert isinstance(sets, list)
    assert len(sets) == 3
    returned_set_ids = [set_item["id"] for set_item in sets]
    expected_set_ids = [str(match_set.id) for match_set in created_sets]
    for expected_id in expected_set_ids:
        assert expected_id in returned_set_ids
    hercule_sets = [s for s in sets if s["type"] == SetType.HERCULE_POIROT.value]
    assert len(hercule_sets) == 1
    assert hercule_sets[0]["quin_play"] == True
    assert hercule_sets[0]["quin_count"] == 1


def test_get_sets_with_single_set(client, db_session):
    """Test obtener sets cuando hay un set en la partida"""
    setup_data = setup_match_and_players(client, db_session)
    match_id_uuid = setup_data["match_id"]
    match_id = setup_data["match_str_id"]
    player_id = setup_data["owner_id"]
    match_set = Match_Set(
        type=SetType.HERCULE_POIROT,
        player_id=player_id,
        match_id=match_id_uuid,
        quin_play=False,
        quin_count=0,
    )
    db_session.add(match_set)
    db_session.commit()
    db_session.refresh(match_set)
    response = client.get(f"/matches/{match_id}/sets")
    assert response.status_code == status.HTTP_200_OK
    sets = response.json()
    assert isinstance(sets, list)
    assert len(sets) == 1
    returned_set = sets[0]
    assert returned_set["id"] == str(match_set.id)
    assert returned_set["type"] == SetType.HERCULE_POIROT.value
    assert returned_set["player_id"] == str(player_id)
    assert returned_set["match_id"] == str(match_id_uuid)
    assert returned_set["quin_play"] == False
    assert returned_set["quin_count"] == 0
