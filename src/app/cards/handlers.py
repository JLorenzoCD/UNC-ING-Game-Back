from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.cards.exceptions import InvalidCardData, CardInvalidAction, CardNotFound


def register_match_exception_handlers(app):

    @app.exception_handler(InvalidCardData)
    async def card_invalid_data_handler(request: Request, exc):
        msg = "Invalid data for Card entity" if str(exc) == "" else str(exc)

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": msg}
        )

    @app.exception_handler(CardInvalidAction)
    async def card_invalid_action_handler(request: Request, exc):
        msg = "Invalid action with Card entity" if str(exc) == "" else str(exc)

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": msg}
        )

    @app.exception_handler(CardNotFound)
    async def card_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Card not found"}
        )
