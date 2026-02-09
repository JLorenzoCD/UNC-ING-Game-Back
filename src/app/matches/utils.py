from app.matches.models import Match
from app.matches.schemas import Match_Player_Schema, MatchOut
from app.player.models import Match_Player
from app.messages.schemas import MatchMessageOut


def db_match_2_match_schema(db_match: Match) -> MatchOut:
    """Db match 2 match schema.

    Args:
        db_match: Parameter db_match.

    Returns:
        Return value."""
    return MatchOut.model_validate(db_match)


def db_match_msg_2_match_msg_schema(db_match_msg):

    return MatchMessageOut.model_validate(db_match_msg)


def db_match_player_2_match_player_schema(
    db_match_player: Match_Player,
) -> Match_Player_Schema:
    """Db match player 2 match player schema.

    Args:
        db_match_player: Parameter db_match_player.

    Returns:
        Return value."""
    return Match_Player_Schema.model_validate(db_match_player)
