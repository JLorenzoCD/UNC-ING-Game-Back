from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timezone

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message

from app.models.db import get_db
from app.player.models import Player, Match_Player

from app.matches import services
from app.matches.models import MatchEventType, MatchStatus

from app.cards import services as services_cards #si no le pones alias a este services se destruye todo porque pisa al services de matches

from app.events import services as services_event
from app.events.models import EventStatus

from app.matches.models import MatchEventType
from app.matches.utils import db_match_2_match_schema
from app.matches.ending import handle_match_ended, MatchEndedReason
from app.matches.schemas import (
    Cards_by_Match_Schema,
    MatchIn,
    MatchOut,
    MatchResponse,
    MatchDTO,
    Players_by_Match_Schema,
    Match_number_of_Player,
    MatchLogOut,
)

# Cards: alias the module to avoid collision with app.matches.services
from app.cards import services as services_cards
# keep a second name used elsewhere in the module
card_services = services_cards
from app.cards.services import Card_event
from app.cards.models import Card, Match_Card
from app.cards.utils import db_match_card_2_match_card_schema
from app.cards.schemas import (
    take_Match_Cards_in,
    discard_Match_Cards_in,
    Match_Card_Schema,
)

# Sets
from app.sets import services as set_services
from app.sets import schemas as set_schemas
from app.sets.schemas import MatchSetOut
from app.sets.models import Match_Set, SetType
from app.sets.utils import db_match_set_2_match_set_schema

# Secrets
from app.secrets import services as secret_services
from app.secrets import schemas as secret_schemas
from app.secrets.models import Match_Secret, Secret_action
from app.secrets.utils import db_match_secret_2_match_secret_schema

router = APIRouter(
    tags   = ["matches"],
    prefix = "/matches"
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MatchResponse)
async def create_match(
    match_in: MatchIn,
    db = Depends(get_db)
) -> MatchResponse:
    try:
        match_dto = match_in.to_dto()
        new_match = services.MatchService(db).create(match_dto)
    except services.OwnerNotFound:
        raise HTTPException(status_code=404, detail="Owner not found")
    except services.MatchValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # PRIMERO: Agregar el owner al match
    manager.enterMatch(new_match.owner_id, new_match.id)
    
    # DESPUÉS: Enviar broadcast
    match_dict                         = new_match.model_dump(mode='json')
    match_dict["current_player_count"] = 1
    ws_message = make_ws_message(WSEvent.MATCH, match_dict)
    await manager.waiting_room_broadcast(ws_message)
    
    return MatchResponse(id=new_match.id)

@router.get("/", status_code=status.HTTP_200_OK, response_model=List[Match_number_of_Player])
async def get_all_matches(db=Depends(get_db)) -> List[Match_number_of_Player]:
    try:
        matches: List[MatchOut] = services.MatchService(db).get_all()
    except Exception:
        raise HTTPException(status_code=404, detail="Matches not found")
    
    return matches

@router.get("/{match_id}", status_code=status.HTTP_200_OK, response_model=Match_number_of_Player)
async def get_match_by_match_ID(match_id: UUID, db=Depends(get_db)):
    try:
        match          = services.MatchService(db).get_match_by_id(match_id)
        match_extended = services.MatchService(db).extended_match(match)
    except Exception:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return match_extended

@router.get("/{match_id}/players", status_code=status.HTTP_200_OK, response_model=List[Players_by_Match_Schema])
async def get_player_by_ID_match(match_id: UUID, db=Depends(get_db)) -> List[Players_by_Match_Schema]:
    try:
        players_match: List[Players_by_Match_Schema] = services.MatchService(db).get_players_by_match(match_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    
    return players_match

@router.post("/{match_id}/join", status_code=status.HTTP_200_OK)
async def join_match(match_id: UUID, player_id: UUID, db=Depends(get_db)):
    # Para el futuro estaria bien hacer services de player
    info_player = db.query(Player).filter(Player.id == player_id).first()
    if not info_player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    services.MatchService(db).join(match_id, player_id)
    
    # PRIMERO: Agregar el jugador al match en el WebSocket manager
    manager.enterMatch(player_id, match_id)
    
    # DESPUÉS: Enviar mensajes de broadcast
    payload = {
        "id":       info_player.id,
        "name":     info_player.name,
        "avatar":   info_player.avatar,
        "birthday": info_player.birthday
    }
    
    await manager.specificBroadcast(make_ws_message(WSEvent.PLAYER_JOIN, payload), match_id)
    
    match_service = services.MatchService(db)
    match         = match_service.get_match_by_id(match_id)
    players_count = match_service.count_players_by_match(match_id)
    new_match     = db_match_2_match_schema(match)
    
    match_dict                         = new_match.model_dump(mode='json')
    match_dict["current_player_count"] = players_count
    message_ws                         = make_ws_message(WSEvent.MATCH, match_dict)
    
    await manager.waiting_room_broadcast(message_ws)
    try:
        log = f"[JOIN] Jugador {info_player.name} se unió a la partida"
        id_log = services.LogService(db).create_log(match_id, log, MatchEventType.PLAYER_JOIN, info_player.id)
        log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
        await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
    except Exception as e:
        print(f"[LOG] error creando/broadcast log de join: {e}")
    return {"match_id": match_id}

@router.post("/{match_id}/start", status_code=status.HTTP_200_OK)
async def start_match(match_id: UUID, db=Depends(get_db)):
    try:
        match = services.MatchService(db).start_game(match_id)

        payload = match.model_dump(mode='json')
        
        await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, payload))
        await manager.specificBroadcast(make_ws_message(WSEvent.MATCH, payload), match_id)
        
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not start match: {str(e)}")
    
    # Obtener el jugador actual después del cambio de turno
    current_player_id = services.MatchService(db).get_current_player_by_match(match_id)
    
    # Crear log con información del jugador actual
    try:
        if current_player_id:
            player_obj = services.PlayersService(db).get_player(current_player_id)
            log = f"[TURN] Es turno de {player_obj.name}"
            id_log = services.LogService(db).create_log(match_id, log, MatchEventType.TURN, player_obj.id)
            log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
            await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
        else:
            print(f"[LOG] No se pudo obtener current_player_id para match {match_id}")
    except Exception as e:
        print(f"[LOG] error creando/broadcast log de turno: {e}")

    return {"status": "Match started successfully"}


@router.post("/{match_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_match(match_id: UUID, owner_id: UUID, db=Depends(get_db)):
    try:
        cancelled_match = services.MatchService(db).cancel_match(match_id, owner_id)
        cancelled_match.status = MatchStatus.COMPLETED

        manager.close_match(match_id)

        payload = cancelled_match.model_dump(mode='json')

        await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, payload))
        
        return {"status": "Match cancelled and deleted successfully", "match_id": match_id}
        
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except services.MatchValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@router.put("/{match_id}/pass_turn", status_code=status.HTTP_200_OK)
async def pass_turn(match_id: UUID, db=Depends(get_db)):
    try:
        match=services.MatchService(db).pass_turn_by_id(match_id)
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")
    
    # Obtener el jugador actual después del cambio de turno
    current_player_id = services.MatchService(db).get_current_player_by_match(match_id)
    
    match_dict = db_match_2_match_schema(match).model_dump(mode="json")
    # Agregar el current_player_id al payload si existe
    if current_player_id:
        match_dict["current_player_id"] = str(current_player_id)
    
    msg = make_ws_message(WSEvent.TURN, match_dict)
    try:
        await manager.specificBroadcast(msg, match_id)
    except Exception as ws_err:
        print(f"[WS] pass_turn broadcast error: {ws_err}")
    
    # Crear log con información del jugador actual
    try:
        if current_player_id:
            player_obj = services.PlayersService(db).get_player(current_player_id)
            log = f"[TURN] Es turno de {player_obj.name}"
            id_log = services.LogService(db).create_log(match_id, log, MatchEventType.TURN, player_obj.id)
            log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
            await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
        else:
            print(f"[LOG] No se pudo obtener current_player_id para match {match_id}")
    except Exception as e:
        print(f"[LOG] error creando/broadcast log de turno: {e}")
    
    return {"match_id": match_id}

@router.get("/{match_id}/secrets", status_code=status.HTTP_200_OK)
async def get_secrets(match_id: UUID, db=Depends(get_db)):
    secrets = services.MatchService(db).get_secrets_by_match(match_id)
    return secrets

@router.get("/{match_id}/cards", status_code=status.HTTP_200_OK, response_model=List[Cards_by_Match_Schema])
async def get_cards(match_id: UUID, db=Depends(get_db)):
    try:
        cards = services.MatchService(db).get_cards_by_match(match_id)
    except services.SQLAlchemyError:
        raise HTTPException(status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return cards

@router.put("/{match_id}/cards/take", status_code=status.HTTP_200_OK)
async def take_card(match_id: UUID, cards: take_Match_Cards_in, db=Depends(get_db)):
    try:
        player_id = cards.player_id
        player = db.query(Match_Player).filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found in this match")
        
        taken_cards_ids       = cards.card_ids
        len_taken_cards_ids   = len(taken_cards_ids)
        count_cards_pile = services.PileService(db).get_count_cards_pile(match_id)
        player_cards_count    = db.query(Match_Card).filter(Match_Card.match_id == match_id, Match_Card.player_id == player_id).count()

        if (count_cards_pile < len_taken_cards_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes tomar más cartas de las que quedan en el mazo"})
        if (len_taken_cards_ids > 6):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes tomar mas de 6 cartas"})
        elif(player_cards_count + len_taken_cards_ids > 6):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes tener mas de 6 cartas"})
        else:
            services.PileService(db).take_cards(player_id, match_id, taken_cards_ids)

            ids = list(set(taken_cards_ids))

            results = services.MatchService(db).get_extended_cards_by_match(match_id, ids)

            payload = [
                {
                "id": card[0],
                "card_id": card[1],
                "match_id": card[2],
                "player_id": card[3],
                "is_discarded": card[4],
                "discarded_at": card[5],
                "name": card[6],
                "type": card[7].value if hasattr(card[7], 'value') else card[7],
                "description": card[8],
                }
                for card in results
            ]

            #ver si el mazo quedó vacío y terminar la partida si es así
            remaining_after = services.PileService(db).get_count_cards_pile(match_id)
            if remaining_after <= 3:
                try:
                    await handle_match_ended(db, manager, match_id, MatchEndedReason.DECK_FINISHED)
                except Exception as e:
                    print(f"Error al handle_match_ended en take_card: {e}")

            await manager.specificBroadcast(make_ws_message(WSEvent.CARDS, payload), match_id)

            # Agregar log para take cards
            try:
                player_obj = services.PlayersService(db).get_player(player_id)
                log_message = f"[TAKE] Jugador {player_obj.name} tomó {len(taken_cards_ids)} carta(s) del mazo"
                
                id_log = services.LogService(db).create_log(match_id, log_message, MatchEventType.TAKE_CARDS, player_obj.id)
                log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
                await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
            except Exception as e:
                print(f"[LOG] error creando/broadcast log de take: {e}")

            return {"status": "success", "cards_taken": len(taken_cards_ids)}
    except HTTPException as exception:
        raise exception

@router.put("/{match_id}/cards/discard", status_code=status.HTTP_200_OK)
async def discard_card(match_id: UUID, cards: discard_Match_Cards_in, db=Depends(get_db)):
    try:
        player_id = cards.player_id
        player = db.query(Match_Player).filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found in this match")

        discarded_cards_ids     = cards.card_ids
        len_discarded_cards_ids = len(discarded_cards_ids)
        player_cards_count      = db.query(Match_Card).filter(Match_Card.match_id == match_id, Match_Card.player_id == player_id, Match_Card.is_discarded == False).count()
        

        if (len_discarded_cards_ids > player_cards_count):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes descartar más cartas de las que tienes"})
        else:
            services.PileService(db).discard_cards(player_id, match_id, discarded_cards_ids)

            ids = list(set(discarded_cards_ids))

            results = services.MatchService(db).get_extended_cards_by_match(match_id, ids)

            payload = [
                {
                "id": card[0],
                "card_id": card[1],
                "match_id": card[2],
                "player_id": card[3],
                "is_discarded": card[4],
                "discarded_at": card[5],
                "name": card[6],
                "type": card[7].value if hasattr(card[7], 'value') else card[7],
                "description": card[8],
                }
                for card in results
            ]

            await manager.specificBroadcast(make_ws_message(WSEvent.CARDS, payload), match_id)
            
            # Agregar log para discard cards
            try:
                player_obj = services.PlayersService(db).get_player(player_id)
                
                # Obtener nombres de las cartas descartadas para el log
                card_names = []
                for card in results:
                    card_names.append(card[6])  # card[6] es el nombre de la carta
                
                cards_text = ", ".join(card_names) if len(card_names) <= 3 else f"{', '.join(card_names[:3])} y {len(card_names) - 3} más"
                log_message = f"[DISCARD] Jugador {player_obj.name} descartó {len(discarded_cards_ids)} carta(s): {cards_text}"
                
                id_log = services.LogService(db).create_log(match_id, log_message, MatchEventType.DISCARD_CARDS, player_obj.id)
                log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
                await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
            except Exception as e:
                print(f"[LOG] error creando/broadcast log de discard: {e}")
            
            return {"status": "success", "cards_discarded": len(discarded_cards_ids)}
    except HTTPException as exception:
        raise exception
    

@router.put("/{match_id}/timeout/{player_id}", status_code=status.HTTP_200_OK)
async def time_out(match_id: UUID, player_id:UUID, db = Depends(get_db)) -> Optional[List[Match_Card_Schema]]:
    try:
        match_services = services.MatchService(db)
        match = match_services.get_match_by_id(match_id)
        time_now = datetime.now(timezone.utc)
        
        # Agregar verificaicon entre el timer de match.timer_turn y el time_now sea mayor a 60 segundos
        if not match.timer_turn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El timer de la partida no está activo."
            )
        time_diff = (time_now - match.timer_turn).total_seconds()
        if time_diff <= 60:
            return None
        
        player = db.query(Match_Player).filter(Match_Player.match_id == match_id, Match_Player.player_id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found in this match")
        
        # Obtener una carta aleaotria de la mano del Player, descartarla y reponer la 4ta carta del mazo regular
        first_card: Match_Card = db.query(Match_Card).filter(
            Match_Card.match_id == match_id,
            Match_Card.player_id == player_id,
            Match_Card.is_discarded == False
        ).first()
        if not first_card:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró la carta de descarte"
            )
        if first_card:
            card_services.Cards_Services(db).discard_card(first_card.id, delete=False)
            discarded_card_schema = db_match_card_2_match_card_schema(first_card)
        
        fourth_card: Match_Card = db.query(Match_Card).filter(
                        Match_Card.player_id == None,
                        Match_Card.is_discarded == False
                        ).order_by(Match_Card.id).offset(3).first()
        
        if fourth_card:
            new_card = services.PileService(db).take_cards(player_id, match_id, cards=[fourth_card.id])
            if new_card.player_id != player_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La carta no se actualizó y el player_id es {new_card.player_id}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró la cuarta carta"
            )
        
        print(fourth_card)
            
        ids = list(set([first_card.id, fourth_card.id]))
             
        results = services.MatchService(db).get_extended_cards_by_match(match_id, ids)
        payload = [
            {
            "id": card[0],
            "card_id": card[1],
            "match_id": card[2],
            "player_id": card[3],
            "is_discarded": card[4],
            "discarded_at": card[5],
            "name": card[6],
            "type": card[7].value if hasattr(card[7], 'value') else card[7],
            "description": card[8],
            }
            for card in results
        ]
        await manager.specificBroadcast(make_ws_message(WSEvent.CARDS, payload), match_id)        
        
        # Logica para pasar el turno
        match=services.MatchService(db).pass_turn_by_id(match_id)
        
        # Obtener el jugador actual después del cambio de turno
        current_player_id = services.MatchService(db).get_current_player_by_match(match_id)
        
        match_dict = db_match_2_match_schema(match).model_dump(mode="json")
        # Agregar el current_player_id al payload si existe
        if current_player_id:
            match_dict["current_player_id"] = str(current_player_id)
        
        msg = make_ws_message(WSEvent.TURN, match_dict)
        try:
            await manager.specificBroadcast(msg, match_id)
        except Exception as ws_err:
            print(f"[WS] pass_turn broadcast error: {ws_err}")
        
        # Crear log con información del jugador actual
        try:
            if current_player_id:
                player_obj = services.PlayersService(db).get_player(current_player_id)
                log = f"[TURN] Es turno de {player_obj.name}"
                id_log = services.LogService(db).create_log(match_id, log, MatchEventType.TURN, player_obj.id)
                log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
                await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
            else:
                print(f"[LOG] No se pudo obtener current_player_id para match {match_id}")
        except Exception as e:
            print(f"[LOG] error creando/broadcast log de turno: {e}")
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

  
    
@router.post("/{match_id}/sets", status_code=status.HTTP_201_CREATED)
async def play_set(match_id: UUID, setIn: set_schemas.SetIn, db = Depends(get_db)) -> Optional[set_schemas.MatchSetOut]:
    try:
        #  ---- Create Set y Eliminar cartas (Menos el caso Lady Eileen) ----
        # Crear log ANTES de procesar el set
        setType = setIn.type
        player  = services.PlayersService(db).get_player(setIn.player_id)
        try:
            log = f"[SET] Jugador {player.name} jugó el set {setType.value}"
            # Mapear SetType a MatchEventType usando el nombre
            event_type = getattr(MatchEventType, setType.name, None)
            if event_type:
                id_log = services.LogService(db).create_log(match_id, log, event_type, player.id)
                log_out = services.LogService(db).get_log_by_id(id_log).model_dump(mode='json')
                await manager.specificBroadcast(make_ws_message(WSEvent.LOG, log_out), match_id)
            else:
                print(f"[LOG] Warning: No matching MatchEventType for SetType {setType.name}")
        except Exception as e:
            print(f"[LOG] error creando/broadcast log de set: {e}")

        # Create Set
        match_card_ids: List[UUID] = setIn.card_ids
        set_service = set_services.SetService(db)
        set_service.set_verification(match_card_ids, match_id, setIn.type, setIn.target_player_id, setIn.target_secret_id)
        
        set_data = {    
            "type" : setIn.type,
            "card_ids": match_card_ids,
            "player_id": setIn.player_id,
            "target_player_id": setIn.target_player_id,
            "target_secret_id": setIn.target_secret_id,
            "match_id": match_id           
        }
        match_set: Optional[set_schemas.MatchSetOut] = None
        
        if setIn.type != SetType.LADY_EILEEN:
            match_set = set_service.create_set(set_data)
            payload = {}
            match_set_out = db_match_set_2_match_set_schema(match_set)
            payload = match_set_out.model_dump(mode='json')
            card_service = card_services.Cards_Services(db)
            for card in setIn.card_ids:
                to_eliminate = True
                eliminate = card_service.discard_card(card, to_eliminate)  
            payload.update({"deleted_cards": [str(uuid) for uuid in match_card_ids]})
            ws_msj = make_ws_message(WSEvent.SET, payload)
            await manager.specificBroadcast(ws_msj, match_id)

        # ---- Crear fila de Match_Event (Revisado por Worker) ----
        print(setIn.type)
        if setIn.type == SetType.TWO_BERESFORD:
            set_payload = set_services.SetService(db).create_set_payload(match_id, setIn, is_Oliver=False)
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                setIn.type.value,
                None,
                set_payload,
                EventStatus.RESOLVED
            )
            payload = services_event.EventService(db).resolve_event(new_event)        
            await manager.specificBroadcast(
                                make_ws_message(WSEvent.PLAYER_SECRET_REVEAL, payload),
                                match_id
                            )
            
        elif setIn.type == SetType.LADY_EILEEN:
            set_payload = set_services.SetService(db).create_set_payload(match_id, setIn, is_Oliver=False)
            set_payload.update({"is_create_set": True})
            new_set_data = {
                "type" : setIn.type.value,
                "card_ids": [str(card_id) for card_id in setIn.card_ids],
                "player_id": str(setIn.player_id),
                "target_player_id": str(setIn.target_player_id),
                "target_secret_id": str(setIn.target_secret_id),
                "match_id": str(match_id)    
            }
            set_payload.update({"set_data": new_set_data})
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                setIn.type.value,
                None,
                set_payload,
            )
            payload = {
                "event_id": str(new_event.id),
                "event_type": setIn.type.value,
                "player_id": str(setIn.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            ) 
            
        else:
            set_payload = set_services.SetService(db).create_set_payload(match_id, setIn, is_Oliver=False)
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                setIn.type.value,
                None,
                set_payload
            )           
            payload = {
                "event_id": str(new_event.id),
                "event_type": setIn.type.value,
                "player_id": str(setIn.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )            
        return match_set
    except (set_services.InvalidCardError, set_services.InvalidMatchIdError, set_services.TargetSecretError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except set_services.InvalidSetError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except (ValueError, secret_services.SecretNotFound) as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put('/{match_id}/sets/{set_id}', status_code=200)
async def put_down_a_detective(match_id: UUID, set_id:UUID, set_info:set_schemas.AddSetIn, db=Depends(get_db)) -> set_schemas.MatchSetOut:
    try:
        # ---- Verificaciones y Bajar carta al Set ----
        match_card_ids: List[UUID] = set_info.card_ids
        set_service = set_services.SetService(db)
        set_service.add_card_verification(match_card_ids, set_id, set_info.target_player_id, set_info.target_secret_id)
        
        match_set = set_service.get_match_set(set_id, match_id)
        match_set_out = db_match_set_2_match_set_schema(match_set)

        card_name = set_service._get_card_names(match_card_ids)[0]
        
        if match_set.type != SetType.LADY_EILEEN or card_name == SetType.ADRIADNE_OLIVER.value:
        # Actualizamos si es el caso de que agregamos a TOMMY_BERESFORD en  TUPPENCE_BERESFORD y viceversa
            if set_service.beresford_brothers_in_set_two_beresford(card_name, match_set.type):
                match_set = set_service.update_setType(set_id, SetType.TWO_BERESFORD)
                match_set_out = db_match_set_2_match_set_schema(match_set)
            payload = match_set_out.model_dump(mode='json')
            
            # Eliminamos las cartas excepto Lady Eileen
            card_service = card_services.Cards_Services(db)
            for card in set_info.card_ids:
                to_eliminate = True
                eliminate = card_service.discard_card(card, to_eliminate)  
            payload.update({"deleted_cards": [str(uuid) for uuid in match_card_ids]})            
            ws_msj = make_ws_message(WSEvent.SET, payload)
            await manager.specificBroadcast(ws_msj, match_id)

        # ---- Casos posibles para el Worker ----
        set_type = match_set.type
        set_in_complete = set_schemas.SetIn(
            type=set_type,
            card_ids=set_info.card_ids,
            player_id=set_info.player_id,
            target_player_id=set_info.target_player_id,
            target_secret_id=set_info.target_secret_id
        )
    
        # Caso Oliver 
        if card_name == SetType.ADRIADNE_OLIVER.value:
            set_in_Oliver = set_schemas.SetIn(
                type=SetType.ADRIADNE_OLIVER,
                card_ids=set_info.card_ids,
                player_id=set_info.player_id,
                target_player_id=set_info.target_player_id,
                target_secret_id=set_info.target_secret_id
            )
            set_payload = set_services.SetService(db).create_set_payload(match_id, set_in_Oliver, is_Oliver=True)
            new_event = services_event.EventService(db).create_event(
                match_id,
                set_info.player_id,
                SetType.ADRIADNE_OLIVER.value,
                None,
                set_payload,
            )
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
                "player_id": str(set_info.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )
        # Caso Two Beresford             
        elif match_set.type == SetType.TWO_BERESFORD:
            set_payload = set_services.SetService(db).create_set_payload(match_id, set_in_complete, is_Oliver=False)
            new_event = services_event.EventService(db).create_event(
                match_id,
                set_info.player_id,
                set_in_complete.type.value,
                None,
                set_payload,
                EventStatus.RESOLVED
            )
            payload=services_event.EventService(db).resolve_event(new_event)          
            await manager.specificBroadcast(
                                make_ws_message(WSEvent.PLAYER_SECRET_REVEAL, payload),
                                match_id
                            )
            
        # Caso Lady Eileen
        elif match_set.type == SetType.LADY_EILEEN:
            set_payload = set_services.SetService(db).create_set_payload(match_id, set_in_complete, is_Oliver=False)
            set_payload.update({"is_create_set": False})
            set_payload.update({"set_id": str(match_set.id)})
            new_event = services_event.EventService(db).create_event(
                match_id,
                set_info.player_id,
                set_in_complete.type.value,
                match_card_ids[0],
                set_payload
            )           
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
                "player_id": str(set_info.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )     
        # Caso otro Detectives                  
        else:
            set_payload = set_services.SetService(db).create_set_payload(match_id, set_in_complete, is_Oliver=False)
            new_event = services_event.EventService(db).create_event(
                match_id,
                set_info.player_id,
                set_in_complete.type.value,
                None,
                set_payload
            )           
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
                "player_id": str(set_info.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )           
        return match_set
    except (set_services.InvalidCardError, set_services.InvalidMatchIdError, set_services.TargetSecretError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except set_services.InvalidSetError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except (ValueError, secret_services.SecretNotFound) as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{match_id}/sets/{set_id}/stolen", status_code=200)
async def play_set_stolen(match_id: UUID, set_id: UUID, stolen_setIn: set_schemas.stoleSetIn, db=Depends(get_db)) -> set_schemas.MatchSetOut:
    try:
    # ---- Verificaciones ----
        match_set = set_services.SetService(db).get_match_set(set_id, match_id)
        set_type = match_set.type
        target_secret = stolen_setIn.target_secret_id
        target_player = stolen_setIn.target_player_id
        if not target_player:
            raise set_services.InvalidCardError
             
        if set_type in [SetType.HERCULE_POIROT, 
                        SetType.MISS_MARPLE, 
                        SetType.PARKER_PYNE] and target_secret is None:
            raise set_services.TargetSecretError("No hay secreto seleccionado")
        
        if target_secret:
            secret = secret_services.Secrets_Services(db).get_match_secret_by_id(target_secret)
            if secret.player_id != target_player:
                raise set_services.TargetSecretError("El secreto y el jugador no coinciden")
            
            if set_type in [SetType.LADY_EILEEN, SetType.TUPPENCE_BERESFORD, 
                            SetType.TOMMY_BERESFORD, SetType.TWO_BERESFORD, 
                            SetType.MR_SATTERTHWAITE]:
                raise set_services.TargetSecretError("No se debería seleccionar secreto en este momento")        
        
        # ---- Acciones ----
        secret_service = secret_services.Secrets_Services(db)        
        if target_secret is not None:
            if match_set.type in [SetType.HERCULE_POIROT, SetType.MISS_MARPLE]:
                target_secret = secret_service.update_secret(secret_services.Secret_action.REVEAL, 
                                                             target_secret, 
                                                             target_player)
                match_secret_out = db_match_secret_2_match_secret_schema(target_secret)
                
            if match_set.type == (SetType.PARKER_PYNE):
                target_secret = secret_service.update_secret(secret_services.Secret_action.HIDE, 
                                                             target_secret, 
                                                             target_player)
                match_secret_out = db_match_secret_2_match_secret_schema(target_secret)              

            payload = match_secret_out.model_dump(mode='json')
            
            ws_msj = make_ws_message(WSEvent.SECRET, payload)
            await manager.specificBroadcast(ws_msj, match_id)
            
        else:
            payload = {"target_player_id" : target_player}
            ws_msj = make_ws_message(WSEvent.PLAYER_SECRET_REVEAL, payload)
            await manager.specificBroadcast(ws_msj, match_id)
        
        match_set_out = db_match_set_2_match_set_schema(match_set)
        return match_set_out
        
    except (set_services.InvalidCardError, 
            set_services.InvalidMatchIdError, 
            set_services.TargetSecretError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except set_services.InvalidSetError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except (ValueError, secret_services.SecretNotFound) as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))        

@router.put("/{match_id}/secrets/{secret_id}", status_code=200)
async def update_secret_in_match(match_id: UUID, secret_id:UUID, secretIn:secret_schemas.SecretUpdate, db=Depends(get_db)) -> secret_schemas.Match_Secret_Schema:
    try: 
        secret_service = secret_services.Secrets_Services(db)
        secret_service.secret_update_verification(match_id, secret_id ,secretIn)
        
        match_secret: Match_Secret = secret_service.update_secret(secretIn.action, secret_id, secretIn.target_player_id)
        match_secret_out: secret_schemas.Match_Secret_Schema = db_match_secret_2_match_secret_schema(match_secret)
        
        #Mensaje de WebScokets 
        payload = match_secret_out.model_dump(mode='json')
        msj_ws = make_ws_message(WSEvent.SECRET, payload)
        await manager.specificBroadcast(msj_ws, match_id)
        
        if secretIn.action == Secret_action.REVEAL and match_secret_out.is_revealed == True:
            try:
                res=secret_service.is_murderer_revealed(match_id)
                if res:
                    await handle_match_ended(db, manager, match_id, MatchEndedReason.MURDERER_REVEALED)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        return match_secret_out
    
    except secret_services.SecretNotFound as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{match_id}/sets", status_code=status.HTTP_200_OK, response_model=List[MatchSetOut])
async def get_sets(match_id: UUID, db=Depends(get_db)):
    try:
        sets = services.SetService(db).get_sets_by_match(match_id)
    except SQLAlchemyError:
        raise HTTPException(status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return sets

@router.post("/{match_id}/events", status_code=status.HTTP_200_OK)
async def play_event(match_id:UUID,player_id: UUID, match_card_id:UUID, event_payload:dict | None, db=Depends(get_db)):
    print("entre al endpoint play_event")
    try:
        services_cards.Cards_Services(db).validate_card_ownership(player_id,match_id,match_card_id)
        print("se valido bien la carta")
        typeEvent=services_cards.Cards_Services(db).get_event_type_by_card(match_card_id)
        print("se hizo bien el gettypeevent")
        print(typeEvent.value)
        if services_cards.Cards_Services(db).is_instant_event(typeEvent.value):
            new_event = services_event.EventService(db).create_event(
                match_id,
                player_id,
                typeEvent.value,
                match_card_id,
                event_payload,
                EventStatus.RESOLVED
            )
            payload=services_event.EventService(db).resolve_event(new_event)
            discarded_card_event = services_cards.Cards_Services(db).discard_card(match_card_id, delete=False)
            discarded_card_event = db_match_card_2_match_card_schema(discarded_card_event).model_dump(mode="json")
            payload["discarded_card_event"]=discarded_card_event
            print("se descarto bien la carta")
            await manager.specificBroadcast(
                                make_ws_message(WSEvent.CARD_EVENT, payload),
                                match_id
                            )
        else:
            new_event = services_event.EventService(db).create_event(
                match_id,
                player_id,
                typeEvent.value,
                match_card_id,
                event_payload
            )
            discarded_card_event = services_cards.Cards_Services(db).discard_card(match_card_id, delete=False)
            discarded_card_event = db_match_card_2_match_card_schema(discarded_card_event).model_dump(mode="json")
            payload = {
                "event_id": str(new_event.id),
                "event_type": typeEvent.value,
                "player_id": player_id,
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": discarded_card_event
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )
        return {"status":"event_created", "event_id": new_event.id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar el evento: {str(e)}"
        )
    
@router.post("/{match_id}/not_so_fast", status_code=status.HTTP_200_OK)
async def play_not_so_fast(match_id:UUID,player_id: UUID, match_card_id:UUID, event_id:UUID, nsf_count:int, db=Depends(get_db)):
    try:
        print("llegue al endpoint de la notsofast")
        services_cards.Cards_Services(db).validate_card_ownership(player_id,match_id,match_card_id)
        typeEvent=services_cards.Cards_Services(db).get_event_type_by_card(match_card_id)
        if (typeEvent.value != "NOT SO FAST"):
            raise Exception("Carta jugada no es una not so fast")
        updated_event=services_event.EventService(db).update_event_nsf(event_id,nsf_count)
        discarded_card_event=services_cards.Cards_Services(db).discard_card(match_card_id)
        discarded_card_event=db_match_card_2_match_card_schema(discarded_card_event)
        payload = {
            "event_id": str(updated_event.id),
            "event_type": typeEvent.value,
            "player_id": player_id,
            "resolve_at_utc": updated_event.resolve_at.isoformat(),
            "nsf_count": updated_event.nsf_count,
            "discarded_card": discarded_card_event.model_dump(mode='json'),
        }
        print("a punto de enviar el otro cancellation window open")
        await manager.specificBroadcast(
            make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
        )
        return {"status": "ok", "message": "Cancelaste la accion"}
    except ValueError as e:
        print(f"alguien ya cancelo la accion error: {e}")
        return {"status": "failed", "message": "Alguien ya canceló la accion "}
    except Exception as e:
        print(f"algun error por algun lado error:{e}")
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar la carta {e}"
        )
    
@router.post("/{match_id}/card_trade", status_code=status.HTTP_200_OK)
async def play_card_trade(match_id: UUID, player_id: UUID, event_id:UUID, event_payload: dict, db=Depends(get_db)):
    try:
        services_cards.Cards_Services(db).validate_card_ownership(player_id,match_id,event_payload['target_card_id'])
        event_update=services_event.EventService(db).update_info_event(event_id,player_id,event_payload['target_card_id'])
        if services_event.EventService(db).is_event_ready_to_resolve(event_update):
            payload=services_event.EventService(db).resolve_event(event_update)
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CARD_EVENT, payload), match_id
            )
        return {"status": "ok","message":"CardTrade de lujo"}
    except Exception as e:
        print(f"Algun error en card trade error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al procesar la carta {e}"
        )


@router.post("/{match_id}/point_your_suspicions", status_code=status.HTTP_200_OK)
async def play_point_your_suspicions(match_id: UUID, player_id: UUID, event_id:UUID, event_payload: dict, db=Depends(get_db)):
    try:
        event_update=services_event.EventService(db).update_info_event(event_id,player_id,event_payload['target_player_id'])
        if services_event.EventService(db).is_event_ready_to_resolve(event_update):
            payload=services_event.EventService(db).resolve_event(event_update)
            await manager.specificBroadcast(
                make_ws_message(WSEvent.PLAYER_SECRET_REVEAL, payload), match_id
            )
        return {"status": "ok","message":"Point your suspicions de lujo"}
    except Exception as e:
        print(f"Algun error en point your suspicions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al procesar la carta {e}"
        )
    
@router.post("/{match_id}/dead_card_folly", status_code=status.HTTP_200_OK)
async def play_dead_card_folly(match_id: UUID, player_id: UUID, event_id:UUID, event_payload: dict, db=Depends(get_db)):
    try:
        services_cards.Cards_Services(db).validate_card_ownership(player_id,match_id,event_payload['target_card_id'])
        event_update=services_event.EventService(db).update_info_event(event_id,player_id,event_payload['target_card_id'])
        if services_event.EventService(db).is_event_ready_to_resolve(event_update):
            payload=services_event.EventService(db).resolve_event(event_update)
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CARD_EVENT, payload), match_id
            )
        return {"status": "ok","message":"Dead card folly de lujo"}
    except Exception as e:
        print(f"Algun error en dead card folly error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al procesar la carta {e}"
        )
    
    
@router.get("/{match_id}/logs", status_code=status.HTTP_200_OK, response_model=List[MatchLogOut])
async def get_logs(match_id: UUID, db=Depends(get_db)) -> List[MatchLogOut]:
    try:
        logs = services.LogService(db).get_logs_by_match(match_id)
    except SQLAlchemyError:
        raise HTTPException(status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return logs

@router.put("/{match_id}/quit", status_code=status.HTTP_200_OK)
async def quit_match(match_id: UUID, player_id: UUID, db = Depends(get_db)):
    # Verificar que el jugador existe ANTES del try-catch
    info_player = db.query(Player).filter(Player.id == player_id).first()
    if not info_player:
        raise HTTPException(status_code=404, detail="Player not found")

    try:
        # Remover jugador de la partida en la base de datos
        services.MatchService(db).quit_match(match_id, player_id)

        # Remover jugador del WebSocket manager
        try:
            manager.quitMatch(player_id, match_id)
        except Exception as ws_e:
            print(f"[WS ERROR] Error removing player {player_id} from websocket match {match_id}: {ws_e}")
            # No lanzamos excepción aquí porque el websocket puede no estar conectado

        # Este codigo esta repetido del join, habria que refactorizarlo en una funcion aparte.

        # DESPUÉS: Enviar mensajes de broadcast
        payload = {
            "id":       info_player.id,
            "name":     info_player.name,
            "avatar":   info_player.avatar,
            "birthday": info_player.birthday
        }
        
        await manager.specificBroadcast(make_ws_message(WSEvent.PLAYER_QUIT, payload), match_id)
        
        match_service = services.MatchService(db)
        match         = match_service.get_match_by_id(match_id)
        players_count = match_service.count_players_by_match(match_id)
        new_match     = db_match_2_match_schema(match)
        
        match_dict                         = new_match.model_dump(mode='json')
        match_dict["current_player_count"] = players_count
        message_ws                         = make_ws_message(WSEvent.MATCH, match_dict)
        
        await manager.waiting_room_broadcast(message_ws)

        return {"status": "success"}
        
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except services.PlayerNotInMatch:
        raise HTTPException(status_code=404, detail="Player not in match")
    except SQLAlchemyError as db_e:
        print(f"[DB ERROR] Database error in quit_match: {db_e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UNEXPECTED ERROR] Unexpected error in quit_match: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        
        
