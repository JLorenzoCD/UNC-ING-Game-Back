from fastapi import WebSocket,FastAPI,WebSocketDisconnect,APIRouter
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

websocket_router = APIRouter()

@dataclass
class ConnectionInfo:
    ws: WebSocket
    matchID: Optional[uuid.UUID] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[ConnectionInfo] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        connection=ConnectionInfo(ws=ws, matchID=None)
        self.active_connections.append(connection)

    def disconnect(self, ws: WebSocket):
        for connection in self.active_connections:
            if connection.ws == ws:
                self.active_connections.remove(connection)
                break
    
    def enterMatch(self, ws:WebSocket, matchID:uuid.UUID):
        for connection in self.active_connections:
            if connection.ws == ws:
                connection.matchID = matchID
                break

    def quitMatch(self, ws:WebSocket):
        for connection in self.active_connections:
            if connection.ws == ws:
                connection.matchID = None
                break

    async def send_message(self, message: str, ws: WebSocket):
        await ws.send_text(message)

    async def generalBroadcast(self,message:str):
        for connection in self.active_connections:
            await self.send_message(message, connection.ws)

    async def specificBroadcast(self, message:str, matchID: uuid.UUID):
        for connection in self.active_connections:
            if connection.matchID == matchID:
                await self.send_message(message, connection.ws)
            

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