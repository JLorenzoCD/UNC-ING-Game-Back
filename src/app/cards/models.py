from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


class Card_Type(PyEnum):
    """Class Card_Type."""

    EVENT = "EVENT"
    DEVIOUS = "DEVIOUS"
    DETECTIVE = "DETECTIVE"
    INSTANT = "INSTANT"


class Card(Base):
    """Class Card."""

    __tablename__ = "cards"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    type: Mapped[Card_Type] = mapped_column(Enum(Card_Type), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)


class Match_Card(Base):
    """Class Match_Card."""

    __tablename__ = "match_cards"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    card_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id"), index=True, nullable=False
    )
    match_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), index=True, nullable=False
    )
    player_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), index=True, nullable=True
    )
    is_discarded: Mapped[bool] = mapped_column(Boolean, default=False)
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    card = relationship("Card", backref="match_cards")
    match = relationship("Match", backref="match_cards")
    player = relationship("Player", backref="match_cards")
