from app.matches.models import Match, Match_Player
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from app.matches import schemas
from app.player.models import Player
from app.matches.utils import db_match_2_match_schema


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
    
    def create(self, match_dto: schemas.MatchDTO) -> schemas.MatchResponse:
        if match_dto.min_player < 2 or match_dto.max_player > 6:
            raise MatchValidationError("Incorrect number of players")
        
        owner:Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()
        
        new_match = Match(
            name = match_dto.name,
            min_player = match_dto.min_player,
            max_player = match_dto.max_player,
            owner_id = owner.id
        )
        try:

            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise
        match_out = db_match_2_match_schema(new_match)
        return schemas.MatchResponse(id=match_out.id)    

    def get_all() -> list[Match]:
        pass

    def get_match_by_id() -> Match | None:
        pass

    def update_match() -> Match:
        pass