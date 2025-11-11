from uuid import UUID
from fastapi import  HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from collections import Counter
from typing import List, Optional

from app.sets.models import Match_Set, SetType
from app.sets.schemas import MatchSetOut, SetIn
from app.sets.utils import db_match_set_2_match_set_schema
from app.cards.models import Card, Card_Type, Match_Card
from app.secrets.models import Secret, Match_Secret


# --- Excepciones ---
class InvalidCardError(Exception):
    pass
class InvalidMatchIdError(Exception):
    pass
class InvalidSetError(Exception):
    pass
class TargetSecretError(Exception):
    pass
class SetUpdateError(Exception):
    """Lanzado cuando la actualización del Set falla."""
    pass

class SetService:
    def __init__(self, db: Session):
        self._db = db
                      
    def set_verification(self, card_ids: List[UUID], match_id: UUID, set_type:SetType,  target_player: UUID, target_secret: Optional[UUID] = None) -> bool:
        for card_id in card_ids:
            match_card = self._db.query(Match_Card).filter(Match_Card.id == card_id).first()
            if not match_card:
                raise InvalidCardError(f"No se encontró la carta con id {card_id}")

            if match_card.match_id != match_id:
                raise InvalidMatchIdError("La carta no pertenece a esta Partida.")

            card = self._db.query(Card).filter(Card.id == match_card.card_id).first()
            if card.type != Card_Type.DETECTIVE:
                raise InvalidCardError("Sólo las cartas de detective pueden formar un Set.")
            
        if set_type in [SetType.HERCULE_POIROT, SetType.MISS_MARPLE, SetType.PARKER_PYNE] and target_secret is None:
            raise TargetSecretError("No hay secreto seleccionado")
        
        if target_secret:
            secret = self._db.query(Match_Secret).filter(Match_Secret.id == target_secret).first()
            if secret is None:
                raise TargetSecretError("No existe el secreto seleccionado")
            
            if secret.player_id != target_player:
                raise TargetSecretError("El secreto y el jugador no coinciden")
            
            if set_type in [SetType.LADY_EILEEN, SetType.TUPPENCE_BERESFORD, SetType.TOMMY_BERESFORD, SetType.TWO_BERESFORD, SetType.MR_SATTERTHWAITE]:
                raise TargetSecretError("No se debería seleccionar secreto en este momento")
                
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
            SetType.TOMMY_BERESFORD:    (lambda c: c["TOMMY BERESFORD"] == 2 or (c["TOMMY BERESFORD"] == 1 and c["HARLEY QUIN WILDCARD"] == 1)),
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

    def create_set(self, set_data: dict) -> MatchSetOut:
        # Obtener nombres de cartas
        card_names = self._get_card_names(set_data["card_ids"])
        card_counts = Counter(card_names)

        # Verificar reglas del set
        self._validate_set_rules(set_data["type"], card_counts)

        # Crear instancia del Set
        quins_count = card_counts.get("HARLEY QUIN WILDCARD", 0)
        new_set = Match_Set(
            type=set_data["type"],
            player_id=set_data["player_id"],
            match_id=set_data["match_id"],
            quin_play="HARLEY QUIN WILDCARD" in card_names,
            quin_count=quins_count
        )

        try:
            self._db.add(new_set)
            self._db.commit()
            self._db.refresh(new_set)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        
        match_set_out = MatchSetOut(
            id=new_set.id,
            type=new_set.type,
            player_id=new_set.player_id,
            match_id=new_set.match_id,
            quin_play=new_set.quin_play,
            quin_count=quins_count
        )
        return match_set_out
    
    def quin_count(self, card_ids: List[UUID]) -> int:
        card_names:list[str] = self._get_card_names(card_ids)
        card_counts = Counter(card_names)
        return card_counts.get("HARLEY QUIN WILDCARD", 0)
                    
    def steal_set(self, set_id: UUID, new_player_id: UUID) -> MatchSetOut:
        match_set = self._db.query(Match_Set).filter(Match_Set.id == set_id).first()
        if not match_set:
            raise InvalidSetError(f"No se encontró el set con id {set_id}")

        match_set.player_id = new_player_id

        try:
            self._db.commit()
            self._db.refresh(match_set)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        return db_match_set_2_match_set_schema(match_set)
    
    def create_set_payload(self, match_id:UUID, setIn: SetIn, is_Oliver: bool):
        if is_Oliver:
            new_set_payload = {    
            "type" : SetType.ADRIADNE_OLIVER.value,
            "player_id": str(setIn.player_id),
            "target_player_id": str(setIn.target_player_id),
            "target_secret_id": str(setIn.target_secret_id),
            "match_id": str(match_id)           
            }
            new_set_payload["match_cards_ids"] = [str(card_id) for card_id in setIn.card_ids]
                   
        else:
            new_set_payload = {    
                "type" : setIn.type.value,
                "player_id": str(setIn.player_id),
                "target_player_id": str(setIn.target_player_id),
                "target_secret_id": str(setIn.target_secret_id),
                "match_id": str(match_id)           
            }
            new_set_payload["match_cards_ids"] = [str(card_id) for card_id in setIn.card_ids]
            
        return new_set_payload
    
    def add_card_verification(self, card_ids: List[UUID], set_id:UUID, target_player: UUID, target_secret: Optional[UUID] = None):
        
        if not card_ids:
            raise InvalidCardError("No hay carta de Detective para bajar")
        if len(card_ids) > 2:
            raise InvalidCardError("Solo se debe mandar una carta")
        
        for card_id in card_ids:
            match_card = self._db.query(Match_Card).filter(Match_Card.id == card_id).first()
            if not match_card:
                raise InvalidCardError(f"No se encontró la carta con id {card_id}")
            
        detective = self._get_card_names(card_ids)
        
        match_set = self._db.query(Match_Set).filter(Match_Set.id == set_id).first()
        if not match_set:
            raise InvalidSetError(f"No se encontró el set con id {set_id}")
        
        for name in detective:
            validation = self._validate_detective_in_set(name, match_set.type.value)
        
        if (match_set.type in [SetType.HERCULE_POIROT, SetType.MISS_MARPLE, SetType.PARKER_PYNE] and target_secret is None) and detective[0] != SetType.ADRIADNE_OLIVER.value:
            raise TargetSecretError("No hay secreto seleccionado")
        
        if target_secret:
            secret = self._db.query(Match_Secret).filter(Match_Secret.id == target_secret).first()
            if secret is None:
                raise TargetSecretError("No existe el secreto seleccionado")
            
            if secret.player_id != target_player:
                raise TargetSecretError("El secreto y el jugador no coinciden")
            
            if match_set.type in [SetType.LADY_EILEEN, SetType.TUPPENCE_BERESFORD, SetType.TOMMY_BERESFORD, SetType.TWO_BERESFORD, SetType.MR_SATTERTHWAITE]:
                raise TargetSecretError("No se debería seleccionar secreto en este momento")
                
        return True        
    
    
    def _validate_detective_in_set(self, card_name: str, setType: str) -> None:
        """
        Verifica si una carta de detective (card_name) pertenece 
        válidamente a un set (setType).
        
        Esta validación ignora a 'HARLEY QUIN WILDCARD' y 'ARIADNE OLIVER'.
        Maneja el caso especial de 'TWO BERESFORD'.

        Levanta HTTPException 409 (Conflict) si la validación falla.
        """

        # 1. Exclusiones: Si la carta es una de las excluidas, 
        if card_name in ["HARLEY QUIN WILDCARD", "ARIADNE OLIVER"]:
            return None

        # 2. Caso Estándar: El nombre del detective debe coincidir 
        if card_name == setType:
            return None

        # 3. Caso Especial: "TWO BERESFORD"
        beresford_detectives = ["TUPPENCE BERESFORD", "TOMMY BERESFORD"]
        
        if card_name in beresford_detectives and (setType == "TWO BERESFORD" or setType in beresford_detectives):
            return None

        # 4. Fallo: Si ninguna de las condiciones anteriores se cumple, 
        raise InvalidCardError(f"El detective '{card_name}' no pertenece al set '{setType}'.")
    
    def get_match_set(self, set_id: UUID, match_id: UUID) -> Match_Set:
        match_set = self._db.query(Match_Set).filter(Match_Set.id == set_id, Match_Set.match_id == match_id).first()
        if not match_set:
            raise InvalidSetError("No se encontró el set")
        return match_set
    
    def beresford_brothers_in_set_two_beresford(self, card_name: str, set_type: SetType) -> bool:
        """
        Verifica si estamos en el caso de que agregamos a TOMMY_BERESFORD en  TUPPENCE_BERESFORD y viceversa
        """
        validation: bool = False
        
        if card_name == SetType.TOMMY_BERESFORD.value and set_type.value == SetType.TUPPENCE_BERESFORD.value:
            validation = True

        if card_name == SetType.TUPPENCE_BERESFORD.value and set_type.value == SetType.TOMMY_BERESFORD.value:
            validation = True
            
        return validation
    
    def update_setType(self, set_id: UUID, now_setType: SetType) -> Match_Set:
        """
        Actualiza el tipo (SetType) de un Match_Set específico         
        Lanza InvalidSetError si no se encuentra.
        Lanza SetUpdateError si la actualización falla.
        """
        match_set = self._db.query(Match_Set).filter(Match_Set.id == set_id).first()
        
        if not match_set:
            raise InvalidSetError(f"No se encontró el set con ID: {set_id}")
            
        try:
            # Realizar la actualización en el objeto
            match_set.type = now_setType
            self._db.commit()
            self._db.refresh(match_set)
            
        except SQLAlchemyError as e:
            # Si el commit() falla (error de DB, etc.)
            self._db.rollback()
            raise SetUpdateError(f"Error de base de datos al actualizar el set: {e}")
        
        if match_set.type != now_setType:
            raise SetUpdateError("Verificación fallida: El tipo del set no coincide post-actualización.")
            
        return match_set