from uuid import UUID

from app.player.schemas import Player_Schema_in
from app.player.models import Player

from sqlalchemy.exc import IntegrityError, DataError


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
        except IntegrityError as e:
            self._db.rollback()
            return None

        # Captura errores de tipo de datos (ej. formato de fecha incorrecto)
        except DataError as e:
            self._db.rollback()
            return None

        except Exception as e:
            self._db.rollback()
            raise  # Algún error inesperado (status=500)

    def validate_player(self, player_id: UUID):
        """
        Verifica que el jugador existe en la bases de datos.

        raise:
            ValueError si el jugador no existe
        """
        id_player_in_db = self._db.query(Player).filter(
            Player.id == player_id,
        ).count()

        if id_player_in_db != 1:
            raise ValueError("El UUID provisto no es valido.")
