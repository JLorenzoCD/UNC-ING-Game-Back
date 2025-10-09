from uuid import UUID
from enum import Enum as PyEnum
from sqlalchemy.exc import SQLAlchemyError

from app.secrets.models import Match_Secret, Secret
from app.secrets import schemas as Secret_schemas
from app.player.models import Player, Match_Player

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
    def reveal_secret(self, match_secret_id: UUID):
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        if not match_secret:
            raise SecretNotFound("Secret not found")

        if match_secret.is_revealed:
            raise ValueError("Secret is already revealed")

        match_secret.is_revealed = True
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e

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
            raise ValueError("Secret not found")
            
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

    def update_secret(self, action: Secret_action, match_secret_id:UUID, player_id: UUID = None):
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