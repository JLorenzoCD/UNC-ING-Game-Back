from uuid import UUID

from app.secrets.models import Match_Secret


class Secrets_Services:
    def __init__(self, db):
        self._db = db

    def iniciar_secretros(self, cant_players: int, match_id: UUID) -> list[Match_Secret]:
        pass