import pytest
from uuid import uuid4
from app.cards.models import Card
from app.cards.schemas import Card_Schema
from app.cards.utils import db_card_2_card_schema

print("Test module loaded successfully!")  # Debugfrom ..utils import *

def test_create_card(db):
    # Creamos una Card en la DB
    new_card = Card(name="Espada mágica", description="Espada +10")
    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    # Verificamos que se guardó
    assert new_card.id is not None
    assert new_card.name == "Espada mágica"
    assert new_card.description == "Espada +10"

    # Convertimos con el schema
    schema_card = db_card_2_card_schema(new_card)

    # Verificamos el schema
    assert isinstance(schema_card, Card_Schema)
    assert schema_card.id == new_card.id
    assert schema_card.name == new_card.name
    assert schema_card.description == new_card.description

    # Verificamos que podemos serializar a dict
    card_dict = schema_card.model_dump()
    assert "id" in card_dict
    assert card_dict["name"] == "Espada mágica"
    assert card_dict["description"] == "Espada +10"
