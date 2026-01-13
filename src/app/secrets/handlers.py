from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.secrets.exceptions import SecretNotFound, SecretInvalidAction


def register_secrets_exception_handlers(app):

    @app.exception_handler(SecretNotFound)
    async def secret_not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)}
        )

    @app.exception_handler(SecretInvalidAction)
    async def secret_invalid_action_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )
