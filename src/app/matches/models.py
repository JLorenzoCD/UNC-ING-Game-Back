from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.orm import Mapped
from app.models.db import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQlEnum, Enum
from app.secrets.models import Secret_Type


class MatchStatus(PyEnum):
    WAITING = "Waiting"
    IN_PROGRESS = "In_progress" 
    COMPLETED = "Completed"
    
class Match(Base):  
    """
    
    Represent a Match
    
    """
    
    __tablename__ = 'matches'
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )
    name: Mapped[String] = mapped_column(String) # nullable=False (inferido automáticamente)
    status: Mapped[MatchStatus] = mapped_column(
        SQlEnum(MatchStatus, name="match_status"), 
        default=MatchStatus.WAITING,
        index=True
    )
    min_players: Mapped[int] = mapped_column(Integer, default=2)
    max_players: Mapped[int] = mapped_column(Integer, default=6)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('players.id'),
        nullable=False,
        index=True
    )
    current_player_order: Mapped[int] = mapped_column(Integer, default=0)
    
    owner = relationship("Player", backref="matches")
    
class Match_Player(Base):
        
        """"
        
        Tabla intermedia que representa la relacion Match <-> Player
        
        """
        
        __tablename__ = 'match_players'
        
        player_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True),
            ForeignKey('players.id'),
            primary_key=True,
            nullable=False,
            index=True
        )
        match_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True),
            ForeignKey('matches.id'),
            primary_key=True,
            nullable=False,
            index=True
        )
        role: Mapped[Secret_Type] = mapped_column(Enum(Secret_Type), nullable=True, index=True)
        order: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
        
        match  = relationship("Match", backref="match_players")
        player = relationship("Player", backref="match_players")