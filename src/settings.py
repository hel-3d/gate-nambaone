from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service
    WEB_SERVICE_HOST: str = "0.0.0.0"
    WEB_SERVICE_PORT: int = 8000
    LOG_LEVEL: str = "info"
    DEBUG: bool = False

    # Provider
    NAMBAONE_BASE_URL: str = "https://api.example.test"
    NAMBAONE_MERCHANT_ID: str = ""
    NAMBAONE_SECRET: str = ""
    NAMBAONE_CALLBACK_URL: str = "http://localhost:8000/notifications/invoice"

    # HTTP
    REQUEST_TIMEOUT: float = Field(default=15.0, gt=0)
    PROXY_URL: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()