"""Validate the project.dependency.summary implementation decision boundary."""

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
    project_dependency_summary_implementation_plan_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DOC = ROOT / "docs/codex/v3-project-dependency-summary-implementation.md"
REQUIRED_DOC_PHRASES = [
    "project.dependency.summary",
    "bounded read-only runtime implementation",
    "adds one tool manifest",
    "approved_limited_read_only",
    "risk `read`",
    "category `project`",
    "workspace_id",
    "root",
    "manifest_kinds",
    "limit",
    "no shell",
    "no package-manager execution",
    "no registry or network access",
    "no recursive discovery",
    "no arbitrary manifest filenames",
    "no file contents",
    "no dependency names",
    "no package script names or values",
    "make project-dependency-summary-implementation-gate",
]
REQUIRED_SOURCE_PHRASES = [
    "_PROJECT_DEPENDENCY_SUMMARY_TOOL = \"project.dependency.summary\"",
    "def project_dependency_summary(self, arguments: JsonObject) -> JsonObject:",
    "_PROJECT_MANIFEST_ALLOWLIST",
    "_PROJECT_MANIFEST_MAX_LIMIT = 20",
    "_PROJECT_MANIFEST_MAX_TOTAL_BYTES",
    "\"dependency_names_included\": False",
    "\"package_script_values_included\": False",
    "\"registry_or_network_access_used\": False",
    "\"package_manager_execution_used\": False",
    "\"recursive_discovery_used\": False",
]
FORBIDDEN_DOC_PHRASES = [
    "broad filesystem access is approved",
    "package-manager execution is approved",
    "network access is approved",
    "dependency names are returned",
    "script values are returned",
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
    plan_gate = project_dependency_summary_implementation_plan_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"implementation-plan: {failure}" for failure in plan_gate["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    doc_path = repo_root / IMPLEMENTATION_DOC.relative_to(ROOT)
    if not doc_path.exists():
        failures.append("project.dependency.summary implementation decision doc is missing")
    else:
        lower = doc_path.read_text(encoding="utf-8").lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation decision doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lower:
                failures.append(f"implementation decision doc contains forbidden phrase: {phrase}")

    source_path = repo_root / "apps/api/src/ithildin_api/read_tools.py"
    source = source_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_SOURCE_PHRASES:
        if phrase not in source:
            failures.append(f"project dependency summary source is missing phrase: {phrase}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "project.dependency.summary",
        "implementation_status": "approved_limited_read_only",
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": False,
        "runtime_implemented": True,
        "deferred_boundaries_unchanged": no_new_powers.get("deferred_boundaries_unchanged"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.dependency.summary implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report['tool_count']}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"runtime_implemented: {str(report['runtime_implemented']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
