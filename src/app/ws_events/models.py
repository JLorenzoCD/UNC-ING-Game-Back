
from app.models.db import Base
import uuid
import datetime
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

class WsEvent(Base):
    """
    Representa un evento de WebSocket.
    created_at es manejado por postgress por default
    """
    __tablename__ = "ws_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key = True,
        index       = True,
        default     = uuid.uuid4,
    )
    
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id"),
        nullable = False,
        index    = True,
    )

    message: Mapped[str] = mapped_column(
        String,
        nullable =False,
    )
    
    send_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

