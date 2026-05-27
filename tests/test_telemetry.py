from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.config import Settings
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.telemetry import configure_telemetry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator


def test_console_telemetry_does_not_export_arguments_or_tool_output(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_dir.joinpath("fs-read.yaml").write_text(
        """
name: fs.read
version: 1.0.0
title: Read file
risk: read
category: test
input_schema:
  type: object
  additionalProperties: false
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
version: test
rules:
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
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("secret.txt").write_text("TOKEN=super-secret\n", encoding="utf-8")
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    service = GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        ApprovalService(approval_store, audit_writer, timedelta(minutes=15)),
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=1024,
            search_result_limit=10,
            git_log_limit=10,
        ),
        telemetry=configure_telemetry(
            Settings(
                admin_token="test-admin-token",
                db_path=db_path,
                audit_log_path=tmp_path / "audit.jsonl",
                manifest_dir=manifest_dir,
                require_manifest_lock=False,
                policy_path=policy_path,
                workspace_root=workspace_root,
                otel_enabled=True,
                otel_console_export=True,
            )
        ),
    )

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "secret.txt"},
        principal={"id": "agent:test"},
        session_id="sess_1",
    )

    captured = capfd.readouterr()
    assert result.status == "completed"
    assert result.content["content"] == "TOKEN=[REDACTED]\n"
    assert "TOKEN=super-secret" not in captured.out
    assert "secret.txt" not in captured.out
