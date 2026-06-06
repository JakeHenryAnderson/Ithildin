"""Validate the operator action states design and wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/operator-action-states-design.md"
REQUIRED_PHRASES = [
    "Status: design-only proposal",
    "does not add runtime behavior",
    "pause",
    "abort",
    "kill",
    "disable",
    "repair",
    "replay",
    "`active`",
    "`paused`",
    "`aborting`",
    "`aborted`",
    "`disabled`",
    "`recovery_required`",
    "`failed_closed`",
    "`completed`",
    "external/source review before implementation",
    "does not",
    "control containers",
    "add API or MCP actions",
    "make operator-action-states-check",
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
    rel_path = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs/codex/agent-run-observability-and-sandbox-roadmap.md").read_text(
        encoding="utf-8"
    )

    if not doc_path.exists():
        failures.append("Operator action states design doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"Operator action states design is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Operator action states design is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Operator action states design is missing from docs-site inputs")
    if "operator-action-states-check:" not in makefile:
        failures.append("Make target is missing: operator-action-states-check")
    if "make operator-action-states-check" not in readme:
        failures.append("README is missing operator-action-states-check")
    if "operator-action-states-design.md" not in roadmap:
        failures.append("Agent Run roadmap is missing the operator action states design link")

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "design": rel_path,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "tool_count": no_new_powers.get("tool_count"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin operator action states design check",
        f"valid: {str(report['valid']).lower()}",
        f"design: {report['design']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "run_control_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
