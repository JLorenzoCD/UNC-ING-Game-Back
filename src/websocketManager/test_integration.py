import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from ws_routes import websocket_router

app = FastAPI()
app.include_router(websocket_router)
client = TestClient(app)


def test_three_websocket_connections():
    """Test three websocket connections."""
    pl_id1, pl_id2, pl_id3 = (uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    with client.websocket_connect(
        f"/ws?player_id={pl_id1}"
    ) as ws1, client.websocket_connect(
        f"/ws?player_id={pl_id2}"
    ) as ws2, client.websocket_connect(
        f"/ws?player_id={pl_id3}"
    ) as ws3:
        assert ws1 is not None
        assert ws2 is not None
        assert ws3 is not None


def test_websocket_connection():
    """Test websocket connection."""
    player_id = uuid.uuid4()
    with client.websocket_connect(f"/ws?player_id={player_id}") as websocket:
        assert websocket is not None
        websocket.send_text("ping")
