"""Validate the Mission Control display importer implementation plan."""

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
DOC = ROOT / "docs/codex/mission-control-display-importer-plan.md"

REQUIRED_PHRASES = [
    "Status: planning-only implementation packet for a future Mission Control display importer.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "file/import display only",
    "Required Input Contract",
    "Required Validation Stages",
    "Display Model",
    "Import Status States",
    "Negative Fixture Coverage",
    "Evidence And Review Requirements",
    "Explicit Non-Goals",
    "planning may continue",
    "Runtime importer implementation remains blocked",
    "post-RC decision record",
    "Mission Control-side implementation plan",
]

REQUIRED_VALIDATION_STAGES = [
    "Packet source",
    "Schema",
    "Authority flags",
    "Display contract",
    "Attachment links",
    "Artifact hashes",
    "Freshness",
    "Secret-free display",
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
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
    "Mission Control may execute",
    "Mission Control may approve",
    "trusted-host promotion is implemented",
    "runtime importer is approved",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control display importer plan is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"display importer plan is missing phrase: {phrase}")
        for phrase in REQUIRED_VALIDATION_STAGES:
            if phrase not in text:
                failures.append(f"display importer plan is missing validation stage: {phrase}")
        for phrase in REQUIRED_DISPLAY_STATES:
            if phrase not in text:
                failures.append(f"display importer plan is missing display state: {phrase}")
        for phrase in REQUIRED_NON_GOALS:
            if phrase not in text:
                failures.append(f"display importer plan is missing non-goal: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"display importer plan contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control display importer plan is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("Mission Control display importer plan is missing from docs-site inputs")
    if "mission-control-display-importer-plan-check:" not in makefile:
        failures.append("Make target is missing: mission-control-display-importer-plan-check")
    if "mission-control-display-importer-plan-check" not in release_check_body:
        failures.append("mission-control-display-importer-plan-check missing from release-check")
    if "make mission-control-display-importer-plan-check" not in readme:
        failures.append("README is missing Mission Control display importer plan command")
    if "mission-control-display-importer-plan.md" not in readme:
        failures.append("README is missing Mission Control display importer plan doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "plan_doc": doc_rel,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display importer plan check",
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
