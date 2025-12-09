from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.secrets.models import Secret_action, Secret_Type


class Secret_Schema(BaseModel):
    """Class Secret_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: Secret_Type
    content: str


class Match_Secret_Schema(BaseModel):
    """Class Match_Secret_Schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    secret_id: UUID
    match_id: UUID
    player_id: UUID
    is_revealed: bool


class SecretUpdate(BaseModel):
    """Class SecretUpdate."""

    target_player_id: UUID
    action: Secret_action
