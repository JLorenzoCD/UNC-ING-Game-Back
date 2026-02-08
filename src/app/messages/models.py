import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base
from app.matches.models import MatchEventType


class MatchMessage(Base):
    """
    Representa los mensajes de una partida (Match), tanto del sistema como de
    los jugadores.
    """

    __tablename__ = "match_messages"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), nullable=True, index=True
    )
    event_type: Mapped[MatchEventType] = mapped_column(
        Enum(
            MatchEventType,
            name="match_event_type",
            values_callable=lambda obj: [e.name for e in obj],
        ),
        nullable=False,
    )
    is_system_msg: Mapped[bool] = mapped_column(Boolean, default=True)

    match = relationship("Match", backref="match_messages")
    player = relationship("Player", backref="match_messages")
