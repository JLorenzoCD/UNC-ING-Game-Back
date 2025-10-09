from app.sets.models import Match_Set
from app.sets.schemas import MatchSetIn, MatchSetOut

def db_match_set_2_match_set_schema(db_match_set: Match_Set) -> MatchSetOut:
    return MatchSetOut.model_validate(db_match_set)
