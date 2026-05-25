from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_mcp_server import IthildinMcpAdapter, create_mcp_server
from ithildin_policy_core import PolicyEvaluator


def write_policy(path: Path) -> None:
    path.write_text(
        """
version: test
rules:
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


def write_manifest(manifest_dir: Path, name: str, risk: str) -> None:
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
  annotations:
    readOnlyHint: {str(risk == "read").lower()}
input_schema:
  type: object
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )


def make_adapter(tmp_path: Path) -> IthildinMcpAdapter:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "fs.apply_patch", "write")
    (manifest_dir / "internal.yaml").write_text(
        """
name: internal.hidden
version: 1.0.0
title: Hidden
risk: read
category: test
mcp:
  exposed: false
input_schema:
  type: object
""",
        encoding="utf-8",
    )
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text("hello from mcp\n", encoding="utf-8")
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(
        approval_store,
        audit_writer,
        default_expiry=timedelta(minutes=15),
    )
    registry = ToolRegistry.load(manifest_dir)
    service = GovernedToolCallService(
        registry,
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
    return IthildinMcpAdapter(registry=registry, tool_call_service=service)


def test_mcp_tools_list_returns_exposed_registry_tools(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    tools = asyncio.run(adapter.list_tools())

    assert [tool.name for tool in tools] == ["fs.apply_patch", "fs.read"]
    assert all(tool.inputSchema["type"] == "object" for tool in tools)


def test_mcp_call_returns_safe_approval_required_response(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    result = asyncio.run(adapter.call_tool("fs.apply_patch", {"path": "app.py"}))

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "approval_required"
    assert set(result.structuredContent) >= {
        "approval_id",
        "request_id",
        "tool_name",
        "summary",
        "expires_at",
        "policy_reason",
    }
    assert "path" not in result.structuredContent


def test_mcp_call_returns_real_read_output(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    result = asyncio.run(adapter.call_tool("fs.read", {"path": "README.md"}))

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "completed"
    assert result.structuredContent["content"] == "hello from mcp\n"
    assert result.structuredContent["byte_count"] == 15


def test_mcp_call_unknown_tool_returns_safe_error(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    result = asyncio.run(adapter.call_tool("fs.missing", {"path": "README.md"}))

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "denied"
    assert result.structuredContent["reason"] == "unknown tool"


def test_create_mcp_server_uses_official_server_type(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    server = create_mcp_server(adapter)

    assert server.name == "ithildin-mcp"
