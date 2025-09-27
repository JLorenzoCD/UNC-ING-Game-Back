from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.matches.models import Match, Match_Player, MatchStatus
from app.matches import schemas
from app.matches.utils import db_match_2_match_schema
from app.player.models import Player
from app.cards.services import Cards_Services


# Excepciones
class OwnerNotFound(Exception):
    pass


class MatchNotFound(Exception):
    pass


class MatchValidationError(Exception):
    pass


class MatchService:
    def __init__(self, db: Session):
        self._db = db

    def create(self, match_dto: schemas.MatchDTO) -> schemas.MatchResponse:
        if match_dto.min_players < 2 or match_dto.max_players > 6:
            raise MatchValidationError("Incorrect number of players")

        owner: Player = self._db.get(Player, match_dto.owner_id)
        if not owner:
            raise OwnerNotFound()

        new_match = Match(
            name=match_dto.name,
            min_players=match_dto.min_players,
            max_players=match_dto.max_players,
            owner_id=owner.id,
        )
        try:
            self._db.add(new_match)
            self._db.commit()
            self._db.refresh(new_match)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        try:
            match_player = Match_Player(
                match_id=new_match.id, player_id=owner.id, order=0
            )
            self._db.add(match_player)
            self._db.commit()
            self._db.refresh(match_player)
        except SQLAlchemyError:
            self._db.rollback()
            raise

        match_out = db_match_2_match_schema(new_match)
        return schemas.MatchResponse(id=match_out.id)

    def get_all(self) -> list[Match]:
        return self._db.query(Match).all()

    def get_match_by_id(self, match_id: UUID) -> Match | None:
        return self._db.query(Match).filter(Match.id == match_id).first()

    def update_status_match(self, match_id: UUID, new_status: str) -> None:
        match: Match = self.get_match_by_id(match_id)
        if not match:
            raise MatchNotFound()
        match.status = new_status
        try:
            self._db.commit()
            self._db.refresh(match)
        except SQLAlchemyError as exception:
            self._db.rollback()
            raise exception

    def get_players_from_match(self, match_id: UUID):
        return (
            self._db.query(Match_Player)
            .filter(Match_Player.match_id == match_id)
            .all()
        )

    def iniciar_partida(self, match_id: UUID) -> None:
        # Actualizar estado de la partida
        self.update_status_match(match_id, MatchStatus.IN_PROGRESS)

        # Obtener jugadores (si los necesitás para lógica futura)
        match_players: list[Match_Player] = self.get_players_from_match(match_id)

        # Inicializar cartas con el servicio de cartas
        Cards_Services(self._db).iniciar_match_cards(match_id)
