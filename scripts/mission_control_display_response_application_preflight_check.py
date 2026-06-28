"""Validate ERG-002 response application preflight wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_response_command_matrix,
    mission_control_display_decision_record_skeleton_check,
    mission_control_display_disposition_closure_check,
    mission_control_display_external_response_intake_check,
    mission_control_display_response_dry_run,
    mission_control_display_response_kit,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-display-response-application-preflight.md"
DOC_NAME = "mission-control-display-response-application-preflight.md"
RAW_RESPONSE_PATH = "var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md"
NORMALIZED_RESPONSE_PATH = (
    mission_control_display_disposition_closure_check.NORMALIZED_RESPONSE_REL
)

REQUIRED_PHRASES = [
    "Status: checked preflight for applying a real `ERG-002` external response.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "Current `ERG-002` status before real reviewer disposition: `planning_only`.",
    "make mission-control-display-response-application-preflight-check",
    "make enterprise-response-command-matrix",
    RAW_RESPONSE_PATH,
    NORMALIZED_RESPONSE_PATH,
    "mission-control-display",
    "EXT-MC-DISPLAY-###",
    "make mission-control-display-disposition-closure-check",
    "make mission-control-display-response-dry-run",
    "make mission-control-display-response-kit-check",
    "make mission-control-display-decision-record-skeleton-check",
    "ready_for_design_only_decision_record",
    "approved_for_planning",
    "does not normalize responses",
    "does not write normalized response files",
    "does not close `ERG-002`",
    "runtime importer behavior remains blocked",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "Mission Control runtime importer behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote delivery",
    "new governed tool powers",
    "public/security-product positioning",
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

    closure = mission_control_display_disposition_closure_check.build_report(repo_root)
    dry_run = mission_control_display_response_dry_run.run_dry_run(repo_root)
    intake = mission_control_display_external_response_intake_check.build_report(repo_root)
    response_kit = mission_control_display_response_kit.build_check_report(repo_root)
    decision_skeleton = mission_control_display_decision_record_skeleton_check.build_report(
        repo_root
    )
    matrix = enterprise_response_command_matrix.build_report(repo_root)

    for label, report in [
        ("closure gate", closure),
        ("response dry run", dry_run),
        ("external response intake", intake),
        ("response kit", response_kit),
        ("decision-record skeleton", decision_skeleton),
        ("enterprise response command matrix", matrix),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    erg002_row = next(
        (row for row in matrix.get("command_rows", []) if row.get("gap") == "ERG-002"),
        None,
    )
    if not erg002_row:
        failures.append("enterprise response command matrix is missing ERG-002")
    else:
        expected_values = {
            "raw_response_path": RAW_RESPONSE_PATH,
            "normalized_response_path": NORMALIZED_RESPONSE_PATH,
            "normalization_area": "mission-control-display",
            "dry_run_command": "make mission-control-display-response-dry-run",
            "closure_gate": "make mission-control-display-disposition-closure-check",
            "allowed_next_state": "ready_for_design_only_decision_record",
        }
        for key, expected in expected_values.items():
            if erg002_row.get(key) != expected:
                failures.append(f"ERG-002 command matrix {key} drifted")

    if closure.get("normalized_response_present") is not False:
        failures.append("ERG-002 normalized response is already present")
    if closure.get("closure_ready") is not False:
        failures.append("ERG-002 closure gate is unexpectedly closure-ready")
    if closure.get("erg_002_status") != "planning_only":
        failures.append("ERG-002 status drifted before real reviewer disposition")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    response_inbox = _read(repo_root / "docs/codex/enterprise-response-inbox.md")
    command_matrix_doc = _read(repo_root / "docs/codex/enterprise-response-command-matrix.md")
    external_intake_doc = _read(
        repo_root / "docs/codex/mission-control-display-external-response-intake.md"
    )
    closure_doc = _read(
        repo_root / "docs/codex/mission-control-display-disposition-closure-gate.md"
    )
    dry_run_doc = _read(repo_root / "docs/codex/mission-control-display-response-dry-run.md")
    response_kit_doc = _read(repo_root / "docs/codex/mission-control-display-response-kit.md")
    decision_skeleton_doc = _read(
        repo_root / "docs/codex/mission-control-display-decision-record-skeleton.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("Mission Control display response application preflight doc is missing")
    else:
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in doc:
                failures.append(
                    "Mission Control display response application preflight doc is missing "
                    f"phrase: {phrase}"
                )
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in doc:
                failures.append(
                    "Mission Control display response application preflight doc is missing "
                    f"blocked boundary: {phrase}"
                )
        for forbidden in [
            "runtime implementation is approved",
            "Mission Control runtime importer behavior is approved",
            "Mission Control execution authority is approved",
            "Mission Control policy authority is approved",
            "Mission Control approval authority is approved",
            "Mission Control audit authority is approved",
            "ERG-002 is closed",
            "Mission Control may execute",
        ]:
            if forbidden.lower() in lowered:
                failures.append(
                    "Mission Control display response application preflight doc contains: "
                    f"{forbidden}"
                )

    target = "mission-control-display-response-application-preflight-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append(
            "Mission Control display response application preflight missing from release-check"
        )
    if target not in release_guardrails:
        failures.append("release guardrails do not require Mission Control display preflight")
    if f"make {target}" not in readme:
        failures.append("README is missing Mission Control display preflight command")
    if DOC_REL not in readme:
        failures.append("README is missing Mission Control display preflight doc")
    if DOC_REL not in docs_site:
        failures.append("Mission Control display preflight is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control display preflight is missing from review docs")
    if "Mission Control Display Response Application Preflight" not in review_index:
        failures.append("review-docs index is missing Mission Control display preflight")
    for label, source in [
        ("response inbox", response_inbox),
        ("enterprise response command matrix", command_matrix_doc),
        ("external response intake", external_intake_doc),
        ("closure gate", closure_doc),
        ("response dry run", dry_run_doc),
        ("response kit", response_kit_doc),
        ("decision-record skeleton", decision_skeleton_doc),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing Mission Control display preflight pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "preflight_doc": DOC_REL,
        "tool_count": 24,
        "erg_002_status": "planning_only",
        "raw_response_path": RAW_RESPONSE_PATH,
        "normalized_response_path": NORMALIZED_RESPONSE_PATH,
        "response_present": closure.get("normalized_response_present"),
        "closure_ready": closure.get("closure_ready"),
        "allowed_future_status": "ready_for_design_only_decision_record",
        "decision_record_outcome": "approved_for_planning",
        "runtime_changes_allowed": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_erg_002": False,
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
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display response application preflight check",
        f"valid: {str(report['valid']).lower()}",
        f"preflight_doc: {report['preflight_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"raw_response_path: {report['raw_response_path']}",
        f"normalized_response_path: {report['normalized_response_path']}",
        f"response_present: {str(report['response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"decision_record_outcome: {report['decision_record_outcome']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"runtime_importer_allowed: {str(report['runtime_importer_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
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
