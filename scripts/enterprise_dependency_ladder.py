"""Validate the enterprise dependency ladder for post-RC work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_current_checkpoint,
    enterprise_progress_model,
    enterprise_readiness_gap_matrix_check,
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-dependency-ladder.md"
DOC_TITLE = "Ithildin Enterprise Dependency Ladder"

LADDER_ROWS: tuple[dict[str, str], ...] = (
    {
        "checkpoint": "v1_local_preview_rc",
        "status": "ready_for_operator_trial",
        "depends_on": "release-check and review-candidate",
        "unlocks": "local technical-preview handoff only",
    },
    {
        "checkpoint": "erg_003_static_preflight",
        "status": "external_review_required",
        "depends_on": "ERG-003 source-level or packet-and-source disposition",
        "unlocks": "static preflight local-preview closure only",
    },
    {
        "checkpoint": "erg_002_mission_control_display",
        "status": "planning_only",
        "depends_on": "ERG-002 display/import planning disposition",
        "unlocks": "Mission Control-side design-only decision record",
    },
    {
        "checkpoint": "erg_004_live_sandbox_vm_poc",
        "status": "blocked",
        "depends_on": "favorable ERG-003 disposition and separate decision record",
        "unlocks": "live POC implementation planning only",
    },
    {
        "checkpoint": "erg_005_trusted_host_promotion",
        "status": "blocked",
        "depends_on": "trusted-host promotion disposition and decision record",
        "unlocks": "promotion implementation planning only",
    },
    {
        "checkpoint": "enterprise_architecture_lanes",
        "status": "planning_only_or_blocked",
        "depends_on": "separate identity/storage/SIEM/compliance/public-positioning dispositions",
        "unlocks": "architecture decisions only",
    },
)

REQUIRED_DOC_PHRASES = [
    "Status: checked enterprise dependency ladder",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Recommended first closure lane: `ERG-003`",
    "Recommended second closure lane: `ERG-002`",
    "`ERG-004` remains blocked until `ERG-003` is favorably dispositioned",
    "Mission Control display/import planning remains design-only",
    "No row in this ladder approves runtime behavior",
    "Do not manually promote a lane",
    "make enterprise-review-send-receipt-template",
    "make enterprise-dual-response-inbox",
    "var/review-runs/enterprise-dual-response-inbox/",
    "make enterprise-dependency-ladder",
]

BLOCKED_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter runtime behavior",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
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
    current = enterprise_current_checkpoint.build_report(repo_root)
    progress = enterprise_progress_model.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    send_readiness = enterprise_review_send_readiness.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)

    for label, report in [
        ("enterprise-current-checkpoint", current),
        ("enterprise-progress-model", progress),
        ("enterprise-readiness-gap-matrix", gap_matrix),
        ("enterprise-review-send-readiness", send_readiness),
        ("enterprise-response-status-board", response_status),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if current.get("tool_count") != 24:
        failures.append("current checkpoint tool count is not 24")
    if current.get("selected_capability") != "not selected":
        failures.append("selected capability must remain not selected")
    if current.get("recommended_send_set") != ["ERG-003", "ERG-002"]:
        failures.append("recommended send set must remain ERG-003 then ERG-002")
    if send_readiness.get("recommended_now") != ["ERG-003", "ERG-002"]:
        failures.append("send-readiness recommended order must remain ERG-003 then ERG-002")
    if response_status.get("response_present_count") != 0:
        failures.append("enterprise responses are present; use response application flow")
    if response_status.get("closure_ready_count") != 0:
        failures.append("enterprise closure-ready lanes exist; use lane-specific closure flow")
    if gap_matrix.get("gap_count") != 10:
        failures.append("enterprise gap count is not 10")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("enterprise dependency ladder doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise dependency ladder doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise dependency ladder doc is missing blocked phrase: {phrase}")

    for row in LADDER_ROWS:
        for value in row.values():
            if value not in doc:
                failures.append(f"enterprise dependency ladder doc is missing row value: {value}")

    if "enterprise-dependency-ladder:" not in makefile:
        failures.append("Make target is missing: enterprise-dependency-ladder")
    if "enterprise-dependency-ladder" not in release_check_body:
        failures.append("enterprise-dependency-ladder is missing from release-check")
    if "$(MAKE) enterprise-dependency-ladder" not in review_candidate_body:
        failures.append("enterprise-dependency-ladder is missing from review-candidate")
    if "make enterprise-dependency-ladder" not in readme:
        failures.append("README is missing enterprise dependency ladder command")
    if DOC_REL not in docs_site:
        failures.append("enterprise dependency ladder is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise dependency ladder is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise dependency ladder")
    if "enterprise-dependency-ladder" not in release_guardrails:
        failures.append("release guardrails do not require enterprise dependency ladder")

    boundary_flags = {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_runtime_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "closes_enterprise_lanes": False,
    }

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "dependency_ladder_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": current.get("selected_capability"),
        "recommended_sequence": ["ERG-003", "ERG-002", "ERG-004"],
        "recommended_first_closure_lane": "ERG-003",
        "recommended_second_closure_lane": "ERG-002",
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "ladder_rows": list(LADDER_ROWS),
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise dependency ladder",
        f"valid: {str(report['valid']).lower()}",
        f"dependency_ladder_doc: {report['dependency_ladder_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_sequence: " + ", ".join(report["recommended_sequence"]),
        f"recommended_first_closure_lane: {report['recommended_first_closure_lane']}",
        f"recommended_second_closure_lane: {report['recommended_second_closure_lane']}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        "ladder_rows:",
    ]
    for row in report["ladder_rows"]:
        lines.append(
            "- {checkpoint}: status={status}; depends_on={depends_on}; unlocks={unlocks}".format(
                **row
            )
        )
    for key in [
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "local_model_invocation_allowed",
        "sandbox_orchestration_allowed",
        "trusted_host_promotion_allowed",
        "siem_adapter_runtime_allowed",
        "compliance_automation_allowed",
        "public_security_product_positioning_allowed",
        "new_power_classes_allowed",
        "closes_enterprise_lanes",
    ]:
        lines.append(f"{key}: {str(report[key]).lower()}")
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
