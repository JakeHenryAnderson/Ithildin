"""Validate the v3 next read-only capability candidate evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import read_only_capability_inventory_gate

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/v3-project-dependency-summary-selection.md"
REQUIRED_PHRASES = [
    "Status: design-only candidate selection",
    "project.dependency.summary",
    "Implementation remains blocked",
    "does not add a manifest",
    "does not add an executor",
    "does not add policy rules",
    "does not add MCP exposure",
    "does not add API behavior",
    "does not add UI behavior",
    "does not add runtime behavior",
    "count-only",
    "Tool count remains `15`",
    "no file contents",
    "no package script values",
    "no dependency names",
    "no registry or network access",
    "no shell",
    "make project-dependency-summary-proposal-check",
    "explicit implementation decision",
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
    path = repo_root / DOC_PATH.relative_to(ROOT)
    if not path.exists():
        failures.append("v3 project.dependency.summary selection doc is missing")
        text = ""
    else:
        text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"candidate selection is missing phrase: {phrase}")

    inventory = read_only_capability_inventory_gate.build_report(repo_root)
    failures.extend(f"inventory: {failure}" for failure in inventory["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "candidate": "project.dependency.summary",
        "candidate_status": "design_only_selected",
        "implementation_allowed": False,
        "tool_count": inventory.get("tool_count"),
        "approved_read_only_capabilities": inventory.get("capability_count"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v3 next capability candidate check",
        f"valid: {str(report['valid']).lower()}",
        f"candidate: {report['candidate']}",
        f"candidate_status: {report['candidate_status']}",
        "implementation_allowed: false",
        f"tool_count: {report.get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
