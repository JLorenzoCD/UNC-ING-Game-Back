from app.ws_events.schemas import WsEventOut


def db_ws_event_2_schema(db_ws_event) -> WsEventOut:
    return WsEventOut.model_validate(db_ws_event)