from fastapi import FastAPI
from websocketManager.ws_routes import websocket_router
from sqlalchemy.orm import Session
import uuid

from app.models.db import engine

from app.matches.endpoints import router as matches_router

from app.matches.models import Match, Match_Player
from app.player.models import Player
from app.cards.models import Card, Match_Card
from app.secrets.models import Secret, Match_Secret

from app.models.db import Base, engine

app = FastAPI()
app.include_router(websocket_router)
app.include_router(matches_router)

def init_data():
    with Session(engine) as session:
        # Verificar si ya existen secretos
        if not session.query(Secret).first():
            session.add_all([
                Secret(id=uuid.uuid4(), type="INNOCENT", content="You are Innocent!"),
                Secret(id=uuid.uuid4(), type="MURDERER", content="You are the Murderer!"),
                Secret(id=uuid.uuid4(), type="ACCOMPLICE", content="You are the Accomplice!")
            ])
            session.commit()
        if not session.query(Card).first():
            pass

Base.metadata.create_all(bind=engine)
init_data()

# Aca tendriamos que llamar a una funcion que inicialice todos los datos (cartas,secretos,etc)

