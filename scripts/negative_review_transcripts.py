"""Generate observed negative-review denial transcripts from local fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_api.http_tools import HttpAllowlist, HttpFetchError, HttpFetchExecutor
from ithildin_api.identity import (
    DisabledPrincipalError,
    PrincipalRegistry,
    UnknownPrincipalError,
    resolve_trusted_principal,
)
from ithildin_api.manifest_lock import ManifestLockError, ManifestLockRecord, write_manifest_lock
from ithildin_api.patches import PatchProposalError, PatchProposalService, PatchProposalStore
from ithildin_api.policy_parity import run_policy_parity
from ithildin_api.read_tools import FilesystemReadTools, ReadToolError
from ithildin_api.registry import ToolRegistry
from ithildin_audit_core import (
    AuditWriter,
    generate_audit_signing_keypair,
    signed_audit_export_bundle,
    verify_signed_audit_export_bundle,
)
from ithildin_schemas import AuditEventType, JsonObject, PolicyDecisionValue, sha256_digest

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.2/negative-review-transcripts")
TRANSCRIPT_NAME = "NEGATIVE_REVIEW_TRANSCRIPTS.md"


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    command_or_setup: str
    expected: str
    observed_status: str
    observed_reason: str
    evidence_pointer: str


class FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[Request] = []

    def open(self, fullurl: Request, timeout: float = 0) -> object:
        self.requests.append(fullurl)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: object,
        resolved_ips: Sequence[str],
        timeout: float = 0,
    ) -> object:
        return self.open(fullurl, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_path = build_transcripts(args.output_dir)
    print(f"Built negative review transcripts at {output_path}")
    return 0


def build_transcripts(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="ithildin-negative-review-") as temp_dir:
        root = Path(temp_dir)
        results = [
            _path_traversal(root / "path-traversal"),
            _symlink_escape(root / "symlink-escape"),
            _hidden_sensitive_path(root / "hidden-sensitive"),
            _stale_base_patch_apply(root / "stale-base"),
            _http_private_redirect(),
            _http_credentials_url(),
            _unknown_principal(root / "unknown-principal"),
            _disabled_principal(root / "disabled-principal"),
            _replayed_approval(root / "replayed-approval"),
            _manifest_lock_tamper(root / "manifest-lock-tamper"),
            _policy_parity_mismatch(root / "policy-parity-mismatch"),
            _patch_apply_ambiguous_diagnostics(root / "patch-apply-ambiguous"),
            _signed_audit_export_tamper(root / "signed-audit-tamper"),
        ]
    transcript_path = output_dir / TRANSCRIPT_NAME
    transcript_path.write_text(_render_transcript(results), encoding="utf-8")
    return transcript_path


def _path_traversal(root: Path) -> ScenarioResult:
    filesystem = _filesystem(root)
    root.joinpath("outside.txt").write_text("do-not-leak-path-traversal", encoding="utf-8")
    try:
        filesystem.read_file("../outside.txt")
    except ReadToolError as exc:
        return _denied(
            name="Path Traversal Denial",
            command_or_setup='fs.read {"path":"../outside.txt","workspace_id":"default"}',
            expected="deny before file content is returned",
            reason=exc.reason,
            evidence="ReadToolError raised before executor returned content",
        )
    raise AssertionError("path traversal was not denied")


def _symlink_escape(root: Path) -> ScenarioResult:
    filesystem = _filesystem(root)
    outside = root / "outside.txt"
    outside.write_text("do-not-leak-symlink", encoding="utf-8")
    filesystem.workspace_root.joinpath("link.txt").symlink_to(outside)
    try:
        filesystem.read_file("link.txt")
    except ReadToolError as exc:
        return _denied(
            name="Symlink Escape Denial",
            command_or_setup='fs.read {"path":"link.txt","workspace_id":"default"}',
            expected="deny symlink/path escape before target content is returned",
            reason=exc.reason,
            evidence="ReadToolError raised during workspace path resolution",
        )
    raise AssertionError("symlink escape was not denied")


def _hidden_sensitive_path(root: Path) -> ScenarioResult:
    filesystem = _filesystem(root)
    filesystem.workspace_root.joinpath(".env").write_text(
        "do-not-leak-hidden-path",
        encoding="utf-8",
    )
    try:
        filesystem.read_file(".env")
    except ReadToolError as exc:
        return _denied(
            name="Hidden Sensitive Path Denial",
            command_or_setup='fs.read {"path":".env","workspace_id":"default"}',
            expected="deny hidden/sensitive path before file content is returned",
            reason=exc.reason,
            evidence="ReadToolError raised by hidden/sensitive path policy",
        )
    raise AssertionError("hidden sensitive path was not denied")


def _stale_base_patch_apply(root: Path) -> ScenarioResult:
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    target = workspace / "README.md"
    target.write_text("old\n", encoding="utf-8")
    db_path = root / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, root / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    filesystem = FilesystemReadTools(workspace, max_read_bytes=4096, search_result_limit=10)
    patch_service = PatchProposalService(patch_store, filesystem, max_patch_bytes=4096)
    principal: JsonObject = {"id": "agent:mcp-local", "roles": ["AgentDeveloper"]}
    proposal = patch_service.create_proposal(
        request_id="req_negative_stale_base",
        principal=principal,
        path="README.md",
        unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
    )
    request_hash = sha256_digest({"scenario": "stale-base-patch-apply"})
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    manifest_hash = "sha256:" + ("a" * 64)
    policy_hash = "sha256:" + ("b" * 64)
    schema_hash = "sha256:" + ("c" * 64)
    scope = patch_service.approval_scope(
        proposal.proposal_id,
        manifest_hash=manifest_hash,
        manifest_version="1.0.0",
        tool_input_schema_hash=schema_hash,
        policy_engine="yaml",
        policy_hash=policy_hash,
        policy_version="policy-v1",
        policy_document_version="default-v1",
        matched_rules=["require_write_approval"],
        requesting_principal=principal,
        request_hash=request_hash,
        expires_at=expires_at,
    )
    approval = approval_service.create_pending(
        CreateApprovalInput(
            principal=principal,
            tool_name="fs.patch.apply",
            resource={"path": "README.md", "workspace_id": "default"},
            summary="Apply stale-base negative review patch",
            one_time_scope=scope,
            request_hash=request_hash,
            expires_at=expires_at,
        )
    )
    approval_service.approve(approval.approval_id, decided_by="admin:negative-review")
    target.write_text("changed before apply\n", encoding="utf-8")
    try:
        patch_service.apply_approved(
            approval_service=approval_service,
            approval_id=approval.approval_id,
            expected_manifest_hash=manifest_hash,
            expected_manifest_version="1.0.0",
            expected_tool_input_schema_hash=schema_hash,
            expected_policy_engine="yaml",
            expected_policy_hash=policy_hash,
            expected_policy_version="policy-v1",
            expected_policy_document_version="default-v1",
            expected_matched_rules=["require_write_approval"],
            expected_principal=principal,
        )
    except PatchProposalError as exc:
        return _denied(
            name="Stale-Base Patch Apply Denial",
            command_or_setup="fs.patch.apply with an approved approval_id after target mutation",
            expected="deny stale base and avoid partial writes",
            reason=exc.reason,
            evidence="PatchProposalError raised before atomic replace",
        )
    raise AssertionError("stale-base patch apply was not denied")


def _http_private_redirect() -> ScenarioResult:
    redirect = HTTPError(
        "https://example.com/",
        302,
        "Found",
        _headers(location="https://metadata.example/"),
        None,
    )

    def resolver(host: str, port: int) -> Sequence[str]:
        return ["169.254.169.254"] if host == "metadata.example" else ["93.184.216.34"]

    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com,https://metadata.example"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=resolver,
        opener=FakeOpener([redirect]),
    )
    try:
        executor.fetch("https://example.com/")
    except HttpFetchError as exc:
        return _denied(
            name="HTTP Private Redirect Denial",
            command_or_setup='http.fetch {"url":"https://example.com/"} with redirect fixture',
            expected="deny redirect destination after DNS/IP revalidation",
            reason=str(exc),
            evidence="HttpFetchError raised before blocked destination body was read",
        )
    raise AssertionError("private redirect was not denied")


def _http_credentials_url() -> ScenarioResult:
    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=FakeOpener([]),
    )
    try:
        executor.fetch("https://user:pass@example.com/")
    except HttpFetchError as exc:
        return _denied(
            name="HTTP Credential URL Denial",
            command_or_setup='http.fetch {"url":"https://user:pass@example.com/"}',
            expected="deny credential-bearing URL before any request is opened",
            reason=str(exc),
            evidence="HttpFetchError raised before opener received a request",
        )
    raise AssertionError("credential-bearing HTTP URL was not denied")


def _unknown_principal(root: Path) -> ScenarioResult:
    registry_path = root / "principals.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text("principals: []\n", encoding="utf-8")
    registry = PrincipalRegistry.load(registry_path)
    try:
        resolve_trusted_principal(registry, {"id": "agent:not-registered", "roles": ["Admin"]})
    except UnknownPrincipalError as exc:
        return _denied(
            name="Unknown Principal Denial",
            command_or_setup='principal {"id":"agent:not-registered","roles":["Admin"]}',
            expected="deny unknown principal and ignore spoofed roles",
            reason=str(exc),
            evidence="UnknownPrincipalError raised during trusted principal resolution",
        )
    raise AssertionError("unknown principal was not denied")


def _disabled_principal(root: Path) -> ScenarioResult:
    registry_path = root / "principals.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        """
principals:
  - id: agent:disabled-review
    type: agent
    display_name: Disabled Review Agent
    roles: [AgentDeveloper]
    enabled: false
""",
        encoding="utf-8",
    )
    registry = PrincipalRegistry.load(registry_path)
    try:
        resolve_trusted_principal(registry, {"id": "agent:disabled-review"})
    except DisabledPrincipalError as exc:
        return _denied(
            name="Disabled Principal Denial",
            command_or_setup='principal {"id":"agent:disabled-review"}',
            expected="deny disabled principal before policy or execution",
            reason=str(exc),
            evidence="DisabledPrincipalError raised during trusted principal resolution",
        )
    raise AssertionError("disabled principal was not denied")


def _replayed_approval(root: Path) -> ScenarioResult:
    db_path = root / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, root / "audit.jsonl")
    audit_writer.initialize()
    store = ApprovalStore(db_path)
    store.initialize()
    service = ApprovalService(store, audit_writer, timedelta(minutes=15))
    approval = service.create_pending(
        CreateApprovalInput(
            principal={"id": "agent:mcp-local"},
            tool_name="fs.patch.apply",
            resource={"path": "README.md"},
            summary="Replay negative review approval",
            one_time_scope={"scenario": "replay-denial"},
        )
    )
    approved = service.approve(approval.approval_id, decided_by="admin:negative-review")
    executing = service.begin_execution(approved.approval_id, approved.request_hash)
    service.complete_execution(executing.approval_id, success=True)
    try:
        service.begin_execution(approved.approval_id, approved.request_hash)
    except ApprovalError as exc:
        return _denied(
            name="Replayed Approval Denial",
            command_or_setup="approval begin_execution after successful completion",
            expected="deny replay after one-time approval consumption",
            reason=str(exc),
            evidence="ApprovalError raised after approval reached executed state",
        )
    raise AssertionError("replayed approval was not denied")


def _manifest_lock_tamper(root: Path) -> ScenarioResult:
    manifest_dir = root / "manifests"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "fs-read.yaml"
    _write_simple_manifest(manifest_path, title="Read")
    registry = ToolRegistry.load(manifest_dir)
    lock_path = root / "tool-manifests.lock.json"
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
    _write_simple_manifest(manifest_path, title="Tampered Read")
    try:
        ToolRegistry.load(manifest_dir, lock_path=lock_path, require_lock=True)
    except ManifestLockError as exc:
        return _denied(
            name="Manifest Lock Tamper Denial",
            command_or_setup="ToolRegistry.load with require_lock=True after manifest mutation",
            expected="fail closed on manifest hash mismatch",
            reason=str(exc),
            evidence="ManifestLockError raised before registry startup completed",
        )
    raise AssertionError("manifest lock tamper was not denied")


def _policy_parity_mismatch(root: Path) -> ScenarioResult:
    fixture = root / "parity.yaml"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(
        """
version: negative-review
cases:
  - id: expected-decision-mismatch
    tool_name: fs.list
    arguments: {path: "."}
    principal: {id: agent:mcp-local}
    session_id: negative-parity
    expect_decision: deny
""",
        encoding="utf-8",
    )
    run = run_policy_parity(repo_root=Path.cwd(), work_dir=root / "work", tests_path=fixture)
    if run.failed > 0:
        return _denied(
            name="Policy Parity Mismatch Detection",
            command_or_setup="policy parity fixture expecting deny for an allowed read",
            expected="fail the parity case without mutating runtime policy",
            reason="; ".join(run.cases[0].failures),
            evidence="Policy parity harness reported a failed fixture case",
        )
    raise AssertionError("policy parity mismatch was not detected")


def _patch_apply_ambiguous_diagnostics(root: Path) -> ScenarioResult:
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    db_path = root / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, root / "audit.jsonl")
    audit_writer.initialize()
    store = ApprovalStore(db_path)
    store.initialize()
    service = ApprovalService(store, audit_writer, timedelta(minutes=15))
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    filesystem = FilesystemReadTools(workspace, max_read_bytes=4096, search_result_limit=10)
    patch_service = PatchProposalService(patch_store, filesystem, max_patch_bytes=4096)
    approval = service.create_pending(
        CreateApprovalInput(
            principal={"id": "agent:mcp-local"},
            tool_name="fs.patch.apply",
            resource={"path": "README.md"},
            summary="Ambiguous diagnostic negative review approval",
            one_time_scope={"proposal_id": "patch_missing"},
        )
    )
    approved = service.approve(approval.approval_id, decided_by="admin:negative-review")
    service.begin_execution(approved.approval_id, approved.request_hash)
    diagnostics = patch_service.patch_apply_diagnostics(service)
    if diagnostics["status"] == "ambiguous":
        return _denied(
            name="Patch Apply Ambiguous Diagnostics",
            command_or_setup="executing fs.patch.apply approval with no apply-attempt record",
            expected="report ambiguous diagnostics and recommend manual review",
            reason="patch apply diagnostics reported ambiguous state",
            evidence="patch_apply_diagnostics returned status=ambiguous",
        )
    raise AssertionError("ambiguous patch apply diagnostics were not reported")


def _signed_audit_export_tamper(root: Path) -> ScenarioResult:
    db_path = root / "ithildin.sqlite3"
    audit_log_path = root / "audit.jsonl"
    private_key_path = root / "audit-ed25519-private.pem"
    public_key_path = root / "audit-ed25519-public.pem"
    writer = AuditWriter(db_path, audit_log_path)
    writer.initialize()
    writer.write_event(
        event_id="evt_negative_signed_audit_001",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_negative_signed_audit_001",
        principal={"id": "demo:reviewer", "roles": ["Auditor"]},
        tool_name="fs.read",
        decision=PolicyDecisionValue.ALLOW,
        metadata={"scenario": "negative signed audit tamper"},
    )
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    bundle = signed_audit_export_bundle(
        jsonl_bundle=writer.export_jsonl_bundle(),
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    tampered = json.loads(json.dumps(bundle))
    tampered["events_sha256"] = "sha256:" + ("f" * 64)
    result = verify_signed_audit_export_bundle(tampered, public_key_path=public_key_path)
    if not result.valid:
        return _denied(
            name="Signed Audit Export Tamper Denial",
            command_or_setup="offline signed audit export verification after digest mutation",
            expected="reject tampered signed bundle during offline verification",
            reason=result.failure or "signed audit verification failed",
            evidence="verify_signed_audit_export_bundle returned verified=false",
        )
    raise AssertionError("tampered signed audit export was not rejected")


def _filesystem(root: Path) -> FilesystemReadTools:
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    return FilesystemReadTools(
        workspace_root=workspace,
        max_read_bytes=4096,
        search_result_limit=10,
    )


def _write_simple_manifest(path: Path, *, title: str) -> None:
    path.write_text(
        f"""
name: fs.read
version: 1.0.0
title: {title}
risk: read
category: test
mcp:
  exposed: true
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


def _denied(
    *,
    name: str,
    command_or_setup: str,
    expected: str,
    reason: str,
    evidence: str,
) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        command_or_setup=command_or_setup,
        expected=expected,
        observed_status="denied",
        observed_reason=_safe_reason(reason),
        evidence_pointer=evidence,
    )


def _safe_reason(reason: str) -> str:
    return " ".join(reason.split())


def _headers(*, location: str) -> Message:
    headers = Message()
    headers["Location"] = location
    return headers


def _render_transcript(results: list[ScenarioResult]) -> str:
    sections = [
        "# Negative Review Transcripts",
        "",
        "These are observed local fixture denials for reviewer convenience. They are not a",
        "replacement for external source review and do not add tools, endpoints, or execution",
        "powers.",
        "",
    ]
    for result in results:
        sections.extend(
            [
                f"## {result.name}",
                "",
                f"- command/setup: `{result.command_or_setup}`",
                f"- expected: {result.expected}",
                f"- observed status: `{result.observed_status}`",
                f"- observed safe reason: `{result.observed_reason}`",
                f"- evidence pointer: {result.evidence_pointer}",
                "",
            ]
        )
    return "\n".join(sections)


if __name__ == "__main__":
    raise SystemExit(main())
