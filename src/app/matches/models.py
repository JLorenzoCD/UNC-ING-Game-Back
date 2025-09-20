from sqlalchemy import Column, Integer, String, Date, Table, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from models.db import Base
from datetime import date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from sqlalchemy import Enum as SQLEnum


class MatchStatus(Enum):
    WAITING = "Waiting"
    IN_PROGRESS = "In_progress" 
    COMPLETED = "Completed"
    
class SecretType(Enum):
    INOCENT = "Inocent"
    MURDERER = "Murderer"
    ACCOMPLICE = "Accomplice"

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
        Enum(MatchStatus), 
        default=MatchStatus.WAITING,
        index=True
    )
    min_player: Mapped[int] = mapped_column(Integer, default=2)
    max_player: Mapped[int] = mapped_column(Integer, default=6)
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
        
        
        
        """
        
        __tablename__ = 'match_players'
        
        player_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True),
            ForeignKey('players.id'),
            nullable=False,
            index=True
        )
        match_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True),
            ForeignKey('matches.id'),
            nullable=False,
            index=True
        )
        role: Mapped[SecretType] = mapped_column(SecretType, ForeignKey('secrets.type'), nullable=True, index=True)
        order: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
        
        match  = relationship("Match", backref="match_players")
        player = relationship("Player", backref="match_players")
        secret = relationship("Secret", backref="matches_players")