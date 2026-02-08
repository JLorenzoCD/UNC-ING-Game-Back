from datetime import datetime
from typing import List, Optional
from uuid import UUID
from contextlib import suppress

from sqlalchemy.exc import SQLAlchemyError

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message

from app.messages.schemas import MatchMessageOut
from app.messages.models import MatchMessage
from app.matches.utils import db_match_log_2_match_log_schema

from app.matches.turn_service import TurnServices
from app.player.services import PlayerServices
from app.sets.services import SetServices

from app.matches.models import MatchEventType
from app.secrets.models import Secret_action
from app.sets.models import SetType
from app.cards.services import Card_event
from app.events.models import EventosDeTurno


class MessageServices:
    """Service class for managing match msg."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def create_log(
        self,
        match_id: UUID,
        message: str,
        event_type: str,
        player_id: Optional[UUID] = None,
    ) -> UUID:
        """Create a new log entry for a match."""
        new_log = MatchMessage(
            match_id=match_id,
            message=message,
            event_type=event_type,
            player_id=player_id,
            created_at=datetime.now(),
        )
        try:
            self._db.add(new_log)
            self._db.commit()
            self._db.refresh(new_log)
            return new_log.id
        except Exception:
            self._db.rollback()
            raise

    def get_log_by_id(self, log_id: UUID) -> MatchMessageOut:
        """Get a specific log by ID."""
        try:
            log = self._db.query(MatchMessage).filter(
                MatchMessage.id == log_id).first()
            return db_match_log_2_match_log_schema(log)
        except Exception:
            self._db.rollback()
            raise

    def get_msgs_by_match(self, match_id: UUID) -> List[MatchMessageOut]:
        """Get all logs for a match."""
        result = self._db.query(MatchMessage).filter(
            MatchMessage.match_id == match_id).all()
        return [db_match_log_2_match_log_schema(match_log) for match_log in result]

    async def create_and_propagate_log(
        self,
        match_id: UUID,
        message: str,
        event_type: str,
        player_id: Optional[UUID] = None,
        is_system_msg: Optional[bool] = True,
    ) -> MatchMessageOut:
        """Create a new log entry for a match and propagate by websockets"""

        new_log = MatchMessage(
            match_id=match_id,
            message=message,
            event_type=event_type,
            player_id=player_id,
            created_at=datetime.now(),
            is_system_msg=is_system_msg
        )
        try:
            self._db.add(new_log)
            self._db.commit()
            self._db.refresh(new_log)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        log_out = db_match_log_2_match_log_schema(
            new_log).model_dump(mode="json")

        with suppress(Exception):
            await manager.specificBroadcast(
                make_ws_message(WSEvent.MESSAGE, log_out, match_id), match_id
            )

        return log_out

    async def _pre_create_and_propagate_log(self, match_id: UUID, msg: str, event_type: MatchEventType, player_id: UUID, err_name: str):
        try:
            await self.create_and_propagate_log(match_id, msg, event_type, player_id)
        except Exception as e:
            print(
                f"[LOG] Error creando/broadcast MessageServices de '{err_name}': {e}")

    async def send_player_join_to_match(self, match_id: UUID, player_id: UUID):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[JOIN] Jugador {player.name} se unió a la partida"

            await self._pre_create_and_propagate_log(
                match_id, log_message, MatchEventType.PLAYER_JOIN, player.id, "send_player_join_to_match")
        except Exception as e:
            print(
                f"[LOG] Error in send_player_join_to_match, para match {match_id}: {e}")

    async def send_player_quit_to_match(self, match_id: UUID, player_id: UUID):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[QUIT] Jugador {player.name} se fue de la partida."

            await self._pre_create_and_propagate_log(
                match_id, log_message, MatchEventType.PLAYER_QUIT, player.id, "send_player_quit_to_match")
        except Exception as e:
            print(
                f"[LOG] Error in send_player_join_to_match, para match {match_id}: {e}")

    async def send_curr_player_turn_in_match(self, match_id: UUID, player_id: UUID | None = None, is_timeout: bool = False):
        try:
            if player_id is None:
                current_player_id = TurnServices(
                    self._db).get_current_player_by_match(match_id)
            else:
                current_player_id = player_id

            if current_player_id is None:
                raise

            player = PlayerServices(self._db).get_player(current_player_id)

            if not is_timeout:
                log_message = f"[TURN] Es turno de {player.name}"
            else:
                log_message = f"[TIMEOUT] Ocurrió un timeout, ahora es turno de {player.name}"

            await self._pre_create_and_propagate_log(
                match_id, log_message, MatchEventType.TURN, player.id, "send_curr_player_turn_in_match")

        except Exception as e:
            print(
                f"[LOG] Error in send_curr_player_turn_in_match, current_player_id para match {match_id}: {e}")

    async def send_player_discard_cards(self, match_id: UUID, player_id: UUID, results: dict, len_discarded_cards: int):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            card_names = []
            for card in results:
                card_names.append(card[6])
            cards_text = (
                ", ".join(card_names)
                if len(card_names) <= 3
                else f"{', '.join(card_names[:3])} y {len(card_names) - 3} más"
            )
            log_message = f"[DISCARD] Jugador {player.name} descartó {len_discarded_cards} carta(s): {cards_text}"

            await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.DISCARD_CARDS, player.id, "send_player_discard_cards")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_discard_cards, para match {match_id}: {e}")

    async def send_player_take_cards(self, match_id: UUID, player_id: UUID, len_take_cards: int):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[TAKE] Jugador {player.name} tomó {len_take_cards} carta(s) del mazo"

            await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.TAKE_CARDS, player.id, "send_player_take_cards")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_take_cards, para match {match_id}: {e}")

    async def send_player_play_set(self, match_id: UUID, player_id: UUID, set_type: SetType):
        try:
            player = PlayerServices(self._db).get_player(player_id)

            msg_nsf = "y puedes jugar una carta 'NOT SO FAST...' para cancelarlo"
            if set_type == SetType.TWO_BERESFORD:
                msg_nsf = " y no puede ser cancelada con una 'NOT SO FAST...'"

            log_message = f"[SET] Jugador '{player.name}' jugó el set '{set_type.value}'{msg_nsf}"

            event_type = getattr(MatchEventType, set_type.name, None)
            if event_type:
                await self._pre_create_and_propagate_log(match_id, log_message, event_type, player.id, "send_player_play_set")
            else:
                print(
                    f"[LOG] Warning: No matching MatchEventType for SetType {set_type.name}"
                )

        except Exception as e:
            print(
                f"[LOG] Error in send_player_play_set, para match {match_id}: {e}")

    async def send_player_put_down_a_detective(self, match_id: UUID, set_id: UUID, type_event: str):
        try:
            set = SetServices(self._db).get_match_set(set_id, match_id)
            setType = set.type
            player = PlayerServices(self._db).get_player(set.player_id)

            msg_nsf = "y puedes jugar una carta 'NOT SO FAST...' para cancelarlo"
            if set.type == SetType.TWO_BERESFORD:
                msg_nsf = " y no puede ser cancelada con una 'NOT SO FAST...'"

            log_message = f"[SET] Jugador {player.name} bajo un detective, ejecutando el evento de set de '{type_event}'{msg_nsf}"
            event_type = getattr(MatchEventType, setType.name, None)

            if event_type:
                await self._pre_create_and_propagate_log(match_id, log_message, event_type, player.id, "send_player_put_down_a_detective")
            else:
                print(
                    f"[LOG] Warning: No matching MatchEventType for SetType {setType.name}"
                )

        except Exception as e:
            print(
                f"[LOG] Error in send_player_put_down_a_detective, para match {match_id}: {e}")

    async def send_player_stolen_set(self, match_id: UUID, player_id: UUID, set_type: SetType):
        try:
            player = PlayerServices(self._db).get_player(player_id)

            log_message = f"[SET] Jugador {player.name} jugó el set {set_type.value}"
            event_type = getattr(MatchEventType, set_type.name, None)
            if event_type:
                await self._pre_create_and_propagate_log(match_id, log_message, event_type, player.id, "send_player_stolen_set")
            else:
                print(
                    f"[LOG] Warning: No matching MatchEventType for SetType {set_type.name}"
                )

        except Exception as e:
            print(
                f"[LOG] Error in send_player_stolen_set, para match {match_id}: {e}")

    async def send_player_play_event_not_cancelable(self, match_id: UUID, player_id: UUID, type_event: Card_event):
        try:
            player = PlayerServices(self._db).get_player(player_id)

            log_message = f"[EVENTO] Jugador {player.name} jugó el evento {type_event.value} y no puede ser cancelada con una 'NOT SO FAST...'"
            event_type = getattr(MatchEventType, type_event.name, None)
            if event_type:
                await self._pre_create_and_propagate_log(match_id, log_message, event_type, player.id, "send_player_play_event_not_cancelable")
            else:
                print(
                    f"[LOG] Warning: No matching MatchEventType for Card_event {type_event.name}")
        except Exception as e:
            print(
                f"[LOG] Error in send_player_play_event_not_cancelable, para match {match_id}: {e}")

    async def send_player_play_event_cancelable(self, match_id: UUID, player_id: UUID, type_event: Card_event):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[EVENTO] Jugador {player.name} jugó el evento {type_event.value}, puedes jugar una carta 'NOT SO FAST...' para cancelarlo"

            event_type = getattr(MatchEventType, type_event.name, None)
            if event_type:
                await self._pre_create_and_propagate_log(match_id, log_message, event_type, player.id, "send_player_play_event_cancelable")
            else:
                print(
                    f"[LOG] Warning: No matching MatchEventType for Card_event {type_event.name}")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_play_event_cancelable, para match {match_id}: {e}")

    async def send_player_select_card_to_trade(self, match_id: UUID, player_id: UUID, match_event: MatchEventType):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[EVENT] El jugador '{player.name}' selecciono una carta para intercambiar'"

            await self._pre_create_and_propagate_log(match_id, log_message, match_event, player.id, "send_player_select_card_to_trade")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_select_card_to_trade, para match {match_id}: {e}")

    async def send_player_trade_devious_card(self, match_id: UUID, player_id: UUID, match_event: MatchEventType):
        try:
            log_message = f"[EVENT] Se ha/n recibido alguna carta 'DEVIOUS', el jugador/es tendrá/n que revelar un secreto propio."

            await self._pre_create_and_propagate_log(match_id, log_message, match_event, player_id, "send_player_trade_devious_card")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_trade_devious_card, para match {match_id}: {e}")

    async def send_player_point_suspicions(self, match_id: UUID, player_id: UUID, target_player_id: UUID):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            player_seleccionado = PlayerServices(
                self._db).get_player(target_player_id)

            log_message = f"[EVENT] El jugador '{player.name}' sospecha del jugador '{player_seleccionado.name}'"

            await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.POINT_YOUR_SUSPICIONS, player.id, "send_player_point_suspicions")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_point_suspicions, para match {match_id}: {e}")

    async def send_player_play_nsf(self, match_id: UUID, player_id: UUID):
        try:
            player = PlayerServices(self._db).get_player(player_id)
            log_message = f"[EVENT] El jugador '{player.name}' jugo una carta 'NOT SO FAST...'"

            await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.NOT_SO_FAST, player.id, "send_player_play_nsf")

        except Exception as e:
            print(
                f"[LOG] Error in send_player_play_nsf, para match {match_id}: {e}")

    async def send_update_secret(self, match_id: UUID, player_id: UUID, secret_action: Secret_action):
        try:
            player = PlayerServices(self._db).get_player(player_id)

            secret_update_type_msg = "revelo"
            if secret_action == Secret_action.HIDE:
                secret_update_type_msg = "oculto"
            elif secret_action == Secret_action.STEAL:
                secret_update_type_msg = "robo"

            log_message = f"[SECRET] Jugador {player.name} {secret_update_type_msg} un secreto"

            await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.UPDATE_SECRET, player.id, "send_update_secret")

        except Exception as e:
            print(
                f"[LOG] Error in send_update_secret, para match {match_id}: {e}")

    async def send_event_not_cancelate(self, match_id: UUID, player_id: UUID, event: EventosDeTurno):
        log_message = f"[EVENT] El evento '{event.event_type.capitalize()}' no fue cancelado"

        await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.NOT_SO_FAST, player_id, "send_event_not_cancelate")

    async def send_event_cancelate(self, match_id: UUID, player_id: UUID, event: EventosDeTurno):
        log_message = f"[EVENT] El evento '{event.event_type.capitalize()}' fue cancelado por una carta 'NOT SO FAST...'"

        await self._pre_create_and_propagate_log(match_id, log_message, MatchEventType.NOT_SO_FAST, player_id, "send_event_cancelate")
