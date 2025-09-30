from fastapi.testclient import TestClient
from ws_routes import websocket_router
from fastapi import FastAPI
import uuid

app = FastAPI()
app.include_router(websocket_router)

client = TestClient(app)

#un usuario
def test_websocket_connection():
    player_id=uuid.uuid4()
    with client.websocket_connect(f"/ws?player_id={player_id}") as websocket:
        #el server aceptó la conexión
        assert websocket is not None
        websocket.send_text("ping")
        #mandamos algo para ver que no se rompe pero el endpoint no esta recibiendo y leyendo mensajes

#varios usuarios a la vez
def test_three_websocket_connections():
    pl_id1,pl_id2,pl_id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with (
        client.websocket_connect(f"/ws?player_id={pl_id1}") as ws1,
        client.websocket_connect(f"/ws?player_id={pl_id2}") as ws2,
        client.websocket_connect(f"/ws?player_id={pl_id3}") as ws3
    ):
        assert ws1 is not None
        assert ws2 is not None
        assert ws3 is not None
