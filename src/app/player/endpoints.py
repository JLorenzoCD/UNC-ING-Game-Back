from fastapi import APIRouter, status, Depends
from app.models.db import get_db
from app.player.utils import db_player_2_Player_Schema_out
from app.player.schemas import Player_Schema_in, Player_Schema_out
from websocketManager.ws_routes import ConnectionManager
from app.player.models import Player

player_router = APIRouter()


@player_router.post(
    path="/players",
    status_code=status.HTTP_201_CREATED
)
async def create_player(
    player_info: Player_Schema_in,
    db = Depends(get_db)
) -> Player_Schema_out:
    new_player = Player(
        name     = player_info.name,
        avatar   = player_info.avatar,
        birthday = player_info.birthday
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    player_info_out = db_player_2_Player_Schema_out(new_player)
    return player_info_out
