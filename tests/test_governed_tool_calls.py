from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import NoReturn, cast
from urllib.request import Request

import pytest
from ithildin_api.approvals import ApprovalService, ApprovalStore, CreateApprovalInput
from ithildin_api.http_tools import HTTP_FETCH_TOOL, HttpAllowlist, HttpFetchExecutor
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.patches import PatchProposalError, PatchProposalService, PatchProposalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import JsonObject, canonical_json, sha256_digest


class FakeHttpResponse:
    def __init__(
        self,
        *,
        body: bytes = b"hello network",
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.body = body
        self.code = 200
        self.headers = {"Content-Type": content_type}

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def getcode(self) -> int:
        return self.code


class FakeHttpOpener:
    def __init__(self, response: FakeHttpResponse | None = None) -> None:
        self.requests: list[Request] = []
        self.response = response or FakeHttpResponse()

    def open(self, fullurl: Request, timeout: float = 0) -> FakeHttpResponse:
        self.requests.append(fullurl)
        return self.response

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


def write_patch_propose_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
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
    manifest_dir.mkdir(exist_ok=True)
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
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("http-fetch.yaml").write_text(
        """
name: http.fetch
version: 1.0.0
title: Fetch URL
risk: network
category: network
mcp:
  exposed: true
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


def make_identity_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "http.fetch", "network", required="url")
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
        principal_registry=PrincipalRegistry.load(Path("principals/local.yaml")),
    )


def make_read_service(
    tmp_path: Path,
    *,
    content: str = "hello governed reads\n",
    policy_yaml: str | None = None,
) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "git.status", "read", required="path")
    policy_path = tmp_path / "policy.yaml"
    if policy_yaml is None:
        write_policy(policy_path)
    else:
        policy_path.write_text(policy_yaml, encoding="utf-8")
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text(content, encoding="utf-8")
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


def make_http_service(
    tmp_path: Path,
    *,
    allowlist: str = "https://example.com",
    opener: FakeHttpOpener | None = None,
) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_http_fetch_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    http_opener = opener or FakeHttpOpener()
    http_executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv(allowlist),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=http_opener,
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        http_fetch_executor=http_executor,
    )


@dataclass(frozen=True)
class PatchHarness:
    service: GovernedToolCallService
    approval_service: ApprovalService
    patch_service: PatchProposalService
    db_path: Path
    workspace_root: Path


def make_patch_harness(tmp_path: Path) -> PatchHarness:
    manifest_dir = tmp_path / "manifests"
    write_patch_propose_manifest(manifest_dir)
    write_patch_apply_manifest(manifest_dir)
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
    workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=1024,
        search_result_limit=10,
        git_log_limit=10,
    )
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    patch_service = PatchProposalService(
        patch_store,
        read_executor.filesystem,
        max_patch_bytes=1024,
    )
    service = GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        read_executor,
        patch_service,
    )
    return PatchHarness(service, approval_service, patch_service, db_path, workspace_root)


def make_patch_service(tmp_path: Path) -> GovernedToolCallService:
    return make_patch_harness(tmp_path).service


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


def test_unknown_principal_is_denied_and_audited_before_policy(tmp_path: Path) -> None:
    service = make_identity_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal={"id": "agent:missing", "roles": ["Admin"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert "unknown principal" in str(result.content["reason"])
    payload = audit_payloads(tmp_path)[0]
    metadata = cast(JsonObject, payload["metadata"])
    assert payload["principal"] == {"id": "agent:missing", "roles": ["Admin"]}
    assert payload["decision"] == "deny"
    assert metadata["identity_source"] == "principal_registry"


def test_role_unauthorized_principal_is_denied_before_execution(tmp_path: Path) -> None:
    service = make_identity_service(tmp_path)

    result = service.call_tool(
        tool_name="http.fetch",
        arguments={"url": "https://example.com/data"},
        principal={"id": "agent:readonly", "roles": ["Admin"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert "not authorized" in str(result.content["reason"])
    payload = audit_payloads(tmp_path)[0]
    metadata = cast(JsonObject, payload["metadata"])
    assert payload["principal"] == {
        "id": "agent:readonly",
        "type": "agent",
        "roles": ["AgentReadOnly"],
    }
    assert payload["decision"] == "deny"
    assert metadata["tool_risk"] == "network"


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
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["policy_engine"] == "yaml"
    assert policy_metadata["policy_document_version"] == "test"
    assert policy_metadata["policy_hash"] == payloads[0]["policy_version"]
    assert policy_metadata["policy_version"] == payloads[0]["policy_version"]
    assert policy_metadata["decision"] == "allow"
    assert policy_metadata["reason"] == "reads allowed"
    manifest_hash = policy_metadata["manifest_hash"]
    assert isinstance(manifest_hash, str)
    assert manifest_hash.startswith("sha256:")
    assert policy_metadata["tool_name"] == "fs.read"
    assert policy_metadata["tool_version"] == "1.0.0"
    assert policy_metadata["tool_risk"] == "read"
    assert policy_metadata["resource_type"] == "file"
    assert policy_metadata["resource_in_scope"] is True
    assert policy_metadata["principal_id"] == "agent:local-dev"
    assert policy_metadata["principal_roles"] == ["AgentDeveloper"]
    assert policy_metadata["session_id"] == "sess_1"
    assert policy_metadata["obligation_keys"] == ["audit_level"]
    metadata = cast(JsonObject, payloads[-1]["metadata"])
    assert metadata["redaction_applied"] is True
    assert metadata["redaction_count"] == 0


def test_read_tool_output_is_redacted_and_audit_summary_is_recorded(tmp_path: Path) -> None:
    service = make_read_service(tmp_path, content="TOKEN=secret-value\nvisible\n")

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "TOKEN=[REDACTED]\nvisible\n"
    payloads = audit_payloads(tmp_path)
    metadata = cast(JsonObject, payloads[-1]["metadata"])
    assert metadata["redaction_count"] == 1
    assert metadata["redaction_paths"] == ["$.content"]


def test_policy_obligation_redact_fields_extends_output_redaction(tmp_path: Path) -> None:
    policy_yaml = """
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
      redact_fields:
        - content
"""
    service = make_read_service(tmp_path, content="ordinary content\n", policy_yaml=policy_yaml)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "[REDACTED]"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[-1]["metadata"])
    assert metadata["redaction_paths"] == ["$.content"]


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


def test_http_fetch_executes_after_policy_allow_and_is_audited(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["body_text"] == "hello network"
    assert opener.requests[0].full_url == "https://example.com/data"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_http_fetch_output_is_redacted_before_return(tmp_path: Path) -> None:
    opener = FakeHttpOpener(
        FakeHttpResponse(
            body=b'{"token":"secret-token","message":"Bearer abcdefghijklmnopqrstuvwxyz"}',
            content_type="application/json; charset=utf-8",
        )
    )
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert "secret-token" not in str(result.content)
    assert "abcdefghijklmnopqrstuvwxyz" not in str(result.content)
    body_json = cast(JsonObject, result.content["body_json"])
    assert body_json["token"] == "[REDACTED]"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[-1]["metadata"])
    assert metadata["redaction_count"] == 3
    assert metadata["redaction_paths"] == [
        "$.body_text",
        "$.body_json.token",
        "$.body_json.message",
    ]


def test_unallowlisted_http_fetch_is_denied_by_policy_and_audited(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, allowlist="", opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert opener.requests == []
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == ["policy.evaluated"]
    assert payloads[0]["decision"] == "deny"


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


def test_patch_proposal_runs_through_policy_and_audit(tmp_path: Path) -> None:
    service = make_patch_service(tmp_path)
    unified_diff = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n"

    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={"path": "README.md", "unified_diff": unified_diff},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["proposal_id"]
    assert result.content["path"] == "README.md"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_invalid_patch_proposal_is_audited_as_failed_execution(tmp_path: Path) -> None:
    service = make_patch_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={"path": "../README.md", "unified_diff": "not a diff"},
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


def test_patch_apply_with_proposal_id_returns_approval_required(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal["proposal_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "approval_required"
    assert result.content["approval_id"]
    assert result.content["proposal_id"] == proposal["proposal_id"]
    assert result.content["proposal_hash"] == proposal["proposal_hash"]
    assert result.content["path"] == "README.md"


def test_patch_apply_approval_scope_binds_evidence(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal["proposal_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    approval = harness.approval_service.get(str(result.content["approval_id"]))
    scope = approval.one_time_scope
    assert scope["tool_name"] == "fs.patch.apply"
    assert scope["proposal_id"] == proposal["proposal_id"]
    assert scope["proposal_hash"] == proposal["proposal_hash"]
    assert scope["base_file_hash"] == proposal["base_file_hash"]
    assert scope["manifest_hash"]
    assert scope["manifest_version"] == "1.0.0"
    tool_input_schema_hash = scope["tool_input_schema_hash"]
    assert isinstance(tool_input_schema_hash, str)
    assert tool_input_schema_hash.startswith("sha256:")
    assert scope["policy_engine"] == "yaml"
    assert scope["policy_hash"] == scope["policy_version"]
    assert scope["matched_rules"] == ["require_write_approval"]
    assert scope["requesting_principal"] == principal()
    assert scope["request_hash"] == approval.request_hash
    assert scope["expires_at"] == approval.expires_at.isoformat()
    assert approval.metadata["approval_scope_hash"] == sha256_digest(scope)


def test_approved_patch_apply_writes_file_and_replay_is_rejected(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    replay = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    attempts = harness.patch_service.list_apply_attempts()
    assert len(attempts) == 1
    assert attempts[0].attempt_id.startswith("pa_")
    assert attempts[0].approval_id == approval["approval_id"]
    assert attempts[0].proposal_id == proposal["proposal_id"]
    assert attempts[0].status == "completed"
    assert attempts[0].base_file_hash == proposal["base_file_hash"]
    assert attempts[0].expected_post_apply_hash == sha256_digest("new\n")
    assert replay.status == "denied"
    assert "not proposed" in str(replay.content["reason"])
    event_types = [payload["event_type"] for payload in audit_payloads(tmp_path)]
    assert "tool.execution.completed" in event_types
    assert event_types[-1] == "tool.execution.failed"


def test_patch_apply_rejects_proposal_hash_mismatch(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            "UPDATE patch_proposals SET proposal_hash = ? WHERE proposal_id = ?",
            ("sha256:" + ("1" * 64), proposal["proposal_id"]),
        )
        connection.commit()

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "hash mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_rejects_manifest_scope_mismatch(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    approval_record = harness.approval_service.get(str(approval["approval_id"]))
    scope = dict(approval_record.one_time_scope)
    scope["manifest_hash"] = "sha256:" + ("2" * 64)
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            "UPDATE approvals SET one_time_scope_json = ? WHERE approval_id = ?",
            (canonical_json(scope), approval["approval_id"]),
        )
        connection.commit()
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "manifest hash mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


@pytest.mark.parametrize(
    ("scope_key", "replacement", "expected_reason"),
    [
        ("policy_hash", "sha256:" + ("3" * 64), "policy hash mismatch"),
        ("policy_version", "sha256:" + ("4" * 64), "policy version mismatch"),
        ("policy_document_version", "drifted-policy", "policy document version mismatch"),
        ("matched_rules", ["different_rule"], "matched rules mismatch"),
        ("manifest_version", "9.9.9", "manifest version mismatch"),
        ("tool_input_schema_hash", "sha256:" + ("5" * 64), "tool input schema mismatch"),
    ],
)
def test_patch_apply_rejects_approval_scope_drift(
    tmp_path: Path,
    scope_key: str,
    replacement: object,
    expected_reason: str,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    _mutate_approval_scope(harness.db_path, str(approval["approval_id"]), scope_key, replacement)
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert expected_reason in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    failed_event = audit_payloads(tmp_path)[-1]
    assert failed_event["event_type"] == "tool.execution.failed"
    failed_metadata = cast(JsonObject, failed_event["metadata"])
    assert failed_metadata["approval_binding_verified"] is False
    assert expected_reason in str(failed_metadata["reason"])


def test_patch_apply_rejects_wrong_requesting_principal(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal={"id": "agent:other", "roles": ["AgentDeveloper"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "principal mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_rejects_stale_base_without_partial_write(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    harness.workspace_root.joinpath("README.md").write_text("changed elsewhere\n", encoding="utf-8")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "changed since proposal" in str(result.content["reason"])
    assert (
        harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8")
        == "changed elsewhere\n"
    )


def test_patch_apply_failure_before_replace_records_failed_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ithildin_api.patches as patches

    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    def fail_before_replace(target: Path, content: str) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(patches, "_atomic_write_text", fail_before_replace)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    attempts = harness.patch_service.list_apply_attempts()
    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    assert attempts[0].status == "failed"
    assert attempts[0].failure_reason == "failed to apply patch safely"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_attempt_creation_failure_leaves_file_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    def fail_create_attempt(attempt: object) -> NoReturn:
        raise sqlite3.Error("simulated attempt insert failure")

    monkeypatch.setattr(harness.patch_service.store, "create_apply_attempt", fail_create_attempt)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    assert harness.patch_service.list_apply_attempts() == []
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_failure_after_replace_records_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    original_set_status = harness.patch_service.store.set_status

    def fail_after_replace(proposal_id: str, status: str) -> NoReturn:
        raise PatchProposalError("simulated database failure after replace")

    monkeypatch.setattr(harness.patch_service.store, "set_status", fail_after_replace)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    monkeypatch.setattr(harness.patch_service.store, "set_status", original_set_status)

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    diagnostic_attempts = cast(list[JsonObject], diagnostics["attempts"])
    stuck_approvals = cast(list[JsonObject], diagnostics["stuck_approvals"])

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executing"
    assert attempts[0].status == "recovery_required"
    assert attempts[0].failure_reason == "simulated database failure after replace"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostic_attempts[0]["current_matches_expected_post_apply_hash"] is True
    assert diagnostic_attempts[0]["diagnostic_status"] == "recovery_required"
    assert stuck_approvals[0]["approval_id"] == approval["approval_id"]


def test_patch_apply_file_replaced_status_failure_is_diagnosable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    original_set_apply_attempt_status = harness.patch_service.store.set_apply_attempt_status

    def fail_file_replaced(
        attempt_id: str,
        status: str,
        failure_reason: str | None = None,
    ) -> NoReturn:
        if status == "file_replaced":
            raise sqlite3.Error("simulated file_replaced update failure")
        raise sqlite3.Error("simulated recovery update failure")

    monkeypatch.setattr(
        harness.patch_service.store,
        "set_apply_attempt_status",
        fail_file_replaced,
    )

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    monkeypatch.setattr(
        harness.patch_service.store,
        "set_apply_attempt_status",
        original_set_apply_attempt_status,
    )

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    diagnostic_attempts = cast(list[JsonObject], diagnostics["attempts"])

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executing"
    assert attempts[0].status == "prepared"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostic_attempts[0]["current_matches_expected_post_apply_hash"] is True
    assert diagnostic_attempts[0]["diagnostic_status"] == "recovery_required"


def test_patch_apply_diagnostics_reports_executing_approval_without_attempt_as_ambiguous(
    tmp_path: Path,
) -> None:
    harness = make_patch_harness(tmp_path)
    approval = harness.approval_service.create_pending(
        CreateApprovalInput(
            principal=principal(),
            tool_name="fs.patch.apply",
            resource={"path": "README.md"},
            summary="Apply patch",
            one_time_scope={"proposal_id": "patch_missing"},
        )
    )
    harness.approval_service.approve(approval.approval_id, decided_by="user:alice")
    harness.approval_service.begin_execution(approval.approval_id, approval.request_hash)

    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    stuck_approvals = cast(list[JsonObject], diagnostics["stuck_approvals"])

    assert diagnostics["status"] == "ambiguous"
    assert diagnostics["attempts"] == []
    assert stuck_approvals[0]["approval_id"] == approval.approval_id
    assert stuck_approvals[0]["has_apply_attempt"] is False


def test_patch_apply_rejects_hardlinked_target_without_partial_write(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    try:
        os.link(harness.workspace_root / "README.md", harness.workspace_root / "README-copy.md")
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "hardlinked" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_denies_symlink_swap_during_apply_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_resolver = harness.patch_service.filesystem.resolve_existing_path
    did_swap = False

    def swap_to_symlink(path: str) -> Path:
        nonlocal did_swap
        resolved = original_resolver(path)
        if path == "README.md" and not did_swap:
            did_swap = True
            resolved.unlink()
            resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(harness.patch_service.filesystem, "resolve_existing_path", swap_to_symlink)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "safe regular file" in str(result.content["reason"])
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_denies_parent_directory_symlink_swap_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    nested = harness.workspace_root / "docs"
    nested.mkdir()
    nested.joinpath("README.md").write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    proposal_result = harness.service.call_tool(
        tool_name="fs.patch.propose",
        arguments={
            "path": "docs/README.md",
            "unified_diff": "--- a/docs/README.md\n+++ b/docs/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        },
        principal=principal(),
        session_id="sess_1",
    )
    assert proposal_result.status == "completed"
    proposal = proposal_result.content
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    import ithildin_api.patches as patches_module

    original_atomic_write = patches_module._atomic_write_text

    def swap_parent_to_symlink(target: Path, content: str) -> None:
        if target.parent.name == "docs":
            target.parent.rename(harness.workspace_root / "docs-original")
            target.parent.symlink_to(outside)
        original_atomic_write(target, content)

    monkeypatch.setattr(patches_module, "_atomic_write_text", swap_parent_to_symlink)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert outside.joinpath("README.md").exists() is False
    assert (harness.workspace_root / "docs-original/README.md").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_direct_patch_payload_cannot_be_applied(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={
            "proposal_id": "patch_123",
            "unified_diff": "--- a/README.md\n+++ b/README.md\n",
        },
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}


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


def propose_patch(service: GovernedToolCallService) -> JsonObject:
    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={
            "path": "README.md",
            "unified_diff": "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        },
        principal=principal(),
        session_id="sess_1",
    )
    assert result.status == "completed"
    return result.content


def request_patch_apply_approval(
    service: GovernedToolCallService,
    proposal_id: str,
) -> JsonObject:
    result = service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal_id},
        principal=principal(),
        session_id="sess_1",
    )
    assert result.status == "approval_required"
    return result.content


def _mutate_approval_scope(
    db_path: Path,
    approval_id: str,
    key: str,
    replacement: object,
) -> None:
    with sqlite3.connect(db_path) as connection:
        raw_scope = connection.execute(
            "SELECT one_time_scope_json FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()[0]
        scope = json.loads(str(raw_scope))
        scope[key] = replacement
        connection.execute(
            "UPDATE approvals SET one_time_scope_json = ? WHERE approval_id = ?",
            (canonical_json(scope), approval_id),
        )
        connection.commit()
