import random
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError, DataError
from sqlalchemy import func

from app.cards.models import Card, Card_Type, Match_Card
from app.cards.schemas import Match_Card_Schema
from app.cards.utils import db_match_card_2_match_card_schema
from app.player.models import Match_Player
from app.secrets import services as secret_services
from app.secrets.services import Secret_action

from app.cards.exceptions import InvalidCardData, CardNotFound, CardInvalidAction


class Card_event(Enum):
    """Class Card_event."""

    CARDS_OFF_THE_TABLE = "CARDS OFF THE TABLE"
    ANOTHER_VICTIM = "ANOTHER VICTIM"
    DEAD_CARD_FOLLY = "DEAD CARD FOLLY"
    LOOK_INTO_THE_ASHES = "LOOK INTO THE ASHES"
    CARD_TRADE = "CARD TRADE"
    AND_THEN_THERE_WAS_ONE_MORE = "AND THEN THERE WAS ONE MORE"
    DELAY_THE_MURDERER_ESCAPE = "DELAY THE MURDERER ESCAPE"
    EARLY_TRAIN_TO_PADDINGTON = "EARLY TRAIN TO PADDINGTON"
    POINT_YOUR_SUSPICIONS = "POINT YOUR SUSPICIONS"
    NOT_SO_FAST = "NOT SO FAST"


class CardsServices:
    """Class CardsServices."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def and_then_there_was_one_more_event(
        self, target_player_id: UUID, target_secret_id: UUID
    ):
        """And then there was one more event.

        Args:
            target_player_id: Parameter target_player_id.
            target_secret_id: Parameter target_secret_id."""
        try:
            match_secret = secret_services.SecretsServices(self._db).update_secret(
                Secret_action.STEAL, target_secret_id, target_player_id
            )
            return match_secret
        except Exception as e:
            raise e

    def another_victim_event(self):
        """Another victim event."""
        return 0

    def cards_off_the_table(
        self,
        match_id: UUID,
        target_player_id: UUID,
        event_card_owner_id: UUID,
        event_card_id: UUID,
    ):
        """
        Descarta las Not so Fast de tipo INSTANT del target_player, descarta la Cards Off the Table.
        del jugador que jugó la carta (event_card_owner_id).
        Devuelve un diccionario de Match_cards de las cartas descartadas.
        """
        result = []
        target_cards: list[Match_Card] = (
            self._db.query(Match_Card)
            .join(Match_Card.card)
            .filter(
                Match_Card.player_id == target_player_id,
                Match_Card.is_discarded == False,
                Card.type == Card_Type.INSTANT,
                Match_Card.match_id == match_id,
            )
            .all()
        )
        if not target_cards:
            result = []
        else:
            for nt in target_cards:
                nt.is_discarded = True
                nt.player_id = None
                nt.discarded_at = datetime.now()
                result.append(nt.id)
        self._db.commit()
        for card in target_cards:
            if not card.is_discarded:
                raise Exception(
                    f"La carta {card.id} no se descartó correctamente")
        return {"discarded_instant_cards": target_cards}

    def delay_the_murderer_escape_event(self, cards_ids: list[int]):
        """Delay the murderer escape event.

        Args:
            cards_ids: Parameter cards_ids."""
        try:
            self._db.query(Match_Card).filter(Match_Card.id.in_(cards_ids)).update(
                {Match_Card.is_discarded: False, Match_Card.discarded_at: None},
                synchronize_session="fetch",
            )
            self._db.commit()
            updated_cards = (
                self._db.query(Match_Card).filter(
                    Match_Card.id.in_(cards_ids)).all()
            )
            return updated_cards
        except SQLAlchemyError as e:
            self._db.rollback()
            raise RuntimeError(
                f"No se actualizaron las cartas correctamente, details {e}"
            )

    def early_train_to_paddington_event(
        self, match_id, card_ids
    ) -> list[Match_Card_Schema]:
        """Early train to paddington event.

        Args:
            match_id: Parameter match_id.
            card_ids: Parameter card_ids.

        Returns:
            Return value."""
        from app.piles.services import PileServices

        if not card_ids:
            raise InvalidCardData(
                "Se requiere al menos una carta para descartar")
        try:
            existing_cards = (
                self._db.query(Match_Card)
                .filter(Match_Card.id.in_(card_ids), Match_Card.match_id == match_id)
                .all()
            )
            if len(existing_cards) != len(card_ids):
                raise InvalidCardData(
                    "Una o más cartas no son válidas o no pertenecen a esta partida"
                )

            PileServices(self._db).discard_cards(
                None, match_id, card_ids
            )

            discarded_cards = (
                self._db.query(Match_Card).filter(
                    Match_Card.id.in_(card_ids)).all()
            )
            result = [
                db_match_card_2_match_card_schema(card) for card in discarded_cards
            ]
            return result
        except SQLAlchemyError as e:
            self._db.rollback()
            raise SQLAlchemyError(
                f"Error al ejecutar evento Early Train to Paddington: {str(e)}"
            )
        except Exception:
            self._db.rollback()
            raise

    def get_cards_by_match(self, match_id: UUID) -> list[Match_Card]:
        """Get cards by match.

        Args:
            match_id: Parameter match_id.

        Returns:
            Return value."""
        return self._db.query(Match_Card).filter(Match_Card.match_id == match_id).all()

    def get_event_type_by_card(self, match_card_id: UUID) -> Card_event:
        """
        Obtiene el nombre/tipo de evento de una carta.
        No valida propiedad, asume que la validación YA se hizo.
        """
        card_name = (
            self._db.query(Card.name)
            .join(Match_Card, Match_Card.card_id == Card.id)
            .filter(Match_Card.id == match_card_id)
            .scalar()
        )
        if not card_name:
            raise CardNotFound(
                "No se pudo encontrar el nombre de la carta (logic error)."
            )
        return Card_event(card_name)

    def init_match_cards(self, match_id: UUID, num_players: int) -> None:
        """Init match cards.

        Args:
            match_id: Parameter match_id.
            num_players: Parameter num_players.

        Returns:
            Return value."""
        if num_players == 2:
            all_cards = [
                {"type": "INSTANT", "name": "NOT SO FAST", "quantity": 10},
                {"type": "DETECTIVE", "name": "PARKER PYNE", "quantity": 3},
                {"type": "DETECTIVE", "name": "LADY EILEEN", "quantity": 3},
                {"type": "DETECTIVE", "name": "TOMMY BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "TUPPENCE BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "HARLEY QUIN WILDCARD", "quantity": 4},
                {"type": "DETECTIVE", "name": "ARIADNE OLIVER", "quantity": 3},
                {"type": "DETECTIVE", "name": "HERCULE POIROT", "quantity": 3},
                {"type": "DETECTIVE", "name": "MISS MARPLE", "quantity": 3},
                {"type": "DETECTIVE", "name": "MR SATTERTHWAITE", "quantity": 2},
                {"type": "EVENT", "name": "CARDS OFF THE TABLE", "quantity": 1},
                {"type": "EVENT", "name": "ANOTHER VICTIM", "quantity": 2},
                {"type": "EVENT", "name": "DEAD CARD FOLLY", "quantity": 3},
                {"type": "EVENT", "name": "LOOK INTO THE ASHES", "quantity": 3},
                {"type": "EVENT", "name": "CARD TRADE", "quantity": 3},
                {"type": "EVENT", "name": "AND THEN THERE WAS ONE MORE", "quantity": 2},
                {"type": "EVENT", "name": "DELAY THE MURDERER ESCAPE", "quantity": 3},
                {"type": "EVENT", "name": "EARLY TRAIN TO PADDINGTON", "quantity": 2},
                {"type": "DEVIOUS", "name": "SOCIAL FAUX PAS", "quantity": 3},
            ]
        else:
            all_cards = [
                {"type": "INSTANT", "name": "NOT SO FAST", "quantity": 10},
                {"type": "DETECTIVE", "name": "PARKER PYNE", "quantity": 3},
                {"type": "DETECTIVE", "name": "LADY EILEEN", "quantity": 3},
                {"type": "DETECTIVE", "name": "TOMMY BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "TUPPENCE BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "HARLEY QUIN WILDCARD", "quantity": 4},
                {"type": "DETECTIVE", "name": "ARIADNE OLIVER", "quantity": 3},
                {"type": "DETECTIVE", "name": "HERCULE POIROT", "quantity": 3},
                {"type": "DETECTIVE", "name": "MISS MARPLE", "quantity": 3},
                {"type": "DETECTIVE", "name": "MR SATTERTHWAITE", "quantity": 2},
                {"type": "EVENT", "name": "CARDS OFF THE TABLE", "quantity": 1},
                {"type": "EVENT", "name": "ANOTHER VICTIM", "quantity": 2},
                {"type": "EVENT", "name": "DEAD CARD FOLLY", "quantity": 3},
                {"type": "EVENT", "name": "LOOK INTO THE ASHES", "quantity": 3},
                {"type": "EVENT", "name": "CARD TRADE", "quantity": 3},
                {"type": "EVENT", "name": "AND THEN THERE WAS ONE MORE", "quantity": 2},
                {"type": "EVENT", "name": "DELAY THE MURDERER ESCAPE", "quantity": 3},
                {"type": "EVENT", "name": "EARLY TRAIN TO PADDINGTON", "quantity": 2},
                {"type": "EVENT", "name": "POINT YOUR SUSPICIONS", "quantity": 3},
                {"type": "DEVIOUS", "name": "BLACKMAILED", "quantity": 1},
                {"type": "DEVIOUS", "name": "SOCIAL FAUX PAS", "quantity": 3},
            ]

        shuffle_cards = []
        for card_info in all_cards:
            card_base = (
                self._db.query(Card)
                .filter_by(name=card_info["name"], type=card_info["type"])
                .first()
            )
            if not card_base:
                continue

            for _ in range(card_info["quantity"]):
                match_card = Match_Card(
                    match_id=match_id, card_id=card_base.id)
                shuffle_cards.append(match_card)

        random.shuffle(shuffle_cards)

        for cards in shuffle_cards:
            self._db.add(cards)
        self._db.commit()

    def is_complex_event(self, event_type_str: str) -> bool:
        """
        Devuelve si un evento se aplica compuesto
        """
        complex_events = [
            Card_event.CARD_TRADE.value,
            Card_event.DEAD_CARD_FOLLY.value,
            Card_event.POINT_YOUR_SUSPICIONS.value,
        ]
        if event_type_str in complex_events:
            return True
        return False

    def is_instant_event(self, event_type_str: str) -> bool:
        """
        Devuelve si un evento se aplica instantaneamente
        Si un evento no es cancelable
        """
        cancellable_events = [Card_event.CARDS_OFF_THE_TABLE.value]
        if event_type_str in cancellable_events:
            return True
        return False

    def look_into_the_ashes_event(self, player_id, match_id, target_card_id):
        """Look into the ashes event.

        Args:
            player_id: Parameter player_id.
            match_id: Parameter match_id.
            target_card_id: Parameter target_card_id."""
        from app.piles.services import PileServices

        PileServices(self._db).take_cards(
            player_id, match_id, [target_card_id]
        )
        try:
            taken_card = (
                self._db.query(Match_Card)
                .filter(Match_Card.id == target_card_id)
                .first()
            )
            if taken_card:
                self._db.refresh(taken_card)
            else:
                raise CardInvalidAction("carta incorrecta")
        except SQLAlchemyError as e:
            raise e
        return taken_card

    def pass_cards_in_direction(
        self, match_id: UUID, card_ids_to_pass, direction
    ) -> list[Match_Card]:
        """
        Ejecuta la lógica de "Dead Card Folly".
        Pasa cada carta al jugador de al lado, según el orden de la mesa.
        ¡Esta función HACE COMMIT!
        """
        try:
            players_in_order = (
                self._db.query(Match_Player)
                .filter(Match_Player.match_id == match_id)
                .order_by(Match_Player.order)
                .all()
            )
            num_players = len(players_in_order)
            player_target_map = {}
            for i in range(num_players):
                current_player = players_in_order[i]
                if direction.lower() == "left":
                    target_player = players_in_order[(i + 1) % num_players]
                elif direction.lower() == "right":
                    target_player = players_in_order[
                        (i - 1 + num_players) % num_players
                    ]
                else:
                    raise InvalidCardData(
                        f"Dirección de pase inválida: {direction}")
                player_target_map[str(current_player.player_id)] = (
                    target_player.player_id
                )
            cards_to_update = (
                self._db.query(Match_Card)
                .filter(Match_Card.id.in_(card_ids_to_pass))
                .all()
            )
            for card in cards_to_update:
                current_owner_id = str(card.player_id)
                new_owner_id = player_target_map[current_owner_id]
                card.player_id = new_owner_id
            self._db.commit()
            for card in cards_to_update:
                self._db.refresh(card)
            return cards_to_update
        except (SQLAlchemyError, InvalidCardData) as e:
            self._db.rollback()
            print(f"Error en pass_cards_in_direction: {e}")
            raise e
        except Exception as e:
            self._db.rollback()
            raise e

    def swap_cards_owners(
        self, match_card_id1: UUID, match_card_id2: UUID
    ) -> list[Match_Card]:
        """
        Intercambia los dueños de dos Match_Card.
        Esta función es "inteligente": busca a los dueños
        y los intercambia.
        """
        try:
            card1 = self._db.get(Match_Card, match_card_id1)
            card2 = self._db.get(Match_Card, match_card_id2)
            if not card1 or not card2:
                raise CardNotFound(
                    "Una o ambas cartas para el intercambio no fueron encontradas."
                )
            if not card1.player_id or not card2.player_id:
                raise CardInvalidAction(
                    "Una de las cartas no tiene dueño (ej: está en el mazo o descarte)."
                )
            owner1_id = card1.player_id
            owner2_id = card2.player_id
            card1.player_id = owner2_id
            card2.player_id = owner1_id
            self._db.commit()
            self._db.refresh(card1)
            self._db.refresh(card2)
            return [card1, card2]
        except Exception as e:
            print(f"Error en swap_card_owners: {e}")
            raise

    def get_player_cards_in_hand(self, player_id: UUID, match_id: UUID) -> list[Match_Card]:
        try:
            player_cards_in_hand = (
                self._db.query(Match_Card)
                .filter(
                    Match_Card.match_id == match_id,
                    Match_Card.player_id == player_id,
                    Match_Card.is_discarded == False,
                ).all()
            )
        except DataError:
            raise InvalidCardData()
        except Exception as e:
            raise e  # Algún error inesperado (status=500)

        return player_cards_in_hand

    def get_card_by_id(self, card_id: UUID) -> Match_Card | None:
        try:
            card = (
                self._db.query(Match_Card).filter(
                    Match_Card.id == card_id).first()
            )

        except DataError:
            raise InvalidCardData()
        except Exception:
            raise  # Algún error inesperado (status=500)

        return card

    def get_random_card_from_player_in_match(self, match_id: UUID, player_id: UUID) -> Match_Card | None:

        try:
            card = (
                self._db.query(Match_Card)
                .filter(
                    Match_Card.match_id == match_id,
                    Match_Card.player_id == player_id,
                    Match_Card.is_discarded == False,
                )
                # Si se usa MySQL se debe cambiar a func.rand()
                .order_by(func.random())
                .first()
            )

        except DataError:
            raise InvalidCardData()
        except Exception:
            raise  # Algún error inesperado (status=500)

        return card

    def get_first_card_of_regular_deck(self, match_id: UUID) -> Match_Card | None:

        try:
            card = (
                self._db.query(Match_Card)
                .filter(
                    Match_Card.match_id == match_id,
                    Match_Card.player_id == None,
                    Match_Card.is_discarded == False,
                )
                .order_by(Match_Card.id)
                .offset(3)
                .first()
            )

        except DataError:
            raise InvalidCardData()
        except Exception:
            raise  # Algún error inesperado (status=500)

        return card

    def validate_card_ownership(
        self, player_id: UUID, match_id: UUID, match_card_id: UUID
    ) -> bool:
        """
        Verifica que la carta pertenece al jugador, está en la partida
        y no está descartada. Devuelve True o levanta un CardNotFound.
        """
        card_exists = (
            self._db.query(Match_Card)
            .filter(
                Match_Card.id == match_card_id,
                Match_Card.match_id == match_id,
                Match_Card.player_id == player_id,
                Match_Card.is_discarded == False,
            )
            .count()
            > 0
        )
        if not card_exists:
            raise CardNotFound(
                "La carta no existe, no pertenece al jugador o ya fue descartada."
            )
        return True
