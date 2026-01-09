from uuid import UUID

from app.player.schemas import Player_Schema_in
from app.player.models import Player

from sqlalchemy.exc import IntegrityError, DataError


class PlayerAlreadyExists(Exception):
    pass


class InvalidPlayerData(Exception):
    pass


class PlayerNotFound(Exception):
    pass


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
