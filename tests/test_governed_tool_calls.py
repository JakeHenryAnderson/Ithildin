from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import cast

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import JsonObject


def write_policy(path: Path) -> None:
    path.write_text(
        """
version: test
rules:
  - id: deny_shell
    decision: deny
    reason: shell denied
    match:
      tool.name_prefix: shell.
    obligations:
      audit_level: full
  - id: require_write_approval
    decision: require_approval
    reason: writes require approval
    match:
      tool.risk: write
    obligations:
      audit_level: full
  - id: allow_reads
    decision: allow
    reason: reads allowed
    match:
      tool.risk: read
      resource.in_scope: true
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )


def write_manifest(manifest_dir: Path, name: str, risk: str, required: str = "path") -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath(f"{name.replace('.', '-')}.yaml").write_text(
        f"""
name: {name}
version: 1.0.0
title: {name}
risk: {risk}
category: test
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["{required}"]
  properties:
    {required}:
      type: string
""",
        encoding="utf-8",
    )


def make_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "fs.apply_patch", "write")
    write_manifest(manifest_dir, "shell.run", "write", required="command")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
    )


def make_read_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "git.status", "read", required="path")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text("hello governed reads\n", encoding="utf-8")
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=1024,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def principal() -> JsonObject:
    return {"id": "agent:local-dev", "roles": ["AgentDeveloper"]}


def audit_payloads(tmp_path: Path) -> list[JsonObject]:
    return [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_unknown_tool_is_denied_and_audited(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.missing",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert audit_payloads(tmp_path)[0]["decision"] == "deny"


def test_invalid_arguments_are_denied_before_policy(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"not_path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}
    metadata = cast(JsonObject, audit_payloads(tmp_path)[0]["metadata"])
    assert metadata["reason"] == "invalid tool arguments"


def test_read_allow_returns_governance_only_success(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "allowed"
    message = result.content["message"]
    assert isinstance(message, str)
    assert "execution is not implemented" in message
    assert audit_payloads(tmp_path)[0]["decision"] == "allow"


def test_read_tool_executes_after_policy_allow_and_is_audited(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "hello governed reads\n"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_denied_read_attempt_is_audited_as_failed_execution(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "../README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.failed",
    ]


def test_arbitrary_git_flags_are_rejected_by_manifest_schema(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="git.status",
        arguments={"path": ".", "flag": "--help"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}
    assert [payload["event_type"] for payload in audit_payloads(tmp_path)] == ["policy.evaluated"]


def test_write_call_creates_approval_required_response(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.apply_patch",
        arguments={"path": "app.py"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "approval_required"
    approval_id = result.content["approval_id"]
    assert isinstance(approval_id, str)
    assert approval_id.startswith("appr_")
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "approval.created",
    ]


def test_denied_policy_decision_is_audited(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="shell.run",
        arguments={"command": "echo nope"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[0]["metadata"])
    assert metadata["reason"] == "shell denied"
