from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message
from app.matches.utils import db_match_2_match_schema
from app.models.db import get_db
from app.player.models import Player, Match_Player
from app.matches import services

from app.cards import services as services_cards #si no le pones alias a este services se destruye todo porque pisa al services de matches

from app.events import services as services_event
from app.events.models import EventStatus

from app.matches.schemas import (
    Cards_by_Match_Schema,
    MatchIn,
    MatchOut,
    MatchResponse,
    MatchDTO,
    Players_by_Match_Schema,
    Match_number_of_Player,
)
from app.cards.models import Card, Match_Card
from app.cards.utils import db_match_card_2_match_card_schema
from app.cards.schemas import (take_Match_Cards_in, discard_Match_Cards_in, Match_Card_Schema)
from app.cards import services as card_services
from app.sets import schemas as set_schemas
from app.sets.schemas import MatchSetOut
from app.sets import services as set_services
from app.sets.models import Match_Set, SetType
from app.secrets import services as secret_services
from app.secrets import schemas as secret_schemas
from app.secrets.models import Match_Secret, Secret_action
from app.secrets.utils import db_match_secret_2_match_secret_schema
from app.matches.ending import handle_match_ended,MatchEndedReason

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
    
    match_dict                         = new_match.model_dump(mode='json')
    match_dict["current_player_count"] = 1
    ws_message = make_ws_message(WSEvent.MATCH, match_dict)
    manager.enterMatch(new_match.owner_id, new_match.id)
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
    
    payload = {
        "id":       info_player.id,
        "name":     info_player.name,
        "avatar":   info_player.avatar,
        "birthday": info_player.birthday
    }
    
    await manager.specificBroadcast(make_ws_message(WSEvent.PLAYER_JOIN, payload), match_id)
    
    manager.enterMatch(player_id, match_id)
    
    match_service = services.MatchService(db)
    match         = match_service.get_match_by_id(match_id)
    players_count = match_service.count_players_by_match(match_id)
    new_match     = db_match_2_match_schema(match)
    
    match_dict                         = new_match.model_dump(mode='json')
    match_dict["current_player_count"] = players_count
    message_ws                         = make_ws_message(WSEvent.MATCH, match_dict)
    
    await manager.waiting_room_broadcast(message_ws)
    
    return {"match_id": match_id}

@router.post("/{match_id}/start", status_code=status.HTTP_200_OK)
async def start_match(match_id: UUID, db=Depends(get_db)):
    try:
        match = services.MatchService(db).start_game(match_id)

        payload = match.model_dump(mode='json')
        
        await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, payload))
        await manager.specificBroadcast(make_ws_message(WSEvent.MATCH, payload), match_id)
        
        return {"status": "Match started successfully"}
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not start match: {str(e)}")
    
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
    match_dict=db_match_2_match_schema(match).model_dump(mode="json")
    msg=make_ws_message(WSEvent.TURN, match_dict)
    try:
        await manager.specificBroadcast(msg, match_id)
    except Exception as ws_err:
        print(f"[WS] pass_turn broadcast error: {ws_err}")
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
            return {"status": "success", "cards_discarded": len(discarded_cards_ids)}
    except HTTPException as exception:
        raise exception
    
@router.post("/{match_id}/sets", status_code=status.HTTP_201_CREATED)
async def play_set(match_id: UUID, setIn: set_schemas.SetIn, db = Depends(get_db)) -> Optional[set_schemas.MatchSetOut]:
    try:
        #  ---- Create Set y Eliminar cartas (Menos el caso Lady Eileen) ----
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
            payload = match_set.model_dump(mode='json')
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
async def put_down_a_detective(match_id: UUID, set_id:UUID, setIn:set_schemas.AddSetIn, db=Depends(get_db)) -> set_schemas.MatchSetOut:
    try:
        # ---- Verificaciones y Bajar carta al Set ----
        match_card_ids: List[UUID] = setIn.card_ids
        set_service = set_services.SetService(db)
        set_service.add_card_verification(match_card_ids, set_id, setIn.target_player_id, setIn.target_secret_id)
        
        match_set = set_service.get_match_set(set_id, match_id)
        card_name = set_service._get_card_names(match_card_ids)[0]
        
        if match_set.type != SetType.LADY_EILEEN:
        # Actualizamos si es el caso de que agregamos a TOMMY_BERESFORD en  TUPPENCE_BERESFORD y viceversa
            if set_service.beresford_brothers_in_set_two_beresford(card_name, match_set.type.value):
                match_set = set_service.update_setType(set_id, SetType.TWO_BERESFORD)
            payload = match_set.model_dump(mode='json')
            
            # Eliminamos las cartas excepto Lady Eileen
            card_service = card_services.Cards_Services(db)
            for card in setIn.card_ids:
                to_eliminate = True
                eliminate = card_service.discard_card(card, to_eliminate)  
            payload.update({"deleted_cards": [str(uuid) for uuid in match_card_ids]})            
            ws_msj = make_ws_message(WSEvent.SET, payload)
            await manager.specificBroadcast(ws_msj, match_id)

        # ---- Casos posibles para el Worker ----
        set_in_complete = set_schemas.SetIn(
            type=match_set.type,
            card_ids=setIn.card_ids,
            player_id=setIn.player_id,
            target_player_id=setIn.target_player_id,
            target_secret_id=setIn.target_secret_id
        )
    
        # Caso Oliver 
        if card_name == SetType.ADRIADNE_OLIVER.value:
            set_in_Oliver = set_schemas.SetIn(
                type=SetType.ADRIADNE_OLIVER,
                card_ids=setIn.card_ids,
                player_id=setIn.player_id,
                target_player_id=setIn.target_player_id,
                target_secret_id=setIn.target_secret_id
            )
            set_payload = set_services.SetService(db).create_set_payload(match_id, set_in_Oliver, is_Oliver=True)
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                SetType.ADRIADNE_OLIVER.value,
                None,
                set_payload,
            )
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
                "player_id": str(setIn.player_id),
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
                setIn.player_id,
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
            set_payload = set_services.SetService(db).create_set_payload(match_id, setIn, is_Oliver=False)
            set_payload.update({"is_create_set": False})
            set_payload.update({"set_id": str(match_set.id)})
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                set_in_complete.type.value,
                match_card_ids[0],
                set_payload
            )           
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
                "player_id": str(setIn.player_id),
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
            }
            await manager.specificBroadcast(
                make_ws_message(WSEvent.CANCELLATION_WINDOW_OPEN, payload), match_id
            )     
        # Caso otro Detectives                  
        else:
            set_payload = set_services.SetService(db).create_set_payload(match_id, setIn, is_Oliver=False)
            new_event = services_event.EventService(db).create_event(
                match_id,
                setIn.player_id,
                set_in_complete.type.value,
                None,
                set_payload
            )           
            payload = {
                "event_id": str(new_event.id),
                "event_type": set_in_complete.type.value,
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
async def play_event(match_id:UUID,player_id: UUID, match_card_id:UUID, event_payload:dict, db=Depends(get_db)):
    try:
        typeEvent=services_cards.Cards_Services(db).get_name_event(player_id,match_id,match_card_id)
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

            payload = {
                "event_id": str(new_event.id),
                "event_type": typeEvent.value,
                "player_id": player_id,
                "resolve_at_utc": new_event.resolve_at.isoformat(),
                "nsf_count": new_event.nsf_count,
                "discarded_card": None
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
        typeEvent=services_cards.Cards_Services(db).get_name_event(player_id,match_id,match_card_id)
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