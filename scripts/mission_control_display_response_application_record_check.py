"""Validate the Mission Control display response-application record."""

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
DOC_REL = "docs/codex/mission-control-display-response-application-record.md"
DOC_NAME = "mission-control-display-response-application-record.md"

REQUIRED_PHRASES = [
    "Status: process-only response-application record for `ERG-002`.",
    "Current governed tool count: `24`.",
    "Current `ERG-002` status before real reviewer disposition: `planning_only`.",
    "Current selected capability: `not selected`.",
    "does not close `ERG-002` by itself",
    "var/review-runs/mission-control-display/normalized-response.json",
    "EXT-MC-DISPLAY-###",
    "can_close_source_rows` is `true`",
    "mutates_findings` is `false`",
    "closes_external_review` is `false`",
    "make mission-control-display-disposition-closure-check",
    "make mission-control-display-response-dry-run",
    "make mission-control-display-response-application-record-check",
    "mission-control-display-decision-record-skeleton.md",
    "ERG-002: planning_only -> ready_for_design_only_decision_record",
    "runtime importer behavior remains blocked",
    "make release-check",
    "make review-candidate",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "Mission Control runtime importer behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "sandbox orchestration",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "new governed tool powers",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime importer is approved",
    "runtime importer behavior is approved",
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control is policy authority",
    "Mission Control is audit authority",
    "API callbacks are approved",
    "polling Ithildin APIs is approved",
    "ERG-002 is closed",
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
    response_kit = _read(repo_root / "docs/codex/mission-control-display-response-kit.md")
    preflight = _read(
        repo_root / "docs/codex/mission-control-display-response-application-preflight.md"
    )
    skeleton = _read(repo_root / "docs/codex/mission-control-display-decision-record-skeleton.md")
    closure_gate = _read(
        repo_root / "docs/codex/mission-control-display-disposition-closure-gate.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    closure_report = mission_control_display_disposition_closure_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("Mission Control display response-application record is missing")
        text = ""
    else:
        text = _read(doc_path)
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(
                    f"response-application record is missing phrase: {phrase}"
                )
        for boundary in REQUIRED_BLOCKED_BOUNDARIES:
            if boundary not in text:
                failures.append(
                    f"response-application record is missing blocked boundary: {boundary}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"response-application record contains forbidden phrase: {phrase}"
                )

    if closure_report["erg_002_status"] != "planning_only":
        failures.append("Mission Control closure gate unexpectedly moved ERG-002")
    if closure_report["closure_ready"] is not False:
        failures.append("Mission Control closure gate unexpectedly reports closure readiness")
    if closure_report["runtime_changes_allowed"] is not False:
        failures.append("Mission Control closure gate unexpectedly allows runtime changes")
    if closure_report["new_power_classes_allowed"] is not False:
        failures.append("Mission Control closure gate unexpectedly allows new power classes")

    target = "mission-control-display-response-application-record-check"
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("response-application record is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("response-application record is missing from docs-site inputs")
    if "Mission Control Display Response Application Record" not in review_index:
        failures.append("review-docs index is missing response-application record")
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body:
        failures.append("response-application record check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require response-application record check")
    if f"make {target}" not in readme:
        failures.append("README is missing response-application record command")
    for label, source in [
        ("response kit", response_kit),
        ("response-application preflight", preflight),
        ("decision-record skeleton", skeleton),
        ("closure gate", closure_gate),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing response-application record pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "response_application_record_doc": DOC_REL,
        "tool_count": 24,
        "erg_002_status": "planning_only",
        "allowed_future_status": "ready_for_design_only_decision_record",
        "decision_record_outcome": "approved_for_planning",
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "requires_real_normalized_response": True,
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
        "Ithildin Mission Control display response-application record check",
        f"valid: {str(report['valid']).lower()}",
        f"response_application_record_doc: {report['response_application_record_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"allowed_future_status: {report['allowed_future_status']}",
        f"decision_record_outcome: {report['decision_record_outcome']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "requires_real_normalized_response: "
        f"{str(report['requires_real_normalized_response']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
