import pytest
from app.matches.ending import handle_match_ended, MatchEndedReason
from app.secrets.services import Secrets_Services
from app.matches.models import MatchStatus
from app.matches.tests.conftest import setup_match_and_players

@pytest.mark.asyncio
async def test_handle_match_ended_basic(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    # inicia partida
    client.post(f"/matches/{match_str_id}/start")

    # mock de un manager trucho que no hace nada ni tiene ws
    class FakeDummyManager:
        def __init__(self):
            self.broadcast_called = False
            self.closed = False

        async def specificBroadcast(self, msg, match_id):
            # simplemente marcamos que fue llamado
            self.broadcast_called = True
            return None

        def close_match(self, match_id):
            self.closed = True

    manager = FakeDummyManager()

    # ejecutamos el ending con el motivo que se reveló el asesino
    payload = await handle_match_ended(
        db_session, manager, match_id, MatchEndedReason.MURDERER_REVEALED
    )

    # vemos que se devolvió un payload válido
    assert payload is not None
    assert "match_id" in payload
    assert "secret_murderer_id" in payload
    assert "reason" in payload
    assert payload["reason"] == MatchEndedReason.MURDERER_REVEALED.value
    assert "details" in payload

    # verificamos que el match esté en estado completed
    from app.matches.services import MatchService
    match = MatchService(db_session).get_match_by_id(match_id)
    assert match.status == MatchStatus.COMPLETED

@pytest.mark.asyncio
async def test_handle_match_ended_deck_finished(db_session, client):
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]

    # inicia partida
    client.post(f"/matches/{match_str_id}/start")

    # mock de un manager trucho que no hace nada ni tiene ws
    class FakeDummyManager:
        def __init__(self):
            self.broadcast_called = False
            self.closed = False

        async def specificBroadcast(self, msg, match_id):
            self.broadcast_called = True
            return None

        def close_match(self, match_id):
            self.closed = True

    manager = FakeDummyManager()

    # ejecutamos el ending con motivo que se terminaron las cartas del mazo
    payload = await handle_match_ended(
        db_session, manager, match_id, MatchEndedReason.DECK_FINISHED
    )

    # verificamos payload
    assert payload is not None
    assert "match_id" in payload
    assert "secret_murderer_id" in payload
    assert "reason" in payload
    assert payload["reason"] == MatchEndedReason.DECK_FINISHED.value
    assert "details" in payload

    # verificamos que el match esté en estado completed
    from app.matches.services import MatchService
    match = MatchService(db_session).get_match_by_id(match_id)
    assert match.status == MatchStatus.COMPLETED
