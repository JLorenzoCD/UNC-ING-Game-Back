import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base
from app.secrets.models import Secret_Type


class Player(Base):
    """
    Representa un jugador
    """

    __tablename__ = "players"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)


class Match_Player(Base):
    """
    Tabla intermedia que representa la relación Match <-> Player.
    """

    __tablename__ = "match_players"
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("players.id"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    role: Mapped[Secret_Type] = mapped_column(
        Enum(Secret_Type), nullable=True, index=True
    )
    order: Mapped[int] = mapped_column(
        Integer, nullable=True, index=True, default=0)
    match = relationship("Match", backref="match_players")
    player = relationship("Player", backref="match_players")
