import uuid
from unittest.mock import patch

import pytest

from websocketManager.ws_routes import ConnectionManager


class FakeWebSocket:
    """Class FakeWebSocket."""

    def __init__(self):
        """init  ."""
        self.accepted = False
        self.sent_messages = []

    async def accept(self):
        """Accept."""
        self.accepted = True

    async def send_text(self, message: str):
        """Send text.

        Args:
            message: Parameter message."""
        self.sent_messages.append(message)


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_close_match_keeps_players_dict_intact(
    mock_ws_events_service, mock_match_service
):
    """
    Al cerrar la sala se usa quitMatch (cuando hay player_id),
    lo cual NO elimina al player de `players`; sólo lo mueve a waiting_room.
    """
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    match_id = uuid.uuid4()
    await manager.connect(ws, player_id)
    manager.enterMatch(player_id, match_id)
    manager.close_match(match_id)
    assert player_id in manager.players
    assert ws in manager.waiting_room
    assert match_id not in manager.matches


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_close_match_moves_all_to_waiting_room(
    mock_ws_events_service, mock_match_service
):
    """Test close match moves all to waiting room.

    Args:
        mock_ws_events_service: Parameter mock_ws_events_service.
        mock_match_service: Parameter mock_match_service."""
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    manager = ConnectionManager()
    ws1, ws2 = (FakeWebSocket(), FakeWebSocket())
    p1, p2 = (uuid.uuid4(), uuid.uuid4())
    match_id = uuid.uuid4()
    await manager.connect(ws1, p1)
    await manager.connect(ws2, p2)
    manager.enterMatch(p1, match_id)
    manager.enterMatch(p2, match_id)
    assert match_id in manager.matches
    assert ws1 in manager.matches[match_id]
    assert ws2 in manager.matches[match_id]
    assert ws1 not in manager.waiting_room
    assert ws2 not in manager.waiting_room
    manager.close_match(match_id)
    assert (
        match_id not in manager.matches
        or len(manager.matches.get(match_id, set())) == 0
    )
    assert ws1 in manager.waiting_room
    assert ws2 in manager.waiting_room


@pytest.mark.asyncio
async def test_close_match_when_match_missing():
    """Test close match when match missing."""
    manager = ConnectionManager()
    manager.close_match(uuid.uuid4())


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_connect_and_disconnect(mock_ws_events_service, mock_match_service):
    """Test connect and disconnect.

    Args:
        mock_ws_events_service: Parameter mock_ws_events_service.
        mock_match_service: Parameter mock_match_service."""
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    await manager.connect(ws, player_id)
    assert player_id in manager.players
    assert ws in manager.waiting_room
    assert ws.accepted is True
    manager.disconnect(player_id)
    assert player_id not in manager.players
    assert ws not in manager.waiting_room


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_enter_and_quit_match(mock_ws_events_service, mock_match_service):
    """Test enter and quit match.

    Args:
        mock_ws_events_service: Parameter mock_ws_events_service.
        mock_match_service: Parameter mock_match_service."""
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    await manager.connect(ws, player_id)
    match_id = uuid.uuid4()
    manager.enterMatch(player_id, match_id)
    assert ws in manager.matches[match_id]
    assert ws not in manager.waiting_room
    manager.quitMatch(player_id, match_id)
    assert ws not in manager.matches[match_id]
    assert ws in manager.waiting_room


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.session_local")
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_last_event_message_arrives_on_reconnection(
    mock_ws_events_service, mock_match_service, mock_session_local
):
    """
    Test específico para verificar que el mensaje del último evento llega correctamente
    cuando un jugador se reconecta a una partida activa.
    """
    from unittest.mock import Mock

    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [
        match_id
    ]
    expected_message = (
        '{"event": "cards", "payload": {"cards": [{"id": 1, "name": "Test Card"}]}}'
    )
    mock_last_event = Mock()
    mock_last_event.message = expected_message
    mock_ws_events_service.return_value.get_last_match_event_no_log.return_value = (
        mock_last_event
    )
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    await manager.connect(ws, player_id)
    assert len(ws.sent_messages) == 1
    assert ws.sent_messages[0] == expected_message
    print(f"✅ Último evento enviado correctamente: {ws.sent_messages[0]}")


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.session_local")
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_no_last_event_no_message_sent(
    mock_ws_events_service, mock_match_service, mock_session_local
):
    """
    Verificar que si no hay último evento, no se envía ningún mensaje adicional.
    """
    from unittest.mock import Mock

    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [
        match_id
    ]
    mock_ws_events_service.return_value.get_last_match_event_no_log.return_value = None
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    await manager.connect(ws, player_id)
    assert len(ws.sent_messages) == 0
    print("✅ Correctamente no se envió mensaje cuando no hay último evento")


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.session_local")
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_reconnection_sends_last_event_immediately(
    mock_ws_events_service, mock_match_service, mock_session_local
):
    """
    Prueba que al reconectarse, el último evento se envía inmediatamente
    sin demora, para evitar que se pierdan eventos posteriores.
    """
    import time
    from unittest.mock import Mock

    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [
        match_id
    ]
    mock_last_event = Mock()
    mock_last_event.message = '{"event": "test", "payload": {"test": true}}'
    mock_ws_events_service.return_value.get_last_match_event_no_log.return_value = (
        mock_last_event
    )
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    start_time = time.time()
    await manager.connect(ws, player_id)
    elapsed_time = time.time() - start_time
    assert (
        elapsed_time < 1.0
    ), f"La reconexión tomó {elapsed_time} segundos, debería ser inmediata"
    assert match_id in manager.matches
    assert ws in manager.matches[match_id]
    assert len(ws.sent_messages) == 1
    assert ws.sent_messages[0] == mock_last_event.message
    assert "test" in ws.sent_messages[0]


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_specific_broadcast(mock_ws_events_service, mock_match_service):
    """Test specific broadcast.

    Args:
        mock_ws_events_service: Parameter mock_ws_events_service.
        mock_match_service: Parameter mock_match_service."""
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    mock_ws_events_service.return_value.create_event.return_value = None
    manager = ConnectionManager()
    ws1, ws2 = (FakeWebSocket(), FakeWebSocket())
    pl_id1, pl_id2 = (uuid.uuid4(), uuid.uuid4())
    await manager.connect(ws1, pl_id1)
    await manager.connect(ws2, pl_id2)
    match_id = uuid.uuid4()
    manager.enterMatch(pl_id1, match_id)
    await manager.specificBroadcast("Match only", match_id)
    assert "Match only" in ws1.sent_messages
    assert ws2.sent_messages == []


@pytest.mark.asyncio
@patch("websocketManager.ws_routes.MatchService")
@patch("websocketManager.ws_routes.WsEventsService")
async def test_waiting_room_broadcast(mock_ws_events_service, mock_match_service):
    """Test waiting room broadcast.

    Args:
        mock_ws_events_service: Parameter mock_ws_events_service.
        mock_match_service: Parameter mock_match_service."""
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    manager = ConnectionManager()
    ws1, ws2 = (FakeWebSocket(), FakeWebSocket())
    pl_id1, pl_id2 = (uuid.uuid4(), uuid.uuid4())
    await manager.connect(ws1, pl_id1)
    await manager.connect(ws2, pl_id2)
    await manager.waiting_room_broadcast("Hello")
    assert "Hello" in ws1.sent_messages
    assert "Hello" in ws2.sent_messages
