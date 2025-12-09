import pytest

from app.matches.ending import MatchEndedReason, handle_match_ended
from app.matches.models import MatchStatus
from app.matches.tests.conftest import setup_match_and_players


@pytest.mark.asyncio
async def test_handle_match_ended_basic(db_session, client):
    """Test handle match ended basic.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    client.post(f"/matches/{match_str_id}/start")

    class FakeDummyManager:
        """Class FakeDummyManager."""

        def __init__(self):
            """init  ."""
            self.broadcast_called = False
            self.closed = False

        def close_match(self, match_id):
            """Close match.

            Args:
                match_id: Parameter match_id."""
            self.closed = True

        async def specificBroadcast(self, msg, match_id):
            """Specificbroadcast.

            Args:
                msg: Parameter msg.
                match_id: Parameter match_id."""
            self.broadcast_called = True
            return None

    manager = FakeDummyManager()
    payload = await handle_match_ended(
        db_session, manager, match_id, MatchEndedReason.MURDERER_REVEALED
    )
    assert payload is not None
    assert "match_id" in payload
    assert "secret_murderer_id" in payload
    assert "reason" in payload
    assert payload["reason"] == MatchEndedReason.MURDERER_REVEALED.value
    assert "details" in payload
    from app.matches.services import MatchService

    match = MatchService(db_session).get_match_by_id(match_id)
    assert match.status == MatchStatus.COMPLETED


@pytest.mark.asyncio
async def test_handle_match_ended_deck_finished(db_session, client):
    """Test handle match ended deck finished.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    client.post(f"/matches/{match_str_id}/start")

    class FakeDummyManager:
        """Class FakeDummyManager."""

        def __init__(self):
            """init  ."""
            self.broadcast_called = False
            self.closed = False

        def close_match(self, match_id):
            """Close match.

            Args:
                match_id: Parameter match_id."""
            self.closed = True

        async def specificBroadcast(self, msg, match_id):
            """Specificbroadcast.

            Args:
                msg: Parameter msg.
                match_id: Parameter match_id."""
            self.broadcast_called = True
            return None

    manager = FakeDummyManager()
    payload = await handle_match_ended(
        db_session, manager, match_id, MatchEndedReason.DECK_FINISHED
    )
    assert payload is not None
    assert "match_id" in payload
    assert "secret_murderer_id" in payload
    assert "reason" in payload
    assert payload["reason"] == MatchEndedReason.DECK_FINISHED.value
    assert "details" in payload
    from app.matches.services import MatchService

    match = MatchService(db_session).get_match_by_id(match_id)
    assert match.status == MatchStatus.COMPLETED


@pytest.mark.asyncio
async def test_handle_match_ended_social_disgrace(db_session, client):
    """Test handle match ended social disgrace.

    Args:
        db_session: Parameter db_session.
        client: Parameter client."""
    setup = setup_match_and_players(client, db_session)
    match_id = setup["match_id"]
    match_str_id = setup["match_str_id"]
    client.post(f"/matches/{match_str_id}/start")

    class FakeDummyManager:
        """Class FakeDummyManager."""

        def __init__(self):
            """init  ."""
            self.broadcast_called = False
            self.closed = False

        def close_match(self, match_id):
            """Close match.

            Args:
                match_id: Parameter match_id."""
            self.closed = True

        async def specificBroadcast(self, msg, match_id):
            """Specificbroadcast.

            Args:
                msg: Parameter msg.
                match_id: Parameter match_id."""
            self.broadcast_called = True
            return None

    manager = FakeDummyManager()
    payload = await handle_match_ended(
        db_session, manager, match_id, MatchEndedReason.SOCIAL_DISGRACE
    )
    assert payload is not None
    assert "match_id" in payload
    assert "secret_murderer_id" in payload
    assert "reason" in payload
    assert payload["reason"] == MatchEndedReason.SOCIAL_DISGRACE.value
    assert "details" in payload
    assert "Everyone is in social disgrace!" in payload["details"]
    from app.matches.services import MatchService

    match = MatchService(db_session).get_match_by_id(match_id)
    assert match.status == MatchStatus.COMPLETED
