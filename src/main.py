from fastapi import FastAPI
from ws_routes import websocket_router

app = FastAPI()

app.include_router(websocket_router)