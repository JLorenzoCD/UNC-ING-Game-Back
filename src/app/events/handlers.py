from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.events.exceptions import EventNotFound, EventInvalidAction


def register_match_exception_handlers(app):

    @app.exception_handler(EventNotFound)
    async def event_not_found_handler(request: Request, exc):
        msg = "Event not found" if str(exc) == "" else str(exc)

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": msg}
        )

    @app.exception_handler(EventInvalidAction)
    async def event_invalid_action_handler(request: Request, exc):
        msg = "Invalid action in Event entity" if str(exc) == "" else str(exc)

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": msg}
        )
