# src/app/cards/tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base

# 👇 IMPORTA TODOS LOS MODELOS AQUÍ
from app.cards.models import Card, Match_Card
from app.matches.models import Match
from app.player.models import Player

# Motor de prueba (SQLite en memoria, o PostgreSQL si prefieres)
engine = create_engine("sqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db():
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
