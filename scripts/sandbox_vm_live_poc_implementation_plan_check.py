"""Validate the ERG-004 live sandbox/VM POC implementation-planning packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_decision_record_check

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-implementation-plan.md"
DOC_NAME = "sandbox-vm-live-poc-implementation-plan.md"
TARGET = "sandbox-vm-live-poc-implementation-plan-check"

REQUIRED_PHRASES = [
    "Status: implementation-planning-only packet for `ERG-004`.",
    "Current `ERG-004` status: `ready_for_implementation_planning_only`.",
    "Current governed tool count: `24`.",
    "make sandbox-vm-live-poc-implementation-plan-check",
    (
        "This packet defines the planning boundary for a future operator-managed live sandbox/VM "
        "proof of"
    ),
    "It does not approve runtime implementation, live VM/container inspection, VM/container",
    "lifecycle management, sandbox orchestration, Mission Control runtime behavior, local model",
    "invocation, trusted-host promotion, network expansion, API/MCP profile loading, SIEM adapter",
    "operator-managed VM",
    "Container profiles remain deferred",
    "Future Source Review Requirement",
    "Stop Conditions",
    "Before any runtime implementation, a future source-review packet must include:",
]

REQUIRED_CATEGORIES = [
    "operator intent evidence",
    "sandbox/VM profile evidence",
    "cleanup transcript digest evidence",
    "failure transcript digest evidence",
    "local model/client label evidence",
    "Mission Control display-only packet evidence",
    "source-review handoff evidence",
    "negative transcript evidence",
    "Cross-source correlation must use safe identifiers and hashes only.",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "sandbox orchestration is approved",
    "trusted-host promotion is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    decision_record = sandbox_vm_live_poc_decision_record_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("sandbox/VM live POC implementation plan is missing")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"implementation plan is missing phrase: {phrase}")
    for category in REQUIRED_CATEGORIES:
        if category not in text:
            failures.append(f"implementation plan is missing evidence category: {category}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"implementation plan contains forbidden phrase: {phrase}")

    if not decision_record["valid"]:
        failures.append("decision record check is not valid")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("implementation plan is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("implementation plan is missing from docs-site inputs")
    if "Sandbox/VM Live POC Implementation Plan" not in review_index:
        failures.append("review-docs index is missing live POC implementation plan")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("implementation plan check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require implementation plan check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing live POC implementation plan command")
    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("enterprise sandbox readiness", readiness),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "implementation_plan_doc": DOC_REL,
        "decision_record_valid": bool(decision_record["valid"]),
        "tool_count": 24,
        "erg_004_status": "ready_for_implementation_planning_only",
        "vm_first": True,
        "container_profiles_deferred": True,
        "implementation_planning_allowed": True,
        "runtime_changes_allowed": False,
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
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC implementation plan check",
        f"valid: {str(report['valid']).lower()}",
        f"implementation_plan_doc: {report['implementation_plan_doc']}",
        f"decision_record_valid: {str(report['decision_record_valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"vm_first: {str(report['vm_first']).lower()}",
        f"container_profiles_deferred: {str(report['container_profiles_deferred']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "external_review_required_before_runtime: "
        f"{str(report['external_review_required_before_runtime']).lower()}",
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
