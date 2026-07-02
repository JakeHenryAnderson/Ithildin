"""Validate the ERG-004 runtime descriptor/correlation contract pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
TARGET = "sandbox-vm-live-poc-runtime-descriptor-contract-check"
DECISION_REL = "docs/codex/sandbox-vm-live-poc-runtime-implementation-decision.md"
CONTRACT_REL = "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md"
NEGATIVE_REL = "docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md"
GATE_REL = "docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md"

REQUIRED_DOC_PHRASES = {
    DECISION_REL: [
        (
            "Status: planning-only implementation decision for the `ERG-004` "
            "descriptor/correlation slice."
        ),
        "Current `ERG-004` status: `runtime_descriptor_contract_planning`.",
        f"make {TARGET}",
        "Runtime implementation remains blocked.",
        "Allowed Planning Scope",
        "Not Approved",
        "Future Gate Requirements",
        "Stop Conditions",
    ],
    CONTRACT_REL: [
        (
            "Status: design-only descriptor contract for the future `ERG-004` "
            "runtime descriptor/correlation"
        ),
        "Ithildin does not yet accept, store, render",
        "descriptor_source: operator_supplied",
        "vm_lifecycle_source: operator_managed",
        "ithildin_live_inspection_performed: false",
        "ithildin_lifecycle_control_performed: false",
        "mission_control_runtime_authority_used: false",
        "trusted_host_promotion_performed: false",
        "Required Fields",
        "Safe Value Classes",
        "Correlation Requirements",
        "Forbidden Payload Content",
        "Explicit Non-Claims",
    ],
    NEGATIVE_REL: [
        (
            "Status: design-only negative fixture plan for the future `ERG-004` "
            "descriptor/correlation slice."
        ),
        "It does not add a runtime validator",
        "Descriptor Shape Failures",
        "Correlation Failures",
        "Forbidden Authority Attempts",
        "Leakage Failures",
        "Required Transcript Shape",
        "VM/container lifecycle management by Ithildin",
        "live VM/container inspection by Ithildin",
        "local model invocation by Ithildin",
        "Mission Control execution, approval, policy, or audit authority",
        "trusted-host promotion",
        "host writes or artifact promotion",
        "API/MCP profile loading",
        "new governed tool powers",
    ],
}

REQUIRED_FIELD_PHRASES = [
    "operator_intent_id",
    "principal_id",
    "workspace_id",
    "run_id",
    "sandbox_id",
    "sandbox_profile_id",
    "vm_profile_label",
    "vm_profile_hash",
    "mount_root_label",
    "workspace_mount_label",
    "network_posture_label",
    "model_client_label",
    "model_request_hash",
    "tool_call_correlation_id",
    "approval_correlation_id",
    "audit_head_hash",
    "signed_export_hash",
    "cleanup_plan_hash",
    "cleanup_transcript_hash",
    "failure_transcript_hash",
    "mission_control_display_packet_hash",
    "promotion_status: not_promoted",
]

FORBIDDEN_APPROVAL_PHRASES = [
    "runtime implementation is approved",
    "Ithildin starts the VM",
    "Ithildin starts containers",
    "live VM inspection is approved",
    "VM lifecycle control is approved",
    "Mission Control may execute",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "API/MCP profile loading is approved",
    "new governed tool power is approved",
    "public security product is approved",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    docs_text: dict[str, str] = {}
    for rel_path, phrases in REQUIRED_DOC_PHRASES.items():
        path = repo_root / rel_path
        if not path.exists():
            failures.append(f"missing ERG-004 runtime descriptor doc: {rel_path}")
            docs_text[rel_path] = ""
            continue
        text = path.read_text(encoding="utf-8")
        docs_text[rel_path] = text
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel_path} is missing phrase: {phrase}")
        for phrase in FORBIDDEN_APPROVAL_PHRASES:
            if phrase in text:
                failures.append(f"{rel_path} contains forbidden approval phrase: {phrase}")

    contract_text = docs_text.get(CONTRACT_REL, "")
    for phrase in REQUIRED_FIELD_PHRASES:
        if phrase not in contract_text:
            failures.append(f"descriptor contract is missing field phrase: {phrase}")

    gate_text = (repo_root / GATE_REL).read_text(encoding="utf-8")
    for rel_path in [DECISION_REL, CONTRACT_REL, NEGATIVE_REL]:
        if rel_path not in review_docs.REVIEW_DOCS:
            failures.append(f"{rel_path} is missing from review docs")
        if rel_path not in docs_site:
            failures.append(f"{rel_path} is missing from docs-site inputs")
        if rel_path.rsplit("/", 1)[1] not in review_index:
            failures.append(f"{rel_path} is missing from review-docs index")

    for phrase in [DECISION_REL, CONTRACT_REL, NEGATIVE_REL]:
        if phrase not in gate_text:
            failures.append(f"runtime implementation gate does not reference {phrase}")

    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append(f"{TARGET} is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append(f"{TARGET} is missing from release guardrails")
    if f"make {TARGET}" not in readme:
        failures.append(f"README is missing make {TARGET}")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "erg_004_status": "runtime_descriptor_contract_planning",
        "runtime_descriptor_contract_docs": [DECISION_REL, CONTRACT_REL, NEGATIVE_REL],
        "runtime_implementation_allowed": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime descriptor contract check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        "runtime_descriptor_contract_docs:",
        *[f"- {path}" for path in report["runtime_descriptor_contract_docs"]],
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        (
            "mission_control_runtime_allowed: "
            f"{str(report['mission_control_runtime_allowed']).lower()}"
        ),
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
