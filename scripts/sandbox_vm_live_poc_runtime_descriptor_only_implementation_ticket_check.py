"""Validate the ERG-004 runtime descriptor-only implementation ticket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    review_docs,
    sandbox_vm_live_poc_runtime_descriptor_contract_check,
    sandbox_vm_live_poc_runtime_descriptor_only_plan_check,
    sandbox_vm_live_poc_runtime_gate_readiness_internal_review_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Implementation Ticket"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check"

REQUIRED_PHRASES = [
    "Status: descriptor-only implementation-ticket packet for the future `ERG-004`",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `ready_for_descriptor_only_runtime_implementation_ticket`.",
    "Current selected capability: `not selected`.",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "approve_internal_runtime_gate_readiness_review",
    "ready_for_descriptor_only_runtime_implementation_planning",
    "Future Implementation Boundary",
    "Required Descriptor Facts",
    "Required Future Test Classes",
    "Required Future Acceptance Evidence",
    "Explicit Non-Approvals",
    "Stop Conditions",
    "validate an operator-supplied descriptor object",
    "reject unknown descriptor fields",
    (
        "store only safe labels, hashes, timestamps, enums, booleans, "
        "correlation IDs, and status codes"
    ),
    (
        "correlate descriptor fields with existing Agent Run, approval, audit, "
        "and signed-export evidence"
    ),
    "descriptor_source: operator_supplied",
    "vm_lifecycle_source: operator_managed",
    "ithildin_live_inspection_performed: false",
    "ithildin_lifecycle_control_performed: false",
    "mission_control_runtime_authority_used: false",
    "trusted_host_promotion_performed: false",
    "source-review handoff using a dedicated `EXT-LIVE-DESC-###` finding namespace",
]

REQUIRED_NEGATIVES = [
    "missing required descriptor fields",
    "unknown descriptor fields",
    "invalid `descriptor_source`",
    "invalid `vm_lifecycle_source`",
    "invalid `ithildin_live_inspection_performed`",
    "invalid `ithildin_lifecycle_control_performed`",
    "invalid `mission_control_runtime_authority_used`",
    "invalid `trusted_host_promotion_performed`",
    "stale or mismatched `vm_profile_hash`",
    "mismatched `sandbox_profile_id`",
    "unsafe `mount_root_label`",
    "unexpected `network_posture_label`",
    "missing `run_id`",
    "mismatched `workspace_id`, `principal_id`, or `run_id`",
    "missing approval correlation where required",
    "missing audit correlation where required",
    "missing signed-export correlation where required",
    "attempted VM/container lifecycle management by Ithildin",
    "attempted live VM/container inspection by Ithildin",
    "attempted local model invocation by Ithildin",
    "attempted Mission Control execution, approval, policy, or audit authority",
    "attempted trusted-host promotion",
    "attempted host write or artifact promotion",
    "arbitrary network expansion",
    "API/MCP profile loading",
    "shell/Docker/Kubernetes/browser execution",
    "cleanup failure",
    "missing or mismatched `failure_transcript_hash`",
    "packet hash mismatch",
    "raw secret, prompt, model response, file content, diff, transcript, dependency name, package",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation in this checkpoint",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "trusted-host promotion",
    "host writes or artifact promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "shell, Docker, Kubernetes, or browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "network expansion is approved",
    "API/MCP profile loading is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    gate_review = sandbox_vm_live_poc_runtime_gate_readiness_internal_review_check.build_report(
        repo_root
    )
    descriptor_contract = sandbox_vm_live_poc_runtime_descriptor_contract_check.build_report(
        repo_root
    )
    descriptor_plan = sandbox_vm_live_poc_runtime_descriptor_only_plan_check.build_report(
        repo_root
    )

    if not doc_path.exists():
        failures.append("runtime descriptor-only implementation ticket doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(
                f"runtime descriptor-only implementation ticket is missing phrase: {phrase}"
            )
    for phrase in REQUIRED_NEGATIVES:
        if phrase not in text:
            failures.append(
                f"runtime descriptor-only implementation ticket is missing negative case: {phrase}"
            )
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(
                f"runtime descriptor-only implementation ticket is missing non-approval: {phrase}"
            )
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                f"runtime descriptor-only implementation ticket contains forbidden phrase: {phrase}"
            )

    if not gate_review["valid"]:
        failures.append("runtime gate-readiness internal review check is not valid")
    if gate_review.get("disposition") != "approve_internal_runtime_gate_readiness_review":
        failures.append("runtime gate-readiness internal review is not approved")
    if not descriptor_contract["valid"]:
        failures.append("runtime descriptor contract check is not valid")
    if not descriptor_plan["valid"]:
        failures.append("runtime descriptor-only plan check is not valid")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime descriptor-only implementation ticket is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append(
            "runtime descriptor-only implementation ticket is missing from docs-site inputs"
        )
    if DOC_TITLE not in review_index:
        failures.append(
            "review-docs index is missing runtime descriptor-only implementation ticket"
        )
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append(
            "runtime descriptor-only implementation ticket check missing from release-check"
        )
    if TARGET not in release_guardrails:
        failures.append(
            "release guardrails do not require runtime descriptor-only implementation ticket check"
        )
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime descriptor-only implementation ticket command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime descriptor-only implementation ticket doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runtime_descriptor_only_implementation_ticket_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "ready_for_descriptor_only_runtime_implementation_ticket",
        "internal_gate_readiness_disposition": gate_review.get("disposition"),
        "descriptor_contract_valid": bool(descriptor_contract.get("valid")),
        "descriptor_only_plan_valid": bool(descriptor_plan.get("valid")),
        "descriptor_only_implementation_ticket_ready": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime descriptor-only implementation ticket check",
        f"valid: {str(report['valid']).lower()}",
        "runtime_descriptor_only_implementation_ticket_doc: "
        f"{report['runtime_descriptor_only_implementation_ticket_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"internal_gate_readiness_disposition: {report['internal_gate_readiness_disposition']}",
        f"descriptor_contract_valid: {str(report['descriptor_contract_valid']).lower()}",
        f"descriptor_only_plan_valid: {str(report['descriptor_only_plan_valid']).lower()}",
        "descriptor_only_implementation_ticket_ready: "
        f"{str(report['descriptor_only_implementation_ticket_ready']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


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


if __name__ == "__main__":
    raise SystemExit(main())
