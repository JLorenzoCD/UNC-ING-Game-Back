from cards.models import *
from cards.schemas import *

def db_card_2_Card_Schema(db_Card: Card) -> Card_Schema:
    return Card_Schema.model_validate(db_Card)

def db_card_match_2_Card_Match_Schema(db_Card_Match: Card_Match) -> Card_Match_Schema:
    return Card_Match_Schema.model_validate(db_Card_Match)

