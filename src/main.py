from fastapi import FastAPI
from app.models.db import Base, engine

app = FastAPI()


Base.metadata.create_all(bind=engine)

# Aca tendriamos que llamar a una funcion que inicialice todos los datos (cartas,secretos,etc)