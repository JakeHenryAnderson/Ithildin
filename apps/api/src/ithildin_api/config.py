"""Configuration for the Ithildin API service."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ITHILDIN_",
        extra="ignore",
    )

    admin_token: str = Field(min_length=1)
    db_path: Path = Path("var/db/ithildin.sqlite3")
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
