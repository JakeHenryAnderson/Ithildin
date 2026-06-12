"""Validate the project.structure.summary design-only capability proposal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_DOC = ROOT / "docs/codex/capability-proposals/project-structure-summary.md"
SELECTION_DOC = ROOT / "docs/codex/v3-project-structure-summary-selection.md"
REQUIRED_PHRASES = [
    "Status: design-only proposal",
    "does not add a tool manifest",
    "does not add an executor",
    "does not add policy rules",
    "does not add MCP exposure",
    "does not add API behavior",
    "does not add UI behavior",
    "does not add runtime behavior",
    "project.structure.summary",
    "structural counts and allowlisted labels only",
    "no file contents",
    "no raw recursive listing",
    "no raw sensitive paths",
    "no stable cross-response path identifiers",
    "no dependency names",
    "no package names",
    "no package script names or values",
    "no code search",
    "no package-manager execution",
    "no registry or network access",
    "no shell",
    "additionalProperties: false",
    "Policy And Audit Evidence",
    "UI/review evidence",
    "Negative Transcripts",
    "Resource limits",
    "Accepted-risk impact",
    "No-new-powers analysis",
    "External/source Review Requirement",
]
SELECTION_PHRASES = [
    "Status: design-only candidate selection",
    "project.structure.summary",
    "tool count remains `16`",
    "Implementation remains blocked",
    "make project-structure-summary-proposal-check",
    "make project-structure-summary-design-review-packet",
]
FORBIDDEN_PHRASES = [
    "implementation allowed",
    "add a tool manifest now",
    "add an executor now",
    "expose through MCP now",
    "return file contents",
    "return raw recursive listing",
    "run package managers",
    "contact registries",
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
    proposal_path = repo_root / PROPOSAL_DOC.relative_to(ROOT)
    if not proposal_path.exists():
        return _report(["project.structure.summary proposal is missing"], {})

    text = proposal_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"proposal is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"proposal contains forbidden implementation phrase: {phrase}")

    selection_path = repo_root / SELECTION_DOC.relative_to(ROOT)
    if not selection_path.exists():
        failures.append("project.structure.summary selection doc is missing")
    else:
        selection_text = selection_path.read_text(encoding="utf-8")
        for phrase in SELECTION_PHRASES:
            if phrase not in selection_text:
                failures.append(f"selection doc is missing phrase: {phrase}")

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    return _report(
        failures,
        {
            "proposal_path": PROPOSAL_DOC.relative_to(ROOT).as_posix(),
            "selection_path": SELECTION_DOC.relative_to(ROOT).as_posix(),
            "tool_count": tool_surface.get("tool_count"),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.structure.summary",
        "scope": "design_only",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.structure.summary proposal check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.structure.summary",
        "scope: design_only",
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
