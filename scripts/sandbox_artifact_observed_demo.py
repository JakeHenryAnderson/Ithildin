"""Generate an observed sandbox.artifact.write_text demo transcript."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.promotion_authority import AdminPrincipalContext
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.sandbox_artifacts import SandboxArtifactWriteService
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import JsonObject, sha256_digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-artifact-observed-demo")
TRANSCRIPT_NAME = "SANDBOX_ARTIFACT_OBSERVED_DEMO.md"
JSON_NAME = "sandbox-artifact-observed-demo.json"
HASHES_NAME = "artifact-hashes.json"
ADMIN_CONTEXT = AdminPrincipalContext(
    principal_id="admin:local-ui",
    principal_type="admin",
    roles=("Admin",),
    authentication_method="local_admin_bearer",
    identity_source="principal_registry",
    identity_generation="sha256:" + ("d" * 64),
)
DEMO_CONTENT = "Hello World\n"


@dataclass(frozen=True)
class Harness:
    service: GovernedToolCallService
    approval_service: ApprovalService
    audit_writer: AuditWriter
    workspace_root: Path


class SandboxArtifactObservedDemoError(RuntimeError):
    """Raised when the observed sandbox artifact demo cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = build_demo(args.output_dir)
    print(f"Built sandbox artifact observed demo at {output_dir}")
    return 0


def build_demo(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="ithildin-sandbox-artifact-observed-") as temp_dir:
        payload = _run_observed_demo(Path(temp_dir))
    _write_json(output_dir / JSON_NAME, payload)
    (output_dir / TRANSCRIPT_NAME).write_text(_render(payload), encoding="utf-8")
    _write_json(output_dir / HASHES_NAME, _artifact_hashes(output_dir))
    return output_dir


def _run_observed_demo(root: Path) -> dict[str, Any]:
    harness = _harness(root)
    arguments: JsonObject = {
        "sandbox_id": "local-demo-sandbox",
        "root": ".",
        "relative_path": "hello-demo/hello.txt",
        "content": DEMO_CONTENT,
        "idempotency_key": "observed-sandbox-artifact-demo",
    }
    request = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments=arguments,
        principal=_principal(),
        session_id="observed-sandbox-artifact-demo",
    )
    if request.status != "approval_required":
        raise SandboxArtifactObservedDemoError(
            f"expected approval_required, observed {request.status}"
        )
    approval_id = cast(str, request.content["approval_id"])
    harness.approval_service.approve(approval_id, context=ADMIN_CONTEXT)
    execution = harness.service.call_tool(
        tool_name="sandbox.artifact.write_text",
        arguments={**arguments, "approval_id": approval_id},
        principal=_principal(),
        session_id="observed-sandbox-artifact-demo",
    )
    if execution.status != "completed":
        raise SandboxArtifactObservedDemoError(f"expected completed, observed {execution.status}")
    approval = harness.approval_service.get(approval_id)
    artifact = harness.workspace_root / "hello-demo" / "hello.txt"
    if not artifact.exists():
        raise SandboxArtifactObservedDemoError("expected artifact was not created")
    artifact_bytes = artifact.read_bytes()
    artifact_sha256 = "sha256:" + hashlib.sha256(artifact_bytes).hexdigest()
    artifact_content_hash = sha256_digest(artifact.read_text(encoding="utf-8"))
    audit_verification = harness.audit_writer.verify_chain().as_dict()
    request_content = cast(dict[str, Any], request.content)
    execution_content = cast(dict[str, Any], execution.content)
    return {
        "schema_version": "1",
        "status": "observed_local_fixture",
        "tool_name": "sandbox.artifact.write_text",
        "tool_count": 24,
        "governed_tool_calls_performed": True,
        "mission_control_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "sandbox_orchestration_performed": False,
        "shell_execution_performed": False,
        "host_promotion_performed": False,
        "request": {
            "status": request.status,
            "request_id": request.request_id,
            "approval_id": approval_id,
            "artifact_label": request_content.get("artifact_label"),
            "content_sha256": request_content.get("content_sha256"),
            "content_bytes": request_content.get("content_bytes"),
            "policy_reason": request_content.get("policy_reason"),
        },
        "approval": {
            "approval_id": approval_id,
            "status": approval.status.value,
            "tool_name": approval.tool_name,
            "summary": approval.summary,
            "content_bound_by_hash": "content_sha256" in approval.one_time_scope,
            "raw_content_stored_in_scope": "content" in approval.one_time_scope,
        },
        "execution": {
            "status": execution.status,
            "request_id": execution.request_id,
            "result_status": execution_content.get("status"),
            "approval_id": execution_content.get("approval_id"),
            "artifact_label": execution_content.get("artifact_label"),
            "content_sha256": execution_content.get("content_sha256"),
            "content_bytes": execution_content.get("content_bytes"),
            "output_policy_keys": sorted(
                cast(dict[str, Any], execution_content.get("output_policy", {})).keys()
            ),
        },
        "artifact": {
            "present": True,
            "label": execution_content.get("artifact_label"),
            "sha256": artifact_content_hash,
            "byte_sha256": artifact_sha256,
            "bytes": len(artifact_bytes),
            "content_matches_execution_hash": artifact_content_hash
            == execution_content.get("content_sha256"),
        },
        "audit": {
            "verification": audit_verification,
        },
        "boundaries": {
            "no_file_contents_in_transcript": True,
            "no_raw_host_paths_in_transcript": True,
            "no_host_promotion": True,
            "no_vm_or_container_lifecycle": True,
            "local_preview_only": True,
        },
    }


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
    return Harness(service, approval_service, audit_writer, workspace_root)


def _principal() -> JsonObject:
    return {"id": "agent:local-dev", "roles": ["AgentDeveloper"]}


def _render(payload: dict[str, Any]) -> str:
    request = payload["request"]
    approval = payload["approval"]
    execution = payload["execution"]
    artifact = payload["artifact"]
    verification = payload["audit"]["verification"]
    return f"""# Sandbox Artifact Observed Demo

Status: observed local fixture execution.

This transcript exercises the implemented `sandbox.artifact.write_text` governed tool in a
temporary local workspace. It records approval, execution, artifact, and audit evidence without
including file contents, raw host paths, prompts, secrets, VM logs, Mission Control runtime state,
or sandbox internals.

## Observed Flow

1. `sandbox.artifact.write_text` requested a bounded text artifact write.
2. The policy path returned `approval_required`.
3. A local admin fixture approved the one-time request.
4. The same governed tool call executed with the approval ID.
5. The target artifact exists in the temporary workspace and matches the approved content hash.
6. The local audit chain verifies after the observed flow.

## Evidence

- Tool: `{payload["tool_name"]}`
- Tool count: `{payload["tool_count"]}`
- Governed tool calls performed: `{str(payload["governed_tool_calls_performed"]).lower()}`
- Initial request status: `{request["status"]}`
- Initial request ID: `{request["request_id"]}`
- Approval ID: `{approval["approval_id"]}`
- Approval status after execution: `{approval["status"]}`
- Approval content bound by hash: `{str(approval["content_bound_by_hash"]).lower()}`
- Raw content stored in approval scope: `{str(approval["raw_content_stored_in_scope"]).lower()}`
- Execution status: `{execution["status"]}`
- Execution request ID: `{execution["request_id"]}`
- Executor result status: `{execution["result_status"]}`
- Artifact label: `{artifact["label"]}`
- Artifact SHA-256: `{artifact["sha256"]}`
- Artifact byte SHA-256: `{artifact["byte_sha256"]}`
- Artifact bytes: `{artifact["bytes"]}`
- Artifact hash matches execution hash: `{str(artifact["content_matches_execution_hash"]).lower()}`
- Audit verification valid: `{str(verification["valid"]).lower()}`
- Audit event count: `{verification["event_count"]}`
- Audit head hash: `{verification["head_hash"]}`

## Boundary

- Mission Control runtime behavior: `false`
- Real VM or container started: `false`
- Sandbox orchestration performed: `false`
- Shell execution performed: `false`
- Host promotion performed: `false`
- Local-preview only: `true`

This demo supports local-preview operator evidence and source review. It does not claim production
sandboxing, external custody, SIEM integration, compliance automation, or enterprise deployment
readiness.
"""


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASHES_NAME:
            continue
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _file_sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": "1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
