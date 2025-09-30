import uuid
import pytest
from app.cards.models import Card, Match_Card
from app.cards import models
from sqlalchemy import func

def test_get_cards(client, db_session):
    #creo player owner
    response = client.post("/players", json={
        "name": "Owner",
        "avatar": "avatar1",
        "birthday": "2000-01-01"
    })
    assert response.status_code == 201
    owner = response.json()
    owner_id = uuid.UUID(owner['id'])

    #creo partida
    match_post = {
        "name": "Partida Test",
        "min_players": 2,
        "max_players": 4,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    match_id = uuid.UUID(match['id'])
    
    #crear otro player
    response = client.post("/players", json={
        "name": "Jugador Nuevo",
        "avatar": "avatar2",
        "birthday": "2000-02-02"
    })
    assert response.status_code == 201
    new_player = response.json()
    new_player_id = uuid.UUID(new_player['id'])

    #entro a la partida
    response = client.post(f"/matches/{match['id']}/join", params={"player_id": new_player["id"]})
    assert response.status_code == 200
    
    #agrego las cartas
    db_session.add_all([
        # Instant Cards
        Card(id=uuid.uuid4(), name="NOT SO FAST", type="INSTANT", description="Play this card at any time, even if it is not your turn. It cancels an action before it is taken, unless otherwise stated, including cancelling another 'Not so fast...' card."),
        # Detective Cards
        Card(id=uuid.uuid4(), name="PARKER PYNE", type="DETECTIVE", description="Parker Pyne focuses on helping his clients achieve happiness... Instead of revealing a secret card, flip any face-up secret card face-down. This may remove social disgrace."),
        # Event Cards
        Card(id=uuid.uuid4(), name="CARDS OFF THE TABLE", type="EVENT", description="Their plans are discovered! Choose a player, who must discard all the 'Not so fast...' cards in their hand. The action cannot be cancelled by a 'Not so fast...' card."),
        Card(id=uuid.uuid4(), name="ANOTHER VICTIM", type="EVENT", description="Take any existing set from another player and play it in front of you. You now own this set."),
        Card(id=uuid.uuid4(), name="DEAD CARD FOLLY", type="EVENT", description="All players must pass one card from their hand, face-down, to the player on their right or left. The active player decides which direction. You may ask for a card of your choice, but beware you may be tricked."),
        # Devious Cards
        Card(id=uuid.uuid4(), name="BLACKMAILED", type="DEVIOUS", description="You have been blackmailed! If you have received this card from another player, you must show them one secret card of their choice, before returning it face-down to your secrets. This action cannot be cancelled by a 'Not so fast...' card. This card can only be used during a Card Trade or a Dead Card Folly."),
        Card(id=uuid.uuid4(), name="SOCIAL FAUX PAS", type="DEVIOUS", description="At dinner, you have been tricked into ordering a dessert wine with a starter... If you have received this card from another player, you must reveal a secret card of your choice. This card can only be used during a Card Trade or a Dead Card Folly.")
            ])
    db_session.commit()   
    
    
    card_count = db_session.query(Card).count()
    assert card_count >= 5
    
    card1 = db_session.query(models.Card).order_by(func.random()).first()
    card2 = db_session.query(models.Card).order_by(func.random()).first()
    card3 = db_session.query(models.Card).order_by(func.random()).first()
    card4 = db_session.query(models.Card).order_by(func.random()).first()
    card5 = db_session.query(models.Card).order_by(func.random()).first()
    
    if (not card1) or (not card2) or (not card3):
        pytest.fail("No se pudieron obtener todas las cartas necesarias")    
        
    match_card1 = Match_Card(
        card_id=card1.id,
        match_id=match_id,
        player_id=owner_id
    )
    match_card2 = Match_Card(
        card_id=card2.id,
        match_id=match_id,
        player_id=owner_id
    )
    match_card3 = Match_Card(
        card_id=card3.id,
        match_id=match_id,
        player_id=owner_id
    )
    match_card4 = Match_Card(
        card_id=card4.id,
        match_id=match_id,
        player_id=new_player_id        
    )
    match_card5 = Match_Card(
        card_id=card5.id,
        match_id=match_id,
        player_id=new_player_id        
    )
    
    
    db_session.add_all([
        match_card1, 
        match_card2, 
        match_card3,
        match_card4,
        match_card5
        ])
    db_session.commit()
    
    response_card = client.get(f"/matches/{match['id']}/cards")
    assert response_card.status_code == 200
    data = response_card.json()
    
    #verificar que es una lista y tiene elementos
    assert isinstance(data, list)
    assert len(data) == 5

    #verificar cada diccionario en la lista
    for card_data in data:
        # 1. 'id' sea distinto al 'card_id'
        assert card_data['id'] != card_data['card_id'], f"id y card_id no deben ser iguales: {card_data}"
        
        # 2. 'match_id' exista y sea el correcto
        assert 'match_id' in card_data, "Falta campo match_id"
        assert card_data['match_id'] == str(match_id), f"match_id incorrecto: {card_data['match_id']}"
        
        # 3. 'player_id' exista (puede ser None o UUID válido)
        assert 'player_id' in card_data, "Falta campo player_id"
        