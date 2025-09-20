from fastapi import FastAPI
from websocketManager.ws_routes import websocket_router
from app.models.db import Base, engine

app = FastAPI()
app.include_router(websocket_router)
Base.metadata.create_all(bind=engine)
# Aca tendriamos que llamar a una funcion que inicialice todos los datos (cartas,secretos,etc)
