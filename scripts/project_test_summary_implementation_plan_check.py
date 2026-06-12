"""Validate the project.test.summary implementation-planning packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import project_test_summary_proposal_check, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
PLAN_DOC = ROOT / "docs/codex/capability-implementation-plans/project-test-summary.md"
REQUIRED_PHRASES = [
    "Status: implementation-planning only",
    "does not add a tool manifest",
    "Implementation state: blocked",
    "Future Manifest Sketch",
    "Proposed Input Contract",
    "additionalProperties: false",
    "Proposed Output Contract",
    "Filesystem Traversal Contract",
    "Category And Extension Allowlist",
    "Policy Fixture Plan",
    "Audit Evidence Plan",
    "UI And Policy Preview Plan",
    "Negative Transcript Plan",
    "Resource Limits",
    "Source Review And Implementation Decision Requirement",
    "count-only test metadata and allowlisted labels only",
    "no test file names",
    "no raw paths",
    "no raw recursive listing",
    "no file contents",
    "no test case names",
    "no dependency names",
    "no package names",
    "no package script names or values",
    "no coverage data",
    "no test execution",
    "no command output",
    "no package-manager execution",
    "no network access",
    "Actual implementation remains blocked",
]
FORBIDDEN_PHRASES = [
    "implementation is approved",
    "runtime behavior is added",
    "this planning sprint adds a manifest",
    "this planning sprint adds an executor",
    "this planning sprint adds mcp exposure",
    "file contents are returned",
    "raw recursive listing is returned",
    "raw paths are returned",
    "test execution is used",
    "package-manager execution is used",
    "network access is used",
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
    plan_path = repo_root / PLAN_DOC.relative_to(ROOT)
    if not plan_path.exists():
        return _report(["project.test.summary implementation plan is missing"], {})

    text = plan_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"implementation plan is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"implementation plan contains forbidden phrase: {phrase}")

    proposal = project_test_summary_proposal_check.build_report(repo_root)
    failures.extend(f"proposal check: {failure}" for failure in proposal["failures"])
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    return _report(
        failures,
        {
            "plan_path": PLAN_DOC.relative_to(ROOT).as_posix(),
            "proposal_valid": proposal["valid"],
            "tool_count": tool_surface.get("tool_count"),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.test.summary",
        "scope": "implementation_planning_only",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.test.summary implementation-plan check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.test.summary",
        "scope: implementation_planning_only",
        "implementation_allowed: false",
        "runtime_changes_allowed: false",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
