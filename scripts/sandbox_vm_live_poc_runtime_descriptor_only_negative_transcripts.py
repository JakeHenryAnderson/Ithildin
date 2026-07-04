"""Generate ERG-004 descriptor-only negative transcripts from local schema fixtures."""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.sandbox_descriptors import SandboxDescriptorPayload

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-negative"
)
TRANSCRIPT_NAME = "SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_NEGATIVE_TRANSCRIPTS.md"

Mutator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class NegativeCase:
    name: str
    expected_denial: str
    safe_reason: str
    mutator: Mutator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    transcript = build_transcripts(args.output_dir)
    print(f"Built ERG-004 descriptor-only negative transcripts at {transcript}")
    return 0


def build_transcripts(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [_run_case(case) for case in _cases()]
    transcript = output_dir / TRANSCRIPT_NAME
    transcript.write_text(_render(results), encoding="utf-8")
    return transcript


def _run_case(case: NegativeCase) -> dict[str, Any]:
    payload = _base_payload()
    case.mutator(payload)
    accepted = False
    observed_status = "rejected"
    try:
        SandboxDescriptorPayload.model_validate(payload)
        accepted = True
        observed_status = "accepted"
    except ValidationError:
        pass
    return {
        "name": case.name,
        "expected_denial": case.expected_denial,
        "observed_status": observed_status,
        "observed_valid": accepted is False,
        "safe_reason": case.safe_reason,
    }


def _cases() -> list[NegativeCase]:
    return [
        NegativeCase(
            "Unknown Field",
            "reject descriptor fields outside the closed schema",
            "unknown_field",
            lambda payload: payload.__setitem__("secret", "redacted-fixture-value"),
        ),
        NegativeCase(
            "Lifecycle Control Claim",
            "reject descriptor claims that Ithildin controlled VM/container lifecycle",
            "forbidden_lifecycle_authority",
            _set("ithildin_lifecycle_control_performed", True),
        ),
        NegativeCase(
            "Live Inspection Claim",
            "reject descriptor claims that Ithildin inspected a live VM/container",
            "forbidden_live_inspection_authority",
            _set("ithildin_live_inspection_performed", True),
        ),
        NegativeCase(
            "Mission Control Authority Claim",
            "reject descriptor claims that Mission Control runtime authority was used",
            "forbidden_mission_control_runtime_authority",
            _set("mission_control_runtime_authority_used", True),
        ),
        NegativeCase(
            "Trusted Host Promotion Claim",
            "reject descriptor claims that trusted-host promotion occurred",
            "forbidden_trusted_host_promotion",
            _set("trusted_host_promotion_performed", True),
        ),
        NegativeCase(
            "Raw Mount Path",
            "reject path-shaped mount labels",
            "raw_path_label",
            _set("mount_root_label", "/Users/demo/workspace"),
        ),
        NegativeCase(
            "Parent Segment Label",
            "reject labels containing parent-directory traversal markers",
            "path_traversal_label",
            _set("sandbox_id", "workspace..escape"),
        ),
        NegativeCase(
            "Control Character Label",
            "reject labels containing control characters",
            "control_character_label",
            _set("model_client_label", "local\nmodel"),
        ),
        NegativeCase(
            "Malformed Profile Hash",
            "reject non-SHA-256 VM profile hashes",
            "malformed_profile_hash",
            _set("vm_profile_hash", "not-a-sha256-digest"),
        ),
        NegativeCase(
            "Malformed Packet Hash",
            "reject non-SHA-256 packet hashes",
            "malformed_packet_hash",
            _set("packet_hash", "sha256:abc"),
        ),
    ]


def _base_payload() -> dict[str, Any]:
    return {
        "workspace_id": "default",
        "principal_id": "agent.local-dev",
        "run_id": "run_11111111111111111111111111111111",
        "sandbox_id": "sandbox-local-preview",
        "sandbox_profile_id": "profile-local-preview",
        "vm_profile_hash": "sha256:" + ("1" * 64),
        "isolation_label": "operator-attested-vm",
        "network_posture_label": "loopback-only",
        "mount_root_label": "sandbox-workspace",
        "model_client_label": "local-model-client",
        "descriptor_source": "operator_supplied",
        "vm_lifecycle_source": "operator_managed",
        "isolation_claim_source": "operator_attested",
        "network_posture_source": "operator_attested",
        "mount_posture_source": "operator_attested",
        "model_client_source": "operator_attested",
        "ithildin_live_inspection_performed": False,
        "ithildin_lifecycle_control_performed": False,
        "mission_control_runtime_authority_used": False,
        "trusted_host_promotion_performed": False,
        "approval_id": "ap_11111111111111111111111111111111",
        "audit_event_id": "evt_11111111111111111111111111111111",
        "signed_export_id": "sig_11111111111111111111111111111111",
        "failure_transcript_hash": "sha256:" + ("2" * 64),
        "packet_hash": "sha256:" + ("3" * 64),
        "operator_notes_label": "operator-reviewed",
    }


def _set(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload[key] = copy.deepcopy(value)

    return mutate


def _render(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Sandbox/VM Live POC Descriptor-Only Negative Transcripts",
        "",
        "Status: observed local schema-fixture denial transcripts for the implemented ERG-004",
        "descriptor-only runtime slice.",
        "",
        "These transcripts are generated from in-memory descriptor payload mutations. They do",
        "not call governed tools, start or inspect VMs/containers, invoke local models, call",
        "Mission Control, write host artifacts, perform network access, or record external",
        "review.",
        "",
        "| Scenario | Expected denial | Observed valid | Observed status | Safe reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        row_template = (
            "| {name} | {expected_denial} | {observed_valid} | {observed_status} | "
            "{safe_reason} |"
        )
        lines.append(
            row_template.format(
                name=result["name"],
                expected_denial=result["expected_denial"],
                observed_valid=str(result["observed_valid"]).lower(),
                observed_status=result["observed_status"],
                safe_reason=result["safe_reason"],
            )
        )
    lines.extend(
        [
            "",
            "Output policy: scenario labels, expected denial classes, observed status, and safe",
            "reason labels only. No raw descriptor payloads, file contents, prompts, model",
            "responses, command lines, shell output, raw paths, environment values, registry",
            "URLs, dependency names, package scripts, secrets, or VM/container handles are",
            "included.",
            "",
            "This artifact does not close `ERG-004`; it only strengthens the local source-review",
            "handoff for the descriptor-only runtime slice.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
