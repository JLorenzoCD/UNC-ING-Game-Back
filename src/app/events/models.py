import uuid
from enum import Enum as PyEnum
from sqlalchemy import Integer, ForeignKey, Enum, String, TIMESTAMP, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.db import Base
from app.cards.models import Match_Card
from app.matches.models import Match
from app.player.models import Player 

class EventStatus(PyEnum):
    PENDING     = "Pending"
    RESOLVED    = "Resolved"
    CANCELLED   = "Cancelled"
    PENDING_TARGET_RESPONSE = "Pending_Target_Response" #para eventos compuestos

class EventosDeTurno(Base):
    """
    Representa un evento de una partida.
    status, nsd_count, created_at y resolve_at son manejados por postgress por default
    """
    __tablename__ = "eventos_de_turno"
    
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
    
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        nullable = False,
        index    = True,
    )

    match_card_id: Mapped[uuid.UUID] =mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_cards.id"),
        nullable=True,
        index=True
    )

    event_type: Mapped[str] = mapped_column(
        String,
        nullable =False,
        index = True
    )
    
    status: Mapped[EventStatus] = mapped_column(
        String(50),
        server_default = "Pending",
        index   = True,
        nullable=False
    )
    
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable = True
    )
    #las cartas involucradas en el set que vayan en el payload y match_card_id NULL
    
    nsf_count: Mapped[int] = mapped_column(
        Integer,
        server_default = text("0"), #se pasa como text para que lo interprete solo
        nullable = False
    )
    
    resolve_at: Mapped[DateTime] = mapped_column(
        TIMESTAMP(timezone=True), #normaliza todos los horarios a UTC(horario universal)
        nullable = False,
        server_default = func.now() + text("'5 seconds'::interval"), #se pasa como text para que lo interprete solo
        index = True
    )
    
    created_at: Mapped[DateTime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    match = relationship("Match", back_populates="events")
    player = relationship("Player")
    event_card=relationship("Match_Card")