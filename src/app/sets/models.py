import uuid
from enum import Enum as PyEnum
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.db import Base

class SetType(PyEnum):
    PARKER_PYNE = "Parker_Pyner"
    LADY_EILEEN = "Lady_Eileen"
    ONE_BERESFORD = "One_Beresford"
    TWO_BERESFORD = "Two_Beresford"
    HERCULE_POIROT = "Hercule_Poirot"
    MISS_MARPLE = "Miss_Marple"
    MR_SATTERTHWAITE = "Mr_Satterthwaite"

class Match_Set (Base):
    """
    Representa un Set de detectives cuando se 
    juega en la Partida
    """
    
    __tablename__= "match_sets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid = True),
        primary_key  = True,
        index        = True,
        default      = uuid.uuid4
    )
    
    type: Mapped[SetType] = mapped_column(
        Enum(SetType, name = "type")
    )
    
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid = True),
        ForeignKey("players.id"),
        index        = True,
        nullable     = False
    )
    
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid = True),
        ForeignKey("matches.id"),
        index        = True,
        nullable     = False
    )
    
    match  = relationship("Match", backref="match_sets")
    player = relationship("Player", backref="match_sets")