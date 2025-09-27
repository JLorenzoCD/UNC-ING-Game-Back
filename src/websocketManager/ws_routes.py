from fastapi import WebSocket,FastAPI,WebSocketDisconnect,APIRouter
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

websocket_router = APIRouter()

@dataclass
class ConnectionInfo:
    ws: WebSocket
    matchID: Optional[uuid.UUID] = None
    playerID: uuid.UUID

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[ConnectionInfo] = []

    async def connect(self, ws: WebSocket, player_id: uuid.UUID):
        await ws.accept()
        connection=ConnectionInfo(ws=ws, matchID=None, playerID=player_id)
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

#el endpoint con el parametro quedaria similar a ws://localhost:8000/ws?player_id={player_id}
@websocket_router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    player_id = ws.query_params.get("player_id") #sacamos el id de los queryparametros
    await manager.connect(ws,player_id)
    try:
        await ws.receive() #queda bloqueado hasta que el cliente cierre
    except WebSocketDisconnect:
        manager.disconnect(ws)