import uuid
from enum import Enum as PyEnum
from sqlalchemy import Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.models.db import Base


class MatchStatus(PyEnum):
    WAITING     = "Waiting"
    IN_PROGRESS = "In_progress"
    COMPLETED   = "Completed"

class MatchEventType(PyEnum):
    # System events
    PLAYER_JOIN = "Player Join"
    TURN = "Turn"
    
    # Detective events
    HERCULE_POIROT = "Hercule Poirot"
    MISS_MARPLE = "Miss Marple"
    MR_SATTERTHWAITE = "Mr Satterthwaite"
    MR_SATTERTHWAITE_QUIN = "Mr Satterthwaite & Quin"
    PARKER_PYNE = "Parker Pyne"
    LADY_EILEEN = "Lady Eileen"
    TOMMY_BERESFORD = "Tommy Beresford"
    TUPPENCE_BERESFORD = "Tuppence Beresford"
    TWO_BERESFORD = "Two Beresford"

    ARIADNE_OLIVER = "Ariadne Oliver"

    # Event cards
    CARDS_OFF_THE_TABLE = "Cards Off The Table"
    ANOTHER_VICTIM = "Another Victim"
    DEAD_CARD_FOLLY = "Dead Card Folly"
    LOOK_INTO_THE_ASHES = "Look Into The Ashes"
    CARD_TRADE = "Card Trade"
    AND_THEN_THERE_WAS_ONE_MORE = "And Then There Was One More"
    DELAY_THE_MURDERER_ESCAPE = "Delay The Murderer Escape"
    EARLY_TRAIN_TO_PADDINGTON = "Early Train To Paddington"
    POINT_YOUR_SUSPICIONS = "Point Your Suspicions"

    # Devious cards
    BLACKMAILED = "Blackmailed"
    SOCIAL_FAUX_PAS = "Social Faux Pas"

    # Card actions
    DISCARD_CARDS = "Discard Cards"
    TAKE_CARDS = "Take Cards"


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
    events = relationship("EventosDeTurno", back_populates="match")

class MatchLogs(Base):
    """
    Representa los logs de una partida (Match).
    """
    __tablename__ = "match_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key = True,
        index       = True,
        default     = uuid.uuid4,
    )
    
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id"),
        nullable = False,
        index    = True,
    )
    
    message: Mapped[str] = mapped_column(
        nullable = False
    )

    created_at: Mapped[datetime] = mapped_column(
        default = datetime.utcnow
    )

    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable = True,
        index    = True
    )

    event_type: Mapped[MatchEventType] = mapped_column(
        Enum(MatchEventType, name="match_event_type", values_callable=lambda obj: [e.name for e in obj]),
        nullable = False
    )

    match = relationship("Match", backref="match_logs")
    player = relationship("Player", backref="match_logs")
