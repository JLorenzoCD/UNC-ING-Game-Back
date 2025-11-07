import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Integer, ForeignKey, Enum, String, TIMESTAMP, DateTime, text
from sqlalchemy.sql import func

from app.events.models import EventosDeTurno

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
        event_payload: dict | None
    ) -> EventosDeTurno:
        """
        Crea la fila del evento en la BBDD con un estado PENDING.
        """
        print("createEvent")
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

    def update_event_nsf(
        self,
        event_id,
        nsf_count
    ) -> EventosDeTurno:
        """
        Actualiza el evento aumentandole +1 a la nsf_count y actualizando el resolve_at_time
        """
        try:
            #query atomica para que no haya condiciones de carrera(2 players o mas jueguen al mismo tiempo)
            update_count = self._db.query(EventosDeTurno).filter(
                EventosDeTurno.id == event_id,
                EventosDeTurno.nsf_count == nsf_count
            ).update({
                EventosDeTurno.nsf_count: nsf_count + 1,
                EventosDeTurno.resolve_at: func.now() + text("'5 seconds'::interval")
                }, synchronize_session=False)
            self._db.commit()


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
                    discarded_card_event=diccionary["discarded_event_card"]

                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]
                    discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)

                #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [card_schema.model_dump(mode='json') for card_schema in updated_match_cards_schemas],
                        "updated_secret": None,
                        "discarded_card_event": discarded_card_event.model_dump(mode='json'),
                        "updated_set": None
                    }
                case Card_event.ANOTHER_VICTIM.value:
                    updated_set=set_services.SetService(db).steal_set(event_payload["target_set_id"],player_id)
                    #convertir a schema
                    discarded_card_event=services_cards.Cards_Services(db).discard_card(match_card_id)
                    discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)
                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": None,
                        "discarded_card_event": discarded_card_event.model_dump(mode='json'),
                        "updated_set": updated_set.model_dump(mode='json')
                    }

                case Card_event.LOOK_INTO_THE_ASHES.value:

                    #efecto de carta look_into_the_ashes y devuelve la carta tomada actualizada para el payload del ws
                    taken_card=services_cards.Cards_Services(db).look_into_the_ashes_event(player_id,match_id,event_payload["target_card_id"])
                    discarded_card_event=services_cards.Cards_Services(db).discard_card(match_card_id)

                    #convertimos a schema para que sean serializables
                    taken_card=db_match_card_2_match_card_schema(taken_card)
                    discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)

                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [taken_card.model_dump(mode='json')],
                        "updated_secret": None,
                        "discarded_card_event": discarded_card_event.model_dump(mode='json'),
                        "updated_set": None
                    }
                case Card_event.AND_THEN_THERE_WAS_ONE_MORE.value:

                    #efecto de carta and_then_there_was_one_more y devuelve secreto actualizado para el payload del ws
                    updated_secret=services_cards.Cards_Services(db).and_then_there_was_one_more_event(event_payload["target_player_id"],event_payload["target_secret_id"])

                    #descartamos la carta de evento jugada
                    discarded_card_event=services_cards.Cards_Services(db).discard_card(match_card_id)

                    #convertimos a schema para que sean serializables
                    updated_secret=db_match_secret_2_match_secret_schema(updated_secret)
                    discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)

                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": None,
                        "updated_secret": updated_secret.model_dump(mode='json'),
                        "discarded_card_event": discarded_card_event.model_dump(mode='json'),
                        "updated_set": None
                    }


                case Card_event.DELAY_THE_MURDERER_ESCAPE.value:
                    if len(event_payload["cards_ids"])>5:
                        raise ValueError("Se pasaron mas de 5 cartas para retrasar")

                    updated_match_cards=services_cards.Cards_Services(db).delay_the_murderer_escape_event(event_payload["cards_ids"])
                    discarded_card_event=services_cards.Cards_Services(db).discard_card(match_card_id)

                    #convertimos a schema para que sean serializables
                    updated_match_cards_schemas = [db_match_card_2_match_card_schema(card) for card in updated_match_cards]
                    discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)

                    #construccion del payload
                    payload={
                        "type": typeEvent,
                        "updated_match_cards": [card_schema.model_dump(mode='json') for card_schema in updated_match_cards_schemas],
                        "updated_secret": None,
                        "discarded_card_event": discarded_card_event.model_dump(mode='json'),
                        "updated_set": None
                    }

                case Card_event.EARLY_TRAIN_TO_PADDINGTON.value:
                    try:
                        if "cards_ids" not in event_payload or not event_payload["cards_ids"]:
                            raise ValueError("Se requiere 'cards_ids' con al menos una carta para el evento Early Train to Paddington")

                        #desvinculamos la foreign asi se permite borrar sin errores
                        event.match_card_id = None
                        db.commit()

                        discarded_cards = services_cards.Cards_Services(db).early_train_to_paddington_event(match_id, event_payload["cards_ids"])

                        discarded_card_event = services_cards.Cards_Services(db).discard_card(match_card_id, delete=True)

                        serialized_discarded_cards = [mc.model_dump(mode="json") for mc in discarded_cards]
                        serialized_discarded_card_event = db_match_card_2_match_card_schema(discarded_card_event).model_dump(mode="json")

                        payload = {
                            "type": typeEvent,
                            "updated_match_cards": serialized_discarded_cards,
                            "updated_secret": None,
                            "discarded_card_event": serialized_discarded_card_event,
                            "updated_set": None
                        }
                    except Exception as e:
                        raise e
            return payload
        except Exception as e:
            raise e