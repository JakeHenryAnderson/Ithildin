"""Validate the read-only project intelligence product slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    next_capability_readiness,
    no_new_powers_guardrail,
    read_only_capability_inventory_gate,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/read-only-project-intelligence.md"
APPROVED_TOOLS = [
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "project.manifest.summary",
    "project.dependency.summary",
    "project.structure.summary",
    "project.test.summary",
]
REQUIRED_DOC_PHRASES = [
    "Status: consolidated local-preview product slice",
    "does not add runtime behavior",
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "project.manifest.summary",
    "project.dependency.summary",
    "project.structure.summary",
    "project.test.summary",
    "Tool count: `16`",
    "Next candidate: not selected",
    "Next candidate status: pending selection",
    "Broader capability expansion remains blocked",
    "New powerful tool classes remain blocked",
    "No file contents",
    "No dependency names",
    "no package-manager execution",
    "no registry/network access",
    "policy preview/runtime parity",
    "make read-only-project-intelligence",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    inventory = read_only_capability_inventory_gate.build_report(repo_root)
    next_capability = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"inventory: {failure}" for failure in inventory["failures"])
    failures.extend(f"next-capability: {failure}" for failure in next_capability["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    if not doc_path.exists():
        failures.append("read-only project intelligence doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in text:
            failures.append(f"read-only project intelligence doc is missing phrase: {phrase}")
    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("read-only project intelligence doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("read-only project intelligence doc is missing from docs-site inputs")
    if doc_rel not in readme:
        failures.append("read-only project intelligence doc is missing from README")
    if "read-only-project-intelligence:" not in makefile:
        failures.append("Make target is missing: read-only-project-intelligence")
    if "read-only-project-intelligence" not in release_check_body:
        failures.append("read-only-project-intelligence is missing from release-check")

    tool_names = set(tool_surface.get("tool_names", []))
    for tool in APPROVED_TOOLS:
        if tool not in tool_names:
            failures.append(f"approved project intelligence tool is missing: {tool}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "approved_tool_count": len(APPROVED_TOOLS),
        "approved_tools": APPROVED_TOOLS,
        "next_candidate": next_capability.get("next_candidate"),
        "broader_capability_expansion_allowed": False,
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin read-only project intelligence readiness",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"approved_tool_count: {report['approved_tool_count']}",
        f"next_candidate: {report.get('next_candidate', 'unknown')}",
        "broader_capability_expansion_allowed: false",
        "new_power_classes_allowed: false",
        "runtime_changes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
