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

    def close_match(self, match_id: uuid.UUID):
        """
        Saca a todos los sockets de la sala del match_id y se
        unen automaticamente al waiting room (listado de partidas)
        """
        conns = self.matches.get(match_id)
        if conns is None:
            return

        # copiamos para iterar seguro aunque se vaya vaciando
        conns_copy = set(conns)
        for ws in conns_copy:
            # buscamos el player_id correspondiente a este ws
            player_id = None
            for pid, conn in self.players.items():
                if conn is ws:
                    player_id = pid
                    break
            if player_id is not None:
                # usa la lógica existente: saca del match y lo manda a waiting_room
                self.quitMatch(player_id, match_id)
            else:
                # si no encontramos player (raro), igual lo sacamos de la sala y lo mandamos a waiting
                try:
                    conns.discard(ws)
                except Exception:
                    pass
                self.waiting_room.add(ws)
        # por si quedó la sala vacía, borramos la key (sin explotar si ya no existe)
        self.matches.pop(match_id, None)



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

    async def safe_send_message(self, message: str, ws: WebSocket):
        try:
            await ws.send_text(message)
        except RuntimeError:
            # Si el socket está cerrado, limpiamos
            player_id_to_remove = next((pid for pid, conn in self.players.items() if conn == ws), None)
            if player_id_to_remove:
                self.disconnect(player_id_to_remove)
            else:
                self.waiting_room.discard(ws)
        except Exception as e:
            print(f"Error inesperado al enviar mensaje: {e}")

    async def waiting_room_broadcast(self, message: str):
        for ws in list(self.waiting_room):
            await self.safe_send_message(message, ws)

    async def specificBroadcast(self, message: str, matchID: uuid.UUID):
        setws = self.matches.get(matchID, set())
        for ws in list(setws):
            await self.safe_send_message(message, ws)
            

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