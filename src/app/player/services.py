from uuid import UUID

from app.player.schemas import Player_Schema_in
from app.player.models import Player, Match_Player

from sqlalchemy.exc import IntegrityError, DataError

from app.player.exceptions import PlayerAlreadyExists, InvalidPlayerData, PlayerNotFound, PlayerNotFoundInMatch


class PlayerServices:
    def __init__(self, db):
        self._db = db

    def create_player(self, player_info: Player_Schema_in) -> Player | None:
        """
        Crea un jugador
        """

        try:
            new_player = Player(
                name=player_info.name,
                avatar=player_info.avatar,
                birthday=player_info.birthday
            )

            self._db.add(new_player)
            self._db.commit()
            self._db.refresh(new_player)
            return new_player

        # Captura errores de integridad (NOT NULL, claves duplicadas)
        except IntegrityError:
            self._db.rollback()
            raise PlayerAlreadyExists()

        # Captura errores de tipo de datos (ej. formato de fecha incorrecto)
        except DataError:
            self._db.rollback()
            raise InvalidPlayerData()

        except Exception as e:
            self._db.rollback()
            raise e  # Algún error inesperado (status=500)

    def get_player(self, player_id: UUID) -> Player | None:
        """Get a player by ID."""

        try:
            player = self._db.get(Player, player_id)
        except DataError:
            raise InvalidPlayerData()
        except Exception as e:
            raise e  # Algún error inesperado (status=500)

        if not player:
            raise PlayerNotFound()

        return player

    def get_player_in_match(self, player_id: UUID, match_id: UUID) -> Player | None:

        try:
            player = (
                self._db.query(Match_Player)
                .filter(
                    Match_Player.match_id == match_id, Match_Player.player_id == player_id
                )
                .first()
            )
        except DataError:
            raise InvalidPlayerData()
        except Exception as e:
            raise e  # Algún error inesperado (status=500)

        if not player:
            raise PlayerNotFoundInMatch()

        return player
