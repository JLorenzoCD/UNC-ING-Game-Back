from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from models.db import Base

class Card(Base):

    __tablename__ = "cards"

    id          = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name        = Column(String, index=True, nullable=False)
    description = Column(String, index=True, nullable=False)

class Card_Match(Base):

    __tablename__ = "cards_match"

    id           = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    card_id      = Column(UUID(as_uuid=True), ForeignKey('cards.id'))
    match_id     = Column(UUID(as_uuid=True), ForeignKey('matches.id')) #Necesito que terminen con el modelo de Match
    player_id    = Column(UUID(as_uuid=True), ForeignKey('players.id'), nullable=False)
    is_discarded = Column(Boolean, index=True, default=False)

    card   = relationship("Card", backref="card_matches")
    match  = relationship("Match", backref="card_matches")
    player = relationship("Player", backref="card_matches")