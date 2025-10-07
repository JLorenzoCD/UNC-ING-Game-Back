from uuid import uuid4
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.db import Base


class Card_Type(PyEnum):
    EVENT     = "EVENT"
    DEVIOUS   = "DEVIOUS"
    DETECTIVE = "DETECTIVE"
    INSTANT   = "INSTANT"


class Card(Base):
    __tablename__ = "cards"

    id          : Mapped[UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name        : Mapped[str]       = mapped_column(String, index=True, nullable=False)
    type        : Mapped[Card_Type] = mapped_column(Enum(Card_Type), index=True, nullable=False)
    description : Mapped[str]       = mapped_column(String, nullable=False)


class Match_Card(Base):
    __tablename__ = "match_cards"

    id          : Mapped[UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    card_id     : Mapped[UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("cards.id"), index=True, nullable=False)
    match_id    : Mapped[UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), index=True, nullable=False)
    player_id   : Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), index=True, nullable=True)
    is_discarded: Mapped[bool]      = mapped_column(Boolean, default=False)

    card   = relationship("Card",  backref="match_cards")
    match  = relationship("Match", backref="match_cards")
    player = relationship("Player", backref="match_cards")
