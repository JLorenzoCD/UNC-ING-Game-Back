import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


class SetType(PyEnum):
    """Class SetType."""

    PARKER_PYNE = "PARKER PYNE"
    LADY_EILEEN = "LADY EILEEN"
    TOMMY_BERESFORD = "TOMMY BERESFORD"
    TUPPENCE_BERESFORD = "TUPPENCE BERESFORD"
    TWO_BERESFORD = "TWO BERESFORD"
    HERCULE_POIROT = "HERCULE POIROT"
    MISS_MARPLE = "MISS MARPLE"
    MR_SATTERTHWAITE = "MR SATTERTHWAITE"
    ADRIADNE_OLIVER = "ARIADNE OLIVER"


class Match_Set(Base):
    """
    Representa un Set de detectives cuando se
    juega en la Partida
    """

    __tablename__ = "match_sets"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    type: Mapped[SetType] = mapped_column(Enum(SetType, name="type"))
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), index=True, nullable=False
    )
    quin_play: Mapped[bool] = mapped_column(Boolean, default=False)
    quin_count: Mapped[int] = mapped_column(Integer, default=0)
    match = relationship("Match", backref="match_sets")
    player = relationship("Player", backref="match_sets")
