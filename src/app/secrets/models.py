import uuid
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


class Secret_Type(PyEnum):
    INNOCENT = "INNOCENT"
    MURDERER = "MURDERER"
    ACCOMPLICE = "ACCOMPLICE"


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    type: Mapped[Secret_Type] = mapped_column(Enum(Secret_Type), index=True, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)


class Match_Secret(Base):
    __tablename__ = "match_secrets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    secret_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("secrets.id"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), index=True, nullable=False
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id"), index=True, nullable=True
    )
    is_revealed: Mapped[bool] = mapped_column(Boolean, default=False)

    secret = relationship("Secret", backref="match_secrets")
    match = relationship("Match", backref="match_secrets")
    player = relationship("Player", backref="match_secrets")
