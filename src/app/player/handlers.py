from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.player.exceptions import PlayerNotFound, PlayerAlreadyExists, InvalidPlayerData, PlayerNotFoundInMatch


def register_player_exception_handlers(app):

    @app.exception_handler(PlayerNotFound)
    async def player_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Player not found"}
        )

    @app.exception_handler(PlayerNotFoundInMatch)
    async def player_in_match_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "The player is not in the match"}
        )

    @app.exception_handler(PlayerAlreadyExists)
    async def player_exists_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Player already exists"}
        )

    @app.exception_handler(InvalidPlayerData)
    async def player_invalid_data_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Invalid player data"}
        )
