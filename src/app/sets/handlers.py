from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.sets.exceptions import InvalidCardError, InvalidMatchIdError, InvalidSetError, TargetSecretError, SetUpdateError


def register_sets_exception_handlers(app):

    @app.exception_handler(InvalidCardError)
    async def card_invalid_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(InvalidMatchIdError)
    async def card_not_in_match_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(TargetSecretError)
    async def unselected_secret_match_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(InvalidSetError)
    async def set_invalid_match_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)}
        )

    @app.exception_handler(SetUpdateError)
    async def set_update_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)}
        )
