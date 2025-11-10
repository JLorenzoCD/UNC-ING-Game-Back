import asyncio
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timezone, datetime

from app.models.db import session_local

from app.events.models import EventosDeTurno, EventStatus
from app.events.services import EventService

from app.matches import services as services_match

from app.cards.services import Card_event
from app.cards import services as card_services
from app.cards.utils import db_match_card_2_match_card_schema

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
                        if card_services.Cards_Services(db).is_complex_event(event.event_type):
                            event.status = EventStatus.PENDING_TARGET_RESPONSE.value
                            db.commit()
                            if (event.event_type==Card_event.CARD_TRADE.value):
                                payload = {
                                    "event_type": event.event_type,
                                    "event_id": event.id,
                                    "players_ids":[event.player_id,event.payload['target_player_id']]
                                }
                            else:
                                    ids=[]
                                    for mp in services_match.MatchService(db).get_players_from_match(event.match_id):
                                        ids.append(mp.player_id)
                                    payload = {
                                    "event_type": event.event_type,
                                    "event_id": event.id,
                                    "players_ids":ids
                                }
                            await manager.specificBroadcast(
                                make_ws_message(WSEvent.PENDING_TARGET_RESPONSE, payload),
                                event.match_id
                            )
                        else:
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
                        payload = {
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "message": "Error in the execution of event"
                        }
                        await manager.specificBroadcast(
                            make_ws_message(WSEvent.EVENT_CANCELLED, payload),
                            event.match_id
                        )
                else:
                    #marcar como cancelado el evento
                    event.status = EventStatus.CANCELLED.value
                    db.commit()


                    payload = {
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "message": "Event was cancelled by Not So Fast",
                        "discarded_card": None,
                    }
                    await manager.specificBroadcast(
                        make_ws_message(WSEvent.EVENT_CANCELLED, payload),
                        event.match_id
                    )
        
        except Exception as e:
            print(f"Error crítico en el bucle de resolución: {e}")
            db.rollback()
        finally:
            db.close()