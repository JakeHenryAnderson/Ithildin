"""Validate the Mission Control display integration proposal and wiring."""

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
DOC = ROOT / "docs/codex/mission-control-display-integration-proposal.md"

REQUIRED_PHRASES = [
    "Status: design-only proposal for the next enterprise-readiness runway step.",
    "Mission Control should be able to display Ithildin evidence",
    "file/import contract, not a live integration",
    "Hello World Mission Control Handoff",
    "Proposed Import Fields",
    "Proposed Display States",
    "Negative Cases",
    "Required Before Implementation",
    "Explicit Non-Goals",
    "Design-only planning may continue.",
    "Runtime implementation remains blocked",
]

REQUIRED_FIELD_GROUPS = [
    "Mission identity",
    "Agent/client",
    "Ithildin evidence",
    "Artifact evidence",
    "Boundary state",
    "Attachments",
]

REQUIRED_WARNINGS = [
    "Mission Control runtime behavior: `false`",
    "local model runtime behavior: `false`",
    "real VM/container started: `false`",
    "sandbox orchestration performed: `false`",
    "shell execution performed: `false`",
    "host promotion performed: `false`",
]

REQUIRED_NEGATIVE_CASES = [
    "missing local-preview warning state",
    "packet version mismatch",
    "mismatched artifact hash",
    "absolute host paths in display fields",
    "raw prompts, file contents, diffs, response bodies, secrets",
    "a packet claiming Mission Control execution",
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
        failures.append("Mission Control display integration proposal is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"proposal is missing phrase: {phrase}")
        for phrase in REQUIRED_FIELD_GROUPS:
            if phrase not in text:
                failures.append(f"proposal is missing field group: {phrase}")
        for phrase in REQUIRED_WARNINGS:
            if phrase not in text:
                failures.append(f"proposal is missing warning: {phrase}")
        for phrase in REQUIRED_NEGATIVE_CASES:
            if phrase not in text:
                failures.append(f"proposal is missing negative case: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"proposal contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control display proposal is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("Mission Control display proposal is missing from docs-site inputs")
    if "mission-control-display-integration-proposal-check:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-display-integration-proposal-check"
        )
    if "mission-control-display-integration-proposal-check" not in release_check_body:
        failures.append(
            "mission-control-display-integration-proposal-check missing from release-check"
        )
    if "make mission-control-display-integration-proposal-check" not in readme:
        failures.append("README is missing Mission Control display proposal command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal_doc": doc_rel,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_execution_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display integration proposal check",
        f"valid: {str(report['valid']).lower()}",
        f"proposal_doc: {report['proposal_doc']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_execution_allowed: "
        f"{str(report['mission_control_execution_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
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
