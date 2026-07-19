"""Validate the active enterprise review route versus historical packet lineage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    enterprise_current_checkpoint,
    enterprise_operator_next_action,
    enterprise_readiness_gap_matrix_check,
    enterprise_review_send_preflight,
    enterprise_review_send_readiness,
    review_docs,
    technical_mvp_execution_board,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-active-route-clarity.md"
DOC_TITLE = "Enterprise Active Route Clarity"
TARGET = "enterprise-active-route-clarity"
ACTIVE_SEND_SET = ["ERG-005"]
NEXT_SEND_SET = ["ERG-006", "ERG-007"]
HISTORICAL_SEND_SET = ["ERG-003", "ERG-002"]
EXPECTED_ACTION = "execute_pis_001_threat_model_dependency_decision"

REQUIRED_DOC_PHRASES = [
    "Status: checked active-route clarification for the current enterprise planning path.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "make enterprise-active-route-clarity",
    "The completed source-finding disposition route is `ERG-005`.",
    "Current expected action: "
    "`execute_pis_001_threat_model_dependency_decision`.",
    "docs/codex/production-identity-storage-architecture-decision-record.md",
    "Current active gap scope: `ERG-006`, `ERG-007`; no new review send is required.",
    "docs/codex/production-identity-storage-pis-001-planning-gate.md",
    "EXT-LIVE-DESC-###",
    "EXT-PROD-IAM-STORAGE-###",
    "Older ERG-003/ERG-002 generated packet surfaces remain in the repository for provenance",
    "Historical dual-send route: `ERG-003`, then `ERG-002`.",
    "completed local-development disposition artifacts preserve the `ERG-004` descriptor-only lane",
    "active operator checkpoint artifacts now point to bounded `PIS-001` planning",
    "What This Does Not Approve",
]

BLOCKED_PHRASES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []

    preflight = enterprise_review_send_preflight.build_report(repo_root)
    checkpoint = enterprise_current_checkpoint.build_report(repo_root)
    operator_next = enterprise_operator_next_action.build_report(repo_root)
    technical_board = technical_mvp_execution_board.build_report(repo_root)
    historical_readiness = enterprise_review_send_readiness.build_report(repo_root)
    progress_assessment = v1_progress_assessment.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)

    for label, report in [
        ("enterprise-review-send-preflight", preflight),
        ("enterprise-current-checkpoint", checkpoint),
        ("enterprise-operator-next-action", operator_next),
        ("technical-mvp-execution-board", technical_board),
        ("v1-progress-assessment", progress_assessment),
        ("enterprise-readiness-gap-matrix", gap_matrix),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if preflight.get("current_send_set") != NEXT_SEND_SET:
        failures.append("preflight current send set is not ERG-006/ERG-007")
    if preflight.get("expected_action") != EXPECTED_ACTION:
        failures.append("preflight expected action is not ERG-006/ERG-007 architecture review")
    if checkpoint.get("recommended_send_set") != NEXT_SEND_SET:
        failures.append("current checkpoint recommended send set is not ERG-006/ERG-007")
    if checkpoint.get("recommended_next_enterprise_review") != "ERG-006/ERG-007":
        failures.append("current checkpoint next enterprise review is not ERG-006/ERG-007")
    if checkpoint.get("next_action") != EXPECTED_ACTION:
        failures.append("current checkpoint next action is not ERG-006/ERG-007 architecture review")
    if operator_next.get("recommended_send_set") != NEXT_SEND_SET:
        failures.append("operator next-action send set is not ERG-006/ERG-007")
    if operator_next.get("recommended_next_enterprise_review") != "ERG-006/ERG-007":
        failures.append("operator next-action enterprise review is not ERG-006/ERG-007")
    if operator_next.get("next_action") != EXPECTED_ACTION:
        failures.append("operator next-action is not ERG-006/ERG-007 architecture review")
    if technical_board.get("current_send_set") != NEXT_SEND_SET:
        failures.append("technical MVP execution board current send set is not ERG-006/ERG-007")
    if technical_board.get("enterprise_next_action") != EXPECTED_ACTION:
        failures.append(
            "technical MVP execution board next action is not ERG-006/ERG-007 architecture review"
        )
    if historical_readiness.get("recommended_now") != HISTORICAL_SEND_SET:
        failures.append("historical dual-send readiness no longer records ERG-003/ERG-002 lineage")
    if progress_assessment.get("recommended_send_set") != NEXT_SEND_SET:
        failures.append("v1 progress assessment active send set is not ERG-006/ERG-007")
    if progress_assessment.get("recommended_next_enterprise_review") != "ERG-006/ERG-007":
        failures.append("v1 progress assessment next review is not ERG-006/ERG-007")
    if gap_matrix.get("active_send_set") != NEXT_SEND_SET:
        failures.append("enterprise gap matrix active send set is not ERG-006/ERG-007")
    if gap_matrix.get("recommended_next_enterprise_review") != "ERG-006/ERG-007":
        failures.append("enterprise gap matrix next review is not ERG-006/ERG-007")

    boundary_flags = {
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }
    for report_name, report in [
        ("preflight", preflight),
        ("checkpoint", checkpoint),
        ("operator_next", operator_next),
        ("technical_board", technical_board),
    ]:
        for key, expected in boundary_flags.items():
            if key in report and report[key] is not expected:
                failures.append(f"{report_name} boundary flag drifted: {key}")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"active-route clarity doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(f"active-route clarity doc is missing blocked phrase: {phrase}")
    for phrase in [
        "runtime implementation is approved",
        "live VM/container inspection is approved",
        "sandbox orchestration is approved",
        "Mission Control runtime behavior is approved",
        "new governed tool powers are approved",
    ]:
        if phrase.lower() in doc.lower():
            failures.append(f"active-route clarity doc contains forbidden phrase: {phrase}")

    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("active-route clarity target is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require active-route clarity")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing active-route clarity command")
    if DOC_REL not in readme:
        failures.append("README is missing active-route clarity doc")
    if DOC_REL not in docs_site:
        failures.append("active-route clarity doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("active-route clarity doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing active-route clarity")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "active_send_set": NEXT_SEND_SET,
        "completed_local_development_route": ACTIVE_SEND_SET,
        "historical_dual_send_set": HISTORICAL_SEND_SET,
        "expected_action": EXPECTED_ACTION,
        "preflight_mode": preflight.get("preflight_mode"),
        "active_route_sources": [
            "enterprise-operator-next-action (canonical state reader)",
            "enterprise-review-send-preflight",
            "enterprise-current-checkpoint",
            "technical-mvp-execution-board",
            "v1-progress-assessment",
            "enterprise-readiness-gap-matrix",
        ],
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise active route clarity",
        f"valid: {str(report['valid']).lower()}",
        f"doc: {report['doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        "active_send_set: " + ", ".join(report["active_send_set"]),
        "historical_dual_send_set: " + ", ".join(report["historical_dual_send_set"]),
        f"expected_action: {report['expected_action']}",
        f"preflight_mode: {report.get('preflight_mode')}",
    ]
    for key in [
        "runtime_changes_allowed",
        "live_vm_inspection_allowed",
        "sandbox_orchestration_allowed",
        "mission_control_runtime_allowed",
        "local_model_invocation_allowed",
        "new_power_classes_allowed",
        "public_security_product_positioning_allowed",
    ]:
        lines.append(f"{key}: {str(report[key]).lower()}")
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
