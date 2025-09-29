from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message

from app.models.db import get_db
from app.player.models import Player
from app.matches import services
from app.matches.models import MatchStatus
from app.matches.schemas import (
    Cards_by_Match_Schema,
    MatchIn,
    MatchOut,
    MatchResponse,
    MatchDTO,
    Players_by_Match_Schema,
    Match_number_of_Player,
)


router = APIRouter(
    tags=["matches"],
    prefix="/matches"
)    

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MatchResponse)
async def create_match(match_in: MatchIn, 
                       db=Depends(get_db)
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

    match_dict = new_match.model_dump(mode='json')
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
        match: MatchOut = services.MatchService(db).get_match_by_id(match_id)
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
async def join_match(match_id: UUID,player_id: UUID, db=Depends(get_db)):
    #Para el futuro estaria bien hacer services de player
    info_player = db.query(Player).filter(Player.id == player_id).first()
    if not info_player:
        raise HTTPException(status_code=404, detail="Player not found")
    services.MatchService(db).join(match_id, player_id) 
    payload={
        "id": info_player.id,
        "name": info_player.name,
        "avatar": info_player.avatar,
        "birthday": info_player.birthday
    }
    await manager.specificBroadcast(make_ws_message(WSEvent.PLAYER_JOIN, payload), match_id)
    manager.enterMatch(player_id, match_id)

    match_service = services.MatchService(db)
    match = match_service.get_match_by_id(match_id)
    players_count = match_service.count_players_by_match(match_id)

    #payload para WS
    match_payload = {
        "id_match": str(match.id),
        "name": match.name,
        "status": match.status.value,   # asumiendo que es Enum
        "min_players": match.min_players,
        "max_players": match.max_players,
        "id_creator": str(match.owner_id),
        "current_player_count": players_count
    }   

    message_ws = make_ws_message(WSEvent.MATCH, match_payload)
    await manager.waiting_room_broadcast(message_ws)

    return {"match_id": match_id}

@router.post("/{match_id}/start", status_code=status.HTTP_200_OK)
async def start_match(match_id: UUID, db=Depends(get_db)):
    try:
        services.MatchService(db).start_game(match_id)
        payload = {
            "status": MatchStatus.IN_PROGRESS.value
        }
        await manager.waiting_room_broadcast(make_ws_message(WSEvent.MATCH, payload))
        return {"status": "Match started successfully"}

    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not start match: {str(e)}")
    
@router.get("/{match_id}/secrets", status_code=status.HTTP_200_OK)
async def get_secrets(match_id: UUID, db=Depends(get_db)):
    secrets=services.MatchService(db).get_secrets_by_match(match_id)
    return secrets

@router.get("/{match_id}/cards", status_code=status.HTTP_200_OK, response_model=List[Cards_by_Match_Schema])
async def get_cards(match_id: UUID, db = Depends(get_db)):
    try:
        cards = services.MatchService(db).get_cards_by_match(match_id)
    except services.SQLAlchemyError:
        raise HTTPException(status_code=500)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return cards
