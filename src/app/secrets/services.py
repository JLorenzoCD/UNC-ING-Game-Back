from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.matches.models import Match, MatchStatus
from app.player.models import Match_Player, Player
from app.secrets.models import Match_Secret, Secret, Secret_action, Secret_Type
from app.secrets.schemas import SecretUpdate

from app.secrets.exceptions import SecretNotFound, SecretInvalidAction
from app.matches.exceptions import MatchInvalidAction, MatchValidationError
from app.player.exceptions import InvalidPlayerData


class Secrets_Services:
    """Class Secrets_Services."""

    def __init__(self, db):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def get_accomplice_id(self, match_id: UUID) -> Optional[UUID]:
        """
        Devuelve el player_id del complice del match.
        None en caso de que no haya complice asignado
        """
        accomplice_player_id = (
            self._db.query(Match_Secret.player_id)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .join(Match, Match.id == Match_Secret.match_id)
            .filter(
                Match.id == match_id,
                Match.status == MatchStatus.IN_PROGRESS,
                Secret.type == Secret_Type.ACCOMPLICE,
                Match_Secret.player_id.isnot(None),
            )
            .scalar()
        )
        return accomplice_player_id

    def get_accomplice_name(self, match_id: UUID) -> Optional[str]:
        """Get accomplice name.

        Args:
            match_id: Parameter match_id.

        Returns:
            Return value."""
        pid = self.get_accomplice_id(match_id)
        return self.get_player_name(pid) if pid else None

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

    def get_match_secret_by_id(self, match_secret_id: UUID) -> Match_Secret:
        """Get match secret by id.

        Args:
            match_secret_id: Parameter match_secret_id.

        Returns:
            Return value."""
        if not match_secret_id:
            raise SecretNotFound("No es un ID valido o el ID es Null")
        match_secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        if not match_secret:
            raise SecretNotFound("Secreto no encontrado por ID")
        return match_secret

    def get_murderer_id(self, match_id: UUID) -> UUID:
        """
        Devuelve el player_id del Murderer del match.
        """
        murderer_player_id = (
            self._db.query(Match_Secret.player_id)
            .join(Secret, Match_Secret.secret_id == Secret.id)
            .join(Match, Match.id == Match_Secret.match_id)
            .filter(
                Match.id == match_id,
                Match.status == MatchStatus.IN_PROGRESS,
                Secret.type == Secret_Type.MURDERER,
                Match_Secret.player_id.isnot(None),
            )
            .scalar()
        )
        if murderer_player_id is None:
            raise MatchInvalidAction(
                "Murderer not assigned or match not started")
        return murderer_player_id

    def get_murderer_name(self, match_id: UUID) -> str:
        """Get murderer name.

        Args:
            match_id: Parameter match_id.

        Returns:
            Return value."""
        pid = self.get_murderer_id(match_id)
        return self.get_player_name(pid)

    def get_player_name(self, player_id: UUID) -> str:
        """Get player name.

        Args:
            player_id: Parameter player_id.

        Returns:
            Return value."""
        p = self._db.query(Player.name).filter(Player.id == player_id).scalar()
        return p

    def get_secrets_by_match(self, match_id: UUID) -> list[Match_Secret]:
        """Get secrets by match.

        Args:
            match_id: Parameter match_id.

        Returns:
            Return value."""
        return (
            self._db.query(Match_Secret).filter(
                Match_Secret.match_id == match_id).all()
        )

    def hide_secret(self, match_secret_id: UUID):
        """Hide secret.

        Args:
            match_secret_id: Parameter match_secret_id."""
        match_secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        if not match_secret:
            raise SecretNotFound("Secret not found")
        if not match_secret.is_revealed:
            raise SecretInvalidAction(
                f"Secret is already {Secret_action.HIDE}")
        match_secret.is_revealed = False
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e

    def init_match_secrets(self, cant_players: int, match_id: UUID) -> None:
        """Init match secrets.

        Args:
            cant_players: Parameter cant_players.
            match_id: Parameter match_id.

        Returns:
            Return value."""
        all_secrets = [{"type": "MURDERER", "quantity": 1}]
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
                raise MatchValidationError("Invalid number of players")
        for secret_info in all_secrets:
            secret_base = (
                self._db.query(Secret).filter_by(
                    type=secret_info["type"]).first()
            )
            if not secret_base:
                continue
            for _ in range(secret_info["quantity"]):
                match_secret = Match_Secret(
                    secret_id=secret_base.id, match_id=match_id)
                self._db.add(match_secret)
        self._db.commit()

    def is_everyone_in_social_disgrace(self, match_id: UUID) -> bool:
        """
        Verifica si todos los jugadores inocentes (no murderer ni accomplice)
        tienen todos sus secretos revelados.

        Returns:
            bool: True si todos los inocentes están en desgracia social, False en caso contrario
        """
        murderer_id = None
        accomplice_id = None
        try:
            murderer_id = self.get_murderer_id(match_id)
        except MatchInvalidAction:
            return False
        try:
            accomplice_id = self.get_accomplice_id(match_id)
        except:
            pass
        from app.player.models import Match_Player

        all_players = (
            self._db.query(Match_Player.player_id)
            .filter(Match_Player.match_id == match_id)
            .all()
        )
        innocent_player_ids = []
        for player in all_players:
            player_id = player[0]
            if player_id != murderer_id and player_id != accomplice_id:
                innocent_player_ids.append(player_id)
        if not innocent_player_ids:
            return False
        for innocent_id in innocent_player_ids:
            player_secrets = (
                self._db.query(Match_Secret)
                .filter(Match_Secret.match_id == match_id)
                .filter(Match_Secret.player_id == innocent_id)
                .all()
            )
            for secret in player_secrets:
                if not secret.is_revealed:
                    return False
        return True

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

    def reveal_secret(self, match_secret_id: UUID):
        """Reveal secret.

        Args:
            match_secret_id: Parameter match_secret_id."""
        match_secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        if not match_secret:
            raise SecretNotFound("Secret not found")
        if match_secret.is_revealed:
            raise SecretInvalidAction(
                f"Secret is already {Secret_action.REVEAL}")
        match_secret.is_revealed = True
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e

    def secret_update_verification(
        self, match_id: UUID, match_secret_id: UUID, secretIn: SecretUpdate
    ):
        """Secret update verification.

        Args:
            match_id: Parameter match_id.
            match_secret_id: Parameter match_secret_id.
            secretIn: Parameter secretIn."""
        if not match_secret_id:
            raise SecretNotFound("Match_Secret ID es Null")
        match_secret: Match_Secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        if not match_secret:
            raise SecretNotFound("Secreto no encontrado")
        if match_secret.match_id != match_id:
            raise SecretNotFound("El secreto no coicide con la Partida")
        if not secretIn.action in [
            Secret_action.HIDE,
            Secret_action.REVEAL,
            Secret_action.STEAL,
        ]:
            raise SecretNotFound("No es una acción valida")
        if (
            secretIn.action in [Secret_action.HIDE, Secret_action.REVEAL]
            and secretIn.target_player_id != match_secret.player_id
        ):
            raise SecretNotFound(
                "No coiciden el secreto y el jugador seleccionado para la accion de Revelar u Ocultar"
            )

    def steal_secret(self, match_secret_id: UUID, player_id: UUID):
        """
        Oculta un secreto revelado y lo roba.
        """
        match_secret: Match_Secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        match_id = match_secret.match_id
        if not match_secret:
            raise SecretNotFound("Secret not found")
        self.hide_secret(match_secret_id)
        owner_player_id = match_secret.player_id
        owner_player = (
            self._db.query(Match_Player)
            .filter(
                Match_Player.player_id == owner_player_id
                and Match_Player.match_id == match_id
            )
            .first()
        )
        stealing_player = (
            self._db.query(Match_Player)
            .filter(
                Match_Player.player_id == player_id
                and Match_Player.match_id == match_id
            )
            .first()
        )
        if not owner_player or not stealing_player:
            raise MatchInvalidAction("Players are not in the same match")
        match_secret.player_id = player_id
        try:
            self._db.commit()
            self._db.refresh(match_secret)
        except SQLAlchemyError as e:
            self._db.rollback()
            raise e

    def update_secret(
        self, action: Secret_action, match_secret_id: UUID, player_id: UUID = None
    ) -> Match_Secret:
        """Update secret.

        Args:
            action: Parameter action.
            match_secret_id: Parameter match_secret_id.
            player_id: Parameter player_id.

        Returns:
            Return value."""
        if action == Secret_action.REVEAL:
            self.reveal_secret(match_secret_id)
        elif action == Secret_action.HIDE:
            self.hide_secret(match_secret_id)
        elif action == Secret_action.STEAL:
            if not player_id:
                raise InvalidPlayerData(
                    "Player ID is required for steal action")
            self.steal_secret(match_secret_id, player_id)
        else:
            raise SecretInvalidAction("Invalid action")
        match_secret = (
            self._db.query(Match_Secret)
            .filter(Match_Secret.id == match_secret_id)
            .first()
        )
        return match_secret
