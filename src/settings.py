"""Defines project settings"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project settings definition"""

    DATABASE_URL : str = "postgresql://admin:admin@localhost:5433/gameDB"

    # Timezone
    DEFAULT_TIMEZONE: str = "Etc/UTC"


settings = Settings()