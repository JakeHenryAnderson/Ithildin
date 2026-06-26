"""Validate the sandbox/VM live POC decision-record skeleton and release wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_decision_closure_check

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md"
DOC_NAME = "sandbox-vm-live-poc-decision-record-skeleton.md"

REQUIRED_PHRASES = [
    "Status: design-only decision-record skeleton for blocked `ERG-004` and",
    "`PRD-SANDBOX-LIVE-POC-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "does not approve runtime implementation",
    "favorable `ERG-003` static preflight disposition is recorded",
    "var/review-runs/sandbox-vm-live-poc/normalized-response.json",
    "make sandbox-vm-live-poc-decision-closure-check",
    "decision_outcome: approve_limited_operator_managed_poc_planning",
    "approved_for_implementation_planning_only",
    "ERG-004: blocked -> ready_for_implementation_planning_only",
    "Live sandbox/VM runtime behavior remains blocked.",
    "Runtime surfaces touched: none.",
    "Tool count impact: none; remains `24`.",
    "Required prior-lane evidence: favorable `ERG-003` static preflight disposition.",
    "make sandbox-vm-live-poc-decision-record-skeleton-check",
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
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter behavior",
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
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "SIEM adapter behavior is approved",
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    intake = _read(repo_root / "docs/codex/sandbox-vm-live-poc-decision-intake.md")
    preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    closure_gate = _read(repo_root / "docs/codex/sandbox-vm-live-poc-decision-closure-gate.md")
    decision_packet = _read(repo_root / "docs/codex/sandbox-vm-live-poc-decision-packet.md")
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    closure_report = sandbox_vm_live_poc_decision_closure_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("sandbox/VM live POC decision-record skeleton doc is missing")
        text = ""
    else:
        text = _read(doc_path)
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"decision-record skeleton is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"decision-record skeleton is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"decision-record skeleton contains forbidden phrase: {phrase}")

    if closure_report["erg_004_status"] != "blocked":
        failures.append("live POC decision closure gate does not keep ERG-004 blocked")
    if closure_report["implementation_planning_allowed"] is not False:
        failures.append(
            "live POC decision closure gate unexpectedly allows implementation planning"
        )
    if closure_report["closure_ready"] is not False:
        failures.append("live POC decision closure gate unexpectedly reports closure readiness")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM live POC decision-record skeleton is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("sandbox/VM live POC decision-record skeleton is missing from docs site")
    if "sandbox-vm-live-poc-decision-record-skeleton-check:" not in makefile:
        failures.append(
            "Make target is missing: sandbox-vm-live-poc-decision-record-skeleton-check"
        )
    if "sandbox-vm-live-poc-decision-record-skeleton-check" not in release_check_body:
        failures.append(
            "sandbox-vm-live-poc-decision-record-skeleton-check missing from release-check"
        )
    if "sandbox-vm-live-poc-decision-record-skeleton-check" not in release_guardrails:
        failures.append("release guardrails do not require live POC decision-record skeleton check")
    if "make sandbox-vm-live-poc-decision-record-skeleton-check" not in readme:
        failures.append("README is missing live POC decision-record skeleton command")
    if "Sandbox/VM Live POC Decision Record Skeleton" not in review_index:
        failures.append("review docs index is missing live POC decision-record skeleton")

    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("decision intake", intake),
        ("preconditions map", preconditions),
        ("closure gate", closure_gate),
        ("decision packet", decision_packet),
        ("enterprise sandbox control-plane readiness", readiness),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing live POC decision-record skeleton pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_skeleton_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "blocked",
        "allowed_future_status": "ready_for_implementation_planning_only",
        "runtime_changes_allowed": False,
        "implementation_planning_allowed_now": False,
        "implementation_planning_after_favorable_review_allowed": True,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC decision-record skeleton check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_skeleton_doc: {report['decision_record_skeleton_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "implementation_planning_allowed_now: "
        f"{str(report['implementation_planning_allowed_now']).lower()}",
        "implementation_planning_after_favorable_review_allowed: "
        f"{str(report['implementation_planning_after_favorable_review_allowed']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"vm_container_lifecycle_allowed: {str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
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


if __name__ == "__main__":
    raise SystemExit(main())
