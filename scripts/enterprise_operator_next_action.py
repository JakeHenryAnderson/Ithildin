"""Validate the current enterprise operator next action."""

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
    enterprise_north_star_roadmap,
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-operator-next-action.md"
DOC_TITLE = "Enterprise Operator Next Action"

SEND_COMMANDS = [
    "make release-check",
    "make review-candidate",
    "make enterprise-dual-review-outbox",
    "make enterprise-review-send-manifest",
    "make enterprise-review-submission-prompt",
    "make enterprise-review-handoff-drill",
]

RESPONSE_COMMANDS = [
    "make enterprise-response-paste-preflight",
    "make enterprise-response-inbox",
    "make enterprise-response-status-board",
    "make enterprise-response-intake-quickstart",
]

REQUIRED_DOC_PHRASES = [
    "Status: checked read-only operator next-action summary",
    "Current governed tool count: `24`",
    "make enterprise-operator-next-action",
    "With no real enterprise reviewer responses present",
    "make enterprise-dual-review-outbox",
    "make enterprise-review-send-manifest",
    "make enterprise-review-submission-prompt",
    "make enterprise-review-handoff-drill",
    "`ERG-003`: static sandbox/VM preflight disposition",
    "`ERG-002`: Mission Control display/import planning review",
    "make enterprise-response-paste-preflight",
    "make enterprise-response-intake-quickstart",
    "What This Does Not Approve",
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

FORBIDDEN_PHRASES = [
    "enterprise-ready",
    "production-ready",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
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


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []

    response_status = enterprise_response_status_board.build_report(repo_root)
    response_failures = _unexpected_response_status_failures(response_status)
    failures.extend(f"enterprise-response-status-board: {failure}" for failure in response_failures)

    response_present_count = int(response_status.get("response_present_count") or 0)
    closure_ready_count = int(response_status.get("closure_ready_count") or 0)
    next_action = _next_action(response_present_count, closure_ready_count)
    action_commands = (
        SEND_COMMANDS
        if next_action == "send_erg_003_and_erg_002"
        else RESPONSE_COMMANDS
    )

    checkpoint: dict[str, Any] = {}
    send_readiness: dict[str, Any] = {"recommended_now": ["ERG-003", "ERG-002"]}
    north_star: dict[str, Any] = {
        "recommended_send_set": ["ERG-003", "ERG-002"],
        "recommended_next_enterprise_review": "ERG-003",
    }

    if next_action == "send_erg_003_and_erg_002":
        checkpoint = enterprise_current_checkpoint.build_report(repo_root)
        send_readiness = enterprise_review_send_readiness.build_report(repo_root)
        north_star = enterprise_north_star_roadmap.build_report(repo_root)

        for label, report in [
            ("enterprise-current-checkpoint", checkpoint),
            ("enterprise-review-send-readiness", send_readiness),
            ("enterprise-north-star-roadmap", north_star),
        ]:
            if report.get("valid") is not True:
                failures.append(f"{label} is not valid")
                failures.extend(
                    f"{label}: {failure}" for failure in report.get("failures", [])
                )

        if checkpoint.get("tool_count") != 24:
            failures.append("current checkpoint tool count is not 24")
        if checkpoint.get("selected_capability") != "not selected":
            failures.append("current checkpoint selected capability is not selected")
    if send_readiness.get("recommended_now") != ["ERG-003", "ERG-002"]:
        failures.append("recommended send set must remain ERG-003 then ERG-002")
    if north_star.get("recommended_send_set") != ["ERG-003", "ERG-002"]:
        failures.append("north-star send set must remain ERG-003 then ERG-002")
    if north_star.get("recommended_next_enterprise_review") != "ERG-003":
        failures.append("recommended next enterprise review must remain ERG-003")

    boundary_flags = {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }
    for key, expected in boundary_flags.items():
        mode_reports = [("response-status", response_status)]
        if next_action == "send_erg_003_and_erg_002":
            mode_reports.extend(
                [
                    ("checkpoint", checkpoint),
                    ("send-readiness", send_readiness),
                    ("north-star", north_star),
                ]
            )
        for label, report in mode_reports:
            if key in report and report[key] is not expected:
                failures.append(f"{label} boundary flag drifted: {key}")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise operator next-action doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(
                f"enterprise operator next-action doc is missing blocked phrase: {phrase}"
            )
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                f"enterprise operator next-action doc contains forbidden phrase: {phrase}"
            )

    if "enterprise-operator-next-action:" not in makefile:
        failures.append("Make target is missing: enterprise-operator-next-action")
    if (
        "enterprise-operator-next-action" not in release_check_body
        and "release-check: enterprise-operator-next-action" not in makefile
    ):
        failures.append("enterprise-operator-next-action is missing from release-check")
    if "$(MAKE) enterprise-operator-next-action" not in review_candidate_body:
        failures.append("enterprise-operator-next-action is missing from review-candidate")
    if "make enterprise-operator-next-action" not in readme:
        failures.append("README is missing enterprise operator next-action command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise operator next-action doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise operator next-action is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise operator next-action is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise operator next action")
    if "enterprise-operator-next-action" not in release_guardrails:
        failures.append("release guardrails do not require enterprise operator next action")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "next_action_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": checkpoint.get("selected_capability", "not selected"),
        "recommended_send_set": send_readiness.get("recommended_now"),
        "recommended_next_enterprise_review": north_star.get(
            "recommended_next_enterprise_review"
        ),
        "response_present_count": response_present_count,
        "closure_ready_count": closure_ready_count,
        "next_action": next_action,
        "action_commands": action_commands,
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise operator next action",
        f"valid: {str(report['valid']).lower()}",
        f"next_action_doc: {report['next_action_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: "
        + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"next_action: {report.get('next_action', 'unknown')}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands", [])],
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _next_action(response_present_count: int, closure_ready_count: int) -> str:
    if closure_ready_count > 0:
        return "run_lane_specific_closure_playbook"
    if response_present_count > 0:
        return "run_response_intake_preflight"
    return "send_erg_003_and_erg_002"


def _unexpected_response_status_failures(report: dict[str, Any]) -> list[str]:
    expected_state_failures = (
        "normalized response is present; run lane intake",
        "closure is ready; run lane-specific closure flow",
    )
    response_present_gaps = {
        row.get("gap") for row in report.get("rows", []) if row.get("response_present") is True
    }
    closure_ready_gaps = {
        row.get("gap") for row in report.get("rows", []) if row.get("closure_ready") is True
    }
    failures = []
    for failure in report.get("failures", []):
        if any(fragment in failure for fragment in expected_state_failures):
            continue
        if (
            "closure gate is not valid" in failure
            and any(str(gap) in failure for gap in response_present_gaps)
        ):
            continue
        if (
            "closure gate is not valid" in failure
            and any(str(gap) in failure for gap in closure_ready_gaps)
        ):
            continue
        failures.append(failure)
    return failures


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
