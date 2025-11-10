import uuid
import pytest
from unittest.mock import patch
from websocketManager.ws_routes import ConnectionManager

class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        self.sent_messages.append(message)

@pytest.mark.asyncio
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_connect_and_disconnect(mock_ws_events_service, mock_match_service):
    # Mock the database services
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()

    await manager.connect(ws,player_id)
    assert player_id in manager.players
    assert ws in manager.waiting_room
    assert ws.accepted is True

    manager.disconnect(player_id)
    assert player_id not in manager.players
    assert ws not in manager.waiting_room

@pytest.mark.asyncio
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_enter_and_quit_match(mock_ws_events_service, mock_match_service):
    # Mock the database services
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
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_waiting_room_broadcast(mock_ws_events_service, mock_match_service):
    # Mock the database services
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    pl_id1,pl_id2= uuid.uuid4(), uuid.uuid4()

    await manager.connect(ws1,pl_id1)
    await manager.connect(ws2,pl_id2)

    await manager.waiting_room_broadcast("Hello")
    assert "Hello" in ws1.sent_messages
    assert "Hello" in ws2.sent_messages

@pytest.mark.asyncio
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_specific_broadcast(mock_ws_events_service, mock_match_service):
    # Mock the database services
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    mock_ws_events_service.return_value.create_event.return_value = None
    
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    pl_id1,pl_id2= uuid.uuid4(), uuid.uuid4()


    await manager.connect(ws1,pl_id1)
    await manager.connect(ws2,pl_id2)

    match_id = uuid.uuid4()
    manager.enterMatch(pl_id1, match_id)

    await manager.specificBroadcast("Match only", match_id)
    assert "Match only" in ws1.sent_messages
    assert ws2.sent_messages == []


@pytest.mark.asyncio
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_close_match_moves_all_to_waiting_room(mock_ws_events_service, mock_match_service):
    # Mock the database services
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    match_id = uuid.uuid4()

    #connect y entrar al match
    await manager.connect(ws1, p1)
    await manager.connect(ws2, p2)
    manager.enterMatch(p1, match_id)
    manager.enterMatch(p2, match_id)

    #precondiciones
    assert match_id in manager.matches
    assert ws1 in manager.matches[match_id]
    assert ws2 in manager.matches[match_id]
    assert ws1 not in manager.waiting_room
    assert ws2 not in manager.waiting_room

    #cerrar el match
    manager.close_match(match_id)

    #ws en el waiting_room
    assert match_id not in manager.matches or len(manager.matches.get(match_id, set())) == 0
    assert ws1 in manager.waiting_room
    assert ws2 in manager.waiting_room

@pytest.mark.asyncio
async def test_close_match_when_match_missing():
    manager = ConnectionManager()
    #cerrar un match que no existe, no ocurre nada
    manager.close_match(uuid.uuid4())

@pytest.mark.asyncio
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_close_match_keeps_players_dict_intact(mock_ws_events_service, mock_match_service):
    """
    Al cerrar la sala se usa quitMatch (cuando hay player_id),
    lo cual NO elimina al player de `players`; sólo lo mueve a waiting_room.
    """
    # Mock the database services
    mock_match_service.return_value.get_active_matches_ids_player.return_value = []
    
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    match_id = uuid.uuid4()

    await manager.connect(ws, player_id)
    manager.enterMatch(player_id, match_id)

    manager.close_match(match_id)

    #player sigue registrado
    assert player_id in manager.players
    #ws vuelve a waiting_room
    assert ws in manager.waiting_room
    #el match fue limpiado
    assert match_id not in manager.matches
