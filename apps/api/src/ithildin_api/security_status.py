"""Public-preview security boundary checks and status."""

from __future__ import annotations

from ithildin_schemas import JsonObject, JsonValue

from ithildin_api.config import DEV_ADMIN_TOKEN, Settings

LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


class SecurityConfigurationError(RuntimeError):
    """Raised when local-preview security configuration is unsafe."""


def validate_security_settings(settings: Settings) -> None:
    if settings.admin_token == DEV_ADMIN_TOKEN and not settings.allow_dev_admin_token:
        raise SecurityConfigurationError(
            "sample admin token requires ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=true"
        )


def security_status(settings: Settings) -> JsonObject:
    warnings: list[JsonValue] = []
    dev_token_active = settings.admin_token == DEV_ADMIN_TOKEN
    if dev_token_active and settings.allow_dev_admin_token:
        warnings.append("sample admin token is enabled for local demo use")
    if settings.storage_backend.strip().lower() != "sqlite":
        warnings.append("unsupported runtime storage backend requested")
    if settings.otel_enabled:
        warnings.append("OpenTelemetry preview export is enabled")

    return {
        "preview_label": "v0.1 local-preview",
        "production_ready": False,
        "dev_admin_token": {
            "sample_token_active": dev_token_active,
            "explicitly_allowed": settings.allow_dev_admin_token,
        },
        "local_only": {
            "api_host_publish": "127.0.0.1:8000 in Compose",
            "ui_host_publish": "127.0.0.1:5173 in Compose",
            "remote_mcp_enabled": False,
        },
        "cors": {
            "allow_credentials": False,
            "allow_origins": list(LOCAL_CORS_ORIGINS),
            "wildcard_allowed": False,
        },
        "warnings": warnings,
    }
