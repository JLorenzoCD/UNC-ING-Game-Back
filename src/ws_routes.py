from fastapi import WebSocket,FastAPI,WebSocketDisconnect,APIRouter

websocket_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

    async def send_message(self, message: str, ws: WebSocket):
        await ws.send_text(message)

    async def broadcast(self,message:str):
        for ws in self.active_connections:
            await ws.send_text(message)
            

manager = ConnectionManager()

@websocket_router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            text = await ws.receive_text()
            print(f"WS recv: {text}")
    except WebSocketDisconnect:
        manager.disconnect(ws)