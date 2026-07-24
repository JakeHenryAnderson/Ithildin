from __future__ import annotations

from pathlib import Path

from scripts import mission_command_runner_bridge_authorization_check as authorization_check


def test_live_runner_bridge_authorization_is_code_only() -> None:
    report = authorization_check.build_report(Path("."))

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["code_implementation_authorized"] is True
    assert report["live_hermes_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False


def test_authorization_rejects_live_authority() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = Path(authorization_check.decision_check.DECISION).read_text(
        encoding="utf-8"
    )
    authorization = authorization_check._contract(  # noqa: SLF001
        text.replace(
            '"live_hermes_execution_authorized":false',
            '"live_hermes_execution_authorized":true',
            1,
        )
    )
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert "runner-bridge authorization live_hermes_execution_authorized must remain false" in (
        failures
    )


def test_authorization_rejects_path_expansion() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = Path(authorization_check.decision_check.DECISION).read_text(
        encoding="utf-8"
    )
    authorization = authorization_check._contract(  # noqa: SLF001
        text.replace(
            '"apps/node/src/ithildin_node/client.py"',
            '"pyproject.toml","apps/node/src/ithildin_node/client.py"',
            1,
        )
    )
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("allowed_runtime_paths" in failure for failure in failures)


def test_authorization_rejects_decision_substitution() -> None:
    text = Path(authorization_check.AUTHORIZATION).read_text(encoding="utf-8")
    decision = (
        Path(authorization_check.decision_check.DECISION).read_text(encoding="utf-8")
        + "\nsubstituted\n"
    )
    authorization = authorization_check._contract(text)  # noqa: SLF001
    failures: list[str] = []

    authorization_check._validate_contract(  # noqa: SLF001
        authorization, decision, failures
    )

    assert any("decision_sha256" in failure for failure in failures)
