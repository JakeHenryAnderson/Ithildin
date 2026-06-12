"""Validate the project.docs.summary implementation decision boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    no_new_powers_guardrail,
    project_docs_summary_implementation_plan_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DOC = ROOT / "docs/codex/v3-project-docs-summary-implementation.md"
REQUIRED_DOC_PHRASES = [
    "project.docs.summary",
    "approved_limited_read_only runtime implementation",
    "add one tool manifest",
    "one executor dispatch path",
    "runtime behavior is bounded read-only",
    "risk `read`",
    "category `project`",
    "workspace_id",
    "root",
    "max_depth",
    "limit",
    "include_categories",
    "count-only documentation metadata and allowlisted labels only",
    "no documentation file names",
    "no raw paths",
    "no raw recursive listing",
    "no file contents",
    "no documentation headings",
    "no dependency names",
    "no package names",
    "no package script names or values",
    "no coverage data",
    "no documentation build execution",
    "no command output",
    "no shell",
    "no package-manager execution",
    "no registry/network access",
    "no broad filesystem writes",
    "project_docs",
    "make project-docs-summary-implementation-gate",
    "Broader capability expansion remains blocked",
]
FORBIDDEN_DOC_PHRASES = [
    "broad filesystem access is approved",
    "package-manager execution is approved",
    "documentation build execution is approved",
    "network access is approved",
    "file contents are returned",
    "raw recursive listing is returned",
    "raw paths are returned",
    "documentation file names are returned",
    "documentation headings are returned",
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
    plan_gate = project_docs_summary_implementation_plan_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"implementation-plan: {failure}" for failure in plan_gate["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    doc_path = repo_root / IMPLEMENTATION_DOC.relative_to(ROOT)
    if not doc_path.exists():
        failures.append("project.docs.summary implementation decision doc is missing")
    else:
        lower = doc_path.read_text(encoding="utf-8").lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation decision doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lower:
                failures.append(f"implementation decision doc contains forbidden phrase: {phrase}")

    manifest_exists = repo_root.joinpath("tool-manifests/project-docs-summary.yaml").exists()

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "project.docs.summary",
        "implementation_status": "approved_limited_read_only",
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": manifest_exists,
        "runtime_implemented": manifest_exists,
        "future_runtime_implementation_allowed": not manifest_exists,
        "deferred_boundaries_unchanged": no_new_powers.get("deferred_boundaries_unchanged"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.docs.summary implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report['tool_count']}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"runtime_implemented: {str(report['runtime_implemented']).lower()}",
        f"future_runtime_implementation_allowed: "
        f"{str(report['future_runtime_implementation_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
