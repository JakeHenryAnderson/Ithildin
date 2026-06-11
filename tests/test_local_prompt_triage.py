from __future__ import annotations

from scripts.local_prompt_triage import estimate_tokens, triage_prompt


def test_exact_task_stays_low_difficulty() -> None:
    result = triage_prompt("Reply with exactly: ok")

    assert result.difficulty == 1
    assert result.recommendation == "local_small"
    assert result.signals["exact_or_mechanical"] is True


def test_multifile_failure_with_auth_routes_to_strong_review() -> None:
    result = triage_prompt(
        "Fix the failing auth regression in apps/api/src/auth.py and tests/test_auth.py. "
        "Traceback shows ValueError after token validation."
    )

    assert result.difficulty >= 4
    assert result.recommendation == "strong_review"
    assert result.file_count == 2
    assert result.signals["risk_domain"] is True
    assert result.signals["error_or_stack"] is True


def test_large_context_signal_is_local_and_deterministic() -> None:
    prompt = "Summarize this review packet.\n" + ("x" * 32_000)
    result = triage_prompt(prompt)

    assert result.estimated_tokens == estimate_tokens(prompt)
    assert result.signals["large_context"] is True
    assert result.difficulty >= 2
