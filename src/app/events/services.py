import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Integer, ForeignKey, Enum, String, TIMESTAMP, DateTime, text
from sqlalchemy.sql import func

from app.events.models import EventosDeTurno
from collections import Counter

from datetime import datetime, timezone,timedelta
#para el resolver
from app.events.models import EventosDeTurno, EventStatus
from app.cards.services import Card_event
from app.cards import services as services_cards
from app.matches import services as services_matches
from app.secrets import services as services_secrets
from app.cards.utils import db_match_card_2_match_card_schema
from app.secrets.utils import db_match_secret_2_match_secret_schema
from app.sets import services as set_services


class EventService:
    def __init__(self, db: Session):
        self._db = db

    def create_event(
        self, 
        match_id: uuid.UUID, 
        player_id: uuid.UUID, 
        event_type_str: str,
        match_card_id: uuid.UUID | None,
        event_payload: dict | None,
        status: EventStatus | None = None
    ) -> EventosDeTurno:
        """
        Crea la fila del evento en la BBDD.
        No enviar status para eventos cancelables
        Enviar status RESOLVED para eventos no cancelables
        """
        print("createEvent")
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
                match_id = match_id,
                player_id = player_id,
                event_type = event_type_str,
                match_card_id = match_card_id,
                payload = event_payload,

                #no por defecto
                status =final_status,
                nsf_count=0,
                resolve_at = resolve_time
            )

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

    def update_event_nsf(
        self,
        event_id,
        nsf_count
    ) -> EventosDeTurno:
        """
        Actualiza el evento aumentandole +1 a la nsf_count y actualizando el resolve_at_time
        """
        try:
            print("antes de hacer la consulta")
            new_resolve_time = datetime.now(timezone.utc) + timedelta(seconds=7)
            #query atomica para que no haya condiciones de carrera(2 players o mas jueguen al mismo tiempo)
            update_count = self._db.query(EventosDeTurno).filter(
                EventosDeTurno.id == event_id,
                EventosDeTurno.nsf_count == nsf_count,
                EventosDeTurno.status == EventStatus.PENDING.value
            ).update({
                EventosDeTurno.nsf_count: nsf_count + 1,
                EventosDeTurno.resolve_at: new_resolve_time
                }, synchronize_session=False)
            self._db.commit()
            print(f"El update_count: {update_count}")


            if update_count==1:
                print(f"Evento actualizado por NSF")
                updated_event = self._db.query(EventosDeTurno).filter(
                    EventosDeTurno.id == event_id
                ).first()
                return updated_event
            else:
                raise ValueError("Event_id no encontrado, ventana de tiempo terminado o alguien ya jugo not so fast")

        except SQLAlchemyError as e:
            self._db.rollback()
            raise
        except Exception as e:
            self._db.rollback()
            raise

    def update_info_event(
        self, 
        event_id: uuid.UUID,
        player_id: uuid.UUID,
        info_from_endpoint: uuid.UUID
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
            responses_list = current_payload.get('responses', [])

            new_responses_list = responses_list.copy()
            new_responses_list.append(str(info_from_endpoint))

            new_payload = current_payload.copy()
            new_payload['responses'] = new_responses_list
            
            event.payload = new_payload 
            
            self._db.commit()
            self._db.refresh(event)
            
            print(f"Respuesta de {player_id} añadida al evento {event.id}")
            return event

        except (SQLAlchemyError, ValueError) as e:
            self._db.rollback()
            print(f"Error al actualizar info del evento: {e}")
            raise e
    

    def is_event_ready_to_resolve(self, event:EventosDeTurno)-> bool:
        """
        Verifica si se cargo toda la info necesaria para resolver el evento
        """
        event_type=event.event_type
        payload = event.payload
        responses = payload.get('responses', [])

        if event_type == Card_event.CARD_TRADE.value:
            return len(responses) == 2
        else:
            return len(responses) == len(services_matches.MatchService(self._db).get_players_from_match(event.match_id))

    def resolve_event(self, event: EventosDeTurno) -> dict:
        """
        Handler de eventos. Contiene toda la logica que tenia antes el endpoint. Full BaseDatos, nada de ws
        """
        for prop,valor in vars(event).items():
            print(prop,valor)
        db = self._db #para no cambiar todo el codigo
        match_id = event.match_id
        player_id = event.player_id
        match_card_id = event.match_card_id
        event_payload = event.payload if event.payload else {}
        typeEvent = event.event_type

        try:
            match typeEvent:
                case Card_event.CARDS_OFF_THE_TABLE.value:
                    diccionary=services_cards.Cards_Services(db).cards_off_the_table(match_id,event_payload["target_player_id"],player_id,match_card_id)
                    updated_match_cards=diccionary["discarded_instant_cards"]

                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]

                #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [card_schema.model_dump(mode='json') for card_schema in updated_match_cards_schemas],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull"
                    }
                case Card_event.ANOTHER_VICTIM.value:
                    updated_set=set_services.SetService(db).steal_set(event_payload["target_set_id"],player_id)
                    #convertir a schema
                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": updated_set.model_dump(mode='json'),
                        "message": f"{typeEvent} was succesfull"
                    }

                case Card_event.LOOK_INTO_THE_ASHES.value:

                    #efecto de carta look_into_the_ashes y devuelve la carta tomada actualizada para el payload del ws
                    taken_card=services_cards.Cards_Services(db).look_into_the_ashes_event(player_id,match_id,event_payload["target_card_id"])


                    #convertimos a schema para que sean serializables
                    taken_card=db_match_card_2_match_card_schema(taken_card)


                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [taken_card.model_dump(mode='json')],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull"
                    }
                case Card_event.AND_THEN_THERE_WAS_ONE_MORE.value:

                    #efecto de carta and_then_there_was_one_more y devuelve secreto actualizado para el payload del ws
                    updated_secret=services_cards.Cards_Services(db).and_then_there_was_one_more_event(event_payload["target_player_id"],event_payload["target_secret_id"])


                    #convertimos a schema para que sean serializables
                    updated_secret=db_match_secret_2_match_secret_schema(updated_secret)

                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": updated_secret.model_dump(mode='json'),
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull"
                    }


                case Card_event.DELAY_THE_MURDERER_ESCAPE.value:
                    if len(event_payload["cards_ids"])>5:
                        raise ValueError("Se pasaron mas de 5 cartas para retrasar")

                    updated_match_cards=services_cards.Cards_Services(db).delay_the_murderer_escape_event(event_payload["cards_ids"])

                    #convertimos a schema para que sean serializables
                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]

                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [card_schema.model_dump(mode='json') for card_schema in updated_match_cards_schemas],
                        "updated_secret": None,
                        "discarded_card_event": None,
                        "updated_set": None,
                        "message": f"{typeEvent} was succesfull"
                    }

                case Card_event.EARLY_TRAIN_TO_PADDINGTON.value:
                    try:
                        if "cards_ids" not in event_payload or not event_payload["cards_ids"]:
                            raise ValueError("Se requiere 'cards_ids' con al menos una carta para el evento Early Train to Paddington")

                        #desvinculamos la foreign asi se permite borrar sin errores
                        event.match_card_id = None
                        db.commit()

                        discarded_cards = services_cards.Cards_Services(db).early_train_to_paddington_event(match_id, event_payload["cards_ids"])
                        services_cards.Cards_Services(db).discard_card(match_card_id, True)

                        serialized_discarded_cards = [mc.model_dump(mode="json") for mc in discarded_cards]

                        payload = {
                            "type": typeEvent,
                            "updated_match_cards": serialized_discarded_cards,
                            "updated_secret": None,
                            "discarded_card_event": None,
                            "updated_set": None,
                            "message": f"{typeEvent} was succesfull"
                        }
                    except Exception as e:
                        raise e
                case Card_event.CARD_TRADE.value:
                    print("Resolviendo el Card Trade...")
                    responses = event_payload.get('responses', [])
                    if len(responses)!=2:
                        raise ValueError("Faltan o sobran respuestas para el card_trade")
                    match_card_id1=responses[0]
                    match_card_id2=responses[1]

                    updated_match_cards = services_cards.Cards_Services(db).swap_cards_owners(match_card_id1,match_card_id2)
                    
                    print(f"Intercambiando {match_card_id1} por {match_card_id2}")

                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]

                    updated_match_cards = [mc.model_dump(mode="json") for mc in updated_match_cards_schemas]

                    payload = {
                            "type": typeEvent,
                            "updated_match_cards": updated_match_cards,
                            "updated_secret": None,
                            "discarded_card_event": None,
                            "updated_set": None,
                            "message": f"{typeEvent} was succesfull"
                        }
                case Card_event.DEAD_CARD_FOLLY.value:
                    print("Resolviendo el Dead Card Folly...")
                    responses = event_payload.get('responses', [])
                    direction = event_payload.get('direction')

                    updated_match_cards = services_cards.Cards_Services(db).pass_cards_in_direction(match_id,responses,direction)
                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]
                    updated_match_cards = [mc.model_dump(mode="json") for mc in updated_match_cards_schemas]

                    payload = {
                            "type": typeEvent,
                            "updated_match_cards": updated_match_cards,
                            "updated_secret": None,
                            "discarded_card_event": None,
                            "updated_set": None,
                            "message": f"{typeEvent} was succesfull"
                        }
                case Card_event.POINT_YOUR_SUSPICIONS.value:
                    print("Resolviendo el Point your suspicions...")
                    responses = event_payload.get('responses', [])
                    
                    vote_counts = Counter(responses)
                    most_voted_player = vote_counts.most_common(1)[0][0]
                    #si hay desempate agarra el que encuentre primero para no hacer tanto quilombo
                    #(1) lista el primer elemento mas comun
                    #[0] agarra la primera tupla de esa lista
                    #[0] devuelve el parametro player_id y no la cantidad de recurrencias

                    payload = {
                            "target_player_id": most_voted_player,
                    }
            
            return payload
        except Exception as e:
            raise e