from app.sets.models import Match_Set
from app.sets.schemas import MatchSetOut


def db_match_set_2_match_set_schema(db_match_set: Match_Set) -> MatchSetOut:
    """Db match set 2 match set schema.

    Args:
        db_match_set: Parameter db_match_set.

    Returns:
        Return value."""
    return MatchSetOut.model_validate(db_match_set)
