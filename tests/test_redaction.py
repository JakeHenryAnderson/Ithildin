from __future__ import annotations

from ithildin_api.redaction import REDACTED_VALUE, RedactionService


def test_redaction_redacts_sensitive_keys_recursively() -> None:
    service = RedactionService()

    result = service.redact(
        {
            "Authorization": "Bearer raw-token",
            "nested": {"api_key": "secret-key"},
            "items": [{"password": "secret-password"}],
            "safe": "visible",
        }
    )

    assert result.value == {
        "Authorization": REDACTED_VALUE,
        "nested": {"api_key": REDACTED_VALUE},
        "items": [{"password": REDACTED_VALUE}],
        "safe": "visible",
    }
    assert result.summary.count == 3
    assert result.summary.paths == ("$.Authorization", "$.nested.api_key", "$.items[0].password")


def test_redaction_redacts_builtin_secret_patterns() -> None:
    service = RedactionService()
    private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "super-secret-material\n"
        "-----END PRIVATE KEY-----"
    )

    result = service.redact(
        {
            "bearer": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "assignment": "TOKEN=secret-value",
            "github": "ghp_abcdefghijklmnopqrstuvwxyz123456",
            "openai": "sk-abcdefghijklmnopqrstuvwxyz123456",
            "private": private_key,
        }
    )

    rendered = str(result.value)
    assert "abcdefghijklmnopqrstuvwxyz" not in rendered
    assert "secret-value" not in rendered
    assert "super-secret-material" not in rendered
    assert result.summary.count == 5


def test_redaction_applies_extra_keys_and_patterns() -> None:
    service = RedactionService(extra_keys={"customer_id"}, extra_patterns=[r"acct_[0-9]+"])

    result = service.redact(
        {
            "customer_id": "cust_123",
            "message": "account acct_12345 is visible",
        }
    )

    assert result.value["customer_id"] == REDACTED_VALUE
    assert result.value["message"] == f"account {REDACTED_VALUE} is visible"
    assert result.summary.count == 2
    assert service.status()["extra_key_count"] == 1
    assert service.status()["extra_pattern_count"] == 1
