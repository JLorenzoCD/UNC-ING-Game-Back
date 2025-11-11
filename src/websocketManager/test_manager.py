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


@pytest.mark.asyncio
@patch('websocketManager.ws_routes.session_local')
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_reconnection_sends_last_event_immediately(mock_ws_events_service, mock_match_service, mock_session_local):
    """
    Prueba que al reconectarse, el último evento se envía inmediatamente
    sin demora, para evitar que se pierdan eventos posteriores.
    """
    import time
    from unittest.mock import Mock
    
    # Setup mocks
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    
    # Mock para simular partida activa
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [match_id]
    
    # Mock para simular último evento
    mock_last_event = Mock()
    mock_last_event.message = '{"event": "test", "payload": {"test": true}}'
    mock_ws_events_service.return_value.get_last_match_event.return_value = mock_last_event
    
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    
    # Registrar tiempo antes de conectar
    start_time = time.time()
    
    # Conectar jugador (simula reconexión)
    await manager.connect(ws, player_id)
    
    # Verificar que no tomó más de 1 segundo (antes tomaba 10+ segundos por el sleep)
    elapsed_time = time.time() - start_time
    assert elapsed_time < 1.0, f"La reconexión tomó {elapsed_time} segundos, debería ser inmediata"
    
    # Verificar que el jugador está en la partida
    assert match_id in manager.matches
    assert ws in manager.matches[match_id]
    
    # Verificar que se envió el último evento directamente (el message del WsEvent)
    assert len(ws.sent_messages) == 1
    assert ws.sent_messages[0] == mock_last_event.message
    assert "test" in ws.sent_messages[0]


@pytest.mark.asyncio
@patch('websocketManager.ws_routes.session_local')
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_last_event_message_arrives_on_reconnection(mock_ws_events_service, mock_match_service, mock_session_local):
    """
    Test específico para verificar que el mensaje del último evento llega correctamente
    cuando un jugador se reconecta a una partida activa.
    """
    from unittest.mock import Mock
    
    # Setup mocks
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    
    # Mock para simular partida activa
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [match_id]
    
    # Mock para simular último evento con un mensaje específico
    expected_message = '{"event": "cards", "payload": {"cards": [{"id": 1, "name": "Test Card"}]}}'
    mock_last_event = Mock()
    mock_last_event.message = expected_message
    mock_ws_events_service.return_value.get_last_match_event.return_value = mock_last_event
    
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    
    # Conectar jugador (simula reconexión)
    await manager.connect(ws, player_id)
    
    # Verificar que llegó exactamente el mensaje esperado
    assert len(ws.sent_messages) == 1
    assert ws.sent_messages[0] == expected_message
    print(f"✅ Último evento enviado correctamente: {ws.sent_messages[0]}")


@pytest.mark.asyncio
@patch('websocketManager.ws_routes.session_local')
@patch('websocketManager.ws_routes.MatchService')
@patch('websocketManager.ws_routes.WsEventsService')
async def test_no_last_event_no_message_sent(mock_ws_events_service, mock_match_service, mock_session_local):
    """
    Verificar que si no hay último evento, no se envía ningún mensaje adicional.
    """
    from unittest.mock import Mock
    
    # Setup mocks
    mock_db = Mock()
    mock_session_local.return_value = mock_db
    mock_db.close = Mock()
    
    # Mock para simular partida activa
    match_id = uuid.uuid4()
    mock_match_service.return_value.get_active_matches_ids_player.return_value = [match_id]
    
    # Mock para simular que NO hay último evento
    mock_ws_events_service.return_value.get_last_match_event.return_value = None
    
    manager = ConnectionManager()
    ws = FakeWebSocket()
    player_id = uuid.uuid4()
    
    # Conectar jugador (simula reconexión)
    await manager.connect(ws, player_id)
    
    # Verificar que NO se envió ningún mensaje
    assert len(ws.sent_messages) == 0
    print("✅ Correctamente no se envió mensaje cuando no hay último evento")
