"""Validate the project.release.summary implementation decision boundary."""

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
    project_release_summary_implementation_plan_check,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DOC = ROOT / "docs/codex/v3-project-release-summary-implementation.md"
REQUIRED_DOC_PHRASES = [
    "project.release.summary",
    "approved limited read-only implementation boundary",
    "runtime not yet implemented",
    "tool count remains `21`",
    "tool name: `project.release.summary`",
    "risk: `read`",
    "category: `project`",
    "proposed resource type: `project_release`",
    "closed object",
    "workspace_id",
    "root",
    "max_depth",
    "limit",
    "count-only release posture labels",
    "skipped counts",
    "limit metadata",
    "output-policy flags",
    "local workspace only and read-only",
    "policy preview/runtime resource parity",
    "no release names",
    "no version strings that reveal cadence",
    "no changelog contents",
    "no tag names",
    "no branch names",
    "no raw paths",
    "no file contents",
    "no package names",
    "no dependency names",
    "no author or maintainer names",
    "no shell",
    "no Git execution",
    "no package-manager execution",
    "no CI execution",
    "no registry or network access",
    "no deployment-readiness claims",
    "no legal claims",
    "no compliance claims",
    "no broad recursive listing",
    "no new powerful tool class",
    "Implementation state: blocked in this sprint",
    "Current gate behavior: preimplementation guard remains active",
    "low implementer while this gate is active",
]
FORBIDDEN_DOC_PHRASES = [
    "runtime is implemented",
    "runtime changes are allowed",
    "broad recursive listing is approved",
    "package-manager execution is approved",
    "network access is approved",
    "ci execution is approved",
    "release names are returned",
    "raw paths are returned",
    "file contents are returned",
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
    plan_gate = project_release_summary_implementation_plan_check.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"implementation-plan: {failure}" for failure in plan_gate["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    doc_path = repo_root / IMPLEMENTATION_DOC.relative_to(ROOT)
    if not doc_path.exists():
        failures.append("project.release.summary implementation decision doc is missing")
    else:
        lower = doc_path.read_text(encoding="utf-8").lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation decision doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_DOC_PHRASES:
            if phrase.lower() in lower:
                failures.append(f"implementation decision doc contains forbidden phrase: {phrase}")

    manifest_path = repo_root / "tool-manifests/project-release-summary.yaml"
    manifest_lock = (repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8")
    runtime_source = (repo_root / "apps/api/src/ithildin_api/read_tools.py").read_text(
        encoding="utf-8"
    )
    if manifest_path.exists():
        failures.append("project.release.summary manifest already exists")
    if "project-release-summary" in manifest_lock:
        failures.append("project.release.summary manifest lock was updated")
    if (
        "def project_release_summary(" in runtime_source
        or "_validate_project_release_summary" in runtime_source
    ):
        failures.append("project.release.summary runtime implementation already exists")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "project.release.summary",
        "implementation_status": "approved_limited_read_only",
        "risk": "read",
        "category": "project",
        "proposed_resource_type": "project_release",
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
        "runtime_changes_allowed": False,
        "runtime_implemented": False,
        "future_runtime_implementation_allowed": True,
        "deferred_boundaries_unchanged": no_new_powers.get("deferred_boundaries_unchanged"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.release.summary implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"risk: {report['risk']}",
        f"category: {report['category']}",
        f"proposed_resource_type: {report['proposed_resource_type']}",
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
