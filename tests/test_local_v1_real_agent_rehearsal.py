from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import local_v1_real_agent_rehearsal as real_agent
from scripts import local_v1_real_agent_rehearsal_check as real_agent_check


def _event(
    event_type: str,
    request_id: str,
    tool_name: str,
    *,
    decision: str | None = None,
    reason: str = "",
    approval_id: str = "",
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "principal_id": real_agent.EXPECTED_PRINCIPAL,
        "session_id": real_agent.EXPECTED_SESSION,
    }
    if reason:
        metadata["reason"] = reason
    if approval_id:
        metadata["approval_id"] = approval_id
    event: dict[str, object] = {
        "event_type": event_type,
        "request_id": request_id,
        "tool_name": tool_name,
        "metadata": metadata,
    }
    if decision is not None:
        event["decision"] = decision
    return event


def test_o2_evaluator_distinguishes_allowed_denied_and_approval_required() -> None:
    events = [
        _event("policy.evaluated", "req-read", "fs.read", decision="allow"),
        _event("tool.execution.completed", "req-read", "fs.read"),
        _event(
            "policy.evaluated",
            "req-deny",
            "fs.read",
            decision="deny",
            reason="Resource is outside the workspace scope.",
        ),
        _event(
            "policy.evaluated",
            "req-write",
            real_agent.EXPECTED_WRITE_TOOL,
            decision="require_approval",
        ),
        _event(
            "approval.created",
            "req-write",
            real_agent.EXPECTED_WRITE_TOOL,
            approval_id="appr_test",
        ),
    ]

    observations = real_agent.evaluate_o2_events(
        events,
        approval_statuses={"appr_test": "pending"},
    )

    assert observations == {
        "allowed_read_completed": True,
        "out_of_scope_read_denied_before_execution": True,
        "approval_required_observed": True,
        "approval_pending_without_execution": True,
        "fixed_stdio_identity_observed": True,
        "approval_count": 1,
    }


def test_o2_evaluator_fails_closed_on_execution_or_wrong_identity() -> None:
    events = [
        _event(
            "policy.evaluated",
            "req-deny",
            "fs.read",
            decision="deny",
            reason="Resource is outside the workspace scope.",
        ),
        _event("tool.execution.completed", "req-deny", "fs.read"),
    ]
    metadata = events[0]["metadata"]
    assert isinstance(metadata, dict)
    metadata["principal_id"] = "agent:wrong"

    observations = real_agent.evaluate_o2_events(events, approval_statuses={})

    assert observations["out_of_scope_read_denied_before_execution"] is False
    assert observations["fixed_stdio_identity_observed"] is False
    assert observations["approval_pending_without_execution"] is False


@pytest.mark.parametrize(
    "execution_event",
    ("tool.execution.started", "tool.execution.failed"),
)
def test_o2_evaluator_counts_started_or_failed_denied_call_as_execution(
    execution_event: str,
) -> None:
    events = [
        _event(
            "policy.evaluated",
            "req-deny",
            "fs.read",
            decision="deny",
            reason="Resource is outside the workspace scope.",
        ),
        _event(execution_event, "req-deny", "fs.read"),
    ]

    observations = real_agent.evaluate_o2_events(events, approval_statuses={})

    assert observations["out_of_scope_read_denied_before_execution"] is False


@pytest.mark.parametrize(
    "execution_event",
    ("tool.execution.started", "tool.execution.failed"),
)
def test_o2_evaluator_counts_started_or_failed_pending_write_as_execution(
    execution_event: str,
) -> None:
    events = [
        _event(
            "policy.evaluated",
            "req-write",
            real_agent.EXPECTED_WRITE_TOOL,
            decision="require_approval",
        ),
        _event(
            "approval.created",
            "req-write",
            real_agent.EXPECTED_WRITE_TOOL,
            approval_id="appr_test",
        ),
        _event(execution_event, "req-write", real_agent.EXPECTED_WRITE_TOOL),
    ]

    observations = real_agent.evaluate_o2_events(
        events,
        approval_statuses={"appr_test": "pending"},
    )

    assert observations["approval_pending_without_execution"] is False


def test_gateway_evidence_requirements_do_not_depend_on_runner_exit() -> None:
    observations = {
        "allowed_read_completed": True,
        "out_of_scope_read_denied_before_execution": True,
        "approval_required_observed": True,
        "approval_pending_without_execution": True,
        "fixed_stdio_identity_observed": True,
        "audit_chain_valid": True,
        "runner_process_exit_zero": False,
    }

    assert real_agent.gateway_evidence_valid(observations) is True
    observations["audit_chain_valid"] = False
    assert real_agent.gateway_evidence_valid(observations) is False


def test_gateway_evidence_failure_is_fixed_secret_safe_projection() -> None:
    observations = {
        "allowed_read_completed": True,
        "out_of_scope_read_denied_before_execution": False,
        "approval_required_observed": True,
        "approval_pending_without_execution": False,
        "fixed_stdio_identity_observed": True,
        "audit_chain_valid": True,
        "audit_event_count": 17,
        "request_id": "req_private",
        "model_output": "private prose",
    }

    assert real_agent.gateway_evidence_failure(observations) == (
        "gateway_o2_evidence_invalid;"
        "required_bitmap=101011;audit_event_count=17"
    )


@pytest.mark.parametrize("event_count", (True, -1, 1_000_001, "17", None))
def test_gateway_evidence_failure_rejects_unbounded_event_count(
    event_count: object,
) -> None:
    observations = {
        name: False for name in real_agent.REQUIRED_GATEWAY_OBSERVATIONS
    }
    observations["audit_event_count"] = event_count

    assert real_agent.gateway_evidence_failure(observations) == (
        "gateway_o2_evidence_invalid;"
        "required_bitmap=000000;audit_event_count=invalid"
    )


def test_docker_run_is_nonroot_bounded_and_has_no_docker_socket(tmp_path: Path) -> None:
    command = real_agent.docker_run_command(
        image="ithildin/hermes-local-v1-o2:test",
        container="ithildin-local-v1-o2-test",
        candidate_root=tmp_path / "candidate",
        runtime_root=tmp_path / "runtime",
    )
    serialized = " ".join(command)

    assert command[:2] == ["docker", "run"]
    assert "--user" in command
    assert f"{os.getuid()}:{os.getgid()}" in command
    assert "--env" in command and "HERMES_HOME=/opt/data" in command
    assert "--cap-drop" in command and "ALL" in command
    assert "no-new-privileges:true" in command
    assert f"/opt/data:uid={os.getuid()},gid={os.getgid()},mode=0700" in command
    assert "/var/run/docker.sock" not in serialized
    assert "OPENAI" not in serialized
    assert "ANTHROPIC" not in serialized
    assert "sandbox_artifact_write_text" in serialized
    assert "mcp__ithildin_local__fs_list" not in serialized
    assert "mcp__ithildin_local__http_fetch" not in serialized


def test_docker_enumeration_failure_does_not_prove_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_command(
        _command: list[str],
        *,
        failure: str,
        check: bool = True,
        timeout: int = real_agent.COMMAND_TIMEOUT_SECONDS,
    ) -> object:
        del failure, check, timeout
        return type("Result", (), {"returncode": 1, "stdout": ""})()

    monkeypatch.setattr(real_agent, "_run_command", failed_command)

    with pytest.raises(real_agent.RealAgentError, match="container_enumeration_failed"):
        real_agent._exact_container_names("ithildin-local-v1-o2-test")  # noqa: SLF001
    with pytest.raises(real_agent.RealAgentError, match="image_enumeration_failed"):
        real_agent._exact_image_references(  # noqa: SLF001
            "ithildin/hermes-local-v1-o2:test"
        )


def test_runtime_evidence_capture_rejects_runner_symlink(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    runtime_root = run_root / "runtime"
    database_root = runtime_root / "hermes-poc/db"
    logs_root = runtime_root / "hermes-poc/logs"
    database_root.mkdir(parents=True)
    logs_root.mkdir()
    ambient = tmp_path / "ambient.sqlite3"
    ambient.write_bytes(b"not runtime evidence")
    database_root.joinpath("ithildin.sqlite3").symlink_to(ambient)
    audit = logs_root / "audit.jsonl"
    audit.write_text("{}\n", encoding="utf-8")
    os.chmod(audit, 0o600)

    with pytest.raises(OSError):
        real_agent._capture_runtime_evidence(  # noqa: SLF001
            run_root=run_root,
            runtime_root=runtime_root,
        )


def test_runtime_evidence_capture_distinguishes_missing_audit(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    runtime_root = run_root / "runtime"
    database_root = runtime_root / "hermes-poc/db"
    logs_root = runtime_root / "hermes-poc/logs"
    database_root.mkdir(parents=True)
    logs_root.mkdir()
    database = database_root / "ithildin.sqlite3"
    database.write_bytes(b"synthetic database evidence")
    os.chmod(database, 0o600)

    with pytest.raises(
        real_agent.RealAgentError,
        match="runtime_audit_required_evidence_missing",
    ):
        real_agent._capture_runtime_evidence(  # noqa: SLF001
            run_root=run_root,
            runtime_root=runtime_root,
        )


def test_runtime_evidence_capture_distinguishes_unexpected_database_entry(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    runtime_root = run_root / "runtime"
    database_root = runtime_root / "hermes-poc/db"
    logs_root = runtime_root / "hermes-poc/logs"
    database_root.mkdir(parents=True)
    logs_root.mkdir()
    for path in (
        database_root / "ithildin.sqlite3",
        database_root / "unexpected.sqlite3",
        logs_root / "audit.jsonl",
    ):
        path.write_bytes(b"synthetic runtime evidence")
        os.chmod(path, 0o600)

    with pytest.raises(
        real_agent.RealAgentError,
        match="runtime_database_evidence_inventory_invalid",
    ):
        real_agent._capture_runtime_evidence(  # noqa: SLF001
            run_root=run_root,
            runtime_root=runtime_root,
        )


def test_checker_rejects_unconfined_report(tmp_path: Path) -> None:
    failures = real_agent_check.validate_report(
        tmp_path / real_agent.REPORT_NAME,
        expected_candidate="a" * 40,
    )

    assert failures == ["report_path_not_confined"]


def test_checker_uses_same_open_directory_for_report_and_siblings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(real_agent, "ROOT", tmp_path)
    monkeypatch.setattr(
        real_agent,
        "EVIDENCE_BASE",
        tmp_path / "var/local-v1-real-agent",
    )
    run_id = "20260727T120000Z-" + ("a" * 32)
    root = real_agent.EVIDENCE_BASE / run_id
    root.mkdir(parents=True)
    report = root / real_agent.REPORT_NAME
    report.write_text("{}\n", encoding="utf-8")
    os.chmod(report, 0o600)
    root.joinpath("retained-private-state").write_text("synthetic", encoding="utf-8")
    replaced = root.with_name(f"{root.name}-replaced")
    real_listdir = os.listdir

    def swap_before_listdir(path: int | str | bytes | os.PathLike[str]) -> list[str]:
        if isinstance(path, int):
            root.rename(replaced)
            root.mkdir()
            root.joinpath(real_agent.REPORT_NAME).write_text("{}\n", encoding="utf-8")
        return real_listdir(path)

    monkeypatch.setattr(os, "listdir", swap_before_listdir)

    _text, _entry, retained_names = (
        real_agent_check._read_report_and_siblings_nofollow(root)  # noqa: SLF001
    )

    assert "retained-private-state" in retained_names
