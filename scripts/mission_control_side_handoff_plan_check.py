"""Validate the Mission Control-side display importer handoff plan."""

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
DOC_REL = "docs/codex/mission-control-side-handoff-plan.md"
DOC = ROOT / DOC_REL

REQUIRED_PHRASES = [
    "Status: planning-only cross-repo handoff",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Implement a local file/import display surface",
    "Required Mission Control Inputs",
    "Required Mission Control Validation",
    "Display States",
    "Required Mission Control Tests",
    "Required Mission Control Evidence",
    "Explicit Non-Goals",
    "Stop Conditions For Mission Control Work",
    "Runtime importer implementation remains blocked",
    "post-RC decision record",
    "Mission Control repository implementation plan",
]

REQUIRED_DISPLAY_STATES = [
    "not_imported",
    "imported_valid",
    "imported_with_warnings",
    "unsupported_schema",
    "stale_packet",
    "hash_mismatch",
    "unsafe_attachment",
    "authority_overclaim",
    "content_leak_rejected",
]

REQUIRED_TEST_FAMILIES = [
    "valid metadata-only handoff import",
    "unsupported schema rejection",
    "Mission Control execution-authority overclaim rejection",
    "Mission Control policy/approval/audit-authority overclaim rejection",
    "absolute attachment path rejection",
    "parent-traversal attachment path rejection",
    "URL attachment rejection",
    "raw prompt/content/diff/response-body display rejection",
    "artifact-hash mismatch warning or rejection",
]

REQUIRED_NON_GOALS = [
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "callback APIs from Mission Control into Ithildin",
    "local model invocation",
    "VM/container lifecycle control",
    "sandbox orchestration",
    "trusted-host promotion",
    "shell execution",
    "direct filesystem mutation by Mission Control",
    "remote MCP",
    "SIEM adapters",
    "production IAM",
    "runtime Postgres",
    "hosted telemetry",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "Mission Control may execute",
    "Mission Control may approve",
    "Mission Control is the policy authority",
    "Mission Control is the audit authority",
    "runtime importer is approved",
    "trusted-host promotion is implemented",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
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
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/mission_control_display_review_packet.py").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control-side handoff plan is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"handoff plan is missing phrase: {phrase}")
        for phrase in REQUIRED_DISPLAY_STATES:
            if phrase not in text:
                failures.append(f"handoff plan is missing display state: {phrase}")
        for phrase in REQUIRED_TEST_FAMILIES:
            if phrase not in text:
                failures.append(f"handoff plan is missing test family: {phrase}")
        for phrase in REQUIRED_NON_GOALS:
            if phrase not in text:
                failures.append(f"handoff plan is missing non-goal: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"handoff plan contains forbidden phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control-side handoff plan is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("Mission Control-side handoff plan is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("Mission Control display review packet does not bundle handoff plan")
    if "mission-control-side-handoff-plan-check:" not in makefile:
        failures.append("Make target is missing: mission-control-side-handoff-plan-check")
    if "mission-control-side-handoff-plan-check" not in release_check_body:
        failures.append("mission-control-side-handoff-plan-check missing from release-check")
    if "make mission-control-side-handoff-plan-check" not in readme:
        failures.append("README is missing Mission Control-side handoff plan command")
    if "mission-control-side-handoff-plan.md" not in readme:
        failures.append("README is missing Mission Control-side handoff plan doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "plan_doc": DOC_REL,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "mission_control_side_runtime_implementation_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control-side handoff plan check",
        f"valid: {str(report['valid']).lower()}",
        f"plan_doc: {report['plan_doc']}",
        f"tool_count: {report['tool_count']}",
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
        "mission_control_side_runtime_implementation_allowed: "
        f"{str(report['mission_control_side_runtime_implementation_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
