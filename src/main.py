from sqlalchemy.orm import Session
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.db import Base, engine
from app.database.init_service import init_data
from app.player.endpoints import player_router
from app.matches.endpoints import router as matches_router
from websocketManager.ws_routes import websocket_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # o ["*"] para todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(websocket_router)
app.include_router(player_router)
app.include_router(matches_router)

Base.metadata.create_all(bind=engine)

# Inicializar datos base
with Session(engine) as session:
    init_data(session)