"""Configuration for the Ithildin API service."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_ADMIN_TOKEN = "dev-admin-token-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ITHILDIN_",
        extra="ignore",
    )

    admin_token: str = Field(min_length=1)
    allow_dev_admin_token: bool = False
    audit_log_path: Path = Path("var/logs/audit.jsonl")
    audit_signing_private_key_path: Path = Path("var/keys/audit-ed25519-private.pem")
    audit_signing_public_key_path: Path = Path("var/keys/audit-ed25519-public.pem")
    db_path: Path = Path("var/db/ithildin.sqlite3")
    storage_backend: str = "sqlite"
    postgres_dsn: str = ""
    manifest_dir: Path = Path("tool-manifests")
    manifest_lock_path: Path = Path("tool-manifests.lock.json")
    require_manifest_lock: bool = True
    manifest_lock_signing_private_key_path: Path = Path(
        "var/keys/manifest-lock-ed25519-private.pem"
    )
    manifest_lock_signing_public_key_path: Path = Path(
        "var/keys/manifest-lock-ed25519-public.pem"
    )
    manifest_lock_signature_path: Path = Path("var/signatures/tool-manifests.lock.sig.json")
    require_signed_manifest_lock: bool = False
    principal_registry_path: Path = Path("principals/local.yaml")
    require_known_principals: bool = True
    policy_path: Path = Path("policies/default.yaml")
    policy_engine: str = "yaml"
    opa_url: str = ""
    opa_decision_path: str = "/v1/data/ithildin/decision"
    opa_bundle_manifest_path: Path = Path("policies/opa/bundle.lock.json")
    approval_expiry_seconds: int = Field(default=900, gt=0)
    workspace_root: Path = Path("workspaces")
    max_read_bytes: int = Field(default=131_072, gt=0)
    max_patch_bytes: int = Field(default=131_072, gt=0)
    http_allowlist: str = ""
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    http_max_response_bytes: int = Field(default=131_072, gt=0)
    http_max_redirects: int = Field(default=3, ge=0)
    redaction_extra_keys: str = ""
    redaction_extra_patterns: str = ""
    search_result_limit: int = Field(default=100, gt=0)
    git_log_limit: int = Field(default=20, gt=0)
    otel_enabled: bool = False
    otel_service_name: str = "ithildin-api"
    otel_console_export: bool = False
    otel_otlp_endpoint: str = ""
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
