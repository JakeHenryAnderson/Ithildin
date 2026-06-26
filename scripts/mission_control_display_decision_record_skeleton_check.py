"""Validate the Mission Control display decision-record skeleton and release wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_control_display_disposition_closure_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-display-decision-record-skeleton.md"
DOC_NAME = "mission-control-display-decision-record-skeleton.md"

REQUIRED_PHRASES = [
    "Status: design-only decision-record skeleton for `ERG-002` and `PRD-MC-DISPLAY-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-002` status: `planning_only`.",
    "Current selected capability: `not selected`.",
    "does not approve runtime behavior",
    "Mission Control runtime importer",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "sandbox orchestration",
    "trusted-host promotion",
    "new governed tool powers",
    "public/security-product positioning",
    "var/review-runs/mission-control-display/normalized-response.json",
    "make mission-control-display-disposition-closure-check",
    "disposition_outcome: continue_design_only",
    "approved_for_planning",
    "ERG-002: planning_only -> ready_for_design_only_decision_record",
    "Runtime surfaces touched: none.",
    "Tool count impact: none; remains `24`.",
    "Mission Control impact: planning artifacts only.",
    "Required source-review or external-review evidence:",
    "Required implementation plan: still required before any runtime importer implementation.",
    "Required negative transcripts:",
    (
        "Go/no-go outcome: go for design-only Mission Control-side planning; "
        "no-go for runtime importer"
    ),
    "make mission-control-display-decision-record-skeleton-check",
    "make release-check",
]

FORBIDDEN_PHRASES = [
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control is policy authority",
    "Mission Control is audit authority",
    "runtime importer is approved",
    "runtime importer behavior is approved",
    "API callbacks are approved",
    "polling Ithildin APIs is approved",
    "sandbox orchestration is implemented",
    "local model invocation is implemented",
    "trusted-host promotion is implemented",
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
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    decision_intake = _read(repo_root / "docs/codex/mission-control-display-decision-intake.md")
    closure_gate = _read(
        repo_root / "docs/codex/mission-control-display-disposition-closure-gate.md"
    )
    response_kit = _read(repo_root / "docs/codex/mission-control-display-response-kit.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    closure_report = mission_control_display_disposition_closure_check.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("Mission Control display decision-record skeleton doc is missing")
    else:
        text = _read(doc_path)
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    "Mission Control display decision-record skeleton is missing phrase: "
                    f"{phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "Mission Control display decision-record skeleton contains forbidden phrase: "
                    f"{phrase}"
                )

    failures.extend(
        f"Mission Control display disposition closure gate: {failure}"
        for failure in closure_report["failures"]
    )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append(
            "Mission Control display decision-record skeleton is missing from review docs"
        )
    if DOC_REL not in docs_site:
        failures.append(
            "Mission Control display decision-record skeleton is missing from docs site"
        )
    if "mission-control-display-decision-record-skeleton-check:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-display-decision-record-skeleton-check"
        )
    if "mission-control-display-decision-record-skeleton-check" not in release_check_body:
        failures.append(
            "mission-control-display-decision-record-skeleton-check missing from release-check"
        )
    if "make mission-control-display-decision-record-skeleton-check" not in readme:
        failures.append("README is missing Mission Control decision-record skeleton command")
    if "Mission Control Display Decision Record Skeleton" not in review_index:
        failures.append("review docs index is missing Mission Control decision-record skeleton")

    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("decision intake", decision_intake),
        ("closure gate", closure_gate),
        ("response kit", response_kit),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing Mission Control decision-record skeleton pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_skeleton_doc": DOC_REL,
        "tool_count": 24,
        "erg_002_status": "planning_only",
        "allowed_future_status": "ready_for_design_only_decision_record",
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "runtime_importer_allowed": False,
        "mission_control_execution_authority_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "api_callbacks_allowed": False,
        "polling_or_mutating_ithildin_apis_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_002": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display decision-record skeleton check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_skeleton_doc: {report['decision_record_skeleton_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"runtime_importer_allowed: {str(report['runtime_importer_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"api_callbacks_allowed: {str(report['api_callbacks_allowed']).lower()}",
        "polling_or_mutating_ithildin_apis_allowed: "
        f"{str(report['polling_or_mutating_ithildin_apis_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
