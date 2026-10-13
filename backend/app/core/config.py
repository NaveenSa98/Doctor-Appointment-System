"""Typed application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets come from the environment, never from code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str
    database_url_migrations: str | None = None
    jwt_secret: str = Field(min_length=32)
    cors_origins: str = "http://localhost:5173"

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_origin(cls, value: str) -> str:
        """Refuse to start with a wildcard CORS origin."""
        if "*" in [origin.strip() for origin in value.split(",")]:
            raise ValueError("CORS_ORIGINS must be an explicit allowlist, not a wildcard")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (loaded once)."""
    return Settings()  # type: ignore[call-arg]
