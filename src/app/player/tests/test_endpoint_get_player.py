import uuid
from datetime import date

from app.player.models import Player


def test_get_player_endpoint(db_session, client):
    # Inicializando la bases de datos
    new_player = Player(
        name="Lorenzo",
        avatar="Parker",
        birthday=date(2000, 2, 2)
    )
    db_session.add(new_player)
    db_session.commit()
    db_session.refresh(new_player)

    # Tests
    player_id = str(new_player.id)

    response = client.get(f"/players/{player_id}")

    assert response.status_code == 200

    data = response.json()
    assert data["id"] is not None
    assert data["id"] == player_id
    assert data["name"] == "Lorenzo"
    assert data["avatar"] == "Parker"
    assert data["birthday"] == "2000-02-02"


def test_player_not_found_endpoint(db_session, client):
    player_id = uuid.uuid4()

    response = client.get(f"/players/{player_id}")

    assert response.status_code == 404


def test_player_is_invalid_uuid_endpoint(db_session, client):
    player_id = ""

    response = client.get(f"/players/{player_id}")

    assert response.status_code == 405
