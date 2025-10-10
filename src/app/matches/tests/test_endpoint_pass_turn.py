import uuid
from unittest.mock import AsyncMock, MagicMock, patch

def test_pass_turn_success_increment(client, setup_match_and_players):
    # Mock WS manager SOLO en este test
    with patch('app.matches.endpoints.manager') as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.enterMatch = MagicMock()

        ctx = setup_match_and_players
        match_id   = ctx["match_str_id"]
        player2_id = ctx["player2_str_id"]

        r = client.post(f"/matches/{match_id}/start")
        assert r.status_code == 200, r.json()

        # estado antes
        before = client.get(f"/matches/{match_id}").json()
        current_before = before["current_player_order"]
        assert current_before == 1  # recién empieza

        # pasar turno
        resp = client.put(f"/matches/{match_id}/pass_turn")
        assert resp.status_code == 200, resp.json()
        assert resp.json()["match_id"] == match_id

        # jugadores
        players_count = len(client.get(f"/matches/{match_id}/players").json())
        assert players_count >= 2

        # estado después
        after = client.get(f"/matches/{match_id}").json()
        current_after = after["current_player_order"]
        assert current_after == 2  # 1 -> 2

        if current_before < players_count:
            assert current_after == current_before + 1
        else:
            assert current_after == 1

def test_pass_turn_match_not_in_progress(client, setup_match_and_players):
    # Mock WS manager SOLO en este test
    with patch('app.matches.endpoints.manager') as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.enterMatch = MagicMock()

        ctx = setup_match_and_players
        match_id   = ctx["match_str_id"]
        player2_id = ctx["player2_str_id"]

        #pasar turno sin iniciar la partida
        resp = client.put(f"/matches/{match_id}/pass_turn")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "The match is not in progress"

def test_pass_turn_invalid_match_id(client):
    with patch('app.matches.endpoints.manager') as ws:
        ws.specificBroadcast = AsyncMock()
        ws.waiting_room_broadcast = AsyncMock()
        ws.enterMatch = MagicMock()

        fake_match_id = str(uuid.uuid4())
        r = client.put(f"/matches/{fake_match_id}/pass_turn")
        assert r.status_code == 404
        assert r.json()["detail"] == "Match not found"
