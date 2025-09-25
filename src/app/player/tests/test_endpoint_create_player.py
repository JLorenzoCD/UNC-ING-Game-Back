from fastapi.testclient import TestClient


def test_create_valid_player_endpoint(client):
    response = client.post("/players", json={
        "name": "Hernan",
        "avatar": "avatar2",
        "birthday": "1800-04-21"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Hernan"
    assert data["avatar"] == "avatar2"
    assert data["birthday"] == "1800-04-21"
    assert data["id"] is not None

def test_create_player_invalid_name_endpoint(client):
    response = client.post("/players", json={
        "name": 4,
        "avatar": "avatar2",
        "birthday": "1800-04-21"
    })
    assert response.status_code == 422

def test_create_player_invalid_avatar_endpoint(client):
    response = client.post("/players", json={
        "name": "pedro",
        "avatar": 5,
        "birthday": "1800-04-21"
    })
    assert response.status_code == 422

def test_create_player_invalid_date_endpoint(client):
    response = client.post("/players", json={
        "name": "pedro",
        "avatar": "avatar3",
        "birthday": "2100-13-40"
    })
    assert response.status_code == 422

    

    