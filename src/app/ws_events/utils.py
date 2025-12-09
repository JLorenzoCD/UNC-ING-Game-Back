from app.ws_events.schemas import WsEventOut


def db_ws_event_2_schema(db_ws_event) -> WsEventOut:
    """Db ws event 2 schema.

    Args:
        db_ws_event: Parameter db_ws_event.

    Returns:
        Return value."""
    return WsEventOut.model_validate(db_ws_event)
