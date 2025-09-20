from app.player.models import Player
from app.player.schemas import Player_Schema_out

def db_player_2_Player_Schema_out(db_player: Player) -> Player_Schema_out:
    return Player_Schema_out.model_validate(db_player)
