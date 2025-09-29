from app.matches.models import Match, Match_Player
from app.matches.schemas import MatchOut, Match_Player_Schema


def db_match_2_match_schema(db_match: Match) -> MatchOut:
    return MatchOut.model_validate(db_match)


def db_match_player_2_match_player_schema(db_match_player: Match_Player) -> Match_Player_Schema:
    return Match_Player_Schema.model_validate(db_match_player)
