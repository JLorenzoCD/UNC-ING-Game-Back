# FastAPI App

Este proyecto utiliza **FastAPI** como framework web y **Uvicorn** como servidor ASGI.

## Requisitos

- [Python 3.8+](https://www.python.org/downloads/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)


Puedes instalar las dependencias ubicandote en el root del proyecto y ejecutar:

```bash
pip install -r requirements.txt
```

## Ejecutar el servidor

### Iniciar la base de datos
Lo primero que hay que hacer es levantar la imagen de docker que esta en `docker-compose.yml`, para ello ejecuta:

```bash
docker-compose up -d
```
> Nota: El contenedor de PostgreSQL expone el puerto `5433` de tu máquina. Asegúrate de que esté libre, o cambia el puerto en `docker-compose.yml`:

```bash
ports:
  - "5432:5432"
```

### Iniciar el servidor

El archivo principal de la aplicación está en `src/main.py`.

Para iniciar el servidor en modo desarrollo, ejecuta:

```bash
uvicorn main:app --reload
```

- `--reload`: reinicia el servidor automáticamente al detectar cambios en el código.  
- La aplicación quedará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Ejecutar tests con coverage

```bash
coverage run -m pytest -v
coverage report -m
```

## Endpoints automáticos

FastAPI genera automáticamente documentación interactiva:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Documentación de la API

- [Link](https://docs.google.com/spreadsheets/d/1LJp2xAyst-Ixmmdeneowb8IcZy14VmEmFJXy1UkVWSs/edit?usp=sharing)