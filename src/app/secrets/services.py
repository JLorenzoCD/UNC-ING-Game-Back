from uuid import UUID

from app.secrets.models import Match_Secret, Secret


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
