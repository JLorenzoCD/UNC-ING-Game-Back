from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message
from app.matches.utils import db_match_2_match_schema
from app.models.db import get_db
from app.player.models import Player
from app.matches import services
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
from app.cards.schemas import (take_discard_Match_Cards_in, Match_Card_Schema)
from app.sets import schemas as set_schemas
from app.sets import services as set_services
from app.sets.models import Match_Set, SetType
from app.secrets import services as secret_services
from app.secrets import schemas as secret_schemas
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


@router.put("/{match_id}/cards", status_code=status.HTTP_200_OK)
async def take_discard_cards(match_id: UUID, cards: take_discard_Match_Cards_in, db = Depends(get_db)):
    try:
        player_id           = cards.player_id
        taken_cards_ids     = cards.taken_card_ids
        discarded_cards_ids = cards.discarded_card_ids

        len_taken_cards_ids     = len(taken_cards_ids)
        len_discarded_cards_ids = len(discarded_cards_ids)
        len_match_cards         = len(services.MatchService(db).get_cards_by_match(match_id))

        if (len_match_cards < len_taken_cards_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes tomar más cartas de las que quedan en el mazo"})
        elif (len_taken_cards_ids > 6):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"No puedes tomar mas de 6 cartas"})
        elif (len_taken_cards_ids == len_discarded_cards_ids):
            services.PileService(db).take_cards(player_id, taken_cards_ids)
            services.PileService(db).discard_cards(player_id, discarded_cards_ids)
            
            ids = list(set(taken_cards_ids + discarded_cards_ids))

            results = services.MatchService(db).get_extended_cards_by_match(match_id, ids)

            payload = [
                {
                "id": r[0],
                "card_id": r[1],
                "match_id": r[2],
                "player_id": r[3],
                "is_discarded": r[4],
                "discarded_at": r[5],
                "name": r[6],
                "type": r[7].value if hasattr(r[7], 'value') else r[7],
                "description": r[8],
                }
                for r in results
            ]

            await manager.specificBroadcast(make_ws_message(WSEvent.CARDS, payload), match_id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error":"Error al procesar las cartas"})
    except HTTPException as exception:
        raise exception
    
@router.post("/{match_id}/sets", status_code=status.HTTP_201_CREATED)
async def play_set(match_id: UUID, setIn: set_schemas.SetIn, db = Depends(get_db)) -> set_schemas.MatchSetOut:
    try:
        # Create Set
        match_card_ids: List[UUID] = setIn.card_ids
        set_service = set_services.SetService(db)
        set_service.set_verification(match_card_ids, match_id, setIn.type, setIn.target_player_id, setIn.target_secret_id)
        set_data = {    
            "type" : setIn.type,
            "card_ids": match_card_ids,
            "player_id": setIn.player_id,
            "match_id": match_id           
        }
        match_set: set_schemas.MatchSetOut = set_service.create_set(set_data)
        match_set_dict = match_set.model_dump(mode='json')
        ws_msj = make_ws_message(WSEvent.SET, match_set_dict)
        await manager.specificBroadcast(ws_msj, match_id)
        
        # Accion del Set (Casos)
        secret_service = secret_services.Secrets_Services(db)
        if setIn.target_secret_id is not None:
            if match_set.type in (SetType.HERCULE_POIROT or SetType.MISS_MARPLE):
                target_secret = secret_service.update_secret(secret_services.Secret_action.REVEAL, setIn.target_secret_id, setIn.target_player_id)
                match_secret_out = db_match_secret_2_match_secret_schema(target_secret)
                
            if match_set.type is (SetType.PARKER_PYNE):
                target_secret = secret_service.update_secret(secret_services.Secret_action.HIDE, setIn.target_secret_id, setIn.target_player_id)
                match_secret_out = db_match_secret_2_match_secret_schema(target_secret)

            payload = match_secret_out.model_dump(mode='json')
            ws_msj = make_ws_message(WSEvent.SECRET, payload)
            await manager.specificBroadcast(ws_msj, match_id)
            
        else:
            payload = {"target_player_id" : setIn.target_player_id}
            ws_msj = make_ws_message(WSEvent.PLAYER_SECRET_REVEAL, payload)
            await manager.specificBroadcast(ws_msj, match_id)
        
           
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