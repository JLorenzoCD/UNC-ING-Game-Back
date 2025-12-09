from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project settings definition"""

    DATABASE_URL: str = "postgresql://admin:admin@localhost:5433/gameDB"
    DEFAULT_TIMEZONE: str = "Etc/UTC"


settings = Settings()
