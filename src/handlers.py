from fastapi import Request, status
from fastapi.responses import JSONResponse

from sqlalchemy.exc import SQLAlchemyError


def register_common_handlers(app):

    @app.exception_handler(SQLAlchemyError)
    async def generic_exception_db_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Database error: {str(exc)}"}
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )
