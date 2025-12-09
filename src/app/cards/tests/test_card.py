from app.cards.models import Card, Card_Type
from app.cards.schemas import Card_Schema
from app.cards.utils import db_card_2_card_schema

print("Test module loaded successfully!")


def test_create_card(db):
    """Test create card.

    Args:
        db: Parameter db."""
    new_card = Card(
        name="Espada mágica", type=Card_Type.EVENT, description="Espada +10"
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    assert new_card.id is not None
    assert new_card.name == "Espada mágica"
    assert new_card.type == Card_Type.EVENT
    assert new_card.description == "Espada +10"
    schema_card = db_card_2_card_schema(new_card)
    assert isinstance(schema_card, Card_Schema)
    assert schema_card.id == new_card.id
    assert schema_card.name == new_card.name
    assert schema_card.type == new_card.type
    assert schema_card.description == new_card.description
    card_dict = schema_card.model_dump()
    assert "id" in card_dict
    assert card_dict["name"] == "Espada mágica"
    assert card_dict["type"] == Card_Type.EVENT
    assert card_dict["description"] == "Espada +10"
