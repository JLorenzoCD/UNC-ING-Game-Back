import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.db import Base, get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client(db_session):
    """Fixture que provee un cliente de prueba con DB mockeada"""

    def override_get_db_with_session():
        """Override get db with session."""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db_with_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Fixture que provee una sesión de base de datos de prueba"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    """Override get db."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()
