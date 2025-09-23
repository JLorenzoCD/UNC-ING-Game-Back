from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQlEnum, Enum


from app.models.db import Base

class Card_Type(PyEnum):
    EVENT     = "EVENT"
    DEVIUS    = "DEVIOUS"
    DETECTIVE = "DETECTIVE"
    INSTANT   = "INSTANT"

class Card(Base):

    __tablename__ = "cards"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name        = Column(String, index=True, nullable=False)
    type        = Column(Enum(Card_Type), index=True, nullable=False)
    description = Column(String, nullable=False)

class Match_Card(Base):

    __tablename__ = "match_cards"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    card_id      = Column(UUID(as_uuid=True), ForeignKey('cards.id'), index=True, nullable=False)
    match_id     = Column(UUID(as_uuid=True), ForeignKey('matches.id'), index=True, nullable=False) 
    player_id    = Column(UUID(as_uuid=True), ForeignKey('players.id'), index=True, nullable=True)
    is_discarded = Column(Boolean, default=False)

    card   = relationship("Card", backref="match_cards")
    match  = relationship("Match", backref="match_cards")
    player = relationship("Player", backref="match_cards")