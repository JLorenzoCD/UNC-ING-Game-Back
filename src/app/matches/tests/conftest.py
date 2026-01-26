import uuid
from enum import Enum
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cards.models import Card, Card_Type
from app.models.db import Base, get_db
from app.secrets.models import Secret, Secret_Type
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client(db_session):
    """Fixture que provee un cliente de prueba con DB mockeada"""

    def override_get_db_with_session():
        """Override get db with session."""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db_with_session
    from websocketManager.ws_routes import manager

    def test_db_session_factory():
        """Test db session factory."""
        return db_session

    manager.set_db_session_factory(test_db_session_factory)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    from app.models.db import session_local

    manager.set_db_session_factory(session_local)


@pytest.fixture
def db_session():
    """Fixture que provee una sesión de base de datos de prueba"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def jsonable_encoder(obj):
    """Convierte un objeto (Pydantic model, etc.) a un dict serializable a JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: jsonable_encoder(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonable_encoder(v) for v in obj]
    if isinstance(obj, (str, int, float, type(None))):
        return obj
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)


def override_get_db():
    """Override get db."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def setup_match_and_players(client, db_session):
    """Configuración común: crea match, players y cartas"""
    response = client.post(
        "/players",
        json={"name": "Owner Player", "avatar": "avatar1",
              "birthday": "2000-01-01"},
    )
    assert response.status_code == 201
    owner = response.json()
    owner_id = uuid.UUID(owner["id"])
    match_post = {
        "name": "Test Match",
        "min_players": 2,
        "max_players": 6,
        "owner_id": owner["id"],
    }
    response = client.post("/matches", json=match_post)
    assert response.status_code == 201
    match = response.json()
    match_id = uuid.UUID(match["id"])
    response = client.post(
        "/players",
        json={"name": "Player Two", "avatar": "avatar2",
              "birthday": "2000-02-02"},
    )
    assert response.status_code == 201
    player2 = response.json()
    player2_id = uuid.UUID(player2["id"])
    response = client.post(
        f"/matches/{match['id']}/join", params={"player_id": player2["id"]}
    )
    assert response.status_code == 200
    cards = [
        Card(
            id=uuid.UUID("d572ba5c-20b8-4ee0-8bf5-f792887b0073"),
            name="NOT SO FAST",
            type=Card_Type.INSTANT,
            description="Instant card",
        ),
        Card(
            id=uuid.UUID("a95eebac-9c02-4ea0-99fd-5bde7882ac79"),
            name="PARKER PYNE",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("d314be48-bbd2-4093-b53f-4715515f6dd7"),
            name="LADY EILEEN",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("7c4e65ec-4d73-43e2-bc46-e04c2eea5dc4"),
            name="TOMMY BERESFORD",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("0092e2f1-78ee-4da7-8acb-1568c212d8c2"),
            name="TUPPENCE BERESFORD",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("7531f174-7099-42dc-86f2-dd5aaccaa9af"),
            name="HARLEY QUIN WILDCARD",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("8d5ddb79-4e52-4386-9a54-9f65664d67dc"),
            name="ARIADNE OLIVER",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("f69ae2be-71a1-4248-a5ad-3293839a7ea7"),
            name="HERCULE POIROT",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("527aefd2-5580-4b25-9ff1-20c5a10eb5dc"),
            name="MISS MARPLE",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("d71ca59e-451f-42f1-a7f0-1d3e2fef72d3"),
            name="MR SATTERTHWAITE",
            type=Card_Type.DETECTIVE,
            description="Detective card",
        ),
        Card(
            id=uuid.UUID("8ba1f702-dba4-4486-aff9-b18a8849b7ae"),
            name="CARDS OFF THE TABLE",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("7cd5bf6d-de4b-4173-aef8-c611c30dbca5"),
            name="ANOTHER VICTIM",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("d9b822e5-1092-49e4-9f13-59369b40a6c2"),
            name="DEAD CARD FOLLY",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("62918044-f5e5-4380-91ba-4a3eacabc550"),
            name="LOOK INTO THE ASHES",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("3eda241c-c47e-470d-832f-637f5cf635eb"),
            name="CARD TRADE",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("fefb72eb-12e4-4406-983e-8facccf3e4ca"),
            name="AND THEN THERE WAS ONE MORE",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("a4574f49-e28f-4c94-8a4e-b50d92448ae1"),
            name="DELAY THE MURDERER ESCAPE",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("70318b8d-62b4-4f76-bf30-4a183b35b354"),
            name="EARLY TRAIN TO PADDINGTON",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("c6a66530-b11c-4eb7-8d1f-c84a261252e5"),
            name="POINT YOUR SUSPICIONS",
            type=Card_Type.EVENT,
            description="Event card",
        ),
        Card(
            id=uuid.UUID("43322138-0471-4beb-a00c-0089758f261e"),
            name="BLACKMAILED",
            type=Card_Type.DEVIOUS,
            description="Devious card",
        ),
        Card(
            id=uuid.UUID("6dac86f0-0e23-499f-993a-40460d7fa090"),
            name="SOCIAL FAUX PAS",
            type=Card_Type.DEVIOUS,
            description="Devious card",
        ),
    ]
    db_session.add_all(cards)
    db_session.commit()
    secrets = [
        Secret(
            id=uuid.uuid4(), type=Secret_Type.MURDERER, content="You are the Murderer!"
        ),
        Secret(
            id=uuid.uuid4(),
            type=Secret_Type.ACCOMPLICE,
            content="You are the Accomplice!",
        ),
        Secret(id=uuid.uuid4(), type=Secret_Type.INNOCENT,
               content="You are Innocent!"),
    ]
    if not db_session.query(Secret).first():
        db_session.add_all(secrets)
        db_session.commit()
    return {
        "match_id": match_id,
        "match_str_id": match["id"],
        "match": match,
        "owner_id": owner_id,
        "owner_str_id": owner["id"],
        "player2_id": player2_id,
        "player2_str_id": player2["id"],
        "cards": cards,
        "secrets": secrets,
    }
