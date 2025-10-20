import pytest
from uuid import uuid4
from datetime import date

from app.player.models import Player
from app.matches.models import Match
from app.cards.models import Card, Match_Card, Card_Type
from app.cards.services import Cards_Services 

def test_cards_off_the_table(db):
    """
    Unit test para verificar la funcionalidad de la carta "Cards Off The Table".
    """
    # 1. --- CONFIGURACIÓN (SETUP) ---

    # Crear jugadores
    player_1 = Player(name="Jugador 1", avatar="p1", birthday=date(2000, 1, 1))
    player_2 = Player(name="Jugador 2", avatar="p2", birthday=date(2001, 2, 2))
    db.add_all([player_1, player_2])
    db.commit()

    # Crear partida
    match = Match(name="Partida de Prueba", owner_id=player_1.id)
    db.add(match)
    db.commit()

    # Crear las cartas base ("Not so Fast" y "Cards Off The Table")
    card_not_so_fast = Card(name="NOT SO FAST", type=Card_Type.INSTANT, description="...")
    card_off_the_table = Card(name="CARDS OFF THE TABLE", type=Card_Type.EVENT, description="...")
    db.add_all([card_not_so_fast, card_off_the_table])
    
    # Crear otras 4 cartas genéricas para completar las manos
    other_cards = [Card(name=f"Otra Carta {i}", type=Card_Type.EVENT, description="...") for i in range(4)]
    other_cards2 = [Card(name=f"Otra Carta2 {i}", type=Card_Type.EVENT, description=".2.") for i in range(5)]

    db.add_all(other_cards + other_cards2)
    db.commit()

    # Crear las manos (Match_Card) de cada jugador
    # Mano del Jugador 1 (dueño del evento)
    hand_player_1: list[Match_Card] = [
        Match_Card(card_id=card_off_the_table.id, match_id=match.id, player_id=player_1.id),
    ] + [Match_Card(card_id=c.id, match_id=match.id, player_id=player_1.id) for c in other_cards2]

    # Mano del Jugador 2 (objetivo)
    hand_player_2: list[Match_Card] = [
        Match_Card(card_id=card_not_so_fast.id, match_id=match.id, player_id=player_2.id),
        Match_Card(card_id=card_not_so_fast.id, match_id=match.id, player_id=player_2.id), # Otra Not so Fast
    ] + [Match_Card(card_id=c.id, match_id=match.id, player_id=player_2.id) for c in other_cards]

    db.add_all(hand_player_1 + hand_player_2)
    db.commit()
    
    # Obtener el ID de la carta de evento
    event_card_id = hand_player_1[0].id

    # 2. --- EJECUCIÓN ---
    
    # Instanciar el servicio y llamar a la función
    card_service = Cards_Services(db)
    result = card_service.cards_off_the_table(
        match.id,
        target_player_id=player_2.id,
        event_card_owner_id=player_1.id,
        event_card_id=event_card_id
    )

    # 3. --- VERIFICACIÓN (ASSERTIONS) ---

    # Extraer los objetos y IDs para las aserciones
    discarded_nsf_objects = result["discarded_instant_cards"]
    discarded_event_id = result["discarded_event_card"]

    # Convertir la lista de objetos devueltos a un set de IDs para una búsqueda eficiente
    discarded_nsf_ids = {card.id for card in discarded_nsf_objects}
    
    # IDs esperados
    expected_nsf_id_1 = hand_player_2[0].id
    expected_nsf_id_2 = hand_player_2[1].id

    # Verificar que la función devolvió la cantidad correcta de cartas
    assert len(discarded_nsf_objects) == 2
    
    # Verificar que los IDs de las cartas "Not so Fast" están en los resultados (sin importar el orden)
    assert expected_nsf_id_1 in discarded_nsf_ids
    assert expected_nsf_id_2 in discarded_nsf_ids

    # Verificar que se devolvió el ID correcto de la carta de evento
    assert discarded_event_id == event_card_id
    
    
    # Verificar que la carta de evento "Cards Off The Table" fue descartada
    event_card_db = db.query(Match_Card).filter(Match_Card.id == event_card_id).first()
    assert event_card_db.is_discarded is True
    assert event_card_db.player_id is None

    # Verificar que las cartas "Not so Fast" del jugador 2 fueron descartadas
    not_so_fast_cards_db = db.query(Match_Card).filter(Match_Card.id.in_([hand_player_2[0].id, hand_player_2[1].id])).all()
    for card in not_so_fast_cards_db:
        assert card.is_discarded is True
        assert card.player_id is None
        
    # Verificar que las otras cartas del jugador 2 no fueron afectadas
    remaining_cards_p2 = db.query(Match_Card).filter(
        Match_Card.player_id == player_2.id,
        Match_Card.is_discarded == False
    ).count()
    assert remaining_cards_p2 == 4 # Tenía 6, se le descartaron 2

    # Verificar que las otras cartas del jugador 1 no fueron afectadas
    remaining_cards_p1 = db.query(Match_Card).filter(
        Match_Card.player_id == player_1.id,
        Match_Card.is_discarded == False
    ).count()
    assert remaining_cards_p1 == 5 # Tenía 6, se le descartó 1