# src/app/matches/tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base

# 👇 IMPORTA TODOS LOS MODELOS AQUÍ
from app.matches.models import Match, Match_Player
from app.secrets.models import Secret
from app.player.models import Player

# Motor de prueba (SQLite en memoria, o PostgreSQL si prefieres)
engine = create_engine("sqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)