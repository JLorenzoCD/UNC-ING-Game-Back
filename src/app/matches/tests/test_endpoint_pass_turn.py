import uuid
from unittest.mock import AsyncMock, patch

from app.matches.tests.conftest import setup_match_and_players


def test_pass_turn_invalid_match_id(client, db_session):
    """Test pass turn invalid match id.

    Args:
        client: Parameter client.
        db_session: Parameter db_session."""
    with patch("app.matches.endpoints.manager") as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.waiting_room_to_specific_player = AsyncMock()
        ws.enterMatch = AsyncMock()
        fake_match_id = str(uuid.uuid4())
        r = client.put(f"/matches/{fake_match_id}/pass_turn")
        assert r.status_code == 404
        assert r.json()["detail"] == "Match not found"


def test_pass_turn_match_not_in_progress(client, db_session):
    """Test pass turn match not in progress.

    Args:
        client: Parameter client.
        db_session: Parameter db_session."""
    with patch("app.matches.endpoints.manager") as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.waiting_room_to_specific_player = AsyncMock()
        ws.enterMatch = AsyncMock()
        ctx = setup_match_and_players(client, db_session)
        match_id = ctx["match_str_id"]
        ctx["player2_str_id"]
        resp = client.put(f"/matches/{match_id}/pass_turn")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "The match is not in progress"


def test_pass_turn_success_increment(client, db_session):
    """Test pass turn success increment.

    Args:
        client: Parameter client.
        db_session: Parameter db_session."""
    with patch("app.matches.endpoints.manager") as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.waiting_room_to_specific_player = AsyncMock()
        ws.enterMatch = AsyncMock()
        ctx = setup_match_and_players(client, db_session)
        match_id = ctx["match_str_id"]
        ctx["player2_str_id"]
        r = client.post(f"/matches/{match_id}/start")
        assert r.status_code == 200, r.json()
        before = client.get(f"/matches/{match_id}").json()
        current_before = before["current_player_order"]
        assert current_before == 1
        resp = client.put(f"/matches/{match_id}/pass_turn")
        assert resp.status_code == 200, resp.json()
        assert resp.json()["match_id"] == match_id
        players_count = len(client.get(f"/matches/{match_id}/players").json())
        assert players_count >= 2
        after = client.get(f"/matches/{match_id}").json()
        current_after = after["current_player_order"]
        assert current_after == 2
        if current_before < players_count:
            assert current_after == current_before + 1
        else:
            assert current_after == 1
