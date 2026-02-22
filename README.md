# Backend - "Agatha Christie's Death on the Cards" game

Este proyecto utiliza **FastAPI** como framework web y **Uvicorn** como servidor ASGI.

## Requisitos

- [Python 3.8+](https://www.python.org/downloads/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Primero se clona el repositorio y luego podes instalar las dependencias ubicandote en el root del proyecto y ejecutar:

```bash
# Se recomienda crear un entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalación de los paquetes
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

Para detener y borrar los datos del contenedor:
```bash
docker-compose down -v
```

### Iniciar el servidor

El archivo principal de la aplicación está en `src/main.py`.

Para iniciar el servidor en modo desarrollo, ejecuta:

```bash
cd src
uvicorn main:app --reload
```

- `--reload`: reinicia el servidor automáticamente al detectar cambios en el código.
- La aplicación quedará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Ejecutar tests

```bash
# Se tiene que tener el contenedor docker levantado
docker-compose up -d

pytest
```

Coverage
```bash
# Se tiene que tener el contenedor docker levantado
docker-compose up -d

coverage run -m pytest -v
coverage report -m
```

## Endpoints automáticos

FastAPI genera automáticamente documentación interactiva:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)


## Detalles del desarrollo

Este proyecto frontend fue realizado por un equipo de 3 integrantes durante el
curso de la materia **Ingeniería del Software 1 - FAMAF - UNC 🏛️**, se realizaron
3 sprints, los cuales detallare ahora y luego un trabajo individual para tratar
de pulirlo y terminar los requerimientos originales que nos dio la cátedra.

### Sprint 1 - 11/09 a 29/09

1. Crear Partida (pública)
2. Listar Partidas
3. Unirse a Partida
4. Iniciar Partida
5. Obtener Cartas
6. Obtener secretos
7. Ver mis cartas
8. Ver Mazos regular y descarte
9. Ver Secretos
10. Ver información del turno actual
11. No ejecutar acción (seleccionable por el jugador)
12. Seleccionar y descartar
13. Reponer del mazo regular
14. Descarte obligatorio
15. Terminar turno
16. Ganar (por ﬁn de mazo)

### Sprint 2 - 02/10 a 21/10

Pendientes del **Sprint 1**:

11. No ejecutar acción (seleccionable por el jugador)
12. Seleccionar y descartar
13. Reponer del mazo regular
14. Descarte obligatorio
15. Terminar turno
16. Ganar (por ﬁn de mazo)

Nuevos:

1. Ver mazo draft (tope de 3 cartas)
2. Ver primeras cartas del mazo (descarte) de manera privada
3. Jugar Set
4. Ver Sets
5. Robar set
6. Revelar Secreto
7. Ocultar Secreto
8. Seleccionar Jugador
9. Robar Secreto
10. Jugar Eventos:
    - Cards off the table
    - Another Victim
    - Look Into The Ashes
    - And Then There Was One More
    - Delay The Murderer Escape
    - Early Train To Paddington

11. Entrar / Salir / Jugar en desgracia social
12. Ganar por revelar asesino
13. Cancelar partida (no iniciada - owner)
14. Abandonar partida (no iniciada - player)
15. Mantener estado de partida (poder hacer f5)
16. Listar mis partidas activas
17. Entrar a partida activa

### Sprint 3 - 23/10 a 11/11

Pendientes del **Sprint 2**:

11. Entrar / Salir / Jugar en desgracia social
12. Cancelar partida (no iniciada - owner)
13. Abandonar partida (no iniciada - player)
14. Mantener estado de partida (poder hacer f5)
15. Listar mis partidas activas
16. Entrar a partida activa

Nuevos:

1. Crear partida con contraseña.
2. Unirse a partida con contraseña
3. Buscar partidas por nombre
4. Ordenar partidas por cantidad de jugadores
5. Implementar temporizador de turnos, con descarte obligatorio en caso de
   llegar al final del tiempo.
6. Ver eventos de partida: tener un log de cada evento que ocurre durante la
   partida, para que todos los jugadores estén al tanto de lo que ocurre (”Jugador
   A bajo un set”).
7. Ver estado actual de jugador (”Debes seleccionar un set”, “Esperando que
   Jugador B seleccione un secreto”, etc). UI que indica la acción que se está
   ejecutando.
8. Chat entre jugadores (general, no 1-1)
9. Enviar carta a otro jugador / intercambiar cartas
10. Mostrar secreto de forma privada entre dos jugadores
11. Cancelar acción (si la acción es cancelable)
12. Bajar detective a set existente propio (debe ejecutar efecto)
13. Recibir carta devious (releer las reglas respecto a la utilización de esta
    carta)
14. Ganar por desgracia social (todos los jugadores menos el asesino entran en
    desgracia social)
15. Jugar Eventos:
    - Not So Fast
    - Point Your Suspicions
    - Dead Card Folly
    - Card Trade

### Lo que termine yo solo:

Sprint 1:

1. Ganar (por ﬁn de mazo): BUG - En un caso borde, donde quedaban 1, 2 o 3 cartas
   en el mazo regular y se jugaba una carta de evento **Early Train To Paddington**,
   el cual pasa 3 cartas del mazo regular al de descarte, no se finalizaba la partida
   de la forma esperada.

Sprint 2:

15. Mantener estado de partida (poder hacer f5): BUG - En ciertos eventos, al apretar
    F5 durante la mitad del mismo, no recuperaba correctamente el estado de la partida.
16. Listar mis partidas activas: No se había implementado.
17. Entrar a partida activa: No se había implementado la forma de hacerlo fácilmente
    para el jugador (solo se podia si se tenia la url)

Sprint 3:

1. Crear partida con contraseña: No se había implementado.
2. Unirse a partida con contraseña: No se había implementado.
3. Buscar partidas por nombre: No se había implementado.
4. Ordenar partidas por cantidad de jugadores: Finalmente no se implemento.
5. Implementar temporizador de turnos, con descarte obligatorio en caso de llegar
   al final del tiempo: BUG - Faltaban de logear algunos eventos, y por la forma en
   la que se implemento este, termino ocasionando que el timer no funcionara correctamente.
6. Ver eventos de partida: Faltaba logear eventos.
7. Chat entre jugadores (general, no 1-1): No se había implementado, para ello
   reutilize los logs del sistema para convertirlos a mensajes del sistema y de los
   jugadores.
8. Recibir carta devious (releer las reglas respecto a la utilización de esta
   carta): No se había implementado.

Extra:

- Termine refactorizando bastante el backend, ya que a diferencia del grupo de
  frontend (en el que estaba), no había nadie con experiencia en el backend, lo que
  termino haciendo que no aya un formato establecido y las formas de hacer las cosas
  era algo variada, dificultando la lectura del código, su mantenimiento y extension.
  Lo cual me sirvió bastante para entender como funciona el backend.

# Créditos

Trabajo realizado para la materia Ingeniería del Software 1 - FAMAF - UNC 🏛️. El
mismo fue realizado por un equipo de 6 integrantes, los cuales decidimos separarnos
en 2 grupos, Frontend y BackEnd, de 3 integrantes cada uno.