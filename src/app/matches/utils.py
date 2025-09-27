from fastapi import Depends
from app.matches.models import Match, Match_Player
from app.matches.schemas import MatchOut, Match_Player_Schema
from app.matches import services as match_services
from app.models.db import get_db
from app.secrets import services as secret_services
from app.secrets.models import Match_Secret
from app.cards import services as card_services
from app.matches.models import MatchStatus

def db_match_2_match_schema(db_match: Match) -> MatchOut:
    return MatchOut.model_validate(db_match)

def db_match_player_2_match_player_schema(db_match_player: Match_Player) -> Match_Player_Schema:
    return Match_Player_Schema.model_validate(db_match_player)