# FastAPI App

Este proyecto utiliza **FastAPI** como framework web y **Uvicorn** como servidor ASGI.

## Requisitos

- Python 3.8+
- FastAPI
- Uvicorn

Puedes instalar las dependencias ubicandote en el root del proyecto y ejecutar:

```bash
pip install -r requirements.txt
```

## Ejecutar el servidor

El archivo principal de la aplicación está en `src/main.py`.

Para iniciar el servidor en modo desarrollo, ejecuta:

```bash
uvicorn src.main:app --reload
```

- `--reload`: reinicia el servidor automáticamente al detectar cambios en el código.  
- La aplicación quedará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Endpoints automáticos

FastAPI genera automáticamente documentación interactiva:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
