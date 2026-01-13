from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.matches.exceptions import MatchNotFound, MatchValidationError, MatchInvalidAction, OwnerNotFound, PlayersInMatchNotFound, PlayersIsInOnGoingMatch


def register_match_exception_handlers(app):

    @app.exception_handler(MatchNotFound)
    async def match_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Match not found"}
        )

    @app.exception_handler(MatchValidationError)
    async def match_invalid_data_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(MatchInvalidAction)
    async def match_invalid_action_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(OwnerNotFound)
    async def owner_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Owner player data"}
        )

    @app.exception_handler(PlayersInMatchNotFound)
    async def players_in_match_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Players for march not found"}
        )

    @app.exception_handler(PlayersIsInOnGoingMatch)
    async def players_is_in_ongoing_match_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Player is already in an ongoing match"}
        )
