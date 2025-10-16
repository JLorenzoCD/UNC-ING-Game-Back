from uuid import UUID
from enum import Enum as PyEnum
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

from app.secrets.models import Match_Secret, Secret, Secret_Type
from app.secrets import schemas as Secret_schemas
from app.player.models import Player, Match_Player
from app.matches.models import Match, MatchStatus
from app.matches.ending import MatchEnded,MatchEndedReason

class Secret_action(PyEnum):
        STEAL = "steal_secret"
        HIDE = "hide_secret"
        REVEAL = "reveal_secret"

class SecretNotFound(Exception):
    pass

class Secrets_Services:
    def __init__(self, db):
        self._db = db

    def init_match_secrets(self, cant_players: int, match_id: UUID) -> None:
        all_secrets = [
            {"type": "MURDERER", "quantity": 1},
        ]

        match cant_players:
            case 2:
                quantity = 5
                all_secrets.append({"type": "INNOCENT", "quantity": quantity})
            case 3:
                quantity = 8
                all_secrets.append({"type": "INNOCENT", "quantity": quantity})
            case 4:
                quantity = 11
                all_secrets.append({"type": "INNOCENT", "quantity": quantity})
            case 5:
                quantity = 13
                all_secrets.append({"type": "INNOCENT", "quantity": quantity})
                all_secrets.append({"type": "ACCOMPLICE", "quantity": 1})
            case 6:
                quantity = 16
                all_secrets.append({"type": "INNOCENT", "quantity": quantity})
                all_secrets.append({"type": "ACCOMPLICE", "quantity": 1})
            case _:
                raise ValueError("Invalid number of players")

        for secret_info in all_secrets:
            secret_base = (
                self._db.query(Secret)
                .filter_by(type=secret_info["type"])
                .first()
            )
            if not secret_base:
                continue 

            for _ in range(secret_info["quantity"]):
                match_secret = Match_Secret(
                    secret_id=secret_base.id,
                    match_id=match_id,
                )
                self._db.add(match_secret)

        self._db.commit()

    def get_secrets_by_match(self, match_id: UUID) -> list[Match_Secret]:
        return (
            self._db.query(Match_Secret)
            .filter(Match_Secret.match_id == match_id)
            .all()
        )
    
    def get_murderer_id(self,match_id: UUID) -> UUID:
        """
        Devuelve el player_id del Murderer del match.
        """
        murderer_player_id=(
            self._db.query(Match_Secret.player_id)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .join(Match, Match.id == Match_Secret.match_id)
            .filter(
                Match.id == match_id,
                Match.status == MatchStatus.IN_PROGRESS,
                Secret.type == Secret_Type.MURDERER,
                Match_Secret.player_id.isnot(None)
            )
            .scalar_one_or_none()
        )
        if murderer_player_id is None:
            raise ValueError("Murderer not assigned or match not started")
        return murderer_player_id
    
    def get_accomplice_id(self,match_id: UUID) -> Optional[UUID]:
        """
        Devuelve el player_id del complice del match.
        None en caso de que no haya complice asignado
        """
        accomplice_player_id=(
            self._db.query(Match_Secret.player_id)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .join(Match, Match.id == Match_Secret.match_id)
            .filter(
                Match.id == match_id,
                Match.status == MatchStatus.IN_PROGRESS,
                Secret.type == Secret_Type.ACCOMPLICE,
                Match_Secret.player_id.isnot(None)
            )
            .scalar_one_or_none()
        )
        return accomplice_player_id
    
    def get_player_name(self, player_id: UUID) -> str:
        p = self._db.query(Player.name).filter(Player.id == player_id).scalar_one()
        return p

    def get_murderer_name(self, match_id: UUID) -> str:
        pid = self.get_murderer_id(match_id)
        return self.get_player_name(pid)

    def get_accomplice_name(self, match_id: UUID) -> Optional[str]:
        pid = self.get_accomplice_id(match_id)
        return self.get_player_name(pid) if pid else None


    def reveal_secret(self, match_secret_id: UUID):
        #traemos el match secret + el tipo de secreto
        row = (
            self._db.query(Match_Secret, Secret.type.label("secret_type"))
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        if not row:
            raise SecretNotFound("Secret not found")
        match_secret, secret_type = row[0],row[1]

        if match_secret.is_revealed:
            raise ValueError("Secret is already revealed")

        match_secret.is_revealed = True
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e
        
        #Si el secreto es murderer terminamos la partida
        if secret_type == Secret_Type.MURDERER:
            #nombre del murderer - No uso servicios porque se me explota todo con unas dependencias circulares imposibles de solucionar
            murderer_name = self.get_murderer_name(match_secret.match_id)
            if not murderer_name:
                raise ValueError("Murderer not assigned")
            
            # nombre del accomplice - No uso servicios porque se me explota todo con unas dependencias circulares imposibles de solucionar
            accomplice_name = self.get_accomplice_name(match_secret.match_id)

            raise MatchEnded(
                reason=MatchEndedReason.MURDERER_REVEALED,
                murderer_name=murderer_name,
                accomplice_name=accomplice_name,
            )


    def hide_secret(self, match_secret_id: UUID):
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        if not match_secret:
            raise SecretNotFound("Secret not found")

        if not match_secret.is_revealed:
            raise ValueError("Secret is already hidden")

        match_secret.is_revealed = False
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e
            
    def steal_secret(self, match_secret_id: UUID, player_id: UUID):
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        if not match_secret:
            raise SecretNotFound("Secret not found")
            
        owner_player_id = match_secret.player_id
        
        owner_player = self._db.query(Match_Player).filter(Match_Player.player_id == owner_player_id).first()
        stealing_player = self._db.query(Match_Player).filter(Match_Player.player_id == player_id).first()

        if not owner_player or not stealing_player or owner_player.match_id != stealing_player.match_id:
            raise ValueError("Players are not in the same match")
            
        match_secret.player_id = player_id
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e

    def update_secret(self, action: Secret_action, match_secret_id:UUID, player_id: UUID = None) -> Match_Secret:
        if action == Secret_action.REVEAL:
            self.reveal_secret(match_secret_id)
        elif action == Secret_action.HIDE:
            self.hide_secret(match_secret_id)
        elif action == Secret_action.STEAL:
            if not player_id:
                raise ValueError("Player ID is required for steal action")
            self.steal_secret(match_secret_id, player_id)
        else:
            raise ValueError("Invalid action")
        
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        return match_secret