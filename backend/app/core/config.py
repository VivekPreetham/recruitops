from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        extra="ignore"
    )

    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_access_ttl_minutes: int = 15

    llm_provider: str = "groq"
    llm_model: str
    llm_temperature: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()