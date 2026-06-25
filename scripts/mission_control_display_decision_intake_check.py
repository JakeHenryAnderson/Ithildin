"""Validate the Mission Control display decision-intake packet."""

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
DOC_REL = "docs/codex/mission-control-display-decision-intake.md"
DOC_NAME = "mission-control-display-decision-intake.md"

REQUIRED_PHRASES = [
    "Status: decision-intake planning packet for `ERG-002` and `PRD-MC-DISPLAY-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-002` status: `planning_only`.",
    "Current selected capability: `not selected`.",
    "make mission-control-display-decision-intake-check",
    "Mission Control-side implementation plan",
    "operator-selected local packet sources",
    "metadata-only",
    "negative fixture plan",
    "Mission Control display review packet",
    "warning chips remain mandatory and visible",
    "source/review evidence",
    "Required Decision Evidence",
    "Allowed Future Decision Outcomes",
    "Required Negative Evidence",
    "go_for_mission_control_side_display_importer_planning",
    "conditional_go_for_display_only_importer_implementation",
    "Mission Control planning allowed: `true`",
    "Mission Control runtime allowed: `false`",
    "Mission Control execution authority allowed: `false`",
    "Mission Control policy authority allowed: `false`",
    "Mission Control approval authority allowed: `false`",
    "Mission Control audit authority allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "SIEM adapter allowed: `false`",
    "new power classes allowed: `false`",
    "public/security-product positioning allowed: `false`",
]

FORBIDDEN_PHRASES = [
    "runtime importer is approved",
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control is policy authority",
    "Mission Control is audit authority",
    "local model invocation is approved",
    "sandbox orchestration is approved",
    "trusted-host promotion is implemented",
    "SIEM adapter is implemented",
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
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not doc_path.exists():
        failures.append("Mission Control display decision intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"Mission Control decision intake is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"Mission Control decision intake contains forbidden phrase: {phrase}"
                )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control display decision intake is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("Mission Control display decision intake is missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing Mission Control display decision intake doc")
    if "make mission-control-display-decision-intake-check" not in readme:
        failures.append("README is missing Mission Control display decision intake command")
    if "mission-control-display-decision-intake-check:" not in makefile:
        failures.append("Make target is missing: mission-control-display-decision-intake-check")
    if "mission-control-display-decision-intake-check" not in release_check_body:
        failures.append("mission-control-display-decision-intake-check missing from release-check")
    if "mission-control-display-decision-intake-check" not in release_guardrails:
        failures.append("release guardrails do not require Mission Control decision intake")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing Mission Control decision intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing Mission Control decision intake pointer")
    if DOC_NAME not in decision_register:
        failures.append(
            "post-RC decision register is missing Mission Control decision intake pointer"
        )
    if "Mission Control Display Decision Intake" not in review_index:
        failures.append("review docs index is missing Mission Control decision intake entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_intake_doc": DOC_REL,
        "tool_count": tool_surface.get("tool_count"),
        "erg_002_status": "planning_only",
        "prd_id": "PRD-MC-DISPLAY-001",
        "mission_control_planning_allowed": True,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display decision intake check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_intake_doc: {report['decision_intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"prd_id: {report['prd_id']}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "mission_control_execution_allowed: "
        f"{str(report['mission_control_execution_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
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
