from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from  app.models.db import Base

class Secret(Base):

    __tablename__ = "secrets"

    id      = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name    = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)

class Match_Secret(Base):

    __tablename__ = "match_secrets"
 
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    secret_id   = Column(UUID(as_uuid=True), ForeignKey('secrets.id'), index=True, nullable=False)
    match_id    = Column(UUID(as_uuid=True), ForeignKey('matches.id'), index=True, nullable=False)
    player_id   = Column(UUID(as_uuid=True), ForeignKey('players.id'), index=True, nullable=True)
    is_revealed = Column(Boolean, default=False)


    secret = relationship("Secret", backref="match_secrets")
    match  = relationship("Match", backref="match_secrets")
    player = relationship("Player", backref="match_secrets")