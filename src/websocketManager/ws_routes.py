from fastapi import WebSocket,FastAPI,WebSocketDisconnect,APIRouter
import uuid
from typing import List, Dict, Any, Optional

websocket_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.matches: dict[uuid.UUID, set[WebSocket]] = {}
        self.players: dict[uuid.UUID, WebSocket] = {}
        self.waiting_room: set[WebSocket] = set()

    async def connect(self, ws: WebSocket, player_id: uuid.UUID):
        await ws.accept()
        self.players[player_id] = ws
        self.waiting_room.add(ws)

    def disconnect(self, player_id:uuid.UUID):
        ws=self.players.pop(player_id, None) #aplica None por defecto si no encuentra un player con ese ID
        if ws is None:
            raise ValueError(f"El jugador {player_id} no se encontro en los jugadores activos")
        self.waiting_room.discard(ws)

        #lo desasocia si esta en alguna partida. No deberia poder desconectarse en partida(por ahora al menos)
        for match_set in self.matches.values():
            match_set.discard(ws)
    
    def enterMatch(self, player_id:uuid.UUID, matchID:uuid.UUID):
        ws=self.players.get(player_id)
        if matchID not in self.matches:
            self.matches[matchID] = set()
        self.matches[matchID].add(ws)
        self.waiting_room.discard(ws)

    def quitMatch(self, player_id:uuid.UUID, matchID:uuid.UUID):
        ws = self.players.get(player_id)
        if matchID in self.matches:
            self.matches[matchID].discard(ws)
        self.waiting_room.add(ws)

    async def send_message(self, message: str, ws: WebSocket):
        await ws.send_text(message)

    async def waiting_room_broadcast(self,message:str):
        for ws in self.waiting_room:
            await self.send_message(message, ws)

    async def specificBroadcast(self, message:str, matchID: uuid.UUID):
        setws = self.matches.get(matchID)
        if setws is not None:
            for ws in setws:
                await self.send_message(message, ws)
            

manager = ConnectionManager()

#el endpoint con el parametro quedaria similar a ws://localhost:8000/ws?player_id={player_id}
@websocket_router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    player_id = uuid.UUID(ws.query_params.get("player_id")) #sacamos el id de los queryparametros
    await manager.connect(ws,player_id)
    try:
        await ws.receive() #queda bloqueado hasta que el cliente cierre
    except WebSocketDisconnect:
        manager.disconnect(player_id)