from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest
from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.config import Settings
from ithildin_api.http_tools import HttpAllowlist, HttpFetchExecutor
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.manifest_lock import (
    ManifestLockRecord,
    generate_manifest_lock_signing_keypair,
    write_manifest_lock,
    write_manifest_lock_signature,
)
from ithildin_api.patches import PatchProposalService, PatchProposalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_mcp_server import IthildinMcpAdapter, create_mcp_server
from ithildin_mcp_server.server import MCP_AGENT_PRINCIPAL_ID, MCP_SESSION_ID, create_adapter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import AuditEventType
from mcp import types


class FakeHttpResponse:
    def __init__(self, body: bytes = b"mcp network") -> None:
        self.body = body
        self.code = 200
        self.headers = {"Content-Type": "text/plain; charset=utf-8"}

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def getcode(self) -> int:
        return self.code


class FakeHttpOpener:
    def __init__(self, body: bytes = b"mcp network") -> None:
        self.requests: list[Request] = []
        self.body = body

    def open(self, fullurl: Request, timeout: float = 0) -> FakeHttpResponse:
        self.requests.append(fullurl)
        return FakeHttpResponse(self.body)

    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: object,
        resolved_ips: object,
        timeout: float = 0,
    ) -> FakeHttpResponse:
        return self.open(fullurl, timeout=timeout)


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
  - id: allow_write_proposals
    decision: allow
    reason: proposals allowed
    match:
      tool.risk: write-proposal
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


def write_patch_propose_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("fs-patch-propose.yaml").write_text(
        """
name: fs.patch.propose
version: 1.0.0
title: Propose patch
risk: write-proposal
category: test
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


def write_patch_apply_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("fs-patch-apply.yaml").write_text(
        """
name: fs.patch.apply
version: 1.0.0
title: Apply patch
risk: write
category: test
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


def write_http_fetch_manifest(manifest_dir: Path) -> None:
    manifest_dir.joinpath("http-fetch.yaml").write_text(
        """
name: http.fetch
version: 1.0.0
title: Fetch URL
risk: network
category: network
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


@dataclass(frozen=True)
class McpAdapterHarness:
    adapter: IthildinMcpAdapter
    audit_writer: AuditWriter


def make_adapter(tmp_path: Path, *, http_body: bytes = b"mcp network") -> IthildinMcpAdapter:
    return make_adapter_harness(tmp_path, http_body=http_body).adapter


def make_adapter_harness(
    tmp_path: Path,
    *,
    http_body: bytes = b"mcp network",
    principal_registry: PrincipalRegistry | None = None,
) -> McpAdapterHarness:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "fs.apply_patch", "write")
    write_patch_propose_manifest(manifest_dir)
    write_patch_apply_manifest(manifest_dir)
    write_http_fetch_manifest(manifest_dir)
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
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=1024,
        search_result_limit=10,
        git_log_limit=10,
    )
    http_executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=FakeHttpOpener(http_body),
    )
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    service = GovernedToolCallService(
        registry,
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        read_executor,
        PatchProposalService(
            patch_store,
            read_executor.filesystem,
            max_patch_bytes=1024,
        ),
        http_executor,
        principal_registry=principal_registry,
    )
    return McpAdapterHarness(
        adapter=IthildinMcpAdapter(
            registry=registry,
            tool_call_service=service,
            principal_registry=principal_registry,
        ),
        audit_writer=audit_writer,
    )


def test_mcp_tools_list_returns_exposed_registry_tools(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    tools = asyncio.run(adapter.list_tools())

    assert [tool.name for tool in tools] == [
        "fs.apply_patch",
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "http.fetch",
    ]
    assert all(tool.inputSchema["type"] == "object" for tool in tools)


def test_mcp_tools_list_filters_for_configured_agent_principal(tmp_path: Path) -> None:
    unfiltered_adapter = make_adapter(tmp_path)
    registry_path = tmp_path / "principals.yaml"
    registry_path.write_text(
        """
principals:
  - id: agent:mcp-local
    type: agent
    display_name: Read-only MCP Agent
    roles: [AgentReadOnly]
""",
        encoding="utf-8",
    )
    adapter = IthildinMcpAdapter(
        registry=unfiltered_adapter.registry,
        tool_call_service=unfiltered_adapter.tool_call_service,
        principal_registry=PrincipalRegistry.load(registry_path),
    )

    tools = asyncio.run(adapter.list_tools())

    assert [tool.name for tool in tools] == ["fs.read"]


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


def test_mcp_call_returns_real_http_fetch_output(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)

    result = asyncio.run(adapter.call_tool("http.fetch", {"url": "https://example.com/data"}))

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "completed"
    assert result.structuredContent["body_text"] == "mcp network"
    assert result.structuredContent["url"] == "https://example.com/data"


def test_mcp_call_denies_registered_tool_not_exposed_over_mcp(tmp_path: Path) -> None:
    harness = make_adapter_harness(tmp_path)

    result = asyncio.run(harness.adapter.call_tool("internal.hidden", {}))

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "denied"
    assert result.structuredContent["reason"] == "tool is not exposed over MCP"
    assert harness.audit_writer.list_events(event_type=AuditEventType.POLICY_EVALUATED.value) == []


def test_mcp_call_uses_fixed_agent_principal_and_audits_policy(
    tmp_path: Path,
) -> None:
    harness = make_adapter_harness(tmp_path)

    result = asyncio.run(
        harness.adapter.call_tool(
            "fs.read",
            {
                "path": "README.md",
                "principal": {"id": "admin:local-ui", "roles": ["Admin"]},
                "session_id": "admin-session",
                "request_id": "req_attacker",
            },
        )
    )

    assert result.structuredContent is not None
    event = harness.audit_writer.list_events(
        event_type=AuditEventType.POLICY_EVALUATED.value,
        request_id=str(result.structuredContent["request_id"]),
    )[0]
    principal = cast(dict[str, object], event["principal"])
    metadata = cast(dict[str, object], event["metadata"])
    assert principal["id"] == MCP_AGENT_PRINCIPAL_ID
    assert metadata["principal_id"] == MCP_AGENT_PRINCIPAL_ID
    assert metadata["session_id"] == MCP_SESSION_ID
    assert metadata["decision"] == "allow"


def test_mcp_call_signature_does_not_accept_caller_identity() -> None:
    signature = inspect.signature(IthildinMcpAdapter.call_tool)

    assert list(signature.parameters) == ["self", "tool_name", "arguments"]


def test_mcp_call_denies_when_fixed_agent_principal_is_not_active(tmp_path: Path) -> None:
    registry_path = tmp_path / "principals.yaml"
    registry_path.write_text(
        """
principals:
  - id: agent:other
    type: agent
    display_name: Other Agent
    roles: [AgentDeveloper]
""",
        encoding="utf-8",
    )
    harness = make_adapter_harness(
        tmp_path,
        principal_registry=PrincipalRegistry.load(registry_path),
    )

    result = asyncio.run(harness.adapter.call_tool("fs.read", {"path": "README.md"}))

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "denied"
    assert "unknown principal" in str(result.structuredContent["reason"])
    event = harness.audit_writer.list_events(
        event_type=AuditEventType.POLICY_EVALUATED.value,
        request_id=str(result.structuredContent["request_id"]),
    )[0]
    assert event["decision"] == "deny"


def test_mcp_unknown_tool_is_denied_and_audited(tmp_path: Path) -> None:
    harness = make_adapter_harness(tmp_path)

    result = asyncio.run(harness.adapter.call_tool("shell.run", {"command": "whoami"}))

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "denied"
    event = harness.audit_writer.list_events(
        event_type=AuditEventType.POLICY_EVALUATED.value,
        request_id=str(result.structuredContent["request_id"]),
    )[0]
    principal = cast(dict[str, object], event["principal"])
    assert event["tool_name"] == "shell.run"
    assert event["decision"] == "deny"
    assert principal["id"] == "agent:mcp-local"


def test_mcp_call_returns_redacted_text_and_structured_content(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path, http_body=b"TOKEN=secret-value")

    result = asyncio.run(adapter.call_tool("http.fetch", {"url": "https://example.com/data"}))

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["body_text"] == "TOKEN=[REDACTED]"
    text_content = result.content[0]
    assert isinstance(text_content, types.TextContent)
    assert "secret-value" not in text_content.text


def test_mcp_call_returns_patch_proposal_metadata(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)
    unified_diff = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-hello from mcp\n+changed\n"

    result = asyncio.run(
        adapter.call_tool(
            "fs.patch.propose",
            {"path": "README.md", "unified_diff": unified_diff},
        )
    )

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "completed"
    assert result.structuredContent["proposal_id"].startswith("patch_")
    assert result.structuredContent["path"] == "README.md"
    assert "unified_diff" not in result.structuredContent


def test_mcp_patch_apply_returns_safe_approval_required_response(tmp_path: Path) -> None:
    adapter = make_adapter(tmp_path)
    unified_diff = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-hello from mcp\n+changed\n"
    proposal = asyncio.run(
        adapter.call_tool(
            "fs.patch.propose",
            {"path": "README.md", "unified_diff": unified_diff},
        )
    )
    assert proposal.structuredContent is not None

    result = asyncio.run(
        adapter.call_tool(
            "fs.patch.apply",
            {"proposal_id": proposal.structuredContent["proposal_id"]},
        )
    )

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "approval_required"
    assert result.structuredContent["approval_id"].startswith("appr_")
    assert result.structuredContent["proposal_id"] == proposal.structuredContent["proposal_id"]
    assert "unified_diff" not in result.structuredContent


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


def test_create_adapter_enforces_manifest_lock_when_enabled(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    settings = Settings(
        admin_token="test-admin-token",
        db_path=tmp_path / "ithildin.sqlite3",
        audit_log_path=tmp_path / "audit.jsonl",
        manifest_dir=manifest_dir,
        manifest_lock_path=tmp_path / "missing.lock.json",
        require_manifest_lock=True,
        policy_path=policy_path,
        workspace_root=tmp_path / "workspace",
    )

    with pytest.raises(RuntimeError, match="manifest lock"):
        create_adapter(settings)


def test_create_adapter_enforces_signed_manifest_lock_when_enabled(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    signature_path = tmp_path / "tool-manifests.lock.sig.json"
    generate_manifest_lock_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    write_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    settings = Settings(
        admin_token="test-admin-token",
        db_path=tmp_path / "ithildin.sqlite3",
        audit_log_path=tmp_path / "audit.jsonl",
        manifest_dir=manifest_dir,
        manifest_lock_path=lock_path,
        require_manifest_lock=True,
        manifest_lock_signing_public_key_path=public_key_path,
        manifest_lock_signature_path=signature_path,
        require_signed_manifest_lock=True,
        policy_path=policy_path,
        workspace_root=tmp_path / "workspace",
    )

    adapter = create_adapter(settings)

    assert [tool.manifest.name for tool in adapter.registry.list_tools()] == ["fs.read"]


def test_create_adapter_fails_when_signed_manifest_lock_is_missing(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    settings = Settings(
        admin_token="test-admin-token",
        db_path=tmp_path / "ithildin.sqlite3",
        audit_log_path=tmp_path / "audit.jsonl",
        manifest_dir=manifest_dir,
        manifest_lock_path=lock_path,
        require_manifest_lock=True,
        manifest_lock_signing_public_key_path=tmp_path / "missing-public.pem",
        manifest_lock_signature_path=tmp_path / "missing-signature.json",
        require_signed_manifest_lock=True,
        policy_path=policy_path,
        workspace_root=tmp_path / "workspace",
    )

    with pytest.raises(RuntimeError, match="manifest lock signature"):
        create_adapter(settings)
