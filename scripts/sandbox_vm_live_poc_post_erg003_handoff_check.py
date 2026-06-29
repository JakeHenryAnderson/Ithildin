"""Validate the post-ERG-003 handoff for the blocked live sandbox/VM POC lane."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-post-erg003-handoff.md"
DOC_NAME = "sandbox-vm-live-poc-post-erg003-handoff.md"
TARGET = "sandbox-vm-live-poc-post-erg003-handoff-check"

REQUIRED_PHRASES = [
    "Status: post-`ERG-003` handoff map for still-blocked `ERG-004`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Current `ERG-004` status: `blocked`.",
    "Use this handoff only after all of these are true:",
    "make sandbox-vm-static-preflight-disposition-closure-check",
    "sandbox-vm-static-preflight-disposition-record-skeleton.md",
    "make sandbox-vm-live-poc-preconditions-ready-check",
    "make sandbox-vm-live-poc-decision-packet",
    "make sandbox-vm-live-poc-external-review-bundle",
    "make sandbox-vm-live-poc-response-kit",
    "ready_for_implementation_planning: false",
    "Only a later committed `PRD-SANDBOX-LIVE-POC-001` decision record",
    "Runtime implementation remains separate.",
    "make sandbox-vm-live-poc-post-erg003-handoff-check",
]

REQUIRED_BLOCKED = [
    "`ERG-004` remains `blocked`",
    "live VM/container inspection remains blocked",
    "local model invocation remains blocked",
    "Mission Control runtime behavior remains blocked",
    "sandbox orchestration remains blocked",
    "trusted-host promotion remains blocked",
    "network expansion remains blocked",
    "tool count remains `24`",
]

FORBIDDEN_PHRASES = [
    "ERG-004 is unblocked",
    "ERG-004 is closed",
    "ready_for_implementation_planning: true",
    "implementation planning is approved",
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "local model invocation is approved",
    "Mission Control runtime behavior is approved",
    "sandbox orchestration is approved",
    "trusted-host promotion is approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    ready_check = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not (repo_root / DOC_REL).exists():
        failures.append("post-ERG-003 handoff doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"post-ERG-003 handoff doc is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED:
        if phrase not in doc:
            failures.append(f"post-ERG-003 handoff doc is missing blocked phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"post-ERG-003 handoff doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("post-ERG-003 handoff doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("post-ERG-003 handoff doc is missing from docs-site inputs")
    if "Sandbox/VM Live POC Post-ERG-003 Handoff" not in review_index:
        failures.append("review-docs index is missing post-ERG-003 handoff")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("post-ERG-003 handoff check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require post-ERG-003 handoff check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing post-ERG-003 handoff command")
    for source_name, text in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("preconditions map", preconditions),
        ("preconditions ready check", ready_check),
    ]:
        if DOC_NAME not in text:
            failures.append(f"{source_name} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "post_erg003_handoff_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "erg_004_status": "blocked",
        "requires_favorable_erg003_disposition": True,
        "requires_later_decision_record": True,
        "ready_for_implementation_planning": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC post-ERG-003 handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"post_erg003_handoff_doc: {report['post_erg003_handoff_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_004_status: {report['erg_004_status']}",
        "requires_favorable_erg003_disposition: "
        f"{str(report['requires_favorable_erg003_disposition']).lower()}",
        f"requires_later_decision_record: {str(report['requires_later_decision_record']).lower()}",
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
