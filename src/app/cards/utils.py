from app.cards.models import Card, Match_Card
from app.cards.schemas import Card_Schema, Match_Card_Schema

def db_card_2_card_schema(db_card: Card) -> Card_Schema:
    return Card_Schema.model_validate(db_card)

def db_match_card_2_match_card_schema(db_card_match: Match_Card) -> Match_Card_Schema:
    return Match_Card_Schema.model_validate(db_card_match)

