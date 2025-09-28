from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends
from app.models.db import get_db
from uuid import UUID
from typing import List, Optional
from websocketManager.ws_routes import manager
from websocketManager.ws_messages import WSEvent, make_ws_message

from app.matches import services
from app.matches.schemas import MatchIn, MatchOut, MatchResponse, MatchDTO, Players_by_Match_Schema, Match_number_of_Player

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

@router.get("/{ID_match}", status_code=status.HTTP_200_OK, response_model=MatchOut)
async def get_match_by_match_ID(ID_match: UUID, db=Depends(get_db)) -> MatchOut:
    try:
        match: MatchOut = services.MatchService(db).get_match_by_id(ID_match)
    except Exception:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return match

@router.get("/{ID_match}/players", status_code=status.HTTP_200_OK, response_model=List[Players_by_Match_Schema])
async def get_player_by_ID_match(ID_match: UUID, db=Depends(get_db)) -> List[Players_by_Match_Schema]:
    try:
        players_match: List[Players_by_Match_Schema] = services.MatchService(db).get_players_by_match(ID_match)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")

    return players_match