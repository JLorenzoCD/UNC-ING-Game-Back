import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import uuid

# --- Importa las cosas de tu app ---
from main import app, populate_initial_data # (Usa el nombre corregido)
from app.models.db import get_db, Base
from app.cards.models import Card, Card_Type
from app.secrets.models import Secret, Secret_Type

# (Esto es copiado de tu 'app/matches/tests/conftest.py')
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

# --- ¡LA FIXTURE! ---
# (La nombramos 'db' para que coincida con tus tests de 'events')
@pytest.fixture
def db():
    """Fixture que provee una sesión de base de datos de prueba"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # --- ¡LLAMAMOS A LA FUNCIÓN DE INIT! ---
    # (Usamos la sesión de test para poblar la BBDD en memoria)
    # (¡Esto arregla el 'init_data() takes 0 positional arguments but 1 was given'!)
    
    # (Tenemos que "falsear" el 'init_data' de main.py
    #  o, mejor, hacer que nuestro 'init_data' local funcione)
    
    # Vamos a usar la sesión local para 'init_data'
    try:
        # (Aquí replicamos la lógica de 'populate_initial_data'
        #  para la BBDD de test en memoria)
        if not session.query(Secret).first():
            session.add_all([
                Secret(id=uuid.uuid4(), type="MURDERER", content="You are the Murderer!"),
                # ... (etc)
            ])
            session.commit()
        if not session.query(Card).first():
            session.add_all([
                Card(id=uuid.uuid4(), name="NOT SO FAST", type=Card_Type.INSTANT, description="..."),
                # ... (etc)
            ])
            session.commit()
    
        yield session
        
    finally:
        session.close()
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