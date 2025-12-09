import uuid
from enum import Enum as PyEnum

from sqlalchemy import TIMESTAMP, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.db import Base


class EventStatus(PyEnum):
    """Class EventStatus."""

    PENDING = "Pending"
    RESOLVED = "Resolved"
    CANCELLED = "Cancelled"
    PENDING_TARGET_RESPONSE = "Pending_Target_Response"


class EventosDeTurno(Base):
    """
    Representa un evento de una partida.
    status, nsd_count, created_at y resolve_at son manejados por postgress por default
    """

    __tablename__ = "eventos_de_turno"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True
    )
    match_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("match_cards.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[EventStatus] = mapped_column(String(50), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    nsf_count: Mapped[int] = mapped_column(Integer, nullable=False)
    resolve_at: Mapped[DateTime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    match = relationship("Match", back_populates="events")
    player = relationship("Player")
    event_card = relationship("Match_Card")
