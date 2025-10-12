from uuid import UUID
from sqlalchemy.orm import Session
from collections import Counter

from app.sets.models import Match_Set, SetType
from app.cards.models import Card, Card_Type, Match_Card
from app.player.models import Player, Match_Player


# --- Excepciones ---
class InvalidCardTypeError(Exception):
    pass

class InvalidMatchIdError(Exception):
    pass

class InvalidSetError(Exception):
    pass


class SetService:
    def __init__(self, db: Session):
        self._db = db

    def set_verification(self, card_ids: list[UUID], match_id: UUID) -> bool:
        for card_id in card_ids:
            match_card = self._db.query(Match_Card).filter(Match_Card.id == card_id).first()
            if not match_card:
                raise InvalidSetError(f"Card with id {card_id} not found")

            if match_card.match_id != match_id:
                raise InvalidMatchIdError("Card does not belong to this match")

            card = self._db.query(Card).filter(Card.id == match_card.card_id).first()
            if card.type != Card_Type.DETECTIVE:
                raise InvalidCardTypeError("Only detective cards can form a set")
        
        return True
    
    def _get_card_names(self, card_ids: list[UUID]) -> list[str]:
        """
        Devuelve los nombres de las cartas asociadas a una lista de Match_Card IDs
        """
        match_cards = self._db.query(Match_Card).filter(Match_Card.id.in_(card_ids)).all()
        if not match_cards:
            raise InvalidSetError("No se encontraron cartas asociadas a los IDs proporcionados")

        card_names = []
        for mc in match_cards:
            card = self._db.query(Card).filter(Card.id == mc.card_id).first()
            if not card:
                raise InvalidSetError(f"No se encontró la carta con id {mc.card_id}")
            card_names.append(card.name)
        return card_names

    def _validate_set_rules(self, set_type: SetType, card_counts: Counter) -> bool:
        """
        Verifica si las cartas cumplen con las reglas del tipo de set.
        """
        set_rules = {
            SetType.PARKER_PYNE:        (lambda c: c["PARKER PYNE"] == 2 or (c["PARKER PYNE"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
            SetType.LADY_EILEEN:        (lambda c: c["LADY EILEEN"] == 2 or (c["LADY EILEEN"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
            SetType.TOMMY_BERESFORD:    (lambda c: c["TOMMY BERESFORD"] == 2 or (c["TUPPENCE BERESFORD"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
            SetType.TUPPENCE_BERESFORD: (lambda c: c["TUPPENCE BERESFORD"] == 2 or (c["TUPPENCE BERESFORD"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
            SetType.TWO_BERESFORD:      (lambda c: c["TUPPENCE BERESFORD"] == 1 and c["TOMMY BERESFORD"] == 1),
            SetType.HERCULE_POIROT:     (lambda c: c["HERCULE POIROT"] == 3 or (c["HERCULE POIROT"] == 2 and c["HARLEY QUIN WILDCARD"] == 1) or (c["HERCULE POIROT"] == 1 and c["HARLEY QUIN WILDCARD"] == 2)),
            SetType.MISS_MARPLE:        (lambda c: c["MISS MARPLE"] == 3 or (c["MISS MARPLE"] == 2 and c["HARLEY QUIN WILDCARD"] == 1) or (c["MISS MARPLE"] == 1 and c["HARLEY QUIN WILDCARD"] == 2)),
            SetType.MR_SATTERTHWAITE:   (lambda c: c["MR SATTERTHWAITE"] == 2 or (c["MR SATTERTHWAITE"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
        }

        if set_type not in set_rules:
            raise InvalidSetError(f"Tipo de set {set_type} no soportado")
        
        # get retorna 0 si no existe la carta en el contador
        safe_counter = Counter({name: card_counts.get(name, 0) for name in card_counts})
        
        if not set_rules[set_type](safe_counter):
            raise InvalidSetError("Combinación inválida de cartas para el tipo de set")

        return True


    def create_set(self, set_data: dict) -> Match_Set:
        # Obtener nombres de cartas
        card_names = self._get_card_names(set_data["card_ids"])
        card_counts = Counter(card_names)

        # Verificar reglas del set
        self._validate_set_rules(set_data["type"], card_counts)

        # Crear instancia del Set
        new_set = Match_Set(
            type=set_data["type"],
            player_id=set_data["player_id"],
            match_id=set_data["match_id"],
            quin_play="HARLEY QUIN WILDCARD" in card_names
        )

        self._db.add(new_set)
        self._db.commit()
        self._db.refresh(new_set)
        return new_set