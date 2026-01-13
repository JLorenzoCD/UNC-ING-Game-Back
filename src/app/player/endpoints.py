from uuid import UUID
from fastapi import APIRouter, status, Depends

from app.models.db import get_db
from app.player.utils import db_player_2_Player_Schema_out
from app.player.schemas import Player_Schema_in, Player_Schema_out


# services
from app.player.services import PlayerServices

player_router = APIRouter(
    tags=["players"],
    prefix="/players"
)


@player_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED
)
async def create_player(player_info: Player_Schema_in, db=Depends(get_db)) -> Player_Schema_out:

    new_player = PlayerServices(db).create_player(player_info)

    player_info_out = db_player_2_Player_Schema_out(new_player)
    return player_info_out


@player_router.get(
    path="/{player_id}",
    status_code=status.HTTP_200_OK
)
async def get_player(player_id: UUID, db=Depends(get_db)) -> Player_Schema_out:

    player = PlayerServices(db).get_player(player_id)

    player_info_out = db_player_2_Player_Schema_out(player)
    return player_info_out
