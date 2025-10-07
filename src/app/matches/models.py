import uuid
from enum import Enum as PyEnum
from sqlalchemy import Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.db import Base


class MatchStatus(PyEnum):
    WAITING     = "Waiting"
    IN_PROGRESS = "In_progress"
    COMPLETED   = "Completed"


class Match(Base):
    """
    Representa una partida (Match).
    """
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key = True,
        index       = True,
        default     = uuid.uuid4,
    )
    
    name: Mapped[str] = mapped_column(
        nullable = False
    )
    
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status"),
        default = MatchStatus.WAITING,
        index   = True,
    )
    
    min_players: Mapped[int] = mapped_column(
        Integer,
        default = 2
    )
    
    max_players: Mapped[int] = mapped_column(
        Integer,
        default = 6
    )
    
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable = False,
        index    = True,
    )
    
    current_player_order: Mapped[int] = mapped_column(
        Integer,
        default = 1
    )
    
    owner = relationship("Player", backref="matches")