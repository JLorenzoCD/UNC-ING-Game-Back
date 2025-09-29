from app.matches.models import Match, Match_Player
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from app.matches import schemas
from app.player.models import Player
from app.matches.utils import db_match_2_match_schema
from typing import List, Optional
from fastapi import HTTPException
from app.cards.models import Card, Match_Card


# Excepciones
class OwnerNotFound(Exception):
    pass

class MatchNotFound(Exception):
    pass

class MatchValidationError(Exception):
    pass



class MatchService:
    def __init__(self, db):
        self._db = db
    
    def create(self, match_dto: schemas.MatchDTO) -> schemas.MatchOut:
        if match_dto.min_players < 2 or match_dto.max_players > 6:
            raise MatchValidationError("Incorrect number of players")
        
        owner:Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()
        
        new_match = Match(
            name = match_dto.name,
            min_players = match_dto.min_players,
            max_players = match_dto.max_players,
            owner_id = owner.id
        )
        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        try:
            match_player = Match_Player (match_id = new_match.id, player_id=owner.id, order=0)
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        match_out = db_match_2_match_schema(new_match)
        return match_out  

    def get_all(self) -> List[schemas.Match_number_of_Player]:
        try:
            matches = self._db.query(Match).all()
            
            combined = []
            for match in matches:
                # Convertir a schema base
                match_out = db_match_2_match_schema(match)
                
                # Obtener conteo de jugadores
                player_count = self.count_players_by_match(match.id)
                
                # Crear schema extendido
                extended_match = schemas.Match_number_of_Player(
                    **match_out.model_dump(),
                    current_player_count=player_count
                )
                combined.append(extended_match)
            
            return combined
        except SQLAlchemyError as e:
            self._db.rollback()
            raise
        except Exception as e:
            raise

    def get_match_by_id(self, match_id: UUID) -> Match | None:
        try:
            match: Match = self._db.query(Match).filter(Match.id == match_id).first()
            if not Match:
                raise Exception("Partida no encontrada")
        except Exception:
            raise
        return match
    
    def get_players_by_match(self, match_id: UUID) -> List[schemas.Players_by_Match_Schema]:
        
        try:    
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Partida no encontrada")
            
            result = []
            for mp in match.match_players:
                result.append({
                    "id": mp.player.id,
                    "player_id": mp.player.id,
                    "match_id" : mp.match.id,
                    "role": mp.role.value if mp.role else None,
                    "order": mp.order,
                    "name": mp.player.name,
                    "avatar": mp.player.avatar,
                    "birthday": mp.player.birthday 
                })
        except Exception as e:
            raise 
        return result
    
    def count_players_by_match(self, match_id: UUID) -> int:
        return (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id)
        .count()
    )   

    def join(self, match_id:UUID, player_id:UUID):
        match = self._db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # contar jugadores con el nuevo servicio
        current_players = self.count_players_by_match(match_id)
        if current_players >= match.max_players:
            raise HTTPException(status_code=400, detail="Match is full")
        
        #no se mete 2 veces el mismo jugador
        already_joined = (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id)
        .first()
        )
        if already_joined:
            raise HTTPException(status_code=400, detail="Player already in")

        match_player = Match_Player (match_id = match_id, player_id=player_id, order=0)
        self._db.add(match_player)
        self._db.commit()
        self._db.refresh(match_player)

    def get_cards_by_match (self, match_id:UUID) -> List[schemas.Cards_by_Match_Schema]:
          
        try:
            match = self._db.query(Match).filter(Match.id == match_id).first()
            if not match:
                raise Exception("Partida no encontrada")
            
            results = self._db.query(
                Match_Card.id,
                Match_Card.card_id,
                Match_Card.match_id,
                Match_Card.player_id,
                Match_Card.is_discarded,
                Card.name,
                Card.type,
                Card.description
            ).join(Card, Match_Card.card_id == Card.id)\
            .filter(Match_Card.match_id == match_id)\
            .all()
            
            combined = []
            for r in results:
                combined.append({
                    "id": r.id,
                    "card_id": r.card_id,
                    "match_id": r.match_id,
                    "player_id": r.player_id,
                    "is_discarded": r.is_discarded,
                    "name": r.name,
                    "type": r.type,
                    "description": r.description  
                })
            
            return combined
        except SQLAlchemyError as e:
            raise Exception(f"Database error: {str(e)}")

    def count_players_by_match(self, match_id: UUID) -> int:
        return (
        self._db.query(Match_Player)
        .filter(Match_Player.match_id == match_id)
        .count()
    )

    def update_match() -> Match:
        pass