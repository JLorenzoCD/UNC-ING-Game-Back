from app.matches.models import Match
from app.matches.schemas import Match_Player_Schema, MatchLogOut, MatchOut
from app.player.models import Match_Player


def db_match_2_match_schema(db_match: Match) -> MatchOut:
    """Db match 2 match schema.

    Args:
        db_match: Parameter db_match.

    Returns:
        Return value."""
    return MatchOut.model_validate(db_match)


def db_match_log_2_match_log_schema(db_match_log):
    """Db match log 2 match log schema.

    Args:
        db_match_log: Parameter db_match_log."""
    return MatchLogOut.model_validate(db_match_log)


def db_match_player_2_match_player_schema(
    db_match_player: Match_Player,
) -> Match_Player_Schema:
    """Db match player 2 match player schema.

    Args:
        db_match_player: Parameter db_match_player.

    Returns:
        Return value."""
    return Match_Player_Schema.model_validate(db_match_player)
