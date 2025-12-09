import uuid
from typing import Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.matches.services import MatchService
from app.models.db import session_local
from app.ws_events.services import WsEventsService


class ConnectionManager:
    """Class ConnectionManager."""

    def __init__(self, db_session_factory: Callable = None):
        """init  .

        Args:
            db_session_factory: Parameter db_session_factory."""
        self.matches: dict[uuid.UUID, set[WebSocket]] = {}
        self.players: dict[uuid.UUID, WebSocket] = {}
        self.waiting_room: set[WebSocket] = set()
        self._db_session_factory = db_session_factory or session_local

    def _get_db_session(self):
        """Get a database session using the configured factory"""
        return self._db_session_factory()

    def close_match(self, match_id: uuid.UUID):
        """
        Saca a todos los sockets de la sala del match_id y se
        unen automaticamente al waiting room (listado de partidas)
        """
        conns = self.matches.get(match_id)
        if conns is None:
            return
        conns_copy = set(conns)
        for ws in conns_copy:
            player_id = None
            for pid, conn in self.players.items():
                if conn is ws:
                    player_id = pid
                    break
            if player_id is not None:
                self.quitMatch(player_id, match_id)
            else:
                try:
                    conns.discard(ws)
                except Exception:
                    pass
                self.waiting_room.add(ws)
        self.matches.pop(match_id, None)

    async def connect(self, ws: WebSocket, player_id: uuid.UUID):
        """Connect.

        Args:
            ws: Parameter ws.
            player_id: Parameter player_id."""
        await ws.accept()
        old_ws = self.players.get(player_id)
        if old_ws:
            print(f"[WS] Desconectando WebSocket anterior para jugador {player_id}")
            try:
                await old_ws.close()
            except Exception:
                pass
            self.waiting_room.discard(old_ws)
            for match_connections in self.matches.values():
                match_connections.discard(old_ws)
        self.players[player_id] = ws
        db = self._get_db_session()
        try:
            in_progress_matches = MatchService(db).get_active_matches_ids_player(
                player_id
            )
            if in_progress_matches:
                for match_id in in_progress_matches:
                    last_event = WsEventsService(db).get_last_match_event(match_id)
                    self.enterMatch(player_id, match_id)
                    if last_event:
                        await self.safe_send_message(last_event.message, ws)
                print(
                    f"[WS] Jugador {player_id} reconectado a {len(in_progress_matches)} partida(s) activa(s)"
                )
            else:
                self.waiting_room.add(ws)
                print(f"[WS] Jugador {player_id} conectado al waiting room")
        except Exception as e:
            print(f"[WS] Error al conectar jugador {player_id}: {e}")
        finally:
            db.close()

    def debug_connections_state(self):
        """Debug method to print current connections state"""
        print(f"[WS] === ESTADO DE CONEXIONES ===")
        print(f"[WS] Total jugadores conectados: {len(self.players)}")
        print(f"[WS] En waiting_room: {len(self.waiting_room)}")
        print(f"[WS] Matches activos: {len(self.matches)}")
        for match_id, connections in self.matches.items():
            print(f"[WS]   Match {match_id}: {len(connections)} conexiones")
        print(f"[WS] ================================")

    def disconnect(self, player_id: uuid.UUID):
        """Disconnect.

        Args:
            player_id: Parameter player_id."""
        ws = self.players.pop(player_id, None)
        if ws is None:
            print(
                f"[WS] ADVERTENCIA: El jugador {player_id} no se encontró en los jugadores activos al desconectar"
            )
            return
        self.waiting_room.discard(ws)
        for match_id, match_set in self.matches.items():
            if ws in match_set:
                match_set.discard(ws)

    def enterMatch(self, player_id: uuid.UUID, matchID: uuid.UUID):
        """Entermatch.

        Args:
            player_id: Parameter player_id.
            matchID: Parameter matchID."""
        ws = self.players.get(player_id)
        if ws is None:
            print(
                f"[WS] ADVERTENCIA: No se encontró WebSocket para jugador {player_id}"
            )
            return
        if matchID not in self.matches:
            self.matches[matchID] = set()
        self.matches[matchID].add(ws)
        self.waiting_room.discard(ws)

    def quitMatch(self, player_id: uuid.UUID, matchID: uuid.UUID):
        """Quitmatch.

        Args:
            player_id: Parameter player_id.
            matchID: Parameter matchID."""
        ws = self.players.get(player_id)
        if matchID in self.matches:
            self.matches[matchID].discard(ws)
        self.waiting_room.add(ws)

    async def safe_send_message(self, message: str, ws: WebSocket):
        """Safe send message.

        Args:
            message: Parameter message.
            ws: Parameter ws."""
        try:
            await ws.send_text(message)
        except RuntimeError as e:
            print(f"[WS] RuntimeError al enviar mensaje: {e}")
            player_id_to_remove = next(
                (pid for pid, conn in self.players.items() if conn == ws), None
            )
            if player_id_to_remove:
                self.players.pop(player_id_to_remove, None)
                for match_connections in self.matches.values():
                    match_connections.discard(ws)
            self.waiting_room.discard(ws)
        except Exception as e:
            print(f"[WS] Error inesperado al enviar mensaje: {e}")
            player_id_to_remove = next(
                (pid for pid, conn in self.players.items() if conn == ws), None
            )
            if player_id_to_remove:
                self.players.pop(player_id_to_remove, None)
                for match_connections in self.matches.values():
                    match_connections.discard(ws)
            self.waiting_room.discard(ws)

    def set_db_session_factory(self, db_session_factory: Callable):
        """Set a custom database session factory (useful for testing)"""
        self._db_session_factory = db_session_factory

    async def specificBroadcast(self, message: str, matchID: uuid.UUID):
        """Specificbroadcast.

        Args:
            message: Parameter message.
            matchID: Parameter matchID."""
        setws = self.matches.get(matchID, set())
        if not setws:
            print(f"[WS] ADVERTENCIA: No hay conexiones en el match {matchID}")
        db = self._get_db_session()
        try:
            WsEventsService(db).create_event(matchID, message)
        finally:
            db.close()
        for ws in list(setws):
            await self.safe_send_message(message, ws)

    async def waiting_room_broadcast(self, message: str):
        """Waiting room broadcast.

        Args:
            message: Parameter message."""
        waiting_room_copy = list(self.waiting_room)
        print(
            f"[WS] Broadcasting a {len(waiting_room_copy)} conexiones en waiting room"
        )
        failed_connections = []
        for ws in waiting_room_copy:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"[WS] Error enviando broadcast a waiting room: {e}")
                failed_connections.append(ws)
        for failed_ws in failed_connections:
            self.waiting_room.discard(failed_ws)
            player_id_to_remove = next(
                (pid for pid, conn in self.players.items() if conn == failed_ws), None
            )
            if player_id_to_remove:
                self.players.pop(player_id_to_remove, None)
                print(
                    f"[WS] Limpiado jugador {player_id_to_remove} por conexión fallida"
                )


websocket_router = APIRouter()
manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """Ws endpoint.

    Args:
        ws: Parameter ws."""
    player_id = uuid.UUID(ws.query_params.get("player_id"))
    await manager.connect(ws, player_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(player_id)
    except Exception as e:
        print(f"[WS] Error en WebSocket para jugador {player_id}: {e}")
        manager.disconnect(player_id)
