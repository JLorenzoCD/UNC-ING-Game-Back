import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db import Base
from app.database.init_service import DatabaseInitService, init_data

# Importar todos los modelos para que SQLAlchemy pueda crear las tablas correctamente
from app.cards.models import Card, Card_Type, Match_Card
from app.secrets.models import Secret, Match_Secret, Secret_Type
from app.matches.models import Match
from app.player.models import Player, Match_Player
from app.sets.models import Match_Set

# Motor de prueba
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


def test_init_base_secrets(db_session):
    """Test que verifica la inicialización de secretos base."""
    service = DatabaseInitService(db_session)
    
    # Verificar que no hay secretos inicialmente
    assert db_session.query(Secret).count() == 0
    
    # Inicializar secretos
    service.init_base_secrets()
    
    # Verificar que se crearon los secretos
    secrets = db_session.query(Secret).all()
    assert len(secrets) == 3
    
    secret_types = [s.type for s in secrets]
    assert Secret_Type.MURDERER in secret_types
    assert Secret_Type.ACCOMPLICE in secret_types
    assert Secret_Type.INNOCENT in secret_types
    
    # Verificar que no se crean duplicados
    service.init_base_secrets()
    assert db_session.query(Secret).count() == 3


def test_init_base_cards(db_session):
    """Test que verifica la inicialización de cartas base."""
    service = DatabaseInitService(db_session)
    
    # Verificar que no hay cartas inicialmente
    assert db_session.query(Card).count() == 0
    
    # Inicializar cartas
    service.init_base_cards()
    
    # Verificar que se crearon las cartas
    cards = db_session.query(Card).all()
    assert len(cards) > 0
    
    # Verificar que se crearon todos los tipos de cartas
    card_types = {c.type for c in cards}
    assert Card_Type.INSTANT in card_types
    assert Card_Type.DETECTIVE in card_types
    assert Card_Type.EVENT in card_types
    assert Card_Type.DEVIOUS in card_types
    
    # Verificar algunas cartas específicas
    card_names = [c.name for c in cards]
    assert "NOT SO FAST" in card_names
    assert "HERCULE POIROT" in card_names
    assert "MISS MARPLE" in card_names
    
    # Verificar que no se crean duplicados
    service.init_base_cards()
    assert db_session.query(Card).count() == len(cards)


def test_init_all_data(db_session):
    """Test que verifica la inicialización de todos los datos."""
    service = DatabaseInitService(db_session)
    
    # Verificar estado inicial
    assert db_session.query(Secret).count() == 0
    assert db_session.query(Card).count() == 0
    
    # Inicializar todos los datos
    service.init_all_data()
    
    # Verificar que se crearon secretos y cartas
    assert db_session.query(Secret).count() == 3
    assert db_session.query(Card).count() > 0


def test_init_data_function(db_session):
    """Test que verifica la función de conveniencia init_data."""
    # Verificar estado inicial
    assert db_session.query(Secret).count() == 0
    assert db_session.query(Card).count() == 0
    
    # Usar la función de conveniencia
    init_data(db_session)
    
    # Verificar que se crearon secretos y cartas
    assert db_session.query(Secret).count() == 3
    assert db_session.query(Card).count() > 0