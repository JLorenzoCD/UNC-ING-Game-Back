import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import uuid

# --- 1. ¡IMPORTA LOS NOMBRES CORRECTOS DE 'main.py'! ---
from main import app, init_data_total 

from app.models.db import get_db, Base
# (El resto de tus imports de modelos si 'init_data_total' no los trae)

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# --- 2. ¡DEFINIMOS EL FIXTURE 'db'! ---
# (Tus tests en 'test_events_services.py' están pidiendo 'db')
@pytest.fixture
def db():
    """
    Fixture que provee una sesión de base de datos de prueba
    (scope 'function', se borra después de cada test)
    """
    # 1. Crea las tablas (¡incluyendo eventos_de_turno!)
    Base.metadata.create_all(bind=engine)
    
    # 2. Llama a tu función de init
    init_data_total() 
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Borra todo para el próximo test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db: Session): # ¡Hacemos que 'client' dependa de 'db'!
    """Fixture que provee un cliente de prueba con DB mockeada"""
    def override_get_db_with_session():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db_with_session
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()