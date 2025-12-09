import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database.init_service import init_data
from app.events.worker import event_resolver_loop
from app.matches.endpoints import router as matches_router
from app.models.db import Base, engine
from app.player.endpoints import player_router
from websocketManager.ws_routes import websocket_router


def init_data_total():
    """Init data total."""
    with Session(engine) as session:
        init_data(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja los eventos de startup y shutdown.
    """
    print("Iniciando servidor")
    Base.metadata.create_all(bind=engine)
    init_data_total()
    print("Worker trabajando en segundo plano")
    asyncio.create_task(event_resolver_loop())
    yield
    print("Apagando servidor")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(websocket_router)
app.include_router(player_router)
app.include_router(matches_router)
