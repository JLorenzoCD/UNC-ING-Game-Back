import uuid
import pytest
from ws_routes import ConnectionManager, ConnectionInfo

class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        self.sent_messages.append(message)

@pytest.mark.asyncio
async def test_connect_and_disconnect():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)
    assert len(manager.active_connections) == 1
    assert manager.active_connections[0].ws == ws
    assert ws.accepted is True

    manager.disconnect(ws)
    assert len(manager.active_connections) == 0

@pytest.mark.asyncio
async def test_enter_and_quit_match():
    manager = ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws)
    match_id = uuid.uuid4()

    manager.enterMatch(ws, match_id)
    assert manager.active_connections[0].matchID == match_id

    manager.quitMatch(ws)
    assert manager.active_connections[0].matchID is None

@pytest.mark.asyncio
async def test_general_broadcast():
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.generalBroadcast("Hello")
    assert "Hello" in ws1.sent_messages
    assert "Hello" in ws2.sent_messages

@pytest.mark.asyncio
async def test_specific_broadcast():
    manager = ConnectionManager()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    match_id = uuid.uuid4()
    manager.enterMatch(ws1, match_id)

    await manager.specificBroadcast("Match only", match_id)
    assert "Match only" in ws1.sent_messages
    assert ws2.sent_messages == []

@pytest.mark.asyncio
async def test_specific_broadcast_only_reaches_target():
    manager = ConnectionManager()
    ws1, ws2, ws3 = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)
    await manager.connect(ws3)

    match_id = uuid.uuid4()
    manager.enterMatch(ws1, match_id)

    await manager.specificBroadcast("hola", match_id)

    assert ws1.sent_messages == ["hola"]
    assert ws2.sent_messages == []
    assert ws3.sent_messages == []
