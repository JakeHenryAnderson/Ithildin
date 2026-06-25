"""Generate a Mission Control handoff packet for the observed Hello World demo."""

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

from scripts import hello_world_sandbox_observed_demo

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/hello-world-mission-control-handoff")
INDEX_NAME = "HELLO_WORLD_MISSION_CONTROL_HANDOFF.md"
JSON_NAME = "mission-control-handoff.json"
HASHES_NAME = "artifact-hashes.json"
OBSERVED_DIR_NAME = "observed-hello-world"


class HelloWorldMissionControlHandoffError(RuntimeError):
    """Raised when the Mission Control handoff packet cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        output_dir = build_handoff(args.output_dir)
    except HelloWorldMissionControlHandoffError as exc:
        print(f"Hello World Mission Control handoff failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built Hello World Mission Control handoff at {output_dir}")
    return 0


def build_handoff(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    observed_dir = output_dir / OBSERVED_DIR_NAME
    hello_world_sandbox_observed_demo.build_demo(observed_dir)
    observed = json.loads(
        observed_dir.joinpath(hello_world_sandbox_observed_demo.JSON_NAME).read_text(
            encoding="utf-8"
        )
    )
    handoff = _handoff(observed)
    _write_json(output_dir / JSON_NAME, handoff)
    output_dir.joinpath(INDEX_NAME).write_text(_render(handoff), encoding="utf-8")
    _write_json(output_dir / HASHES_NAME, _artifact_hashes(output_dir))
    return output_dir


def _handoff(observed: dict[str, Any]) -> dict[str, Any]:
    artifact = observed["artifact"]
    approval = observed["approval"]
    audit = observed["audit"]
    return {
        "schema_version": "1",
        "handoff_type": "mission_control.hello_world_observed_demo",
        "status": "metadata_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "mission_control_runtime_behavior": False,
        "mission_control_authority": "display_and_operator_review_only",
        "ithildin_remains_policy_authority": True,
        "local_llm_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "sandbox_orchestration_performed": False,
        "shell_execution_performed": False,
        "host_promotion_performed": False,
        "tool_count": observed["tool_count"],
        "mission": {
            "mission_id": observed["operator_intent"]["mission_id"],
            "operator_intent_label": observed["operator_intent"]["intent_label"],
            "status_label": "observed_ithildin_mediated_artifact_created",
            "review_status": "pending_operator_review",
            "promotion_status": "not_promoted",
        },
        "model_plan": {
            "model_client_label": observed["local_llm_plan"]["model_client_label"],
            "plan_status": observed["local_llm_plan"]["plan_status"],
            "proposed_action": observed["local_llm_plan"]["proposed_action"],
            "artifact_label": observed["local_llm_plan"]["artifact_label"],
            "content_sha256": observed["local_llm_plan"]["content_sha256"],
            "raw_prompt_recorded": False,
            "chain_of_thought_recorded": False,
        },
        "ithildin_evidence": {
            "tool_name": observed["tool_name"],
            "request_status": observed["governed_request"]["status"],
            "request_id": observed["governed_request"]["request_id"],
            "approval_id": approval["approval_id"],
            "approval_status": approval["status"],
            "approval_content_bound_by_hash": approval["content_bound_by_hash"],
            "approval_raw_content_stored": approval["raw_content_stored_in_scope"],
            "execution_status": observed["execution"]["status"],
            "executor_result_status": observed["execution"]["result_status"],
            "artifact_label": artifact["artifact_label"],
            "artifact_content_sha256": artifact["content_sha256"],
            "artifact_byte_sha256": artifact["byte_sha256"],
            "artifact_bytes": artifact["bytes"],
            "artifact_hash_matches_execution": artifact["hash_matches_execution"],
            "audit_valid": audit["valid"],
            "audit_event_count": audit["event_count"],
            "audit_head_hash": audit["head_hash"],
        },
        "attachments": [
            {
                "label": "observed_hello_world_index",
                "path": f"{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.INDEX_NAME}",
                "purpose": "operator-facing observed Hello World evidence",
            },
            {
                "label": "observed_hello_world_json",
                "path": f"{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.JSON_NAME}",
                "purpose": "machine-readable observed Hello World evidence",
            },
            {
                "label": "observed_governed_tool_transcript",
                "path": (
                    f"{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME}/"
                    "SANDBOX_ARTIFACT_OBSERVED_DEMO.md"
                ),
                "purpose": "underlying governed tool transcript",
            },
        ],
        "display_contract": {
            "show_fields": [
                "mission_id",
                "operator_intent_label",
                "model_client_label",
                "tool_name",
                "request_status",
                "approval_status",
                "execution_status",
                "artifact_label",
                "artifact_content_sha256",
                "audit_valid",
                "audit_head_hash",
                "promotion_status",
            ],
            "warning_chips": [
                "local_preview_only",
                "mission_control_metadata_only",
                "local_llm_not_invoked",
                "vm_not_started",
                "host_promotion_not_performed",
            ],
            "hide_fields": [
                "file_contents",
                "raw_host_paths",
                "raw_model_prompt",
                "chain_of_thought",
                "private_keys",
                "tokens",
                "environment_values",
            ],
        },
        "boundaries": {
            "mission_control_must_not_claim_execution": True,
            "mission_control_must_not_claim_policy_authority": True,
            "mission_control_must_not_claim_vm_or_sandbox_control": True,
            "mission_control_must_not_claim_host_promotion": True,
            "no_file_contents": True,
            "no_raw_host_paths": True,
            "local_preview_only": True,
        },
    }


def _render(handoff: dict[str, Any]) -> str:
    evidence = handoff["ithildin_evidence"]
    mission = handoff["mission"]
    model = handoff["model_plan"]
    return f"""# Hello World Mission Control Handoff

Status: metadata-only handoff for Mission Control display.

This packet gives Mission Control a small, safe import/display shape for the observed Hello World
Ithildin flow. Mission Control is not the executor, policy authority, approval authority, sandbox
controller, local model runtime, or host-promotion mechanism in this packet.

## Mission Summary

- Mission ID: `{mission["mission_id"]}`
- Operator intent label: `{mission["operator_intent_label"]}`
- Mission status label: `{mission["status_label"]}`
- Review status: `{mission["review_status"]}`
- Promotion status: `{mission["promotion_status"]}`
- Model/client label: `{model["model_client_label"]}`
- Plan status: `{model["plan_status"]}`
- Proposed action: `{model["proposed_action"]}`

## Ithildin Evidence

- Tool: `{evidence["tool_name"]}`
- Request status: `{evidence["request_status"]}`
- Approval ID: `{evidence["approval_id"]}`
- Approval status: `{evidence["approval_status"]}`
- Approval content bound by hash: `{str(evidence["approval_content_bound_by_hash"]).lower()}`
- Approval raw content stored: `{str(evidence["approval_raw_content_stored"]).lower()}`
- Execution status: `{evidence["execution_status"]}`
- Artifact label: `{evidence["artifact_label"]}`
- Artifact content SHA-256: `{evidence["artifact_content_sha256"]}`
- Artifact byte SHA-256: `{evidence["artifact_byte_sha256"]}`
- Artifact bytes: `{evidence["artifact_bytes"]}`
- Artifact hash matches execution: `{str(evidence["artifact_hash_matches_execution"]).lower()}`
- Audit valid: `{str(evidence["audit_valid"]).lower()}`
- Audit event count: `{evidence["audit_event_count"]}`
- Audit head hash: `{evidence["audit_head_hash"]}`

## Mission Control Display Contract

Mission Control may display mission labels, status chips, attachment links, artifact hashes,
approval status, execution status, and audit status. It must keep these warnings visible:

- local-preview only;
- Mission Control metadata only;
- local LLM not invoked;
- VM/container not started;
- host promotion not performed.

Mission Control must not display or infer file contents, raw host paths, raw prompts,
chain-of-thought, private keys, tokens, environment values, or production/compliance conclusions.

## Reading Order

1. `{JSON_NAME}` for the importable handoff payload.
2. `{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.INDEX_NAME}` for the observed Hello
   World evidence.
3. `{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.JSON_NAME}` for machine-readable
   observed evidence.
4. `{OBSERVED_DIR_NAME}/{hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME}/`
   `SANDBOX_ARTIFACT_OBSERVED_DEMO.md` for the governed tool transcript.
5. `{HASHES_NAME}` for packet digests.

## Boundary

- Mission Control runtime behavior: `false`
- Local LLM runtime behavior: `false`
- Real VM or container started: `false`
- Sandbox orchestration performed: `false`
- Shell execution performed: `false`
- Host promotion performed: `false`

This handoff supports local operator review only. It is not OS isolation, SIEM custody, compliance
automation, production identity, external notarization, or proof of activity outside
Ithildin-mediated actions.
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
