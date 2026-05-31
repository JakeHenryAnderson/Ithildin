"""Check local-preview resource limits stay bounded and explicit."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from ithildin_api.config import Settings, load_settings

MAX_BYTES_LIMIT = 16 * 1024 * 1024
MAX_SEARCH_RESULTS = 10_000
MAX_GIT_LOG_LIMIT = 1_000
MAX_HTTP_TIMEOUT_SECONDS = 60.0
MAX_HTTP_REDIRECTS = 10


class ResourceLimitError(RuntimeError):
    """Raised when configured local-preview resource limits are not sane."""


@dataclass(frozen=True)
class ResourceLimitSummary:
    source: str
    limits: dict[str, int | float | bool]
    warnings: tuple[str, ...]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-env", action="store_true", help="load settings from env/.env")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    settings = (
        load_settings()
        if args.from_env
        else Settings(admin_token="resource-limit-check-token-000000000000")
    )
    summary = check_resource_limits(settings, source="env" if args.from_env else "defaults")
    payload = {
        "source": summary.source,
        "limits": summary.limits,
        "warnings": list(summary.warnings),
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Resource limit check passed: "
            f"read={summary.limits['max_read_bytes']} "
            f"patch={summary.limits['max_patch_bytes']} "
            f"http={summary.limits['http_max_response_bytes']}"
        )
        for warning in summary.warnings:
            print(f"- warning: {warning}")
    return 0


def check_resource_limits(settings: Settings, *, source: str = "settings") -> ResourceLimitSummary:
    limits: dict[str, int | float | bool] = {
        "max_read_bytes": settings.max_read_bytes,
        "max_patch_bytes": settings.max_patch_bytes,
        "http_max_response_bytes": settings.http_max_response_bytes,
        "http_timeout_seconds": settings.http_timeout_seconds,
        "http_max_redirects": settings.http_max_redirects,
        "search_result_limit": settings.search_result_limit,
        "git_log_limit": settings.git_log_limit,
        "http_allowlist_configured": bool(settings.http_allowlist.strip()),
    }
    failures: list[str] = []
    warnings: list[str] = []
    for key in ("max_read_bytes", "max_patch_bytes", "http_max_response_bytes"):
        value = int(limits[key])
        if value <= 0:
            failures.append(f"{key} must be positive")
        if value > MAX_BYTES_LIMIT:
            failures.append(f"{key} exceeds local-preview ceiling {MAX_BYTES_LIMIT}")
    if settings.search_result_limit > MAX_SEARCH_RESULTS:
        failures.append(f"search_result_limit exceeds local-preview ceiling {MAX_SEARCH_RESULTS}")
    if settings.git_log_limit > MAX_GIT_LOG_LIMIT:
        failures.append(f"git_log_limit exceeds local-preview ceiling {MAX_GIT_LOG_LIMIT}")
    if settings.http_timeout_seconds > MAX_HTTP_TIMEOUT_SECONDS:
        failures.append(
            f"http_timeout_seconds exceeds local-preview ceiling {MAX_HTTP_TIMEOUT_SECONDS}"
        )
    if settings.http_max_redirects > MAX_HTTP_REDIRECTS:
        failures.append(f"http_max_redirects exceeds local-preview ceiling {MAX_HTTP_REDIRECTS}")
    if not settings.http_allowlist.strip():
        warnings.append("http.fetch allowlist is empty, so network fetches deny by default")
    if failures:
        raise ResourceLimitError("; ".join(failures))
    return ResourceLimitSummary(source=source, limits=limits, warnings=tuple(warnings))


if __name__ == "__main__":
    raise SystemExit(main())
