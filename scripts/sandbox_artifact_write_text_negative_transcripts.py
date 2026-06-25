"""Generate observed sandbox.artifact.write_text negative-review transcripts."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.sandbox_artifacts import SandboxArtifactWriteService
from ithildin_api.tool_calls import GovernedToolCallResult, GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import JsonObject

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-artifact-write-text-negative")
TRANSCRIPT_NAME = "SANDBOX_ARTIFACT_WRITE_TEXT_NEGATIVE_TRANSCRIPTS.md"


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    setup: str
    expected: str
    observed_status: str
    observed_reason: str
    evidence_pointer: str


@dataclass(frozen=True)
class Harness:
    service: GovernedToolCallService
    approval_service: ApprovalService
    workspace_root: Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    transcript_path = build_transcripts(args.output_dir)
    print(f"Built sandbox artifact negative transcripts at {transcript_path}")
    return 0


def build_transcripts(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="ithildin-sandbox-write-negative-") as temp_dir:
        root = Path(temp_dir)
        results = [
            _path_traversal(root / "path-traversal"),
            _hidden_sensitive_path(root / "hidden-sensitive"),
            _symlink_target(root / "symlink-target"),
            _approval_content_mismatch(root / "content-mismatch"),
            _replayed_approval(root / "replayed-approval"),
            _overwrite_denied_by_default(root / "overwrite-denied"),
            _existing_non_utf8_target(root / "non-utf8-target"),
        ]
    transcript_path = output_dir / TRANSCRIPT_NAME
    transcript_path.write_text(_render(results), encoding="utf-8")
    return transcript_path


def _path_traversal(root: Path) -> ScenarioResult:
    harness = _harness(root)
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={
            "sandbox_id": "local-demo-sandbox",
            "relative_path": "../outside.txt",
            "content": "redacted fixture text",
        },
        principal=_principal(),
        session_id="negative-path-traversal",
    )
    return _scenario(
        name="Traversal Denial",
        setup='sandbox.artifact.write_text {"relative_path":"../outside.txt"}',
        expected="deny before approval creation or file write",
        result=result,
        evidence_pointer="GovernedToolCallResult returned denied; temp workspace unchanged",
    )


def _hidden_sensitive_path(root: Path) -> ScenarioResult:
    harness = _harness(root)
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={
            "sandbox_id": "local-demo-sandbox",
            "relative_path": ".env",
            "content": "redacted fixture text",
        },
        principal=_principal(),
        session_id="negative-hidden-sensitive",
    )
    return _scenario(
        name="Hidden/Sensitive Path Denial",
        setup='sandbox.artifact.write_text {"relative_path":".env"}',
        expected="deny hidden or sensitive artifact target",
        result=result,
        evidence_pointer="Sandbox artifact path validator rejected hidden/sensitive path",
    )


def _symlink_target(root: Path) -> ScenarioResult:
    harness = _harness(root)
    outside = root / "outside.txt"
    outside.write_text("outside fixture text", encoding="utf-8")
    harness.workspace_root.joinpath("hello-demo", "link.txt").symlink_to(outside)
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={
            "sandbox_id": "local-demo-sandbox",
            "relative_path": "hello-demo/link.txt",
            "content": "redacted fixture text",
        },
        principal=_principal(),
        session_id="negative-symlink",
    )
    return _scenario(
        name="Symlink Target Denial",
        setup='sandbox.artifact.write_text {"relative_path":"hello-demo/link.txt"}',
        expected="deny symlink target before approval creation or file write",
        result=result,
        evidence_pointer="Sandbox artifact path validator rejected symlink target",
    )


def _approval_content_mismatch(root: Path) -> ScenarioResult:
    harness = _harness(root)
    arguments: JsonObject = {
        "sandbox_id": "local-demo-sandbox",
        "relative_path": "hello-demo/mismatch.txt",
        "content": "redacted approved fixture text",
    }
    request = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments=arguments,
        principal=_principal(),
        session_id="negative-content-mismatch",
    )
    approval_id = cast(str, request.content["approval_id"])
    harness.approval_service.approve(approval_id, decided_by="admin:local-ui")
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={
            **arguments,
            "content": "redacted changed fixture text",
            "approval_id": approval_id,
        },
        principal=_principal(),
        session_id="negative-content-mismatch",
    )
    target_exists = harness.workspace_root.joinpath("hello-demo", "mismatch.txt").exists()
    return _scenario(
        name="Approval Content Mismatch Denial",
        setup="approved content hash does not match execution content hash",
        expected="deny execution without writing target",
        result=result,
        evidence_pointer=f"target_exists_after_denial={str(target_exists).lower()}",
    )


def _replayed_approval(root: Path) -> ScenarioResult:
    harness = _harness(root)
    arguments: JsonObject = {
        "sandbox_id": "local-demo-sandbox",
        "relative_path": "hello-demo/replay.txt",
        "content": "redacted fixture text",
    }
    request = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments=arguments,
        principal=_principal(),
        session_id="negative-replay",
    )
    approval_id = cast(str, request.content["approval_id"])
    harness.approval_service.approve(approval_id, decided_by="admin:local-ui")
    first = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={**arguments, "approval_id": approval_id},
        principal=_principal(),
        session_id="negative-replay",
    )
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={**arguments, "approval_id": approval_id},
        principal=_principal(),
        session_id="negative-replay",
    )
    return _scenario(
        name="Replayed Approval Denial",
        setup=f"first_execution_status={first.status}; second execution reuses approval_id",
        expected="second execution denied and approval remains non-replayable",
        result=result,
        evidence_pointer=f"approval_status={harness.approval_service.get(approval_id).status.value}",
    )


def _overwrite_denied_by_default(root: Path) -> ScenarioResult:
    harness = _harness(root)
    target = harness.workspace_root / "hello-demo" / "existing.txt"
    target.write_text("existing fixture text", encoding="utf-8")
    arguments: JsonObject = {
        "sandbox_id": "local-demo-sandbox",
        "relative_path": "hello-demo/existing.txt",
        "content": "redacted replacement fixture text",
    }
    request = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments=arguments,
        principal=_principal(),
        session_id="negative-overwrite",
    )
    approval_id = cast(str, request.content["approval_id"])
    harness.approval_service.approve(approval_id, decided_by="admin:local-ui")
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={**arguments, "approval_id": approval_id},
        principal=_principal(),
        session_id="negative-overwrite",
    )
    return _scenario(
        name="Overwrite Denied By Default",
        setup="target exists and overwrite flag is false",
        expected="deny overwrite and preserve existing target",
        result=result,
        evidence_pointer=f"target_size_after_denial={target.stat().st_size}",
    )


def _existing_non_utf8_target(root: Path) -> ScenarioResult:
    harness = _harness(root)
    target = harness.workspace_root / "hello-demo" / "binary.txt"
    target.write_bytes(b"\xff\xfe\x00")
    arguments: JsonObject = {
        "sandbox_id": "local-demo-sandbox",
        "relative_path": "hello-demo/binary.txt",
        "content": "redacted fixture text",
        "overwrite": True,
    }
    request = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments=arguments,
        principal=_principal(),
        session_id="negative-non-utf8",
    )
    approval_id = cast(str, request.content["approval_id"])
    harness.approval_service.approve(approval_id, decided_by="admin:local-ui")
    result = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={**arguments, "approval_id": approval_id},
        principal=_principal(),
        session_id="negative-non-utf8",
    )
    return _scenario(
        name="Existing Non-UTF-8 Target Denial",
        setup="existing target is not valid UTF-8 text",
        expected="deny safely without raw decoder error or overwrite",
        result=result,
        evidence_pointer=f"target_size_after_denial={target.stat().st_size}",
    )


def _harness(root: Path) -> Harness:
    db_path = root / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, root / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = root / "workspace"
    workspace_root.mkdir(parents=True)
    workspace_root.joinpath("hello-demo").mkdir()
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=4096,
        search_result_limit=10,
        git_log_limit=10,
    )
    service = GovernedToolCallService(
        ToolRegistry.load(ROOT / "tool-manifests"),
        PolicyEvaluator.load(ROOT / "policies/default.yaml"),
        approval_service,
        audit_writer,
        read_executor,
        sandbox_artifact_service=SandboxArtifactWriteService.from_read_executor(read_executor),
    )
    return Harness(service, approval_service, workspace_root)


def _principal() -> JsonObject:
    return {"id": "agent:local-dev", "roles": ["AgentDeveloper"]}


def _scenario(
    *,
    name: str,
    setup: str,
    expected: str,
    result: GovernedToolCallResult,
    evidence_pointer: str,
) -> ScenarioResult:
    status = result.status
    content = result.content
    reason = content.get("reason")
    if not isinstance(reason, str):
        reason = json.dumps(content, sort_keys=True)
    return ScenarioResult(
        name=name,
        setup=setup,
        expected=expected,
        observed_status=str(status),
        observed_reason=reason,
        evidence_pointer=evidence_pointer,
    )


def _render(results: list[ScenarioResult]) -> str:
    lines = [
        "# sandbox.artifact.write_text Negative Review Transcripts",
        "",
        "Status: observed local fixture transcripts.",
        "",
        "These transcripts exercise the implemented bounded local-preview write path in temporary",
        "workspaces. They do not expose file contents, raw host paths, prompts, secrets, VM logs,",
        "Mission Control state, or sandbox internals.",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.name}",
                "",
                f"- Setup/command: `{result.setup}`",
                f"- Expected: {result.expected}",
                f"- Observed status: `{result.observed_status}`",
                f"- Observed reason: `{result.observed_reason}`",
                f"- Evidence pointer: {result.evidence_pointer}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- No host promotion is performed.",
            "- No VM/container lifecycle is started.",
            "- No shell, Docker, Kubernetes, browser automation, arbitrary HTTP, or broad",
            "  filesystem write behavior is introduced.",
            "- These transcripts support local-preview source review; they do not claim external",
            "  review closure or production safety.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
