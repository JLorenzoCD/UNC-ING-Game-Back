import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


from app.events.models import EventosDeTurno

class EventService:
    def __init__(self, db: Session):
        self._db = db

    def create_event(
        self, 
        match_id: uuid.UUID, 
        player_id: uuid.UUID, 
        event_type_str: str,
        match_card_id: uuid.UUID | None,
        event_payload: dict | None
    ) -> EventosDeTurno:
        """
        Crea la fila del evento en la BBDD con un estado PENDING.
        """
        try:
            #solo pasamos los campos que la BBDD no tiene definidos por defecto.
            new_event = EventosDeTurno(
                match_id = match_id,
                player_id = player_id,
                event_type = event_type_str,
                match_card_id = match_card_id,
                payload = event_payload
            )
            
            #por defecto:
            #status = 'Pending', nsf_count = 0, created_at = NOW(), resolve_at = NOW() + 5s
            self._db.add(new_event)
            self._db.commit()
            self._db.refresh(new_event)
            
            print(f"Evento (ID: {new_event.id}) creado: {event_type_str}")
            return new_event

        except SQLAlchemyError as e:
            self._db.rollback()
            print(f"Error al crear evento: {e}")
            raise
        except Exception as e:
            self._db.rollback()
            print(f"Error inesperado al crear evento: {e}")
            raise