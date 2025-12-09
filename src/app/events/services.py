import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cards import services as services_cards
from app.cards.services import Card_event
from app.cards.utils import db_match_card_2_match_card_schema
from app.events.models import EventosDeTurno, EventStatus
from app.matches import services as services_matches
from app.piles.service import PileService
from app.secrets import models as secret_models
from app.secrets import services as secret_service
from app.secrets.utils import db_match_secret_2_match_secret_schema
from app.sets import models as set_models
from app.sets import services as set_services
from app.sets.utils import db_match_set_2_match_set_schema


class EventService:
    """Class EventService."""

    def __init__(self, db: Session):
        """init  .

        Args:
            db: Parameter db."""
        self._db = db

    def create_event(
        self,
        match_id: uuid.UUID,
        player_id: uuid.UUID,
        event_type_str: str,
        match_card_id: uuid.UUID | None,
        event_payload: dict | None,
        status: EventStatus | None = None,
    ) -> EventosDeTurno:
        """
        Crea la fila del evento en la BBDD.
        No enviar status para eventos cancelables
        Enviar status RESOLVED para eventos no cancelables
        """
        try:
            if status:
                final_status = status.value
            else:
                final_status = EventStatus.PENDING.value
            now_utc = datetime.now(timezone.utc)
            if final_status == EventStatus.PENDING.value:
                resolve_time = now_utc + timedelta(seconds=7)
            else:
                resolve_time = now_utc
            new_event = EventosDeTurno(
                match_id=match_id,
                player_id=player_id,
                event_type=event_type_str,
                match_card_id=match_card_id,
                payload=event_payload,
                status=final_status,
                nsf_count=0,
                resolve_at=resolve_time,
            )
            self._db.add(new_event)
            self._db.commit()
            self._db.refresh(new_event)
            return new_event
        except SQLAlchemyError as e:
            self._db.rollback()
            print(f"Error al crear evento: {e}")
            raise
        except Exception as e:
            self._db.rollback()
            print(f"Error inesperado al crear evento: {e}")
            raise

    def is_event_ready_to_resolve(self, event: EventosDeTurno) -> bool:
        """
        Verifica si se cargo toda la info necesaria para resolver el evento
        """
        event_type = event.event_type
        payload = event.payload
        responses = payload.get("responses", [])
        if event_type == Card_event.CARD_TRADE.value:
            return len(responses) == 2
        else:
            return len(responses) == len(
                services_matches.MatchService(self._db).get_players_from_match(
                    event.match_id
                )
            )

    def resolve_event(self, event: EventosDeTurno) -> dict:
        """
        Handler de eventos. Contiene toda la logica que tenia antes el endpoint. Full BaseDatos, nada de ws
        """
        for prop, valor in vars(event).items():
            print(prop, valor)
        db = self._db
        match_id = event.match_id
        player_id = event.player_id
        match_card_id = event.match_card_id
        event_payload = event.payload if event.payload else {}
        typeEvent = event.event_type
        try:
            match typeEvent:
                case Card_event.CARDS_OFF_THE_TABLE.value:
                    diccionary = services_cards.Cards_Services(db).cards_off_the_table(
                        match_id,
                        event_payload["target_player_id"],
                        player_id,
                        match_card_id,
                    )
                    updated_match_cards = diccionary["discarded_instant_cards"]
                    updated_match_cards_schemas = [
                        db_match_card_2_match_card_schema(card)
                        for card in updated_match_cards
                    ]
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": [
                            card_schema.model_dump(mode="json")
                            for card_schema in updated_match_cards_schemas
                        ],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.ANOTHER_VICTIM.value:
                    updated_set = set_services.SetService(db).steal_set(
                        event_payload["target_set_id"], player_id
                    )
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": updated_set.model_dump(mode="json"),
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.LOOK_INTO_THE_ASHES.value:
                    taken_card = services_cards.Cards_Services(
                        db
                    ).look_into_the_ashes_event(
                        player_id, match_id, event_payload["target_card_id"]
                    )
                    taken_card = db_match_card_2_match_card_schema(taken_card)
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": [taken_card.model_dump(mode="json")],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.AND_THEN_THERE_WAS_ONE_MORE.value:
                    updated_secret = services_cards.Cards_Services(
                        db
                    ).and_then_there_was_one_more_event(
                        event_payload["target_player_id"],
                        event_payload["target_secret_id"],
                    )
                    updated_secret = db_match_secret_2_match_secret_schema(
                        updated_secret
                    )
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": updated_secret.model_dump(mode="json"),
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.DELAY_THE_MURDERER_ESCAPE.value:
                    if len(event_payload["cards_ids"]) > 5:
                        raise ValueError("Se pasaron mas de 5 cartas para retrasar")
                    event.match_card_id = None
                    db.commit()
                    updated_match_cards = services_cards.Cards_Services(
                        db
                    ).delay_the_murderer_escape_event(event_payload["cards_ids"])
                    PileService(db).discard_cards(
                        None, match_id, [match_card_id], delete=True
                    )
                    updated_match_cards_schemas = [
                        db_match_card_2_match_card_schema(card)
                        for card in updated_match_cards
                    ]
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": [
                            card_schema.model_dump(mode="json")
                            for card_schema in updated_match_cards_schemas
                        ],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.EARLY_TRAIN_TO_PADDINGTON.value:
                    try:
                        if (
                            "cards_ids" not in event_payload
                            or not event_payload["cards_ids"]
                        ):
                            raise ValueError(
                                "Se requiere 'cards_ids' con al menos una carta para el evento Early Train to Paddington"
                            )
                        event.match_card_id = None
                        db.commit()
                        discarded_cards = services_cards.Cards_Services(
                            db
                        ).early_train_to_paddington_event(
                            match_id, event_payload["cards_ids"]
                        )
                        PileService(db).discard_cards(
                            None, match_id, [match_card_id], delete=True
                        )
                        serialized_discarded_cards = [
                            mc.model_dump(mode="json") for mc in discarded_cards
                        ]
                        payload = {
                            "type": typeEvent,
                            "updated_match_cards": serialized_discarded_cards,
                            "updated_secret": None,
                            "discarded_card_event": None,
                            "updated_set": None,
                            "message": f"{typeEvent} was succesfull",
                        }
                    except Exception as e:
                        raise e
                case Card_event.CARD_TRADE.value:
                    print("Resolviendo el Card Trade...")
                    responses = event_payload.get("responses", [])
                    if len(responses) != 2:
                        raise ValueError(
                            "Faltan o sobran respuestas para el card_trade"
                        )
                    match_card_id1 = responses[0]
                    match_card_id2 = responses[1]
                    updated_match_cards = services_cards.Cards_Services(
                        db
                    ).swap_cards_owners(match_card_id1, match_card_id2)
                    print(f"Intercambiando {match_card_id1} por {match_card_id2}")
                    updated_match_cards_schemas = [
                        db_match_card_2_match_card_schema(card)
                        for card in updated_match_cards
                    ]
                    updated_match_cards = [
                        mc.model_dump(mode="json") for mc in updated_match_cards_schemas
                    ]
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": updated_match_cards,
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.DEAD_CARD_FOLLY.value:
                    print("Resolviendo el Dead Card Folly...")
                    responses = event_payload.get("responses", [])
                    direction = event_payload.get("direction")
                    updated_match_cards = services_cards.Cards_Services(
                        db
                    ).pass_cards_in_direction(match_id, responses, direction)
                    updated_match_cards_schemas = [
                        db_match_card_2_match_card_schema(card)
                        for card in updated_match_cards
                    ]
                    updated_match_cards = [
                        mc.model_dump(mode="json") for mc in updated_match_cards_schemas
                    ]
                    payload = {
                        "type": typeEvent,
                        "updated_match_cards": updated_match_cards,
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull",
                    }
                case Card_event.POINT_YOUR_SUSPICIONS.value:
                    print("Resolviendo el Point your suspicions...")
                    responses = event_payload.get("responses", [])
                    vote_counts = Counter(responses)
                    most_voted_player = vote_counts.most_common(1)[0][0]
                    payload = {"target_player_id": most_voted_player}
                case t if t in (
                    set_models.SetType.HERCULE_POIROT.value,
                    set_models.SetType.MISS_MARPLE.value,
                    set_models.SetType.PARKER_PYNE.value,
                ):
                    try:
                        if typeEvent in (
                            set_models.SetType.HERCULE_POIROT.value,
                            set_models.SetType.MISS_MARPLE.value,
                        ):
                            target_secret = secret_service.Secrets_Services(
                                db
                            ).update_secret(
                                secret_models.Secret_action.REVEAL,
                                uuid.UUID(event_payload["target_secret_id"]),
                                uuid.UUID(event_payload["target_player_id"]),
                            )
                            match_secret_out = db_match_secret_2_match_secret_schema(
                                target_secret
                            )
                        if typeEvent == set_models.SetType.PARKER_PYNE.value:
                            target_secret = secret_service.Secrets_Services(
                                db
                            ).update_secret(
                                secret_models.Secret_action.HIDE,
                                uuid.UUID(event_payload["target_secret_id"]),
                                uuid.UUID(event_payload["target_player_id"]),
                            )
                            match_secret_out = db_match_secret_2_match_secret_schema(
                                target_secret
                            )
                        payload = match_secret_out.model_dump(mode="json")
                        payload["type"] = typeEvent
                    except Exception as e:
                        raise e
                case t if t in (
                    set_models.SetType.TOMMY_BERESFORD.value,
                    set_models.SetType.TUPPENCE_BERESFORD.value,
                    set_models.SetType.MR_SATTERTHWAITE.value,
                ):
                    payload = {"target_player_id": event_payload["target_player_id"]}
                    payload["type"] = typeEvent
                case set_models.SetType.TWO_BERESFORD.value:
                    payload = {"target_player_id": event_payload["target_player_id"]}
                case set_models.SetType.ADRIADNE_OLIVER.value:
                    payload = {"target_player_id": event_payload["target_player_id"]}
                    payload["type"] = typeEvent
                case set_models.SetType.LADY_EILEEN.value:
                    accion_set = {"target_player_id": event_payload["target_player_id"]}
                    payload = {"accion_set": accion_set, "type": typeEvent}
                    if event_payload["is_create_set"] == True:
                        data = event_payload["set_data"]
                        set_data = {
                            "type": set_models.SetType.LADY_EILEEN,
                            "card_ids": [
                                uuid.UUID(card_id) for card_id in data["card_ids"]
                            ],
                            "player_id": player_id,
                            "target_player_id": uuid.UUID(data["target_player_id"]),
                            "target_secret_id": None,
                            "match_id": match_id,
                        }
                        match_set = set_services.SetService(db).create_set(set_data)
                        match_set_out = db_match_set_2_match_set_schema(match_set)
                        create_payload = match_set_out.model_dump(mode="json")
                        PileService(db).discard_cards(
                            None, match_id, set_data["card_ids"], delete=True
                        )
                        create_payload.update({"deleted_cards": data["card_ids"]})
                        payload["data_set"] = create_payload
                    elif event_payload["is_create_set"] == False:
                        match_set_id = uuid.UUID(event_payload["set_id"])
                        match_set = set_services.SetService(db).get_match_set(
                            match_set_id, match_id
                        )
                        match_set_out = db_match_set_2_match_set_schema(match_set)
                        update_payload = match_set_out.model_dump(mode="json")
                        PileService(db).discard_cards(
                            None, match_id, [match_card_id], delete=True
                        )
                        update_payload.update(
                            {"deleted_cards": [str(uuid) for uuid in data["card_ids"]]}
                        )
                        payload["data_set"] = update_payload
            return payload
        except Exception as e:
            raise e

    def update_event_nsf(self, event_id, nsf_count) -> EventosDeTurno:
        """
        Actualiza el evento aumentandole +1 a la nsf_count y actualizando el resolve_at_time
        """
        try:
            new_resolve_time = datetime.now(timezone.utc) + timedelta(seconds=7)
            update_count = (
                self._db.query(EventosDeTurno)
                .filter(
                    EventosDeTurno.id == event_id,
                    EventosDeTurno.nsf_count == nsf_count,
                    EventosDeTurno.status == EventStatus.PENDING.value,
                )
                .update(
                    {
                        EventosDeTurno.nsf_count: nsf_count + 1,
                        EventosDeTurno.resolve_at: new_resolve_time,
                    },
                    synchronize_session=False,
                )
            )
            self._db.commit()
            if update_count == 1:
                updated_event = (
                    self._db.query(EventosDeTurno)
                    .filter(EventosDeTurno.id == event_id)
                    .first()
                )
                return updated_event
            else:
                raise ValueError(
                    "Event_id no encontrado, ventana de tiempo terminado o alguien ya jugo not so fast"
                )
        except SQLAlchemyError:
            self._db.rollback()
            raise
        except Exception:
            self._db.rollback()
            raise

    def update_info_event(
        self, event_id: uuid.UUID, player_id: uuid.UUID, info_from_endpoint: uuid.UUID
    ) -> EventosDeTurno:
        """
        "Pushea" la respuesta de un jugador al 'payload' del evento.
        """
        try:
            event = self._db.get(EventosDeTurno, event_id)
            if not event:
                raise ValueError("Evento no encontrado")
            if event.status != EventStatus.PENDING_TARGET_RESPONSE.value:
                raise ValueError("El evento no está esperando una respuesta.")
            current_payload = event.payload if event.payload else {}
            responses_list = current_payload.get("responses", [])
            new_responses_list = responses_list.copy()
            new_responses_list.append(str(info_from_endpoint))
            new_payload = current_payload.copy()
            new_payload["responses"] = new_responses_list
            event.payload = new_payload
            self._db.commit()
            self._db.refresh(event)
            print(f"Respuesta de {player_id} añadida al evento {event.id}")
            return event
        except (SQLAlchemyError, ValueError) as e:
            self._db.rollback()
            print(f"Error al actualizar info del evento: {e}")
            raise e
