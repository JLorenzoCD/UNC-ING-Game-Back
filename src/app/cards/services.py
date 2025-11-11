from uuid import UUID
from enum import Enum
import random
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.cards.models import Card, Match_Card, Card_Type
from app.cards.schemas import Match_Card_Schema
from app.cards.utils import db_match_card_2_match_card_schema
from app.secrets import services as secret_services
from app.secrets.services import Secret_action
from app.player.models import Match_Player

class Card_event(Enum):
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

        # Crear Match_Card según la cantidad
        shuffle_cards = []
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
                shuffle_cards.append(match_card)
        
        #Agregamos las cartas a la base de datos
        random.shuffle(shuffle_cards)
        random.shuffle(shuffle_cards)
        random.shuffle(shuffle_cards)
        for cards in shuffle_cards:
            self._db.add(cards)
            
        self._db.commit()
        
    def get_cards_by_match(self, match_id: UUID) -> list[Match_Card]:
        return (
            self._db.query(Match_Card)
            .filter(Match_Card.match_id == match_id)
            .all()
        )
    
    def is_complex_event(self, event_type_str: str) -> bool:
        """
        Devuelve si un evento se aplica compuesto
        """
        #poner los eventos que no son cancelables
        complex_events = [
            Card_event.CARD_TRADE.value,
            Card_event.DEAD_CARD_FOLLY.value,
            Card_event.POINT_YOUR_SUSPICIONS.value
        ]
        
        if event_type_str in complex_events:
            return True
        return False


    def validate_card_ownership(
        self, 
        player_id: UUID, 
        match_id: UUID, 
        match_card_id: UUID
    ) -> bool:
        """
        Verifica que la carta pertenece al jugador, está en la partida
        y no está descartada. Devuelve True o levanta un valueError.
        """
        card_exists = self._db.query(Match_Card).filter(
            Match_Card.id == match_card_id,
            Match_Card.match_id == match_id,
            Match_Card.player_id == player_id,
            Match_Card.is_discarded == False
        ).count() > 0
        
        if not card_exists:
            raise ValueError("La carta no existe, no pertenece al jugador o ya fue descartada.")
        
        return True
    
    def get_event_type_by_card(self, match_card_id: UUID) -> Card_event:
        """
        Obtiene el nombre/tipo de evento de una carta.
        No valida propiedad, asume que la validación YA se hizo.
        """
        card_name = self._db.query(Card.name).join(
            Match_Card, Match_Card.card_id == Card.id
        ).filter(
            Match_Card.id == match_card_id
        ).scalar()
        
        if not card_name:
            raise ValueError("No se pudo encontrar el nombre de la carta (logic error).")
            
        return Card_event(card_name)
    

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
        #robamos el secreto y lo guardamos para devolverlo
        try:
            match_secret=secret_services.Secrets_Services(self._db).update_secret(Secret_action.STEAL, target_secret_id, target_player_id)
            return match_secret
        except Exception as e:
            raise e

    def cards_off_the_table(self, match_id:UUID, target_player_id: UUID, event_card_owner_id: UUID, event_card_id: UUID):
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
                Match_Card.match_id == match_id
            ).all())
        
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
                raise ValueError(f"La carta {card.id} no se descartó correctamente")            
                    
        return {"discarded_instant_cards": target_cards}

    def look_into_the_ashes_event(self,player_id,match_id,target_card_id):
        from app.matches import services as matches_services
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
        from app.matches import services as matches_services
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


    def swap_cards_owners(
        self, 
        match_card_id1: UUID, 
        match_card_id2: UUID
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
                raise ValueError("Una o ambas cartas para el intercambio no fueron encontradas.")

            if not card1.player_id or not card2.player_id:
                raise ValueError("Una de las cartas no tiene dueño (ej: está en el mazo o descarte).")

            print(f"Swap: P1 ({card1.player_id}) -> Card2, P2 ({card2.player_id}) -> Card1")

            #guarda dueños actuales
            owner1_id = card1.player_id
            owner2_id = card2.player_id

            #swap
            card1.player_id = owner2_id
            card2.player_id = owner1_id
            
            self._db.commit()
            self._db.refresh(card1)
            self._db.refresh(card2)
            
            return [card1, card2]
            
        except Exception as e:
            print(f"Error en swap_card_owners: {e}")
            raise e
    
    def pass_cards_in_direction(
        self,
        match_id:UUID,
        card_ids_to_pass,
        direction# "Left" o "Right"
    ) -> list[Match_Card]:
        """
        Ejecuta la lógica de "Dead Card Folly".
        Pasa cada carta al jugador de al lado, según el orden de la mesa.
        ¡Esta función HACE COMMIT!
        """
        try:
            #orden de los jugadores
            players_in_order = self._db.query(Match_Player).filter(
                Match_Player.match_id == match_id
            ).order_by(Match_Player.order).all()
            
            num_players = len(players_in_order)

            player_target_map = {} #{ "id_P1": "id_P2", "id_P2": "id_P3", ... }
            
            for i in range(num_players):
                current_player = players_in_order[i]
                
                if direction.lower() == "left":
                    target_player = players_in_order[(i + 1) % num_players]
                elif direction.lower() == "right":
                    target_player = players_in_order[(i - 1 + num_players) % num_players]
                else:
                    raise ValueError(f"Dirección de pase inválida: {direction}")
                
                player_target_map[str(current_player.player_id)] = target_player.player_id
     
            cards_to_update = self._db.query(Match_Card).filter(
                Match_Card.id.in_(card_ids_to_pass)
            ).all()

            for card in cards_to_update:
                current_owner_id = str(card.player_id)          
                new_owner_id = player_target_map[current_owner_id]
                
                print(f"Pasando carta {card.id} de {current_owner_id} a {new_owner_id}")
                card.player_id = new_owner_id
            
            self._db.commit()
            
            for card in cards_to_update:
                self._db.refresh(card)

            return cards_to_update

        except (SQLAlchemyError, ValueError) as e:
            self._db.rollback()
            print(f"Error en pass_cards_in_direction: {e}")
            raise e
        except Exception as e:
            self._db.rollback()
            raise e
        
    def is_instant_event(self, event_type_str: str) -> bool:
        """
        Devuelve si un evento se aplica instantaneamente
        Si un evento no es cancelable
        """
        #poner los eventos que no son cancelables
        cancellable_events = [
            Card_event.CARDS_OFF_THE_TABLE.value
        ]
        
        if event_type_str in cancellable_events:
            return True
        return False
    

