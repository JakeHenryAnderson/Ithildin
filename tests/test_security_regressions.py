from __future__ import annotations

import json
from datetime import timedelta
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest
import yaml
from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_api.http_tools import HttpAllowlist, HttpFetchError, HttpFetchExecutor
from ithildin_api.patches import PatchProposalError, PatchProposalService, PatchProposalStore
from ithildin_api.read_tools import FilesystemReadTools, ReadToolError, ReadToolExecutor
from ithildin_api.redaction import RedactionService
from ithildin_api.registry import DuplicateToolManifest, InvalidToolManifest, ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator


class FakeResponse:
    code = 200
    headers = {"Content-Type": "text/plain; charset=utf-8"}

    def read(self, size: int) -> bytes:
        return b"ok"[:size]

    def getcode(self) -> int:
        return self.code


class FakeOpener:
    def __init__(self, responses: list[object] | None = None) -> None:
        self.responses = responses or [FakeResponse()]
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
        resolved_ips: object,
        timeout: float = 0,
    ) -> object:
        return self.open(fullurl, timeout=timeout)


def test_security_regression_filesystem_scope_and_secret_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem = _filesystem(tmp_path, max_read_bytes=4)
    filesystem.workspace_root.joinpath("ok.txt").write_text("ok", encoding="utf-8")
    filesystem.workspace_root.joinpath("large.txt").write_text("large", encoding="utf-8")
    filesystem.workspace_root.joinpath("binary.txt").write_bytes(b"ok\x00")
    filesystem.workspace_root.joinpath("latin1.txt").write_bytes(b"\xff")
    filesystem.workspace_root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    secrets = filesystem.workspace_root / "secrets"
    secrets.mkdir()
    secrets.joinpath("note.txt").write_text("secret", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    filesystem.workspace_root.joinpath("link.txt").symlink_to(outside)
    filesystem.workspace_root.joinpath("inside-link.txt").symlink_to(
        filesystem.workspace_root / "ok.txt"
    )

    denied = [
        ("../ok.txt", "traversal"),
        (str(outside), "absolute"),
        ("link.txt", "symlink"),
        ("inside-link.txt", "symlink"),
        (".env", "hidden or sensitive"),
        ("secrets/note.txt", "hidden or sensitive"),
        ("large.txt", "read limit"),
        ("binary.txt", "binary"),
        ("latin1.txt", "UTF-8"),
    ]
    for path, reason in denied:
        with pytest.raises(ReadToolError, match=reason):
            filesystem.read_file(path)

    race_target = filesystem.workspace_root / "race.txt"
    race_target.write_text("safe", encoding="utf-8")
    original_resolver = filesystem.resolve_existing_path

    def swap_to_symlink(path: str) -> Path:
        resolved = original_resolver(path)
        resolved.unlink()
        resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(filesystem, "resolve_existing_path", swap_to_symlink)
    with pytest.raises(ReadToolError, match="safe regular file"):
        filesystem.read_file("race.txt")


def test_security_regression_patch_validation_and_stale_apply(tmp_path: Path) -> None:
    service = _patch_service(tmp_path)
    target = service.filesystem.workspace_root / "README.md"
    target.write_text("old\n", encoding="utf-8")

    for invalid_diff in [
        "not a diff",
        "Binary files a/README.md and b/README.md differ\n",
        "--- a/README.md\n+++ b/other.md\n@@ -1 +1 @@\n-old\n+new\n",
        "--- /dev/null\n+++ b/README.md\n@@ -0,0 +1 @@\n+new\n",
        "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-stale\n+new\n",
    ]:
        with pytest.raises(PatchProposalError):
            service.create_proposal(
                request_id="req_1",
                principal={"id": "agent:test"},
                path="README.md",
                unified_diff=invalid_diff,
            )

    target.write_bytes(b"old\x00")
    with pytest.raises(PatchProposalError, match="binary"):
        service.create_proposal(
            request_id="req_2",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        )


def test_security_regression_approval_replay_and_hash_mismatch(tmp_path: Path) -> None:
    audit_writer = AuditWriter(tmp_path / "ithildin.sqlite3", tmp_path / "audit.jsonl")
    audit_writer.initialize()
    store = ApprovalStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    service = ApprovalService(store, audit_writer, timedelta(minutes=15))
    approval = service.create_pending(
        CreateApprovalInput(
            principal={"id": "agent:test"},
            tool_name="fs.patch.apply",
            resource={"path": "README.md"},
            summary="Apply patch",
            one_time_scope={"proposal_id": "patch_1"},
        )
    )
    approved = service.approve(approval.approval_id, decided_by="admin:test")

    with pytest.raises(ApprovalError, match="hash mismatch"):
        service.begin_execution(approved.approval_id, "sha256:" + ("1" * 64))

    executing = service.begin_execution(approved.approval_id, approved.request_hash)
    service.complete_execution(executing.approval_id, success=True)
    with pytest.raises(ApprovalError):
        service.begin_execution(approved.approval_id, approved.request_hash)


def test_security_regression_manifest_fail_closed_and_hash_changes(tmp_path: Path) -> None:
    manifest_path = tmp_path / "fs-read.yaml"
    _write_manifest(manifest_path, name="fs.read", title="Read file")
    first_hash = ToolRegistry.load(tmp_path).get_tool("fs.read").manifest_hash
    _write_manifest(manifest_path, name="fs.read", title="Tampered read file")
    second_hash = ToolRegistry.load(tmp_path).get_tool("fs.read").manifest_hash

    assert first_hash != second_hash

    _write_manifest(tmp_path / "duplicate.yaml", name="fs.read", title="Duplicate")
    with pytest.raises(DuplicateToolManifest):
        ToolRegistry.load(tmp_path)

    broken = tmp_path / "broken"
    broken.mkdir()
    broken.joinpath("broken.yaml").write_text("name: [", encoding="utf-8")
    with pytest.raises(InvalidToolManifest):
        ToolRegistry.load(broken)


def test_security_regression_http_ssrf_redirect_and_invalid_url_blocks() -> None:
    opener = FakeOpener()
    executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=lambda host, port: ["127.0.0.1"],
        opener=opener,
    )
    with pytest.raises(HttpFetchError, match="blocked IP"):
        executor.fetch("https://example.com/")
    assert opener.requests == []

    for url in ["file:///etc/passwd", "https://user:pass@example.com/", "https://example.com/#x"]:
        with pytest.raises(HttpFetchError):
            executor.fetch(url)

    redirect = HTTPError(
        "https://example.com/",
        302,
        "Found",
        _headers(location="https://metadata.example/"),
        None,
    )

    def resolver(host: str, port: int) -> list[str]:
        return ["169.254.169.254"] if host == "metadata.example" else ["93.184.216.34"]

    redirect_opener = FakeOpener([redirect])
    redirect_executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv("https://example.com,https://metadata.example"),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=resolver,
        opener=redirect_opener,
    )
    with pytest.raises(HttpFetchError, match="blocked IP"):
        redirect_executor.fetch("https://example.com/")


def test_security_regression_redaction_and_denied_audit_chain(tmp_path: Path) -> None:
    redacted = RedactionService().redact(
        {
            "content": "TOKEN=secret-value",
            "nested": {"authorization": "Bearer abcdefghijklmnopqrstuvwxyz"},
        }
    )
    assert "secret-value" not in str(redacted.value)
    assert "abcdefghijklmnopqrstuvwxyz" not in str(redacted.value)

    service, audit_writer = _governed_read_service(tmp_path)
    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "../README.md"},
        principal={"id": "agent:test"},
        session_id="sess_1",
    )

    assert result.status == "denied"
    verification = audit_writer.verify_chain()
    assert verification.valid is True
    payloads = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [payload["event_type"] for payload in payloads] == ["policy.evaluated"]
    assert payloads[0]["decision"] == "deny"
    assert (
        payloads[0]["metadata"]["reason"]
        == "path traversal is outside the workspace scope"
    )


def test_deployment_security_boundaries_are_loopback_and_no_docker_socket() -> None:
    compose_text = Path("deploy/docker-compose.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    services = compose["services"]

    all_ports = [
        port
        for service in services.values()
        for port in service.get("ports", [])
    ]
    all_volumes = [
        volume
        for service in services.values()
        for volume in service.get("volumes", [])
    ]

    assert all(str(port).startswith("127.0.0.1:") for port in all_ports)
    assert "docker.sock" not in compose_text
    assert all("docker.sock" not in str(volume) for volume in all_volumes)


def _filesystem(tmp_path: Path, *, max_read_bytes: int = 128) -> FilesystemReadTools:
    return FilesystemReadTools(
        workspace_root=tmp_path / "workspace",
        max_read_bytes=max_read_bytes,
        search_result_limit=10,
    )


def _patch_service(tmp_path: Path) -> PatchProposalService:
    filesystem = _filesystem(tmp_path, max_read_bytes=4096)
    store = PatchProposalStore(tmp_path / "patches.sqlite3")
    store.initialize()
    return PatchProposalService(store, filesystem, max_patch_bytes=4096)


def _governed_read_service(tmp_path: Path) -> tuple[GovernedToolCallService, AuditWriter]:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    _write_manifest(manifest_dir / "fs-read.yaml", name="fs.read", title="Read file")
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
version: security-regression
rules:
  - id: allow_reads
    decision: allow
    reason: reads allowed
    match:
      tool.risk: read
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=tmp_path / "workspace",
        max_read_bytes=128,
        search_result_limit=10,
        git_log_limit=10,
    )
    read_executor.filesystem.workspace_root.joinpath("README.md").write_text(
        "safe\n",
        encoding="utf-8",
    )
    service = GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        ApprovalService(approval_store, audit_writer, timedelta(minutes=15)),
        audit_writer,
        read_executor,
    )
    return service, audit_writer


def _write_manifest(path: Path, *, name: str, title: str) -> None:
    path.write_text(
        f"""
name: {name}
version: 1.0.0
title: {title}
risk: read
category: security
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


def _headers(*, location: str) -> Message:
    headers = Message()
    headers["Location"] = location
    return headers
