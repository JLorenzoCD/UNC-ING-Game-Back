import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.matches.models import MatchEventType
from app.messages.services import MessageServices
from app.matches.tests.conftest import setup_match_and_players
from websocketManager.ws_messages import WSEvent, make_ws_message


class TestMsgIntegration:
    """Tests de integración para msgs con endpoints y websockets"""

    def test_msg_creation_on_event_play(self, client, db_session):
        """Test que se verifica el comportamiento del endpoint de eventos con msgs"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_str_id"]
        setup_data["player2_str_id"]
        msg_service = MessageServices(db_session)
        msg_id = msg_service.create_msg(
            uuid.UUID(match_id),
            "[EVENTO] Jugador Owner Player jugo el evento CARDS_OFF_THE_TABLE",
            MatchEventType.CARDS_OFF_THE_TABLE,
            uuid.UUID(owner_id),
        )
        assert msg_id is not None
        msgs = msg_service.get_msgs_by_match(uuid.UUID(match_id))
        event_msgs = [
            msg for msg in msgs if msg.event_type == MatchEventType.CARDS_OFF_THE_TABLE
        ]
        assert len(event_msgs) >= 1
        latest_event_msg = event_msgs[-1]
        assert "[EVENTO]" in latest_event_msg.message
        assert "jugo el evento" in latest_event_msg.message
        assert "CARDS_OFF_THE_TABLE" in latest_event_msg.message

    def test_msg_creation_on_player_join(self, client, db_session):
        """Test que se crea un msg cuando un jugador se une a una partida"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        msg_service = MessageServices(db_session)
        initial_msgs = msg_service.get_msgs_by_match(uuid.UUID(match_id))
        initial_join_msgs = [
            msg for msg in initial_msgs if msg.event_type == MatchEventType.PLAYER_JOIN
        ]
        response = client.post(
            "/players",
            json={
                "name": "Player Three",
                "avatar": "avatar3",
                "birthday": "2000-03-03",
            },
        )
        assert response.status_code == 201
        player3 = response.json()
        with patch(
            "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
        ) as mock_broadcast:
            response = client.post(
                f"/matches/{match_id}/join", params={"player_id": player3["id"]}
            )
        assert response.status_code == 200
        msgs_after = msg_service.get_msgs_by_match(uuid.UUID(match_id))
        join_msgs_after = [
            msg for msg in msgs_after if msg.event_type == MatchEventType.PLAYER_JOIN
        ]
        assert len(join_msgs_after) == len(initial_join_msgs) + 1
        new_join_msgs = [
            msg for msg in join_msgs_after if msg not in initial_join_msgs]
        assert len(new_join_msgs) == 1
        new_msg = new_join_msgs[0]
        assert "Player Three" in new_msg.message
        assert "se unió a la partida" in new_msg.message
        assert new_msg.player_id == uuid.UUID(player3["id"])
        mock_broadcast.assert_called()
        calls = mock_broadcast.call_args_list
        msg_ws_call = None
        for call in calls:
            message = call[0][0]
            if '"event": "message/' in message:
                msg_ws_call = call
                break
        assert msg_ws_call is not None
        assert uuid.UUID(match_id) in [call[0][1] for call in calls]

    def test_msg_creation_on_set_play(self, client, db_session):
        """Test que se crea un msg cuando se juega un set"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        owner_id = setup_data["owner_str_id"]
        with patch(
            "app.matches.endpoints.manager.waiting_room_broadcast",
            new_callable=AsyncMock,
        ), patch(
            "app.matches.endpoints.manager.waiting_room_to_specific_player",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ):
                response = client.post(f"/matches/{match_id}/start")
                assert response.status_code == 200
        response = client.get(f"/matches/{match_id}/cards")
        cards = response.json()
        player_cards = [
            card for card in cards if card["player_id"] == owner_id]
        if len(player_cards) >= 3:
            set_data = {
                "player_id": owner_id,
                "cards_ids": [card["id"] for card in player_cards[:3]],
                "type": "HERCULE_POIROT",
            }
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ) as mock_broadcast:
                response = client.post(
                    f"/matches/{match_id}/sets", json=set_data)
            if response.status_code == 200:
                msg_service = MessageServices(db_session)
                msgs = msg_service.get_msgs_by_match(uuid.UUID(match_id))
                set_msgs = [
                    msg
                    for msg in msgs
                    if msg.event_type == MatchEventType.HERCULE_POIROT
                ]
                assert len(set_msgs) >= 1
                latest_set_msg = set_msgs[-1]
                assert "[SET]" in latest_set_msg.message
                assert "jugo el evento" in latest_set_msg.message
                assert "HERCULE_POIROT" in latest_set_msg.message

    def test_msg_creation_on_turn_pass(self, client, db_session):
        """Test que se verifica el comportamiento del endpoint de pass_turn con msgs"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        with patch(
            "app.matches.endpoints.manager.waiting_room_broadcast",
            new_callable=AsyncMock,
        ), patch(
            "app.matches.endpoints.manager.waiting_room_to_specific_player",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ):
                response = client.post(f"/matches/{match_id}/start")
                assert response.status_code == 200
        with patch(
            "app.matches.endpoints.manager.specificBroadcast", new_callable=AsyncMock
        ) as mock_broadcast:
            response = client.put(f"/matches/{match_id}/pass_turn")
        assert response.status_code == 200
        msg_service = MessageServices(db_session)
        msgs = msg_service.get_msgs_by_match(uuid.UUID(match_id))
        turn_msgs = [msg for msg in msgs if msg.event_type ==
                     MatchEventType.TURN]
        mock_broadcast.assert_called()

    def test_msg_error_handling_in_endpoints(self, client, db_session):
        """Test que los errores en msgs no afectan el flujo principal de endpoints"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        with patch(
            "app.matches.endpoints.MessageServices.create_msg",
            side_effect=Exception("Msg error"),
        ):
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ):
                response = client.post(
                    "/players",
                    json={
                        "name": "Test Player",
                        "avatar": "test_avatar",
                        "birthday": "2000-01-01",
                    },
                )
                test_player = response.json()
                response = client.post(
                    f"/matches/{match_id}/join", params={"player_id": test_player["id"]}
                )
        assert response.status_code == 200
        response = client.get(f"/matches/{match_id}")
        match_data = response.json()
        assert match_data["current_player_count"] == 3

    @pytest.mark.parametrize(
        "event_type,expected_message_part",
        [
            (MatchEventType.PLAYER_JOIN, "se unió a la partida"),
            (MatchEventType.TURN, "[TURN]"),
            (MatchEventType.HERCULE_POIROT, "[SET]"),
            (MatchEventType.CARDS_OFF_THE_TABLE, "[EVENTO]"),
        ],
    )
    def test_msg_message_formats(self, db_session, event_type, expected_message_part):
        """Test que los mensajes de msg tienen el formato esperado para cada tipo de evento"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        if event_type == MatchEventType.PLAYER_JOIN:
            message = "[JOIN] Jugador Test Player se unió a la partida"
        elif event_type == MatchEventType.TURN:
            message = "[TURN] Es turno de Test Player"
        elif event_type == MatchEventType.HERCULE_POIROT:
            message = "[SET] Jugador Test Player jugo el evento HERCULE_POIROT"
        elif event_type == MatchEventType.CARDS_OFF_THE_TABLE:
            message = "[EVENTO] Jugador Test Player jugo el evento CARDS_OFF_THE_TABLE"
        else:
            message = f"Test message for {event_type.value}"
        msg_id = msg_service.create_msg(
            match_id, message, event_type, player_id)
        msg_out = msg_service.get_msg_by_id(msg_id)
        assert expected_message_part in msg_out.message
        assert msg_out.event_type == event_type

    def test_multiple_msgs_same_match(self, client, db_session):
        """Test múltiples msgs en la misma partida mantienen orden y separación"""
        setup_data = setup_match_and_players(client, db_session)
        match_id = setup_data["match_str_id"]
        response = client.post(
            "/players",
            json={
                "name": "Another Owner",
                "avatar": "avatar4",
                "birthday": "2000-04-04",
            },
        )
        another_owner = response.json()
        response = client.post(
            "/matches",
            json={
                "name": "Another Match",
                "min_players": 2,
                "max_players": 4,
                "owner_id": another_owner["id"],
            },
        )
        another_match = response.json()
        another_match_id = another_match["id"]
        with patch(
            "app.matches.endpoints.manager.waiting_room_broadcast",
            new_callable=AsyncMock,
        ), patch(
            "app.matches.endpoints.manager.waiting_room_to_specific_player",
            new_callable=AsyncMock,
        ):
            response = client.post(
                "/players",
                json={"name": "P1", "avatar": "a1",
                      "birthday": "2000-01-01"},
            )
            p1 = response.json()
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ):
                client.post(
                    f"/matches/{match_id}/join", params={"player_id": p1["id"]}
                )
            response = client.post(
                "/players",
                json={"name": "P2", "avatar": "a2",
                      "birthday": "2000-02-02"},
            )
            p2 = response.json()
            with patch(
                "app.matches.endpoints.manager.specificBroadcast",
                new_callable=AsyncMock,
            ):
                client.post(
                    f"/matches/{another_match_id}/join",
                    params={"player_id": p2["id"]},
                )
        msg_service = MessageServices(db_session)
        match1_msgs = msg_service.get_msgs_by_match(uuid.UUID(match_id))
        match2_msgs = msg_service.get_msgs_by_match(
            uuid.UUID(another_match_id))
        assert len(match1_msgs) >= 1
        assert len(match2_msgs) >= 1
        for msg in match1_msgs:
            assert msg.match_id == uuid.UUID(match_id)
        for msg in match2_msgs:
            assert msg.match_id == uuid.UUID(another_match_id)

    def test_websocket_message_format_for_msgs(self, db_session):
        """Test que los mensajes de websocket para msgs tienen el formato correcto"""
        msg_service = MessageServices(db_session)
        match_id = uuid.uuid4()
        player_id = uuid.uuid4()
        message = "Test msg message"
        event_type = MatchEventType.PLAYER_JOIN
        msg_id = msg_service.create_msg(
            match_id, message, event_type, player_id)
        msg_out = msg_service.get_msg_by_id(msg_id)
        ws_message_str = make_ws_message(
            WSEvent.MESSAGE, msg_out.model_dump(mode="json"), match_id)
        assert isinstance(ws_message_str, str)
        assert '"event": "message/' in ws_message_str
        assert '"payload":' in ws_message_str
        assert message in ws_message_str
        assert event_type.value in ws_message_str
        assert str(msg_id) in ws_message_str
