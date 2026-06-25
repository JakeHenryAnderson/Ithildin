"""Generate an observed Hello World sandbox demo packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sandbox_artifact_observed_demo

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/hello-world-sandbox-observed-demo")
INDEX_NAME = "HELLO_WORLD_SANDBOX_OBSERVED_DEMO.md"
JSON_NAME = "hello-world-sandbox-observed-demo.json"
HASHES_NAME = "artifact-hashes.json"
OBSERVED_DIR_NAME = "observed-governed-tool"


class HelloWorldSandboxObservedDemoError(RuntimeError):
    """Raised when the observed Hello World sandbox demo cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        output_dir = build_demo(args.output_dir)
    except HelloWorldSandboxObservedDemoError as exc:
        print(f"Hello World observed sandbox demo failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built observed Hello World sandbox demo at {output_dir}")
    return 0


def build_demo(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    observed_dir = output_dir / OBSERVED_DIR_NAME
    sandbox_artifact_observed_demo.build_demo(observed_dir)
    observed_payload = json.loads(
        observed_dir.joinpath(sandbox_artifact_observed_demo.JSON_NAME).read_text(
            encoding="utf-8"
        )
    )
    payload = _payload(observed_payload)
    _write_json(output_dir / JSON_NAME, payload)
    output_dir.joinpath(INDEX_NAME).write_text(_render(payload), encoding="utf-8")
    _write_json(output_dir / HASHES_NAME, _artifact_hashes(output_dir))
    return output_dir


def _payload(observed: dict[str, Any]) -> dict[str, Any]:
    artifact = observed["artifact"]
    approval = observed["approval"]
    audit = observed["audit"]["verification"]
    execution = observed["execution"]
    request = observed["request"]
    return {
        "schema_version": "1",
        "status": "observed_hello_world_local_fixture",
        "generated_at": datetime.now(UTC).isoformat(),
        "demo_goal": "hello_world_sandbox_artifact",
        "tool_name": observed["tool_name"],
        "tool_count": observed["tool_count"],
        "governed_tool_calls_performed": True,
        "mission_control_runtime_behavior": False,
        "local_llm_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "sandbox_orchestration_performed": False,
        "shell_execution_performed": False,
        "host_promotion_performed": False,
        "operator_intent": {
            "mission_id": "mc-hello-world-demo",
            "intent_label": "create fixed hello world sandbox artifact",
            "mission_control_authority": "metadata_only",
        },
        "local_llm_plan": {
            "plan_status": "simulated_metadata_only",
            "model_client_label": "local-llm-plan-dry-run",
            "proposed_action": "write_text_file",
            "artifact_label": artifact["label"],
            "content_sha256": artifact["sha256"],
            "requires_approval": True,
            "raw_prompt_recorded": False,
            "chain_of_thought_recorded": False,
        },
        "governed_request": {
            "status": request["status"],
            "request_id": request["request_id"],
            "approval_id": request["approval_id"],
            "policy_reason": request["policy_reason"],
        },
        "approval": {
            "approval_id": approval["approval_id"],
            "status": approval["status"],
            "tool_name": approval["tool_name"],
            "content_bound_by_hash": approval["content_bound_by_hash"],
            "raw_content_stored_in_scope": approval["raw_content_stored_in_scope"],
        },
        "execution": {
            "status": execution["status"],
            "request_id": execution["request_id"],
            "result_status": execution["result_status"],
            "approval_id": execution["approval_id"],
            "content_sha256": execution["content_sha256"],
            "content_bytes": execution["content_bytes"],
            "output_policy_keys": execution["output_policy_keys"],
        },
        "artifact": {
            "present": artifact["present"],
            "artifact_label": artifact["label"],
            "content_sha256": artifact["sha256"],
            "byte_sha256": artifact["byte_sha256"],
            "bytes": artifact["bytes"],
            "hash_matches_execution": artifact["content_matches_execution_hash"],
        },
        "audit": {
            "valid": audit["valid"],
            "event_count": audit["event_count"],
            "head_hash": audit["head_hash"],
        },
        "observed_governed_tool_packet": {
            "path": f"{OBSERVED_DIR_NAME}/{sandbox_artifact_observed_demo.TRANSCRIPT_NAME}",
            "json": f"{OBSERVED_DIR_NAME}/{sandbox_artifact_observed_demo.JSON_NAME}",
        },
        "boundaries": {
            "no_file_contents_in_index": True,
            "no_raw_host_paths_in_index": True,
            "no_mission_control_runtime_behavior": True,
            "no_local_llm_runtime_behavior": True,
            "no_real_vm_or_container": True,
            "no_sandbox_orchestration": True,
            "no_shell_execution": True,
            "no_host_promotion": True,
            "local_preview_only": True,
        },
    }


def _render(payload: dict[str, Any]) -> str:
    return f"""# Hello World Sandbox Observed Demo

Status: observed local fixture execution.

This packet is the concrete local-preview Hello World workbench proof. It wraps the observed
`sandbox.artifact.write_text` approval/execution packet with operator intent and local-model plan
metadata. It performs a real governed Ithildin tool call in a temporary fixture workspace, but it
does not start Mission Control, call a local LLM, start a VM/container, orchestrate a sandbox,
execute shell, or promote an artifact onto the trusted host.

## Observed Flow

1. Operator intent is represented as metadata: create the fixed Hello World sandbox artifact.
2. A local-model plan is represented as metadata only.
3. `sandbox.artifact.write_text` requests a bounded artifact write through Ithildin.
4. Policy returns `approval_required`.
5. A local admin fixture approves the one-time request.
6. The governed tool call executes and creates the sandbox-labeled artifact.
7. Artifact hash, approval consumption, and audit-chain verification are recorded.

## Evidence

- Demo status: `{payload["status"]}`
- Tool: `{payload["tool_name"]}`
- Tool count: `{payload["tool_count"]}`
- Governed tool calls performed: `{str(payload["governed_tool_calls_performed"]).lower()}`
- Mission Control runtime behavior: `{str(payload["mission_control_runtime_behavior"]).lower()}`
- Local LLM runtime behavior: `{str(payload["local_llm_runtime_behavior"]).lower()}`
- Real VM or container started: `{str(payload["real_vm_or_container_started"]).lower()}`
- Sandbox orchestration performed: `{str(payload["sandbox_orchestration_performed"]).lower()}`
- Shell execution performed: `{str(payload["shell_execution_performed"]).lower()}`
- Host promotion performed: `{str(payload["host_promotion_performed"]).lower()}`
- Mission ID: `{payload["operator_intent"]["mission_id"]}`
- Plan status: `{payload["local_llm_plan"]["plan_status"]}`
- Initial request status: `{payload["governed_request"]["status"]}`
- Approval ID: `{payload["approval"]["approval_id"]}`
- Approval status after execution: `{payload["approval"]["status"]}`
- Approval content bound by hash: `{str(payload["approval"]["content_bound_by_hash"]).lower()}`
- Raw content stored in approval scope:
  `{str(payload["approval"]["raw_content_stored_in_scope"]).lower()}`
- Execution status: `{payload["execution"]["status"]}`
- Artifact label: `{payload["artifact"]["artifact_label"]}`
- Artifact content SHA-256: `{payload["artifact"]["content_sha256"]}`
- Artifact byte SHA-256: `{payload["artifact"]["byte_sha256"]}`
- Artifact bytes: `{payload["artifact"]["bytes"]}`
- Artifact hash matches execution: `{str(payload["artifact"]["hash_matches_execution"]).lower()}`
- Audit verification valid: `{str(payload["audit"]["valid"]).lower()}`
- Audit event count: `{payload["audit"]["event_count"]}`
- Audit head hash: `{payload["audit"]["head_hash"]}`

## Reading Order

1. `{JSON_NAME}` for machine-readable Hello World demo evidence.
2. `{OBSERVED_DIR_NAME}/{sandbox_artifact_observed_demo.TRANSCRIPT_NAME}` for the raw governed
   tool-call transcript.
3. `{OBSERVED_DIR_NAME}/{sandbox_artifact_observed_demo.JSON_NAME}` for approval/execution/audit
   fields.
4. `{HASHES_NAME}` for artifact digests.

## Boundary

This packet proves only a mediated local-preview fixture action through Ithildin. Mission Control
and local LLM behavior are represented as metadata only. VM/container lifecycle, sandbox
orchestration, host promotion, production identity, SIEM custody, compliance automation, and
activity outside Ithildin-mediated tool calls remain out of scope.
"""


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASHES_NAME:
            continue
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": "1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
