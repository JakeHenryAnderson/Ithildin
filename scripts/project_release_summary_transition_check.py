"""Validate the project.release.summary implementation-transition handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import project_release_summary_implementation_gate, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/project-release-summary-implementation-transition.md"

REQUIRED_PHRASES = [
    "Status: implementation transition completed.",
    "canonical handoff",
    "current tool count: `22`",
    "current runtime status: implemented",
    "implementation-aware guard active",
    "Add exactly one bounded read-only manifest for `project.release.summary`.",
    "Add exactly one bounded read-only executor path.",
    "Manifest lock updated intentionally.",
    "resource type `project_release`",
    "Run `make release-check` and `make review-candidate`",
    "local workspace only and read-only",
    "count-only and label-only",
    "no release names",
    "no version strings that reveal cadence",
    "no raw paths",
    "no file contents",
    "no Git execution",
    "no package-manager execution",
    "no registry or network access",
    "no new powerful tool class",
    "Low implementers may help with fixture inventory or docs-only scans.",
    "Runtime implementation completed as main-manager work",
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
    doc_rel = DOC_PATH.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    implementation_gate = project_release_summary_implementation_gate.build_report(repo_root)
    failures.extend(
        f"implementation-gate: {failure}" for failure in implementation_gate["failures"]
    )
    if implementation_gate.get("runtime_implemented") is not True:
        failures.append("transition check expects runtime_implemented=true")
    if implementation_gate.get("future_runtime_implementation_allowed") is not False:
        failures.append("transition check expects future runtime implementation to be closed")

    if not doc_path.exists():
        failures.append("project.release.summary implementation transition doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"transition doc is missing phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("transition doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("transition doc is missing from docs-site inputs")
    if "project-release-summary-transition-check:" not in makefile:
        failures.append("Make target is missing: project-release-summary-transition-check")
    if "project-release-summary-transition-check" not in release_check_body:
        failures.append("project-release-summary-transition-check is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "project.release.summary",
        "transition_status": "manager_owned_implementation_completed",
        "tool_count": 23,
        "runtime_implemented": True,
        "runtime_changes_allowed_now": True,
        "future_runtime_implementation_allowed": False,
        "low_implementer_runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.release.summary transition check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"transition_status: {report['transition_status']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_implemented: {str(report['runtime_implemented']).lower()}",
        f"runtime_changes_allowed_now: {str(report['runtime_changes_allowed_now']).lower()}",
        "future_runtime_implementation_allowed: "
        f"{str(report['future_runtime_implementation_allowed']).lower()}",
        "low_implementer_runtime_changes_allowed: "
        f"{str(report['low_implementer_runtime_changes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
