from uuid import UUID

from app.cards.models import Match_Card


class Cards_Services:
    def __init__(self, db):
        self._db = db

    def iniciar_cartas(self, match_id: UUID) -> None:
        all_cards = [
            # Detective cards
            {"type": "Detective", "name": "Harley Quin Wildcard", "quantity": 4},
            {"type": "Detective", "name": "Adriane Oliver", "quantity": 3},
            {"type": "Detective", "name": "Miss Maple", "quantity": 3},
            {"type": "Detective", "name": "Parker Pyne", "quantity": 3},
            {"type": "Detective", "name": "Tommy Beresford", "quantity": 3},
            {"type": "Detective", "name": "Lady Eileen \"Bundle\" Brent", "quantity": 3},
            {"type": "Detective", "name": "Tuppence Beresford", "quantity": 2},
            {"type": "Detective", "name": "Hercule Poirot", "quantity": 1},
            {"type": "Detective", "name": "Mr Satterthwaite", "quantity": 2},
            
            # Instant cards
            {"type": "Instant", "name": "Not so fast", "quantity": 10},
            
            # Devious cards
            {"type": "Devious", "name": "Blackmailed", "quantity": 3},
            {"type": "Devious", "name": "Social Faux Pas", "quantity": 3},
            
            # Event cards
            {"type": "Event", "name": "Delay the murderer's escape!", "quantity": 3},
            {"type": "Event", "name": "Point your suspicions", "quantity": 3},
            {"type": "Event", "name": "Dead end clue", "quantity": 3},
            {"type": "Event", "name": "Another Victim", "quantity": 2},
            {"type": "Event", "name": "Look into the ashes", "quantity": 3},
            {"type": "Event", "name": "Card trade", "quantity": 2},
            {"type": "Event", "name": "And then there was one more...", "quantity": 2},
            {"type": "Event", "name": "Early train to paddington", "quantity": 2},
            {"type": "Event", "name": "Cards off the table", "quantity": 2},
        ]
        
        # Crear la lista completa de cartas expandida
        cards = []
        for card_info in all_cards:
            for _ in range(card_info["quantity"]):
                cards.append({
                    "type": card_info["type"],
                    "name": card_info["name"]
                })

        for card in cards:
            new_card = Match_Card(match_id=match_id, type=card.get("type"), name=card.get("name"))
            self._db.add(new_card)
            self._db.commit()
            self._db.refresh(new_card)