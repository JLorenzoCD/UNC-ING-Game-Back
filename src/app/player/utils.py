from app.player.models import Player
from app.player.schemas import PlayerOut

def db_player_2_player_schema(db_player: Player) -> PlayerOut:
    return PlayerOut.model_validate(db_player)
