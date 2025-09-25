from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Depends
from app.models.db import get_db
from uuid import UUID

from app.matches import services
from app.matches.schemas import MatchIn, MatchOut, MatchResponse, MatchDTO

router = APIRouter(
    tags=["matches"],
    prefix="/matches"
)    

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_match(match_in: MatchIn, db=Depends(get_db)) -> MatchResponse:
    try:
        match_dto = match_in.to_dto()
        new_match = services.MatchService(db).create(match_dto)
        return new_match
    except services.OwnerNotFound:
        raise HTTPException(status_code=404, detail="Owner not found")
    except services.MatchNotFound:
        raise HTTPException(status_code=404, detail="Match not found")
    except services.MatchValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        