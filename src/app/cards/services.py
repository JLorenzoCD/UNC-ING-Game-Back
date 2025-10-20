from uuid import UUID
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.cards.models import Card, Match_Card
from app.cards.schemas import Match_Card_Schema
from app.cards.utils import db_match_card_2_match_card_schema
from app.secrets import services as secret_services
from app.secrets.services import Secret_action
from app.matches import services as matches_services


class Card_event(Enum):
    CARDS_OFF_THE_TABLE = "CARDS OFF THE TABLE"
    ANOTHER_VICTIM = "ANOTHER_VICTIM"
    DEAD_CARD_FOLLY = "DEAD CARD FOLLY"
    LOOK_INTO_THE_ASHES = "LOOK INTO THE ASHES"
    CARD_TRADE = "CARD TRADE"
    AND_THEN_THERE_WAS_ONE_MORE = "AND THEN THERE WAS ONE MORE"
    DELAY_THE_MURDERER_ESCAPE = "DELAY THE MURDERER ESCAPE"
    EARLY_TRAIN_TO_PADDINGTON = "EARLY TRAIN TO PADDINGTON"
    POINT_YOUR_SUSPICIONS = "POINT YOUR SUSPICIONS"

class Cards_Services:
    def __init__(self, db):
        self._db = db

    def init_match_cards(self, match_id: UUID, num_players: int) -> None:
        # Lista de cartas con cantidad
        if num_players == 2:
            all_cards = [
                {"type": "INSTANT", "name": "NOT SO FAST", "quantity": 10},
                {"type": "DETECTIVE", "name": "PARKER PYNE", "quantity": 3},
                {"type": "DETECTIVE", "name": "LADY EILEEN", "quantity": 3},
                {"type": "DETECTIVE", "name": "TOMMY BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "TUPPENCE BERESFORD", "quantity": 2},
                {"type": "DETECTIVE", "name": "HARLEY QUIN WILDCARD", "quantity": 4},
                {"type": "DETECTIVE", "name": "ARIADNE OLIVER", "quantity": 3},
                {"type": "DETECTIVE", "name": "HERCULE POIROT", "quantity": 1},
                {"type": "DETECTIVE", "name": "MISS MARPLE", "quantity": 3},
                {"type": "DETECTIVE", "name": "MR SATTERTHWAITE", "quantity": 2},
                {"type": "EVENT", "name": "CARDS OFF THE TABLE", "quantity": 1},
                {"type": "EVENT", "name": "ANOTHER VICTIM", "quantity": 2},
                {"type": "EVENT", "name": "DEAD CARD FOLLY", "quantity": 3},
                {"type": "EVENT", "name": "LOOK INTO THE ASHES", "quantity": 3},
                {"type": "EVENT", "name": "CARD TRADE", "quantity": 2},
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
                {"type": "DETECTIVE", "name": "HERCULE POIROT", "quantity": 1},
                {"type": "DETECTIVE", "name": "MISS MARPLE", "quantity": 3},
                {"type": "DETECTIVE", "name": "MR SATTERTHWAITE", "quantity": 2},
                {"type": "EVENT", "name": "CARDS OFF THE TABLE", "quantity": 1},
                {"type": "EVENT", "name": "ANOTHER VICTIM", "quantity": 2},
                {"type": "EVENT", "name": "DEAD CARD FOLLY", "quantity": 3},
                {"type": "EVENT", "name": "LOOK INTO THE ASHES", "quantity": 3},
                {"type": "EVENT", "name": "CARD TRADE", "quantity": 2},
                {"type": "EVENT", "name": "AND THEN THERE WAS ONE MORE", "quantity": 2},
                {"type": "EVENT", "name": "DELAY THE MURDERER ESCAPE", "quantity": 3},
                {"type": "EVENT", "name": "EARLY TRAIN TO PADDINGTON", "quantity": 2},
                {"type": "EVENT", "name": "POINT YOUR SUSPICIONS", "quantity": 3},
                {"type": "DEVIOUS", "name": "BLACKMAILED", "quantity": 3},
                {"type": "DEVIOUS", "name": "SOCIAL FAUX PAS", "quantity": 3},
            ]

        # Crear Match_Card según la cantidad
        for card_info in all_cards:
            # Buscar la carta base en la tabla cards
            card_base = (
                self._db.query(Card)
                .filter_by(name=card_info["name"], type=card_info["type"])
                .first()
            )
            if not card_base:
                continue  # O lanzar excepción si no existe

            for _ in range(card_info["quantity"]):
                match_card = Match_Card(
                    match_id=match_id,
                    card_id=card_base.id,
                )
                self._db.add(match_card)

        self._db.commit()

    def get_cards_by_match(self, match_id: UUID) -> list[Match_Card]:
        return (
            self._db.query(Match_Card)
            .filter(Match_Card.match_id == match_id)
            .all()
        )
    
    def get_name_event(self, player_id:UUID, match_id:UUID,match_card_id:UUID):
        """
        Devuelve el tipo de evento que es, verifica que la carta sea del jugador y pertenezca a la partida.       Si no encuentra la carta en la partida o no es del jugador levanta una excepcion
        """
        row=(self._db.query(Card)
                   .join(Match_Card, Match_Card.card_id == Card.id)
                   .filter(Match_Card.id == match_card_id,
                           Match_Card.match_id == match_id,
                           Match_Card.player_id == player_id
                           )
                   .first()
        )
        if not row:
            raise ValueError("Carta, player o partida incorrecto")
        return Card_event(row.name)
    
    def discard_card(self,match_card_id,delete=False):
        """
        Recibe una match_card_id y actualiza en la base de datos que es descartada, el discarded_at y que ya no tiene un player_id asociado
        Tiene un parametro opcional para cuando se debe eliminar del juego y no enviar a la pia de descarte
        """
        try:
            if not delete:
                self._db.query(Match_Card).filter(Match_Card.id == match_card_id).update(
                    {
                        Match_Card.is_discarded: True,
                        Match_Card.player_id: None,
                        Match_Card.discarded_at: datetime.now()
                    },
                    synchronize_session="fetch"
                )
                self._db.commit()

                #traemos el match_card actualizado para devolver
                updated_card = self._db.query(Match_Card).filter(Match_Card.id == match_card_id).first()
                return updated_card
            else:
                #eliminamos la carta de la base de datos
                card_to_delete = self._db.query(Match_Card).filter(Match_Card.id == match_card_id).first()
                if not card_to_delete:
                    raise ValueError("La carta no existe o ya fue eliminada")

                self._db.delete(card_to_delete)
                self._db.commit()
                return card_to_delete

        except SQLAlchemyError as e:
            self._db.rollback()
            raise RuntimeError(f"No se pudo descartar la carta: {e}")

    def delay_the_murderer_escape_event(self,cards_ids: list[int]):
        try:

            self._db.query(Match_Card).filter(Match_Card.id.in_(cards_ids)).update(
                {
                    Match_Card.is_discarded: False,
                    Match_Card.discarded_at: None
                },
                synchronize_session="fetch"
                #usamos esto porque en los update y delete es importante como sincronizar los cambios
            )
            self._db.commit()

            #traemos todo el match card de todas las cartas que tengan la id en nuestros cards_ids
            updated_cards = self._db.query(Match_Card).filter(Match_Card.id.in_(cards_ids)).all()
            return updated_cards

        except SQLAlchemyError as e:
            self._db.rollback()
            raise RuntimeError(f"No se actualizaron las cartas correctamente, details {e}")
        
    def and_then_there_was_one_more_event(self, target_player_id:UUID, target_secret_id:UUID):
        #ocultamos el secreto
        secret_services.Secrets_Services(self._db).update_secret(Secret_action.REVEAL, target_secret_id)
        #robamos el secreto y lo guardamos para devolverlo
        match_secret=secret_services.Secrets_Services(self._db).update_secret(Secret_action.STEAL, target_secret_id, target_player_id)
        return match_secret
    
    def look_into_the_ashes_event(self,player_id,match_id,target_card_id):
        #toma la carta targeteada, y hace un lista de un elemento como el take_cards lo requiere
        matches_services.PileService(self._db).take_cards(player_id,match_id,[target_card_id])
        try:
            taken_card=self._db.query(Match_Card).filter(Match_Card.id==target_card_id).first()
            if taken_card:
                self._db.refresh(taken_card)
            else:
                raise ValueError("carta incorrecta")
        except SQLAlchemyError as e:
            raise e
        return taken_card
    
    def another_victim_event(self):
        #falta implementacion(necesito que este ready steal_set)
        return 0

    def early_train_to_paddington_event(self, match_id, card_ids) -> list[Match_Card_Schema]:
        if not card_ids:
            raise ValueError("Se requiere al menos una carta para descartar")
        
        try:
            existing_cards = self._db.query(Match_Card).filter(
                Match_Card.id.in_(card_ids),
                Match_Card.match_id == match_id
            ).all()
            
            if len(existing_cards) != len(card_ids):
                raise ValueError("Una o más cartas no son válidas o no pertenecen a esta partida")
            
            matches_services.PileService(self._db).discard_cards(None, match_id, card_ids)
            
            discarded_cards = self._db.query(Match_Card).filter(Match_Card.id.in_(card_ids)).all()
            result = [db_match_card_2_match_card_schema(card) for card in discarded_cards]
            
            return result
            
        except SQLAlchemyError as e:
            self._db.rollback()
            raise SQLAlchemyError(f"Error al ejecutar evento Early Train to Paddington: {str(e)}")
        except Exception as e:
            self._db.rollback()
            raise

    def cards_off_the_table(self):
        #falta implementacion
        return 0
    