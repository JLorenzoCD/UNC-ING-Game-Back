from fastapi import FastAPI
from websocketManager.ws_routes import websocket_router
from app.matches.endpoints import router as matches_router
from app.matches.models import Match, Match_Player
from app.player.models import Player
from app.cards.models import Card, Match_Card
from app.secrets.models import Secret, Match_Secret
from app.models.db import Base, engine

app = FastAPI()
app.include_router(websocket_router)
app.include_router(matches_router)
Base.metadata.create_all(bind=engine)

# Aca tendriamos que llamar a una funcion que inicialice todos los datos (cartas,secretos,etc)

