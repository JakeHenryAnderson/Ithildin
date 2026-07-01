"""Validate the blocked live sandbox/VM POC preconditions map."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-preconditions-map.md"
DOC_NAME = "sandbox-vm-live-poc-preconditions-map.md"

REQUIRED_PHRASES = [
    "Status: preconditions map for blocked `ERG-004`.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Current `ERG-004` status: `blocked`.",
    "favorable `ERG-003` static preflight disposition evidence",
    "This map is not that decision record.",
    "Required Preconditions",
    "Current Artifact Map",
    "Command Sequence",
    "Decision Outcomes",
    "What This Map Does Not Prove",
    "make sandbox-vm-live-poc-preconditions-map-check",
]

REQUIRED_COMMANDS = [
    "make sandbox-vm-static-preflight-reviewer-reproduction-map-check",
    "make sandbox-vm-static-preflight-disposition-packet-check",
    "make sandbox-vm-static-preflight-external-response-intake-check",
    "make sandbox-vm-live-poc-decision-intake-check",
    "make sandbox-vm-live-poc-evidence-contract-check",
    "make sandbox-vm-live-poc-decision-packet",
    "make sandbox-vm-live-poc-decision-packet-check",
    "make sandbox-vm-live-poc-preconditions-map-check",
    "make external-findings-intake-dry-run",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

REQUIRED_ARTIFACTS = [
    "docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-plan.md",
    "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-packet.md",
    "docs/codex/sandbox-vm-live-poc-decision-intake.md",
    "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
    "docs/codex/sandbox-vm-live-poc-decision-packet.md",
    "docs/codex/enterprise-sandbox-control-plane-readiness.md",
    "docs/codex/post-rc-decision-register.md",
    "var/review-packets/v3/sandbox-vm-static-preflight-source-review/",
    "var/review-packets/v3/sandbox-vm-static-preflight-disposition/",
    "var/review-packets/v3/sandbox-vm-live-poc-decision/",
    "var/review-packets/v3/sandbox-vm-poc-review/",
]

REQUIRED_BOUNDARIES = [
    "`ERG-003` is recorded as `closed_local_preview_static_preflight`",
    "`ERG-004` remains `blocked`",
    "live VM/container inspection remains blocked",
    "sandbox orchestration remains blocked",
    "local model invocation remains blocked",
    "Mission Control runtime behavior remains blocked",
    "trusted-host promotion remains blocked",
    "network expansion remains blocked",
    "tool count remains `24`",
]

FORBIDDEN_PHRASES = [
    "live VM/container inspection allowed",
    "sandbox orchestration allowed",
    "local model invocation allowed",
    "Mission Control runtime behavior allowed",
    "trusted-host promotion allowed",
    "network expansion allowed",
    "ERG-004 is closed",
    "implementation is approved",
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
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM live POC preconditions map is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"preconditions map is missing phrase: {phrase}")
    for command in REQUIRED_COMMANDS:
        if command not in doc:
            failures.append(f"preconditions map is missing command: {command}")
    for artifact in REQUIRED_ARTIFACTS:
        if artifact not in doc:
            failures.append(f"preconditions map is missing artifact: {artifact}")
    for phrase in REQUIRED_BOUNDARIES:
        if phrase not in doc:
            failures.append(f"preconditions map is missing boundary phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"preconditions map contains forbidden phrase: {phrase}")

    target = "sandbox-vm-live-poc-preconditions-map-check"
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("preconditions map is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("preconditions map is missing from docs-site inputs")
    if "Sandbox/VM Live POC Preconditions Map" not in review_index:
        failures.append("review-docs index is missing preconditions map")
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("preconditions map check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require preconditions map check")
    if f"make {target}" not in readme:
        failures.append("README is missing preconditions map command")
    if DOC_NAME not in runway:
        failures.append("enterprise runway is missing preconditions map pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing preconditions map pointer")
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing preconditions map pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "preconditions_map_doc": DOC_REL,
        "tool_count": 24,
        "erg_003_status": "closed_local_preview_static_preflight",
        "erg_003_disposition_recorded": True,
        "erg_004_status": "blocked",
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
        "Ithildin sandbox/VM live POC preconditions map check",
        f"valid: {str(report['valid']).lower()}",
        f"preconditions_map_doc: {report['preconditions_map_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        "erg_003_disposition_recorded: "
        f"{str(report['erg_003_disposition_recorded']).lower()}",
        f"erg_004_status: {report['erg_004_status']}",
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
