"""Validate the ERG-004 runtime gate-readiness decision-record skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_runtime_gate_readiness_review_bundle

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"
DOC_NAME = "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"

REQUIRED_PHRASES = [
    "Status: design-only decision-record skeleton for the `ERG-004` runtime gate-readiness review.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `ready_for_runtime_implementation_gate_review`.",
    "Current selected capability: `not selected`.",
    "does not approve runtime implementation",
    "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
    "make sandbox-vm-live-poc-runtime-implementation-gate-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check",
    "EXT-LIVE-GATE-###",
    "approved_for_descriptor_only_runtime_implementation_planning",
    (
        "ERG-004: ready_for_runtime_implementation_gate_review -> "
        "ready_for_descriptor_only_runtime_implementation_planning"
    ),
    "Runtime behavior remains blocked.",
    "Runtime surfaces touched: none.",
    "Tool count impact: none; remains `24`.",
    "Required packet evidence:",
    "Required reviewed commit:",
    "Required reviewed packet hash:",
    "Required future implementation plan: still required before any runtime implementation.",
    (
        "Required source review: still required after any future descriptor-only "
        "implementation exists."
    ),
    "Escalate to High review first",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check",
    "make release-check",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "host writes",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
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
    "ERG-004 is closed",
    "public security product approved",
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
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    active_route = _read(repo_root / "docs/codex/enterprise-active-route-clarity.md")
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    execution_board = _read(repo_root / "docs/codex/technical-mvp-execution-board.md")
    gate_doc = _read(repo_root / "docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md")
    bundle_doc = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    bundle_report = sandbox_vm_live_poc_runtime_gate_readiness_review_bundle.build_check_report(
        repo_root
    )

    if not doc_path.exists():
        failures.append("runtime gate-readiness decision-record skeleton doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    "runtime gate-readiness decision skeleton is missing phrase: "
                    + phrase
                )
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(
                    "runtime gate-readiness decision skeleton is missing blocked boundary: "
                    + phrase
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "runtime gate-readiness decision skeleton contains forbidden phrase: "
                    + phrase
                )

    if bundle_report["valid"] is not True:
        failures.append("runtime gate-readiness review bundle check is not valid")
    if bundle_report["runtime_implementation_allowed"] is not False:
        failures.append("runtime gate-readiness bundle unexpectedly allows implementation")
    if bundle_report["closes_erg_004"] is not False:
        failures.append("runtime gate-readiness bundle unexpectedly closes ERG-004")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime gate-readiness decision skeleton is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("runtime gate-readiness decision skeleton is missing from docs site")
    if "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check:" not in makefile:
        failures.append("Make target is missing: runtime gate-readiness decision skeleton check")
    if "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check" not in (
        release_check_body
    ):
        failures.append("runtime gate-readiness decision skeleton check missing from release-check")
    if "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check" not in (
        release_guardrails
    ):
        failures.append(
            "release guardrails do not require runtime gate-readiness decision skeleton"
        )
    if "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check" not in (
        readme
    ):
        failures.append("README is missing runtime gate-readiness decision skeleton command")
    if "Sandbox/VM Live POC Runtime Gate Readiness Decision Record Skeleton" not in review_index:
        failures.append("review docs index is missing runtime gate-readiness decision skeleton")

    for label, source in [
        ("active route clarity", active_route),
        ("enterprise current checkpoint", current_checkpoint),
        ("technical MVP execution board", execution_board),
        ("runtime implementation gate", gate_doc),
        ("runtime gate-readiness review bundle", bundle_doc),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing runtime gate-readiness decision skeleton pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_skeleton_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_implementation_gate_review",
        "allowed_future_status": "ready_for_descriptor_only_runtime_implementation_planning",
        "finding_namespace": "EXT-LIVE-GATE-###",
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "descriptor_only_planning_after_favorable_review_allowed": True,
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
        "public_security_product_positioning_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime gate-readiness decision skeleton check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_skeleton_doc: {report['decision_record_skeleton_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        "descriptor_only_planning_after_favorable_review_allowed: "
        f"{str(report['descriptor_only_planning_after_favorable_review_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"vm_container_lifecycle_allowed: {str(report['vm_container_lifecycle_allowed']).lower()}",
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
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
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


if __name__ == "__main__":
    raise SystemExit(main())
