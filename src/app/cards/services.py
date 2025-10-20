from uuid import UUID
import random
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


from app.cards.models import Card, Match_Card, Card_Type


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
        
    
    def cards_off_the_table(self, match_id:UUID, target_player_id: UUID, event_card_owner_id: UUID, event_card_id: UUID):
        """
        Descarta las Not so Fast de tipo INSTANT del target_player, descarta la Cards Off the Table 
        del jugador que jugó la carta (event_card_owner_id).
        Devuelve un diccionario de UUIDs de las cartas descartadas
        """
        event_card: Match_Card =  self._db.query(Match_Card).filter(Match_Card.id == event_card_id).first()
        result = []
        
        if not event_card:
            raise ValueError("La carta no existe o ya fue eliminada")

        if event_card.player_id != event_card_owner_id:
            raise ValueError("La carta de evento no pertenece al jugador")
        
        if target_player_id == event_card_owner_id:
            raise ValueError("El jugador no puede usar el evento sobre el mismo")
        
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
                result.append(nt.id)
        event_card.is_discarded = True
        event_card.player_id = None
        
        self._db.commit()
        
        # self._db.refresh(event_card)
        if event_card.is_discarded == False:
            raise ValueError("Cards Off the Table no se descartó correctamente")
        
        for card in target_cards:
            if not card.is_discarded:
                raise ValueError(f"La carta {card.id} no se descartó correctamente")            
                    
        return {"discarded_instant_cards": target_cards, "discarded_event_card": event_card.id}
