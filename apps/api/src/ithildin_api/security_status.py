"""Public-preview security boundary checks and status."""

from __future__ import annotations

from ithildin_schemas import JsonObject, JsonValue

from ithildin_api.config import DEV_ADMIN_TOKEN, Settings

RECOMMENDED_ADMIN_TOKEN_LENGTH = 32

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
    token_has_whitespace = settings.admin_token.strip() != settings.admin_token or any(
        character.isspace() for character in settings.admin_token
    )
    token_length_ok = len(settings.admin_token) >= RECOMMENDED_ADMIN_TOKEN_LENGTH
    if dev_token_active and settings.allow_dev_admin_token:
        warnings.append("sample admin token is enabled for local demo use")
    if token_has_whitespace:
        warnings.append("admin token contains whitespace")
    if not dev_token_active and not token_length_ok:
        warnings.append("admin token is shorter than the recommended local minimum")
    if settings.storage_backend.strip().lower() != "sqlite":
        warnings.append("unsupported runtime storage backend requested")
    if settings.otel_enabled:
        warnings.append("OpenTelemetry preview export is enabled")

    return {
        "preview_label": "v0.2 review candidate for v0.1 local-preview runtime boundary",
        "production_ready": False,
        "dev_admin_token": {
            "sample_token_active": dev_token_active,
            "explicitly_allowed": settings.allow_dev_admin_token,
        },
        "admin_token": {
            "recommended_min_length": RECOMMENDED_ADMIN_TOKEN_LENGTH,
            "length_ok": token_length_ok,
            "contains_whitespace": token_has_whitespace,
            "weak": token_has_whitespace or (not dev_token_active and not token_length_ok),
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
