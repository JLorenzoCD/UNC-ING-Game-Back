from sqlalchemy import Column, Integer, String, Date, Table, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from models.db import Base
from datetime import date
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Match(Base):
    """
    
    Represent a Match
    
    """
    
    __tablename__ = 'matches'
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )
    name: Mapped[String] = mapped_column(String) # nullable=False (inferido automáticamente)
    status: Mapped[String] = mapped_column(String) # Crear tipo enum para status
    min_player: Mapped[int] = mapped_column(Integer, default=2)
    max_player: Mapped[int] = mapped_column(Integer, default=6)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("players.id"),
        nullable=False,
        index=True
    )
    current_player_order: Mapped[int] = mapped_column(int)