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
    audit_log_path: Path = Path("var/logs/audit.jsonl")
    db_path: Path = Path("var/db/ithildin.sqlite3")
    manifest_dir: Path = Path("tool-manifests")
    policy_path: Path = Path("policies/default.yaml")
    approval_expiry_seconds: int = Field(default=900, gt=0)
    workspace_root: Path = Path("workspaces")
    max_read_bytes: int = Field(default=131_072, gt=0)
    search_result_limit: int = Field(default=100, gt=0)
    git_log_limit: int = Field(default=20, gt=0)
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
