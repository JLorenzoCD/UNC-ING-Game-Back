import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cards import services as card_services
from app.cards.models import Match_Card
from app.cards.services import Card_event
from app.cards.utils import db_match_card_2_match_card_schema
from app.events.models import EventosDeTurno, EventStatus
from app.events.services import EventService
from app.matches import services as match_services
from app.matches.ending import MatchEndedReason, handle_match_ended
from app.models.db import session_local
from app.secrets import services as secret_service
from app.sets.models import SetType
from websocketManager.ws_messages import WSEvent, make_ws_message
from websocketManager.ws_routes import manager

from app.logs.service import LogService
from app.matches.models import MatchEventType
from app.piles.service import PileService


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
            events_to_resolve = (
                db.query(EventosDeTurno)
                .filter(
                    EventosDeTurno.status == EventStatus.PENDING.value,
                    EventosDeTurno.resolve_at <= datetime.now(timezone.utc),
                )
                .all()
            )
            for event in events_to_resolve:
                if event.nsf_count % 2 == 0:
                    try:
                        if card_services.Cards_Services(db).is_complex_event(
                            event.event_type
                        ):
                            event.status = EventStatus.PENDING_TARGET_RESPONSE.value
                            db.commit()
                            if event.event_type == Card_event.CARD_TRADE.value:
                                payload = {
                                    "event_type": event.event_type,
                                    "event_id": event.id,
                                    "players_ids": [
                                        event.player_id,
                                        event.payload["target_player_id"],
                                    ],
                                }
                            else:
                                ids = []
                                for mp in match_services.MatchService(
                                    db
                                ).get_players_from_match(event.match_id):
                                    ids.append(mp.player_id)
                                payload = {
                                    "event_type": event.event_type,
                                    "event_id": event.id,
                                    "players_ids": ids,
                                }
                            await manager.specificBroadcast(
                                make_ws_message(
                                    WSEvent.PENDING_TARGET_RESPONSE, payload
                                ),
                                event.match_id,
                            )
                        else:
                            result_payload = event_service.resolve_event(event)
                            event.status = EventStatus.RESOLVED.value
                            db.commit()
                            if result_payload:
                                if result_payload.get("type") in [
                                    e.value for e in Card_event
                                ]:
                                    await manager.specificBroadcast(
                                        make_ws_message(
                                            WSEvent.CARD_EVENT, result_payload
                                        ),
                                        event.match_id,
                                    )
                                    if (
                                        result_payload.get("type")
                                        == Card_event.EARLY_TRAIN_TO_PADDINGTON.value
                                        and PileService(
                                            db
                                        ).get_count_cards_pile(event.match_id)
                                        <= 3
                                    ):
                                        await handle_match_ended(
                                            db,
                                            manager,
                                            event.match_id,
                                            MatchEndedReason.DECK_FINISHED,
                                        )
                                elif result_payload.get("type") in (
                                    SetType.HERCULE_POIROT.value,
                                    SetType.MISS_MARPLE.value,
                                    SetType.PARKER_PYNE.value,
                                ):
                                    await manager.specificBroadcast(
                                        make_ws_message(
                                            WSEvent.SECRET, result_payload),
                                        event.match_id,
                                    )
                                    try:
                                        if event.event_type in [
                                            SetType.HERCULE_POIROT.value,
                                            SetType.MISS_MARPLE.value,
                                        ]:
                                            res = secret_service.Secrets_Services(
                                                db
                                            ).is_murderer_revealed(event.match_id)
                                            if res:
                                                await handle_match_ended(
                                                    db,
                                                    manager,
                                                    event.match_id,
                                                    MatchEndedReason.MURDERER_REVEALED,
                                                )
                                            elif secret_service.Secrets_Services(
                                                db
                                            ).is_everyone_in_social_disgrace(
                                                event.match_id
                                            ):
                                                await handle_match_ended(
                                                    db,
                                                    manager,
                                                    event.match_id,
                                                    MatchEndedReason.SOCIAL_DISGRACE,
                                                )
                                    except Exception as e:
                                        raise HTTPException(
                                            status_code=400, detail=str(e)
                                        )
                                elif (
                                    result_payload.get("type")
                                    == SetType.LADY_EILEEN.value
                                ):
                                    data_set = result_payload["data_set"]
                                    data_set_payload = make_ws_message(
                                        WSEvent.SET, data_set
                                    )
                                    await manager.specificBroadcast(
                                        data_set_payload, event.match_id
                                    )
                                    data_accion = result_payload["accion_set"]
                                    await manager.specificBroadcast(
                                        make_ws_message(
                                            WSEvent.PLAYER_SECRET_REVEAL, data_accion
                                        ),
                                        event.match_id,
                                    )
                                else:
                                    await manager.specificBroadcast(
                                        make_ws_message(
                                            WSEvent.PLAYER_SECRET_REVEAL, result_payload
                                        ),
                                        event.match_id,
                                    )

                        try:
                            log_message = f"[EVENT] El evento '{event.event_type.capitalize()}' no fue cancelado"
                            await LogService(db).create_and_propagate_log(event.match_id, log_message, MatchEventType.NOT_SO_FAST, event.player_id)
                        except Exception as e:
                            print(
                                f"[LOG] error creando/broadcast log de worker-played: {e}")

                    except Exception as e:
                        db.rollback()
                        print("Ejecucion del evento fallo")
                        print(e)
                        event.status = EventStatus.CANCELLED.value
                        db.commit()
                        payload = {
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "message": "Error in the execution of event",
                        }
                        await manager.specificBroadcast(
                            make_ws_message(WSEvent.EVENT_CANCELLED, payload),
                            event.match_id,
                        )
                else:
                    event.status = EventStatus.CANCELLED.value
                    db.commit()
                    payload = {}
                    if event.event_type in [e.value for e in Card_event]:
                        PileService(db).discard_cards(
                            None, event.match_id, [event.match_card_id], delete=False
                        )
                        discarded_card = (
                            db.query(Match_Card)
                            .filter(Match_Card.id == event.match_card_id)
                            .first()
                        )
                        discarded_card_schema = db_match_card_2_match_card_schema(
                            discarded_card
                        )
                        payload = {
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "message": "Event was cancelled by Not So Fast",
                            "discarded_card": discarded_card_schema.model_dump(
                                mode="json"
                            ),
                        }
                    elif event.event_type in [e.value for e in SetType]:
                        payload = {
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "message": "Event was cancelled by Not So Fast",
                        }

                    await manager.specificBroadcast(
                        make_ws_message(WSEvent.EVENT_CANCELLED, payload),
                        event.match_id,
                    )

                    try:
                        log_message = f"[EVENT] El evento '{event.event_type.capitalize()}' fue cancelado por una carta 'NOT SO FAST...'"
                        await LogService(db).create_and_propagate_log(event.match_id, log_message, MatchEventType.NOT_SO_FAST, event.player_id)
                    except Exception as e:
                        print(
                            f"[LOG] error creando/broadcast log de worker-canceled: {e}")
        except Exception as e:
            print(f"Error crítico en el bucle de resolución: {e}")
            db.rollback()
        finally:
            db.close()
