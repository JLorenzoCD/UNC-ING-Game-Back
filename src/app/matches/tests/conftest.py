# src/app/matches/tests/conftest.py

import pytest
from sqlalchemy import create_engine
from main import app
from sqlalchemy.orm import sessionmaker
from app.models.db import Base
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.models.db import Base, get_db
from app.matches.endpoints import router as matches_router

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

@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c
