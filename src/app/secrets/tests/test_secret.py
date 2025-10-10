import pytest
from uuid import uuid4
from app.secrets.models import Secret, Secret_Type
from app.secrets.schemas import Secret_Schema
from app.secrets.utils import db_secret_2_secret_schema

print("Test module loaded successfully!")  # Debugfrom ..utils import *

def test_create_card(db_session):
    # Creamos una Card en la DB
    new_secret = Secret(type=Secret_Type.MURDERER, content="Your the murderer")
    db_session.add(new_secret)
    db_session.commit()
    db_session.refresh(new_secret)

    # Verificamos que se guardó
    assert new_secret.id is not None
    assert new_secret.type == Secret_Type.MURDERER
    assert new_secret.content == "Your the murderer"

    # Convertimos con el schema
    schema_secret = db_secret_2_secret_schema(new_secret)

    # Verificamos el schema
    assert isinstance(schema_secret, Secret_Schema)
    assert schema_secret.id == new_secret.id
    assert schema_secret.type == new_secret.type
    assert schema_secret.content == new_secret.content

    # Verificamos que podemos serializar a dict
    card_dict = schema_secret.model_dump()
    assert "id" in card_dict
    assert card_dict["type"] == Secret_Type.MURDERER
    assert card_dict["content"] == "Your the murderer"