from app.secrets.models import Secret, Match_Secret
from app.secrets.schemas import Secret_Schema, Match_Secret_Schema

def db_secret_2_secret_schema(db_secret: Secret) -> Secret_Schema:
    return Secret_Schema.model_validate(db_secret)

def db_match_secret_2_match_secret_schema(db_secret_match: Match_Secret) -> Match_Secret_Schema:
    return Match_Secret_Schema.model_validate(db_secret_match)
