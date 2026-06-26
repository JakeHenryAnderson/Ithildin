"""Summarize whether the blocked sandbox/VM live POC lane is ready to await review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
    sandbox_vm_live_poc_decision_closure_check,
    sandbox_vm_live_poc_decision_intake_check,
    sandbox_vm_live_poc_decision_packet,
    sandbox_vm_live_poc_preconditions_map_check,
    sandbox_vm_live_poc_response_kit,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md"
DOC_NAME = "sandbox-vm-live-poc-preconditions-ready-check.md"
TARGET = "sandbox-vm-live-poc-preconditions-ready-check"

REQUIRED_PHRASES = [
    "Status: deterministic readiness check for blocked `ERG-004`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "ready_for_implementation_planning: false",
    "blocking_prerequisite: favorable `ERG-003` static preflight disposition",
    "ERG-004 wiring is ready to await external/source review feedback",
    "This check does not approve live VM/container inspection",
    "make sandbox-vm-live-poc-preconditions-ready-check",
]

REQUIRED_LINKS = [
    "sandbox-vm-live-poc-preconditions-map.md",
    "sandbox-vm-live-poc-decision-intake.md",
    "sandbox-vm-live-poc-decision-packet.md",
    "sandbox-vm-live-poc-decision-closure-gate.md",
    "sandbox-vm-live-poc-response-kit.md",
]

FORBIDDEN_PHRASES = [
    "ready_for_implementation_planning: true",
    "implementation planning is approved",
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "ERG-004 is closed",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    component_reports = {
        "preconditions_map": sandbox_vm_live_poc_preconditions_map_check.build_report(
            repo_root
        ),
        "decision_intake": sandbox_vm_live_poc_decision_intake_check.build_report(repo_root),
        "decision_packet": sandbox_vm_live_poc_decision_packet.build_check_report(repo_root),
        "response_kit": sandbox_vm_live_poc_response_kit.build_check_report(repo_root),
        "closure_gate": sandbox_vm_live_poc_decision_closure_check.build_report(repo_root),
    }
    for name, report in component_reports.items():
        if not report.get("valid"):
            failures.append(f"{name} is not valid")

    closure = component_reports["closure_gate"]
    if closure.get("normalized_response_present") is not False:
        failures.append("normalized live POC response unexpectedly exists")
    if closure.get("closure_ready") is not False:
        failures.append("live POC closure is unexpectedly ready")
    if closure.get("implementation_planning_allowed") is not False:
        failures.append("implementation planning is unexpectedly allowed")

    if not doc_path.exists():
        failures.append("live POC preconditions ready-check doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"ready-check doc is missing phrase: {phrase}")
    for link in REQUIRED_LINKS:
        if link not in doc:
            failures.append(f"ready-check doc is missing link: {link}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"ready-check doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("ready-check doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("ready-check doc is missing from docs-site inputs")
    if "Sandbox/VM Live POC Preconditions Ready Check" not in review_index:
        failures.append("review-docs index is missing ready-check doc")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("ready-check target is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require ready-check target")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing ready-check command")
    for source_name, text in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("enterprise sandbox readiness", readiness),
    ]:
        if DOC_NAME not in text:
            failures.append(f"{source_name} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ready_check_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "erg_004_status": "blocked",
        "preconditions_map_valid": component_reports["preconditions_map"].get("valid")
        is True,
        "decision_intake_valid": component_reports["decision_intake"].get("valid") is True,
        "decision_packet_valid": component_reports["decision_packet"].get("valid") is True,
        "response_kit_valid": component_reports["response_kit"].get("valid") is True,
        "closure_gate_valid": component_reports["closure_gate"].get("valid") is True,
        "normalized_response_present": closure.get("normalized_response_present"),
        "closure_ready": closure.get("closure_ready"),
        "blocking_prerequisite": "favorable ERG-003 static preflight disposition",
        "ready_for_implementation_planning": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC preconditions ready check",
        f"valid: {str(report['valid']).lower()}",
        f"ready_check_doc: {report['ready_check_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"preconditions_map_valid: {str(report['preconditions_map_valid']).lower()}",
        f"decision_intake_valid: {str(report['decision_intake_valid']).lower()}",
        f"decision_packet_valid: {str(report['decision_packet_valid']).lower()}",
        f"response_kit_valid: {str(report['response_kit_valid']).lower()}",
        f"closure_gate_valid: {str(report['closure_gate_valid']).lower()}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"blocking_prerequisite: {report['blocking_prerequisite']}",
        "ready_for_implementation_planning: "
        f"{str(report['ready_for_implementation_planning']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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
