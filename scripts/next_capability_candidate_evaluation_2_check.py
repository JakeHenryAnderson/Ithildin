"""Validate the v3 next capability candidate evaluation 2 planning doc."""

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
DOC_PATH = ROOT / "docs/codex/v3-next-capability-candidate-evaluation-2.md"
REQUIRED_PHRASES = [
    "Status: planning-only candidate evaluation",
    "does not add a tool manifest",
    "does not add an executor",
    "does not add policy rules",
    "does not add MCP exposure",
    "does not add API behavior",
    "does not add UI behavior",
    "does not add runtime behavior",
    "project.release.summary",
    "project.license.summary",
    "project.ownership.summary",
    "tool count remains `21`",
    "next candidate: `not selected`",
    "Further manager review is required",
    "Intended Safe Value",
    "Proposed Resource Type",
    "Safe Output Labels/Counts Only",
    "Strict Non-Goals",
    "Sensitive Metadata Risks",
    "Policy/Audit Evidence Expectations",
    "Negative Cases",
    "Source-Review Requirement",
    "Deferred",
]
FORBIDDEN_PHRASES = [
    "implementation allowed",
    "runtime behavior is added",
    "add a tool manifest now",
    "add an executor now",
    "add policy rules now",
    "expose through MCP now",
    "approved for implementation",
    "selected candidate",
    "go-live",
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
    doc_path = repo_root / DOC_PATH.relative_to(ROOT)
    if not doc_path.exists():
        failures.append("candidate evaluation doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")

    lower = " ".join(text.split()).lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"evaluation doc is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"evaluation doc contains forbidden phrase: {phrase}")

    inventory = read_only_capability_inventory_gate.build_report(repo_root)
    failures.extend(f"inventory: {failure}" for failure in inventory["failures"])

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_docs = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    index = (repo_root / "docs/codex/review-docs-index.md").read_text(encoding="utf-8")

    if "make next-capability-candidate-evaluation-2-check" not in readme:
        failures.append("README is missing the new planning gate command")
    if "next-capability-candidate-evaluation-2-check:" not in makefile:
        failures.append("Makefile is missing the new planning gate target")
    if "next-capability-candidate-evaluation-2-check" not in release_check_body:
        failures.append("release-check is missing the new planning gate target")
    if DOC_PATH.relative_to(ROOT).as_posix() not in docs_site:
        failures.append("docs-site inputs are missing the new planning gate doc")
    if DOC_PATH.relative_to(ROOT).as_posix() not in review_docs:
        failures.append("review docs metadata is missing the new planning gate doc")
    if "v3 Next Capability Candidate Evaluation 2" not in index:
        failures.append("review docs index is missing the new planning gate doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": inventory.get("tool_count"),
        "next_candidate": "not selected",
        "manager_review_required": True,
        "selection_status": "deferred",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v3 next capability candidate evaluation 2 check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"next_candidate: {report['next_candidate']}",
        "manager_review_required: true",
        f"selection_status: {report['selection_status']}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
