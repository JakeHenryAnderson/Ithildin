from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.http_tools import HttpAllowlist, HttpFetchExecutor
from ithildin_api.patches import PatchProposalService, PatchProposalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_mcp_server import IthildinMcpAdapter
from ithildin_policy_core import PolicyEvaluator
from mcp import types

JsonObject = dict[str, Any]


class IntegrationHttpResponse:
    code = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}

    def read(self, size: int) -> bytes:
        return b'{"token":"secret-http-token","message":"Bearer abcdefghijklmnopqrstuvwxyz"}'[
            :size
        ]

    def getcode(self) -> int:
        return self.code


class IntegrationHttpOpener:
    def __init__(self) -> None:
        self.requests: list[Request] = []

    def open(self, fullurl: Request, timeout: float = 0) -> IntegrationHttpResponse:
        self.requests.append(fullurl)
        return IntegrationHttpResponse()

    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: object,
        resolved_ips: object,
        timeout: float = 0,
    ) -> IntegrationHttpResponse:
        return self.open(fullurl, timeout=timeout)


@dataclass(frozen=True)
class IntegrationHarness:
    adapter: IthildinMcpAdapter
    approval_service: ApprovalService
    audit_writer: AuditWriter
    workspace_root: Path
    http_opener: IntegrationHttpOpener
    audit_jsonl_path: Path


def test_mcp_governed_flow_covers_policy_tools_redaction_approval_and_audit(
    tmp_path: Path,
) -> None:
    harness = make_integration_harness(tmp_path)

    asyncio.run(run_integration_flow(harness))


async def run_integration_flow(harness: IntegrationHarness) -> None:
    tools = await harness.adapter.list_tools()
    assert [tool.name for tool in tools] == [
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "http.fetch",
    ]

    read_result = await harness.adapter.call_tool("fs.read", {"path": "README.md"})
    assert read_result.isError is False
    read_content = _structured(read_result)
    assert read_content["status"] == "completed"
    assert read_content["content"] == "hello integration\nTOKEN=[REDACTED]\npatch target\n"
    assert "secret-read-token" not in _text(read_result)

    http_result = await harness.adapter.call_tool(
        "http.fetch",
        {"url": "https://example.com/data"},
    )
    assert http_result.isError is False
    http_content = _structured(http_result)
    assert http_content["body_json"]["token"] == "[REDACTED]"
    assert "secret-http-token" not in str(http_content)
    assert "abcdefghijklmnopqrstuvwxyz" not in _text(http_result)
    assert harness.http_opener.requests[0].full_url == "https://example.com/data"

    before = harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8")
    after = before.replace("patch target\n", "patch applied\n", 1)
    proposal_result = await harness.adapter.call_tool(
        "fs.patch.propose",
        {"path": "README.md", "unified_diff": _unified_diff("README.md", before, after)},
    )
    assert proposal_result.isError is False
    proposal = _structured(proposal_result)
    proposal_id = str(proposal["proposal_id"])
    assert proposal_id.startswith("patch_")
    assert "unified_diff" not in proposal

    approval_result = await harness.adapter.call_tool(
        "fs.patch.apply",
        {"proposal_id": proposal_id},
    )
    assert approval_result.isError is False
    approval = _structured(approval_result)
    approval_id = str(approval["approval_id"])
    assert approval_id.startswith("appr_")

    approved = harness.approval_service.approve(
        approval_id,
        decided_by="admin:integration-test",
        reason="integration flow",
    )
    assert approved.status.value == "approved"

    apply_result = await harness.adapter.call_tool("fs.patch.apply", {"approval_id": approval_id})
    assert apply_result.isError is False
    applied = _structured(apply_result)
    assert applied["status"] == "completed"
    assert "patch applied" in harness.workspace_root.joinpath("README.md").read_text(
        encoding="utf-8"
    )

    replay_result = await harness.adapter.call_tool("fs.patch.apply", {"approval_id": approval_id})
    assert replay_result.isError is True
    replay_content = _structured(replay_result)
    assert replay_content["status"] == "denied"

    verification = harness.audit_writer.verify_chain()
    assert verification.valid is True
    assert verification.event_count >= 12
    export_metadata = json.loads(harness.audit_writer.export_jsonl_bundle().splitlines()[0])[
        "metadata"
    ]
    assert export_metadata["verification"]["valid"] is True
    assert export_metadata["event_count"] == verification.event_count

    audit_text = harness.audit_jsonl_path.read_text(encoding="utf-8")
    assert "secret-read-token" not in audit_text
    assert "secret-http-token" not in audit_text
    assert "redaction_count" in audit_text
    assert "tool.execution.failed" in audit_text


def make_integration_harness(tmp_path: Path) -> IntegrationHarness:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    _write_manifest(manifest_dir, "fs.read", "read", required='required: ["path"]')
    _write_patch_propose_manifest(manifest_dir)
    _write_patch_apply_manifest(manifest_dir)
    _write_http_fetch_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    _write_policy(policy_path)

    db_path = tmp_path / "ithildin.sqlite3"
    audit_jsonl_path = tmp_path / "audit.jsonl"
    audit_writer = AuditWriter(db_path, audit_jsonl_path)
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text(
        "hello integration\nTOKEN=secret-read-token\npatch target\n",
        encoding="utf-8",
    )
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=10,
        git_log_limit=10,
    )
    http_opener = IntegrationHttpOpener()
    http_executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=4096,
        max_redirects=3,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=http_opener,
    )
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    service = GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        read_executor,
        PatchProposalService(patch_store, read_executor.filesystem, max_patch_bytes=4096),
        http_executor,
    )
    return IntegrationHarness(
        adapter=IthildinMcpAdapter(
            registry=ToolRegistry.load(manifest_dir),
            tool_call_service=service,
        ),
        approval_service=approval_service,
        audit_writer=audit_writer,
        workspace_root=workspace_root,
        http_opener=http_opener,
        audit_jsonl_path=audit_jsonl_path,
    )


def _write_policy(path: Path) -> None:
    path.write_text(
        """
version: integration-test
rules:
  - id: require_write_approval
    decision: require_approval
    reason: writes require approval
    match:
      tool.risk: write
    obligations:
      audit_level: full
  - id: allow_write_proposals
    decision: allow
    reason: proposals allowed
    match:
      tool.risk: write-proposal
      resource.in_scope: true
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
  - id: allow_network
    decision: allow
    reason: network allowed
    match:
      tool.risk: network
      resource.in_scope: true
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )


def _write_manifest(manifest_dir: Path, name: str, risk: str, *, required: str) -> None:
    manifest_dir.joinpath(f"{name.replace('.', '-')}.yaml").write_text(
        f"""
name: {name}
version: 1.0.0
title: {name}
risk: {risk}
category: integration
mcp:
  exposed: true
  annotations:
    readOnlyHint: {str(risk == "read").lower()}
input_schema:
  type: object
  additionalProperties: false
  {required}
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )


def _write_patch_propose_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("fs-patch-propose.yaml").write_text(
        """
name: fs.patch.propose
version: 1.0.0
title: Propose patch
risk: write-proposal
category: integration
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["path", "unified_diff"]
  properties:
    path:
      type: string
    unified_diff:
      type: string
""",
        encoding="utf-8",
    )


def _write_patch_apply_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("fs-patch-apply.yaml").write_text(
        """
name: fs.patch.apply
version: 1.0.0
title: Apply patch
risk: write
category: integration
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    proposal_id:
      type: string
    approval_id:
      type: string
  oneOf:
    - required: ["proposal_id"]
    - required: ["approval_id"]
""",
        encoding="utf-8",
    )


def _write_http_fetch_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("http-fetch.yaml").write_text(
        """
name: http.fetch
version: 1.0.0
title: Fetch URL
risk: network
category: integration
mcp:
  exposed: true
  annotations:
    readOnlyHint: true
input_schema:
  type: object
  additionalProperties: false
  required: ["url"]
  properties:
    url:
      type: string
""",
        encoding="utf-8",
    )


def _structured(result: types.CallToolResult) -> JsonObject:
    assert result.structuredContent is not None
    return result.structuredContent


def _text(result: types.CallToolResult) -> str:
    content = result.content[0]
    assert isinstance(content, types.TextContent)
    return content.text


def _unified_diff(path: str, before: str, after: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
