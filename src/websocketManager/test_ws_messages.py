import json
import uuid
from datetime import date
from websocketManager.ws_messages import make_ws_message, WSEvent

def test_make_ws_message_with_uuid_and_date():
    player_id = uuid.uuid4()
    birthday = date(2000, 1, 1)

    payload = {
        "id": player_id,
        "name": "hernan",
        "birthday": birthday
    }

    #mensaje
    message = make_ws_message(WSEvent.PLAYER_JOIN, payload)

    #asegurarse que es un string válido de JSON
    parsed = json.loads(message)

    assert "event" in parsed
    assert "payload" in parsed
    assert parsed["event"] == WSEvent.PLAYER_JOIN

    #validar que UUID y date como string
    assert isinstance(parsed["payload"]["id"], str)
    assert parsed["payload"]["id"] == str(player_id)
    assert isinstance(parsed["payload"]["birthday"], str)
    assert parsed["payload"]["birthday"] == birthday.isoformat()

    #validar que todo sigue bien igual
    assert parsed["payload"]["name"] == "hernan"
