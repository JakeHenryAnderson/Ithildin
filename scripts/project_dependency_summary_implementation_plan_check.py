"""Validate the project.dependency.summary implementation-planning packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import project_dependency_summary_proposal_check, v09_design_only_gate

ROOT = Path(__file__).resolve().parents[1]
PLAN_DOC = ROOT / "docs/codex/capability-implementation-plans/project-dependency-summary.md"
REQUIRED_PHRASES = [
    "Status: implementation-planning only",
    "does not add a tool manifest",
    "Implementation state: blocked",
    "Future Manifest Sketch",
    "Proposed Input Contract",
    "additionalProperties: false",
    "Proposed Output Contract",
    "Parser Contract Checklist",
    "Policy Fixture Plan",
    "Audit Evidence Plan",
    "UI And Policy Preview Plan",
    "Negative Transcript Plan",
    "Resource Limits",
    "Source Review And Implementation Decision Requirement",
    "no file contents",
    "no dependency names",
    "no package names",
    "no package version constraints",
    "no package script names or values",
    "no lockfile contents",
    "no registry URLs",
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
    "dependency names are returned",
    "script values are returned",
    "registry access is used",
    "network access is used",
    "package-manager execution is used",
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
        return _report(["project.dependency.summary implementation plan is missing"], {})

    text = plan_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"implementation plan is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"implementation plan contains forbidden phrase: {phrase}")

    proposal = project_dependency_summary_proposal_check.build_report(repo_root)
    design_gate = v09_design_only_gate.build_report(repo_root)
    failures.extend(f"proposal check: {failure}" for failure in proposal["failures"])
    failures.extend(f"v0.9 design-only gate: {failure}" for failure in design_gate["failures"])

    return _report(
        failures,
        {
            "plan_path": PLAN_DOC.relative_to(ROOT).as_posix(),
            "proposal_valid": proposal["valid"],
            "v09_baseline_commit": design_gate["evidence"].get("v09_baseline_commit"),
            "tool_count": design_gate["evidence"].get("tool_count"),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.dependency.summary",
        "scope": "implementation_planning_only",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.dependency.summary implementation-plan check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.dependency.summary",
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
