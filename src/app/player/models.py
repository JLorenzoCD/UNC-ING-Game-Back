from sqlalchemy import Column, Integer, String, Date, Table, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from typing import List
from sqlalchemy.orm import Mapped
from models.db import Base
from datetime import date
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Player(Base):
    """
    Represent a Player

    """

    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),               # usa UUID en Postgres
        primary_key=True,
        index=True,
        default=uuid.uuid4               # genera UUID automáticamente
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date,nullable=False)