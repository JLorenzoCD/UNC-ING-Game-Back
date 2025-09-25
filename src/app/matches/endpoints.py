from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from app.matches.utils import start_match

router = APIRouter(
    tags=["matches"],
    prefix="/matches"
)

@router.post("/{id_match}/start", status_code=status.HTTP_200_OK)
async def start_match(id_match: UUID):
    try:
        start_match(id_match)
        return {"message": "Match started successfully"}
    except Exception as exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exception))