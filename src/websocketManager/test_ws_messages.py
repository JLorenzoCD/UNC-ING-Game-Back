import json
import uuid
from datetime import date

from websocketManager.ws_messages import WSEvent, make_ws_message


def test_make_ws_message_with_uuid_and_date():
    """Test make ws message with uuid and date."""
    player_id = uuid.uuid4()
    birthday = date(2000, 1, 1)
    payload = {"id": player_id, "name": "hernan", "birthday": birthday}
    message = make_ws_message(WSEvent.PLAYER_JOIN, payload)
    parsed = json.loads(message)
    assert "event" in parsed
    assert "payload" in parsed
    assert parsed["event"] == WSEvent.PLAYER_JOIN
    assert isinstance(parsed["payload"]["id"], str)
    assert parsed["payload"]["id"] == str(player_id)
    assert isinstance(parsed["payload"]["birthday"], str)
    assert parsed["payload"]["birthday"] == birthday.isoformat()
    assert parsed["payload"]["name"] == "hernan"
