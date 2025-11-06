import asyncio
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timezone, datetime

from app.models.db import session_local

from app.events.models import EventosDeTurno, EventStatus
from app.events.services import EventService


from websocketManager.ws_routes import manager

from websocketManager.ws_messages import WSEvent, make_ws_message 

async def event_resolver_loop():
    """
    Esto va a correr el worker de fondo infinitamente
    Revisa la BBDD cada segundo y resuelve eventos pendientes.
    """
    print("Iniciando Worker de Resolución de Eventos...")
    
    while True:
        await asyncio.sleep(1) 
        
        db: Session = session_local()
        event_service = EventService(db)
        
        try:     
            events_to_resolve = db.query(EventosDeTurno).filter(
                EventosDeTurno.status == EventStatus.PENDING.value,
                EventosDeTurno.resolve_at <= datetime.now(timezone.utc)
            ).all() 
            if not events_to_resolve:
                print("No hay eventos para resolver")
            for event in events_to_resolve:
                #verifica si se va a ejecutar el evento o no
                if event.nsf_count % 2 == 0:
                    #hay nsf_count par se ejecuta
                    try:
                        #llamo al handler del evento
                        result_payload = event_service.resolve_event(event)

                        #marcar como resuelto el evento
                        event.status = EventStatus.RESOLVED.value
                        db.commit()

                        #avisar que se ejecuto el evento
                        if result_payload:
                            await manager.specificBroadcast(
                                make_ws_message(WSEvent.CARD_EVENT, result_payload),
                                event.match_id
                            )
                        
                    except Exception as e:
                        #resolve event fallo, no deberia pasar bajo ningun concepto pero podria cancelarlo al evento si se rompe algo, o crear un failed
                        db.rollback()
                        print("Ejecucion del evento fallo")
                        print(e)
                        event.status = EventStatus.CANCELLED.value
                        db.commit()

                """
                else:
                    #marcar como cancelado el evento
                    event.status = EventStatus.CANCELLED
                    db.commit()
                    
                    #falta toda la implementacion
                """
        
        except Exception as e:
            print(f"Error crítico en el bucle de resolución: {e}")
            db.rollback()
        finally:
            db.close()