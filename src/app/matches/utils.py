from app.matches.models import Match
from app.matches.schemas import MatchOut, Match_Player_Schema, MatchLogOut
from app.player.models import Match_Player

def db_match_2_match_schema(db_match: Match) -> MatchOut:
    return MatchOut.model_validate(db_match)


def db_match_player_2_match_player_schema(db_match_player: Match_Player) -> Match_Player_Schema:
    return Match_Player_Schema.model_validate(db_match_player)

def db_match_log_2_match_log_schema(db_match_log):
    return MatchLogOut.model_validate(db_match_log)