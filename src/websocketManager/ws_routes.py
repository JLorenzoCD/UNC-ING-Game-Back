from fastapi import WebSocket,FastAPI,WebSocketDisconnect,APIRouter
import uuid
from typing import List, Dict, Any, Optional, Callable

from app.models.db import session_local
from app.matches.services import MatchService
from app.ws_events.services import WsEventsService

websocket_router = APIRouter()

class ConnectionManager:
    def __init__(self, db_session_factory: Callable = None):
        self.matches: dict[uuid.UUID, set[WebSocket]] = {}
        self.players: dict[uuid.UUID, WebSocket] = {}
        self.waiting_room: set[WebSocket] = set()
        # Use provided session factory or default to session_local
        self._db_session_factory = db_session_factory or session_local
    
    def set_db_session_factory(self, db_session_factory: Callable):
        """Set a custom database session factory (useful for testing)"""
        self._db_session_factory = db_session_factory
    
    def _get_db_session(self):
        """Get a database session using the configured factory"""
        return self._db_session_factory()

    async def connect(self, ws: WebSocket, player_id: uuid.UUID):
        await ws.accept()
        
        # Evitar conexiones duplicadas - desconectar WebSocket anterior si existe
        old_ws = self.players.get(player_id)
        if old_ws:
            print(f"[WS] Desconectando WebSocket anterior para jugador {player_id}")
            try:
                await old_ws.close()
            except Exception:
                pass  # Ignorar errores al cerrar conexión anterior
            # Limpiar de todas las estructuras
            self.waiting_room.discard(old_ws)
            for match_connections in self.matches.values():
                match_connections.discard(old_ws)
        
        self.players[player_id] = ws

        db = self._get_db_session()
        try:
            in_progress_matches = MatchService(db).get_active_matches_ids_player(player_id)
            
            if in_progress_matches:
                for match_id in in_progress_matches:
                    # Primero obtenemos el último evento ANTES de entrar al match
                    last_event = WsEventsService(db).get_last_match_event(match_id)  
                    # Luego entramos al match para recibir eventos futuros
                    self.enterMatch(player_id, match_id)
                    # Finalmente enviamos el último evento si existe
                    if last_event:
                        await self.safe_send_message(last_event.message, ws)
                print(f"[WS] Jugador {player_id} reconectado a {len(in_progress_matches)} partida(s) activa(s)")
            else:
                self.waiting_room.add(ws)
                print(f"[WS] Jugador {player_id} conectado al waiting room")
                
        except Exception as e:
            print(f"[WS] Error al conectar jugador {player_id}: {e}")
        finally:
            db.close()

    def disconnect(self, player_id:uuid.UUID):
        ws=self.players.pop(player_id, None) #aplica None por defecto si no encuentra un player con ese ID
        if ws is None:
            print(f"[WS] ADVERTENCIA: El jugador {player_id} no se encontró en los jugadores activos al desconectar")
            return
        
        self.waiting_room.discard(ws)

        #lo desasocia si esta en alguna partida. No deberia poder desconectarse en partida(por ahora al menos)
        for match_id, match_set in self.matches.items():
            if ws in match_set:
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
        if ws is None:
            print(f"[WS] ADVERTENCIA: No se encontró WebSocket para jugador {player_id}")
            return
        if matchID not in self.matches:
            self.matches[matchID] = set()
        self.matches[matchID].add(ws)
        self.waiting_room.discard(ws)

    def quitMatch(self, player_id:uuid.UUID, matchID:uuid.UUID):
        ws = self.players.get(player_id)
        if matchID in self.matches:
            self.matches[matchID].discard(ws)
        self.waiting_room.add(ws)

    def debug_connections_state(self):
        """Debug method to print current connections state"""
        print(f"[WS] === ESTADO DE CONEXIONES ===")
        print(f"[WS] Total jugadores conectados: {len(self.players)}")
        print(f"[WS] En waiting_room: {len(self.waiting_room)}")
        print(f"[WS] Matches activos: {len(self.matches)}")
        for match_id, connections in self.matches.items():
            print(f"[WS]   Match {match_id}: {len(connections)} conexiones")
        print(f"[WS] ================================")

    async def safe_send_message(self, message: str, ws: WebSocket):
        try:
            await ws.send_text(message)
        except RuntimeError as e:
            print(f"[WS] RuntimeError al enviar mensaje: {e}")
            # Si el socket está cerrado, limpiamos SIN causar desconexión explícita
            player_id_to_remove = next((pid for pid, conn in self.players.items() if conn == ws), None)
            if player_id_to_remove:
                # Solo removemos de las estructuras, no llamamos disconnect que puede causar loops
                self.players.pop(player_id_to_remove, None)
                for match_connections in self.matches.values():
                    match_connections.discard(ws)
            self.waiting_room.discard(ws)
        except Exception as e:
            print(f"[WS] Error inesperado al enviar mensaje: {e}")
            # En caso de error inesperado, también limpiamos silenciosamente
            player_id_to_remove = next((pid for pid, conn in self.players.items() if conn == ws), None)
            if player_id_to_remove:
                self.players.pop(player_id_to_remove, None)
                for match_connections in self.matches.values():
                    match_connections.discard(ws)
            self.waiting_room.discard(ws)

    async def waiting_room_broadcast(self, message: str):
        # Crear una copia de la lista para evitar modificaciones concurrentes
        waiting_room_copy = list(self.waiting_room)
        print(f"[WS] Broadcasting a {len(waiting_room_copy)} conexiones en waiting room")
        
        failed_connections = []
        for ws in waiting_room_copy:
            try:
                await ws.send_text(message)
            except Exception as e:
                print(f"[WS] Error enviando broadcast a waiting room: {e}")
                failed_connections.append(ws)
        
        # Limpiar conexiones que fallaron
        for failed_ws in failed_connections:
            self.waiting_room.discard(failed_ws)
            # Buscar y limpiar el jugador asociado
            player_id_to_remove = next((pid for pid, conn in self.players.items() if conn == failed_ws), None)
            if player_id_to_remove:
                self.players.pop(player_id_to_remove, None)
                print(f"[WS] Limpiado jugador {player_id_to_remove} por conexión fallida")

    async def specificBroadcast(self, message: str, matchID: uuid.UUID):
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
            
manager = ConnectionManager()

#el endpoint con el parametro quedaria similar a ws://localhost:8000/ws?player_id={player_id}
@websocket_router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    player_id = uuid.UUID(ws.query_params.get("player_id")) #sacamos el id de los queryparametros
    await manager.connect(ws,player_id)
    try:
        while True:
            # Mantener la conexión activa y recibir mensajes del cliente
            data = await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(player_id)
    except Exception as e:
        print(f"[WS] Error en WebSocket para jugador {player_id}: {e}")
        manager.disconnect(player_id)