"""Storage backend readiness checks."""

from __future__ import annotations

from ithildin_schemas import JsonObject

from ithildin_api.config import Settings


class StorageConfigurationError(RuntimeError):
    """Raised when runtime storage configuration would be unsafe or misleading."""


SUPPORTED_RUNTIME_BACKENDS = ("sqlite",)


def validate_storage_settings(settings: Settings) -> None:
    backend = settings.storage_backend.strip().lower()
    if backend not in SUPPORTED_RUNTIME_BACKENDS:
        raise StorageConfigurationError(
            f"storage backend {settings.storage_backend!r} is not runtime-enabled; "
            "SQLite is the only supported runtime backend in this preview"
        )


def storage_status(settings: Settings) -> JsonObject:
    backend = settings.storage_backend.strip().lower()
    postgres_configured = bool(settings.postgres_dsn.strip())
    return {
        "runtime_backend": backend,
        "runtime_enabled": backend in SUPPORTED_RUNTIME_BACKENDS,
        "supported_runtime_backends": list(SUPPORTED_RUNTIME_BACKENDS),
        "sqlite": {
            "db_path": settings.db_path.as_posix(),
            "runtime_enabled": backend == "sqlite",
        },
        "postgres": {
            "configured": postgres_configured,
            "dsn_configured": postgres_configured,
            "runtime_enabled": False,
            "readiness": "configured_not_runtime_enabled"
            if postgres_configured
            else "not_configured",
        },
    }
