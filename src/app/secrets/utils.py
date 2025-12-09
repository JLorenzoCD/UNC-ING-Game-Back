from app.secrets.models import Match_Secret, Secret
from app.secrets.schemas import Match_Secret_Schema, Secret_Schema


def db_match_secret_2_match_secret_schema(
    db_secret_match: Match_Secret,
) -> Match_Secret_Schema:
    """Db match secret 2 match secret schema.

    Args:
        db_secret_match: Parameter db_secret_match.

    Returns:
        Return value."""
    return Match_Secret_Schema.model_validate(db_secret_match)


def db_secret_2_secret_schema(db_secret: Secret) -> Secret_Schema:
    """Db secret 2 secret schema.

    Args:
        db_secret: Parameter db_secret.

    Returns:
        Return value."""
    return Secret_Schema.model_validate(db_secret)
