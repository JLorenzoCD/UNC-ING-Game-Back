from datetime import date

from app.cards.models import Card, Card_Type, Match_Card
from app.cards.services import CardsServices
from app.matches.models import Match
from app.player.models import Player


def test_cards_off_the_table(db):
    """
    Unit test para verificar la funcionalidad de la carta "Cards Off The Table".
    """
    player_1 = Player(name="Jugador 1", avatar="p1", birthday=date(2000, 1, 1))
    player_2 = Player(name="Jugador 2", avatar="p2", birthday=date(2001, 2, 2))
    db.add_all([player_1, player_2])
    db.commit()
    match = Match(name="Partida de Prueba", owner_id=player_1.id)
    db.add(match)
    db.commit()
    card_not_so_fast = Card(
        name="NOT SO FAST", type=Card_Type.INSTANT, description="..."
    )
    card_off_the_table = Card(
        name="CARDS OFF THE TABLE", type=Card_Type.EVENT, description="..."
    )
    db.add_all([card_not_so_fast, card_off_the_table])
    other_cards = [
        Card(name=f"Otra Carta {i}", type=Card_Type.EVENT, description="...")
        for i in range(4)
    ]
    other_cards2 = [
        Card(name=f"Otra Carta2 {i}", type=Card_Type.EVENT, description=".2.")
        for i in range(5)
    ]
    db.add_all(other_cards + other_cards2)
    db.commit()
    hand_player_1: list[Match_Card] = [
        Match_Card(
            card_id=card_off_the_table.id, match_id=match.id, player_id=player_1.id
        )
    ] + [
        Match_Card(card_id=c.id, match_id=match.id, player_id=player_1.id)
        for c in other_cards2
    ]
    hand_player_2: list[Match_Card] = [
        Match_Card(
            card_id=card_not_so_fast.id, match_id=match.id, player_id=player_2.id
        ),
        Match_Card(
            card_id=card_not_so_fast.id, match_id=match.id, player_id=player_2.id
        ),
    ] + [
        Match_Card(card_id=c.id, match_id=match.id, player_id=player_2.id)
        for c in other_cards
    ]
    db.add_all(hand_player_1 + hand_player_2)
    db.commit()
    event_card_id = hand_player_1[0].id
    card_service = CardsServices(db)
    result = card_service.cards_off_the_table(
        match.id,
        target_player_id=player_2.id,
        event_card_owner_id=player_1.id,
        event_card_id=event_card_id,
    )
    discarded_nsf_objects = result["discarded_instant_cards"]
    discarded_nsf_ids = {card.id for card in discarded_nsf_objects}
    expected_nsf_id_1 = hand_player_2[0].id
    expected_nsf_id_2 = hand_player_2[1].id
    assert len(discarded_nsf_objects) == 2
    assert expected_nsf_id_1 in discarded_nsf_ids
    assert expected_nsf_id_2 in discarded_nsf_ids
    not_so_fast_cards_db = (
        db.query(Match_Card)
        .filter(Match_Card.id.in_([hand_player_2[0].id, hand_player_2[1].id]))
        .all()
    )
    for card in not_so_fast_cards_db:
        assert card.is_discarded is True
        assert card.player_id is None
    remaining_cards_p2 = (
        db.query(Match_Card)
        .filter(Match_Card.player_id == player_2.id, Match_Card.is_discarded == False)
        .count()
    )
    assert remaining_cards_p2 == 4
