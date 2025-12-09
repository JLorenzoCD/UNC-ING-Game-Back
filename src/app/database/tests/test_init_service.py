import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cards.models import Card, Card_Type
from app.database.init_service import DatabaseInitService, init_data
from app.models.db import Base
from app.secrets.models import Secret, Secret_Type

engine = create_engine("sqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    """Fixture para crear una base de datos en memoria para tests."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_init_all_data(db_session):
    """Test que verifica la inicialización de todos los datos."""
    service = DatabaseInitService(db_session)
    assert db_session.query(Secret).count() == 0
    assert db_session.query(Card).count() == 0
    service.init_all_data()
    assert db_session.query(Secret).count() == 3
    assert db_session.query(Card).count() > 0


def test_init_base_cards(db_session):
    """Test que verifica la inicialización de cartas base."""
    service = DatabaseInitService(db_session)
    assert db_session.query(Card).count() == 0
    service.init_base_cards()
    cards = db_session.query(Card).all()
    assert len(cards) > 0
    card_types = {c.type for c in cards}
    assert Card_Type.INSTANT in card_types
    assert Card_Type.DETECTIVE in card_types
    assert Card_Type.EVENT in card_types
    assert Card_Type.DEVIOUS in card_types
    card_names = [c.name for c in cards]
    assert "NOT_SO_FAST" in card_names
    assert "HERCULE_POIROT" in card_names
    assert "MISS_MARPLE" in card_names
    service.init_base_cards()
    assert db_session.query(Card).count() == len(cards)


def test_init_base_secrets(db_session):
    """Test que verifica la inicialización de secretos base."""
    service = DatabaseInitService(db_session)
    assert db_session.query(Secret).count() == 0
    service.init_base_secrets()
    secrets = db_session.query(Secret).all()
    assert len(secrets) == 3
    secret_types = [s.type for s in secrets]
    assert Secret_Type.MURDERER in secret_types
    assert Secret_Type.ACCOMPLICE in secret_types
    assert Secret_Type.INNOCENT in secret_types
    service.init_base_secrets()
    assert db_session.query(Secret).count() == 3


def test_init_data_function(db_session):
    """Test que verifica la función de conveniencia init_data."""
    assert db_session.query(Secret).count() == 0
    assert db_session.query(Card).count() == 0
    init_data(db_session)
    assert db_session.query(Secret).count() == 3
    assert db_session.query(Card).count() > 0
