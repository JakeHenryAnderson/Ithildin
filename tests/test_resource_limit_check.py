from __future__ import annotations

import pytest
from ithildin_api.config import Settings

from scripts.resource_limit_check import ResourceLimitError, check_resource_limits


def test_default_resource_limits_pass() -> None:
    summary = check_resource_limits(
        Settings(admin_token="resource-limit-check-token-000000000000"),
        source="test",
    )

    assert summary.source == "test"
    assert summary.limits["max_read_bytes"] == 131_072
    assert summary.limits["max_patch_bytes"] == 131_072
    assert summary.limits["http_max_response_bytes"] == 131_072
    assert summary.limits["http_allowlist_configured"] is False
    assert "http.fetch allowlist is empty" in summary.warnings[0]


def test_resource_limit_check_rejects_oversized_limits() -> None:
    with pytest.raises(ResourceLimitError, match="max_read_bytes exceeds"):
        check_resource_limits(
            Settings(
                admin_token="resource-limit-check-token-000000000000",
                max_read_bytes=64 * 1024 * 1024,
            )
        )


def test_resource_limit_check_reports_allowlist_configured() -> None:
    summary = check_resource_limits(
        Settings(
            admin_token="resource-limit-check-token-000000000000",
            http_allowlist="https://example.com",
        )
    )

    assert summary.limits["http_allowlist_configured"] is True
    assert summary.warnings == ()
