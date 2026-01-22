from uuid import UUID
import json
from typing import Callable, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.db import session_local
from app.ws_events.services import WsEventsService


class MatchUUID(UUID):
    pass


class GameWebSocket(WebSocket):
    player_id: Optional[UUID] = None
    match_id: Optional[UUID] = None


class ConnectionManager:
    """Class ConnectionManager."""

    def __init__(self, db_session_factory: Callable = None):

        # Diccionario que almacena como clave el match_id y como valor un conjunto
        # de conexiones WS de los jugadores en esa partida
        self.matches: dict[MatchUUID, set[GameWebSocket]] = {}

        # Es el conjunto de conexiones WS de los jugadores que no están en una
        # partida
        self.waiting_room: set[GameWebSocket] = set()

        self._db_session_factory = db_session_factory or session_local

    def _get_db_session(self):
        """Get a database session using the configured factory"""

        return self._db_session_factory()

    def set_db_session_factory(self, db_session_factory: Callable):
        """Set a custom database session factory (useful for testing)"""

        self._db_session_factory = db_session_factory

    async def safe_send_message(self, message: str, ws: GameWebSocket):

        try:
            await ws.send_text(message)
        except Exception as e:

            if isinstance(e, RuntimeError):
                print(f"[WS] RuntimeError al enviar mensaje: {e}")
            else:
                print(f"[WS] Error inesperado al enviar mensaje: {e}")

            # Al haber error, se desconecta el WS del jugador
            self.disconnect(ws)

    async def connect(self, ws: GameWebSocket):
        await ws.accept()

        self.waiting_room.add(ws)

    def disconnect(self, ws: GameWebSocket):

        # Si el WS del jugador se encuentra en el conjunto de conexiones para los
        # jugadores que no están en partida, se lo elimina
        self.waiting_room.discard(ws)

        match_id = ws.match_id
        if match_id is None:
            # Si no esta en partida, no se hace nada
            return

        if match_id not in self.matches:
            # Si el match no se encuentra en el diccionario de matches, no se
            # hace nada
            return

        # Se descarta el WS del jugador de la partida en la que se encuentra
        self.matches[match_id].discard(ws)

    async def enterMatch(self, ws: GameWebSocket, match_id: UUID):

        # Se elimina el WS del jugador del conjunto de conexiones WS que no están
        # en partida
        self.waiting_room.discard(ws)

        if match_id not in self.matches:
            # Se inicializa el self.matches[match_id] si no se lo inicializo
            self.matches[match_id] = set()

        # Se añade el WS del jugador al conjunto de conexiones WS de los jugadores
        # de el match actual
        self.matches[match_id].add(ws)
        ws.match_id = match_id

        # Si la partida esta en progreso, se envía un mensaje WS del ultimo
        # evento que no sea un log
        db = self._get_db_session()
        try:
            last_event = WsEventsService(
                db).get_last_match_event_no_log(match_id)

            if last_event:
                await self.safe_send_message(last_event.message, ws)

        except Exception as e:
            print(f"[WS] Error al conectar jugador {ws.player_id}: {e}")

        finally:
            db.close()

    def quitMatch(self, ws: GameWebSocket):

        match_id = ws.match_id
        if match_id is None:
            # Si el WS del jugador no tiene un ws.match_id, entonces no esta en
            # partida, por lo que no se hace nada
            return

        if match_id in self.matches:
            # Se elimina el WS del jugador del conjunto de WS que se encuentran
            # en la partida actual
            self.matches[match_id].discard(ws)

        # Se modifica el WS para indicar que no esta en partida y se lo mete al
        # jugador al conjunto de conexiones que no están en partida
        ws.match_id = None
        self.waiting_room.add(ws)

    def close_match(self, match_id: UUID):
        """
        Saca a todos los sockets de la sala del match_id y se
        unen automaticamente al waiting room (listado de partidas)
        """

        if match_id not in self.matches:
            # Si la partida no se encuentra, no se hace nada
            return

        # Se obtiene el conjunto de WS de jugadores que se encuentran en la partida
        # actual
        players_in_match = self.matches[match_id]

        # Se elimina el WS del jugador de la partida actual
        players_in_match_copy = set(players_in_match)
        for player_ws in players_in_match_copy:
            self.quitMatch(player_ws)

        # Se elimina el match actual del diccionario de matches
        self.matches.pop(match_id, None)

    async def specificBroadcast(self, message: str, match_id: UUID):

        setws = self.matches.get(match_id, set())

        db = self._get_db_session()
        try:
            WsEventsService(db).create_event(match_id, message)
        finally:
            db.close()

        for ws in list(setws):
            await self.safe_send_message(message, ws)

    async def waiting_room_broadcast(self, message: str):

        waiting_room_copy = list(self.waiting_room)

        for ws in waiting_room_copy:
            await self.safe_send_message(message, ws)

    def debug_connections_state(self):
        """Debug method to print current connections state"""

        print(f"[WS] === ESTADO DE CONEXIONES ===")
        print(f"[WS] En waiting_room: {len(self.waiting_room)}")
        print(f"[WS] Matches activos: {len(self.matches)}")
        for match_id, connections in self.matches.items():
            print(f"[WS]   Match {match_id}: {len(connections)} conexiones")
        print(f"[WS] ================================")


websocket_router = APIRouter()
manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def ws_endpoint(ws: GameWebSocket):

    ws.player_id = None
    ws.match_id = None

    player_id = UUID(ws.query_params.get("player_id"))
    ws.player_id = player_id

    try:
        await manager.connect(ws)

        while True:
            data = await ws.receive_text()

            try:
                data: dict = json.loads(data)
            except Exception:
                continue

            is_subscribe_or_unsubscribe_event = "event" in data and (
                data["event"] == "subscribe_match" or data["event"] == "unsubscribe_match")
            is_valid_subscribe_or_unsubscribe_event = "payload" in data and "match_id" in data[
                "payload"]

            if not (is_subscribe_or_unsubscribe_event and is_valid_subscribe_or_unsubscribe_event):
                continue

            match_id = UUID(data["payload"]["match_id"])

            if data["event"] == "subscribe_match":
                await manager.enterMatch(ws, match_id)
            if data["event"] == "unsubscribe_match":
                manager.quitMatch(ws)

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        print(f"[WS] Error en WebSocket para jugador {player_id}: {e}")
        manager.disconnect(ws)
