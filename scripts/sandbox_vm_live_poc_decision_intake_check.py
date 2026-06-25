"""Validate the live sandbox/VM POC decision-intake packet."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-decision-intake.md"
DOC_NAME = "sandbox-vm-live-poc-decision-intake.md"

REQUIRED_PHRASES = [
    "Status: decision-intake planning packet for `ERG-004`.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "Requires favorable `ERG-003` disposition before implementation planning.",
    "does not approve live VM/container inspection",
    "does not approve sandbox orchestration",
    "does not approve local model invocation",
    "does not approve Mission Control runtime behavior",
    "does not approve trusted-host promotion",
    "post-RC decision record",
    "operator-managed VM profile",
    "network/mount/root contract",
    "cleanup transcript",
    "failure transcript",
    "external/source review",
    "Ithildin-governed tool boundary",
    "Mission Control display-only boundary",
    "no shell",
    "no Docker socket",
    "no Kubernetes",
    "no browser automation",
    "no arbitrary HTTP",
    "no broad filesystem writes",
    "no production identity",
    "no SIEM adapter",
    "no compliance automation",
    "public/security-product positioning remains blocked",
    "implementation_approved: false",
]

FORBIDDEN_PHRASES = [
    "live VM control is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "implementation approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM live POC decision intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"decision intake doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"decision intake doc contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM live POC decision intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("sandbox/VM live POC decision intake doc is missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing sandbox/VM live POC decision intake doc")
    if "make sandbox-vm-live-poc-decision-intake-check" not in readme:
        failures.append("README is missing sandbox/VM live POC decision intake command")
    if "sandbox-vm-live-poc-decision-intake-check:" not in makefile:
        failures.append("Make target is missing: sandbox-vm-live-poc-decision-intake-check")
    if "sandbox-vm-live-poc-decision-intake-check" not in release_check_body:
        failures.append("sandbox-vm-live-poc-decision-intake-check missing from release-check")
    if "sandbox-vm-live-poc-decision-intake-check" not in release_guardrails:
        failures.append("release guardrails do not require the live POC decision intake check")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing live POC decision intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing live POC decision intake pointer")
    if "Sandbox/VM Live POC Decision Intake" not in review_index:
        failures.append("review docs index is missing live POC decision intake entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_intake_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "blocked",
        "requires_erg_003_favorable_disposition": True,
        "decision_record_required": True,
        "implementation_approved": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC decision intake check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_intake_doc: {report['decision_intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        "requires_erg_003_favorable_disposition: "
        f"{str(report['requires_erg_003_favorable_disposition']).lower()}",
        f"decision_record_required: {str(report['decision_record_required']).lower()}",
        f"implementation_approved: {str(report['implementation_approved']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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
