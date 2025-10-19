from uuid import UUID
from enum import Enum as PyEnum
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

from app.secrets.models import Match_Secret, Secret, Secret_action, Secret_Type
from app.secrets.schemas import SecretUpdate
from app.player.models import Player, Match_Player
from app.matches.models import Match, MatchStatus

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
            .scalar()
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
            .scalar()
        )
        return accomplice_player_id
    
    def get_player_name(self, player_id: UUID) -> str:
        p = self._db.query(Player.name).filter(Player.id == player_id).scalar()
        return p

    def get_murderer_name(self, match_id: UUID) -> str:
        pid = self.get_murderer_id(match_id)
        return self.get_player_name(pid)

    def get_accomplice_name(self, match_id: UUID) -> Optional[str]:
        pid = self.get_accomplice_id(match_id)
        return self.get_player_name(pid) if pid else None
        
    def reveal_secret(self, match_secret_id: UUID):
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        if not match_secret:
            raise SecretNotFound("Secret not found")

        if match_secret.is_revealed:
            raise ValueError(f"Secret is already {Secret_action.REVEAL}")

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
            raise ValueError(f"Secret is already {Secret_action.HIDE}")

        match_secret.is_revealed = False
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e
            
    def steal_secret(self, match_secret_id: UUID, player_id: UUID):
        """
        Oculta un secreto revelado y lo roba. 
        """
        match_secret:Match_Secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        match_id = match_secret.match_id
        if not match_secret:
            raise SecretNotFound("Secret not found")

        # Ocultar el secreto
        self.hide_secret(match_secret_id)
            
        # Robar el secreto
        owner_player_id = match_secret.player_id
        
        owner_player = self._db.query(Match_Player).filter(Match_Player.player_id == owner_player_id and Match_Player.match_id == match_id).first()
        stealing_player = self._db.query(Match_Player).filter(Match_Player.player_id == player_id and Match_Player.match_id == match_id).first()

        if not owner_player or not stealing_player:
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
    
    def secret_update_verification(self, match_id: UUID, match_secret_id:UUID, secretIn: SecretUpdate):
        if not match_secret_id:
            raise SecretNotFound("Match_Secret ID es Null")
        
        match_secret:Match_Secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        if not match_secret:
            raise SecretNotFound("Secreto no encontrado")
        if match_secret.match_id != match_id:
            raise SecretNotFound("El secreto no coicide con la Partida")
        if not (secretIn.action in [Secret_action.HIDE, Secret_action.REVEAL, Secret_action.STEAL]):
            raise SecretNotFound("No es una acción valida")
        if secretIn.action in [Secret_action.HIDE, Secret_action.REVEAL] and secretIn.target_player_id != match_secret.player_id:
            raise SecretNotFound("No coiciden el secreto y el jugador seleccionado para la accion de Revelar u Ocultar")
        
    def get_match_secret_by_id(self, match_secret_id:UUID) -> Match_Secret:
        if not match_secret_id:
            raise SecretNotFound("No es un ID valido o el ID es Null")
        
        match_secret = self._db.query(Match_Secret).filter(Match_Secret.id == match_secret_id).first()
        
        if not match_secret:
            raise SecretNotFound("Secreto no encontrado por ID")
        
        return match_secret
    def is_murderer_revealed(self, match_id: UUID) -> dict | None:
        """
        Devuelve info si el murderer ya fue revelado.
        Retorna:
          {
              "secret_id": UUID del murderer,
              "murderer_name": str,
              "accomplice_name": str | None
          }
        o None si todavía no fue revelado.
        """
        row = (
            self._db.query(Match_Secret, Secret.type)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .filter(Secret.type == Secret_Type.MURDERER)
            .first()
        )

        if not row:
            return None

        match_secret, secret_type = row
        if not match_secret.is_revealed:
            return None

        murderer_name = self.get_murderer_name(match_id)
        accomplice_name = self.get_accomplice_name(match_id)
        return {
            "secret_id": match_secret.id,
            "murderer_name": murderer_name,
            "accomplice_name": accomplice_name,
        }
    
    def get_full_info(self, match_id: UUID) -> dict | None:
        """
        Devuelve toda la info necesaria para el ending.
        Retorna None si no hay murderer asignado.
        """
        match_secret = (
            self._db.query(Match_Secret)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .filter(Secret.type == Secret_Type.MURDERER)
            .first()
        )
        if not match_secret:
            return None
        murderer_name = self.get_murderer_name(match_id)
        accomplice_name = self.get_accomplice_name(match_id)
        accomplice_secret = (
            self._db.query(Match_Secret)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .filter(Match_Secret.match_id == match_id)
            .filter(Secret.type == Secret_Type.ACCOMPLICE)
            .first()
        )

        return {
            "murderer_secret_id": match_secret.id,
            "murderer_name": murderer_name,
            "accomplice_secret_id": accomplice_secret.id if accomplice_secret else None,
            "accomplice_name": accomplice_name,
        }
    
    
