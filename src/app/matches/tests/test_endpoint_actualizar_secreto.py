import pytest
import json
from uuid import UUID
from unittest.mock import patch, AsyncMock
from app.sets.models import Match_Set, SetType
from app.player.models import Player
from app.matches.models import Match
from app.cards.models import Card, Match_Card, Card_Type
from app.secrets.models import Secret, Secret_Type, Match_Secret, Secret_action
from app.secrets import services as secret_services
from app.matches.tests.conftest import setup_match_and_players, jsonable_encoder

def create_match_cards_for_set(db_session, card_names: list[str], match_id: UUID, player_id: UUID) -> list[UUID]:
    """Helper para crear Match_Card a partir de una lista de nombres de cartas."""
    card_ids = []
    for name in card_names:
        card = db_session.query(Card).filter(Card.name == name).first()
        assert card is not None, f"Card with name '{name}' not found in test setup."

        match_card = Match_Card(
            card_id=card.id,
            match_id=match_id,
            player_id=player_id
        )
        db_session.add(match_card)
        db_session.commit()
        db_session.refresh(match_card)
        card_ids.append(match_card.id)
    
    return card_ids

def create_match_secrets(db_session, secret: Secret, match_id: UUID, player_ids: list[UUID]) -> list[UUID]:
    """Helper para crear Match_Secret para una lista de jugadores."""
    secret_ids = []
    for player_id in player_ids:
        match_secret = Match_Secret(
            secret_id=secret.id,
            match_id=match_id,
            player_id=player_id,
            is_revealed=False
        )
        db_session.add(match_secret)
        db_session.commit()
        db_session.refresh(match_secret)
        secret_ids.append(match_secret.id)
    return secret_ids

# @pytest.mark.parametrize("action, expected_state", [
#     #Reveal
#     (Secret_action.REVEAL, True )
# ])