"""Validate the enterprise post-review transition map."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dependency_ladder,
    enterprise_readiness_gap_matrix_check,
    enterprise_response_application_protocol,
    enterprise_response_status_board,
    next_capability_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-transition-map.md"
DOC_TITLE = "Enterprise Transition Map"

TRANSITION_ROWS: tuple[dict[str, str], ...] = (
    {
        "lane": "v1_local_preview_rc",
        "current_state": "operator_trial_observed",
        "required_evidence": "release-check and review-candidate evidence",
        "allowed_next_state": "local_technical_preview_handoff",
    },
    {
        "lane": "ERG-003",
        "current_state": "external_review_required",
        "required_evidence": "favorable source-level or packet-and-source response",
        "allowed_next_state": "closed_local_preview_static_preflight",
    },
    {
        "lane": "ERG-002",
        "current_state": "planning_only",
        "required_evidence": "favorable display/import planning response",
        "allowed_next_state": "ready_for_design_only_decision_record",
    },
    {
        "lane": "ERG-004",
        "current_state": "blocked",
        "required_evidence": "favorable ERG-003 disposition plus separate ERG-004 decision record",
        "allowed_next_state": "ready_for_decision_record",
    },
    {
        "lane": "ERG-005",
        "current_state": "ready_for_implementation_planning_only",
        "required_evidence": "trusted-host promotion decision record",
        "allowed_next_state": "implementation_plan_refinement_only",
    },
    {
        "lane": "ERG-006/ERG-007",
        "current_state": "planning_only",
        "required_evidence": "favorable identity/storage architecture response and closure gate",
        "allowed_next_state": "architecture_continuation_only",
    },
    {
        "lane": "ERG-008",
        "current_state": "planning_only",
        "required_evidence": "favorable SIEM adapter architecture response and closure gate",
        "allowed_next_state": "architecture_continuation_only",
    },
    {
        "lane": "ERG-009",
        "current_state": "planning_only",
        "required_evidence": "favorable compliance-mapping architecture response and closure gate",
        "allowed_next_state": "architecture_continuation_only",
    },
    {
        "lane": "ERG-010",
        "current_state": "blocked",
        "required_evidence": "favorable docs/claims public-preview disposition closure gate",
        "allowed_next_state": "positioning_decision_record_only",
    },
)

REQUIRED_DOC_PHRASES = [
    "Status: checked post-review transition map",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-003` may move only to `closed_local_preview_static_preflight`.",
    "`ERG-002` may move only to `ready_for_design_only_decision_record`.",
    "`ERG-004` remains blocked until `ERG-003` is favorably dispositioned",
    "`ERG-005` may continue only to `implementation_plan_refinement_only`.",
    "Architecture continuation states are not runtime approval states.",
    "No transition in this map approves new governed tool powers.",
    "Do not manually promote a lane",
    "make enterprise-response-paste-preflight",
    "var/review-runs/enterprise-dual-response-inbox/",
    "make enterprise-transition-map",
]

BLOCKED_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "direct host writes",
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

    capability = next_capability_readiness.build_report(repo_root)
    ladder = enterprise_dependency_ladder.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    response_protocol = enterprise_response_application_protocol.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)

    for label, report in [
        ("next-capability-readiness", capability),
        ("enterprise-dependency-ladder", ladder),
        ("enterprise-readiness-gap-matrix", gap_matrix),
        ("enterprise-response-application-protocol", response_protocol),
        ("enterprise-response-status-board", response_status),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if capability.get("tool_count") != 24:
        failures.append("next capability readiness tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("selected capability must remain not selected")
    if ladder.get("recommended_sequence") != ["ERG-003", "ERG-002", "ERG-004"]:
        failures.append("enterprise dependency ladder recommended sequence drifted")
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
        failures.append("enterprise transition map doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise transition map doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise transition map doc is missing blocked phrase: {phrase}")
    for row in TRANSITION_ROWS:
        for value in row.values():
            if value not in doc:
                failures.append(f"enterprise transition map doc is missing row value: {value}")

    if "enterprise-transition-map:" not in makefile:
        failures.append("Make target is missing: enterprise-transition-map")
    if "enterprise-transition-map" not in release_check_body:
        failures.append("enterprise-transition-map is missing from release-check")
    if "$(MAKE) enterprise-transition-map" not in review_candidate_body:
        failures.append("enterprise-transition-map is missing from review-candidate")
    if "make enterprise-transition-map" not in readme:
        failures.append("README is missing enterprise transition map command")
    if DOC_REL not in docs_site:
        failures.append("enterprise transition map is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise transition map is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise transition map")
    if "enterprise-transition-map" not in release_guardrails:
        failures.append("release guardrails do not require enterprise transition map")

    boundary_flags = {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "siem_adapter_runtime_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_mcp_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "closes_enterprise_lanes": False,
    }

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "transition_map_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": capability.get("next_candidate"),
        "recommended_sequence": ["ERG-003", "ERG-002", "ERG-004"],
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "transition_rows": list(TRANSITION_ROWS),
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise transition map",
        f"valid: {str(report['valid']).lower()}",
        f"transition_map_doc: {report['transition_map_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_sequence: " + ", ".join(report["recommended_sequence"]),
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        "transition_rows:",
    ]
    for row in report["transition_rows"]:
        lines.append(
            "- "
            f"{row['lane']}: {row['current_state']} -> {row['allowed_next_state']}; "
            f"requires={row['required_evidence']}"
        )
    for key in [
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "local_model_invocation_allowed",
        "sandbox_orchestration_allowed",
        "trusted_host_promotion_allowed",
        "direct_host_writes_allowed",
        "siem_adapter_runtime_allowed",
        "production_identity_allowed",
        "runtime_postgres_allowed",
        "hosted_telemetry_allowed",
        "remote_mcp_allowed",
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
