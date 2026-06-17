"""Validate the project.release.summary source-review handoff wiring."""

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
    project_release_summary_implementation_gate,
    project_release_summary_preimplementation_check,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVIEW_DOC = ROOT / "docs/codex/v3-project-release-summary-source-review.md"
NEGATIVE_TRANSCRIPTS_DOC = ROOT / "docs/codex/project-release-summary-negative-transcripts.md"
IMPLEMENTATION_BOUNDARY_DOC = ROOT / "docs/codex/v3-project-release-summary-implementation.md"
FIXTURE_PLAN_DOC = ROOT / "docs/codex/project-release-summary-fixture-plan.md"
REQUIRED_SCENARIOS = [
    "traversal denied",
    "absolute root denied",
    "hidden/sensitive path skipped",
    ".git skipped",
    "symlink skipped",
    "hardlink skipped",
    "binary/NUL skipped",
    "unsupported encoding skipped",
    "depth limit truncation",
    "item limit truncation",
    "release names suppressed",
    "version strings suppressed",
    "changelog contents suppressed",
    "tag names suppressed",
    "branch names suppressed",
    "command/script values suppressed",
    "unauthorized principal denied",
]
STRICT_NON_LEAK_PHRASES = [
    "no release names",
    "no version strings",
    "no changelog contents",
    "no tag names",
    "no branch names",
    "no raw file names",
    "no raw paths",
    "no file contents",
    "no package names",
    "no dependency names",
    "no author/maintainer names",
    "no email addresses",
    "no command/script values",
    "no environment names/values",
    "no registry URLs",
    "no shell/Git/package-manager/CI output",
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
    preimplementation = project_release_summary_preimplementation_check.build_report(repo_root)
    implementation_gate = project_release_summary_implementation_gate.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    failures.extend(f"preimplementation: {failure}" for failure in preimplementation["failures"])
    failures.extend(
        f"implementation-gate: {failure}" for failure in implementation_gate["failures"]
    )
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    source_review_path = repo_root / SOURCE_REVIEW_DOC.relative_to(ROOT)
    negative_plan_path = repo_root / NEGATIVE_TRANSCRIPTS_DOC.relative_to(ROOT)
    boundary_path = repo_root / IMPLEMENTATION_BOUNDARY_DOC.relative_to(ROOT)
    fixture_path = repo_root / FIXTURE_PLAN_DOC.relative_to(ROOT)

    if not source_review_path.exists():
        failures.append("implemented source-review handoff doc is missing")
    else:
        source_text = source_review_path.read_text(encoding="utf-8")
        for phrase in [
            "Status: source-review handoff for implemented bounded read-only lane",
            "project.release.summary",
            "Resource type: `project_release`",
            "Current tool count remains `23`",
            "Runtime implementation is present",
            "Finding namespace: `EXT-RELEASE-SUMMARY-###`",
            "manifest/schema shape",
            "workspace traversal and path safety",
            "category allowlist and skipped-count behavior",
            "policy preview/runtime resource parity",
            "MCP governed path",
            "audit metadata count-only behavior",
            "no-new-powers evidence",
            "This lane remains source-review pending until a focused reviewer disposition exists",
        ]:
            if phrase not in source_text:
                failures.append(f"source-review handoff doc is missing phrase: {phrase}")

    if not negative_plan_path.exists():
        failures.append("negative-transcript plan doc is missing")
    else:
        negative_text = negative_plan_path.read_text(encoding="utf-8")
        for scenario in REQUIRED_SCENARIOS:
            if scenario not in negative_text:
                failures.append(f"negative-transcript plan is missing scenario: {scenario}")
        for phrase in STRICT_NON_LEAK_PHRASES:
            if phrase not in negative_text:
                failures.append(
                    f"negative-transcript plan is missing strict non-leak phrase: {phrase}"
                )

    if not boundary_path.exists():
        failures.append("implementation boundary doc is missing")
    if not fixture_path.exists():
        failures.append("fixture plan doc is missing")

    if not (repo_root / "tool-manifests/project-release-summary.yaml").exists():
        failures.append("project.release.summary manifest is missing")

    if implementation_gate.get("runtime_implemented") is not True:
        failures.append("implementation gate must report runtime_implemented: true")
    if implementation_gate.get("future_runtime_implementation_allowed") is not False:
        failures.append(
            "implementation gate must close future_runtime_implementation_allowed"
        )
    if implementation_gate.get("tool_count") != 23:
        failures.append("implementation gate tool count is not 23")
    if tool_surface.get("tool_count") != 23:
        failures.append("tool surface tool count is not 23")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers guardrail allows new power classes")

    review_docs_text = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    docs_site_text = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    for doc in [
        "docs/codex/v3-project-release-summary-source-review.md",
        "docs/codex/project-release-summary-negative-transcripts.md",
    ]:
        if doc not in review_docs.REVIEW_DOCS:
            failures.append(f"review docs registry is missing {doc}")
        if doc not in review_docs_text:
            failures.append(f"review docs source is missing {doc}")
        if doc not in docs_site_text:
            failures.append(f"docs site source is missing {doc}")

    if "project-release-summary-review-handoff-check:" not in makefile:
        failures.append("Makefile is missing project-release-summary-review-handoff-check")
    if "project-release-summary-source-review-bundle:" not in makefile:
        failures.append("Makefile is missing project-release-summary-source-review-bundle")
    if "project-release-summary-review-handoff-check" not in release_check_body:
        failures.append("release-check is missing project-release-summary-review-handoff-check")

    if not (repo_root / "tool-manifests.lock.json").exists():
        failures.append("tool-manifests.lock.json is missing")
    else:
        lockfile = (repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8")
        if "project-release-summary" not in lockfile:
            failures.append("project.release.summary manifest lock entry is missing")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.release.summary",
        "scope": "implemented_source_review_handoff",
        "implementation_allowed": True,
        "runtime_changes_allowed": True,
        "runtime_implemented": implementation_gate.get("runtime_implemented"),
        "future_runtime_implementation_allowed": implementation_gate.get(
            "future_runtime_implementation_allowed"
        ),
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "evidence": {
            "source_review_doc": SOURCE_REVIEW_DOC.relative_to(ROOT).as_posix(),
            "negative_transcripts_doc": NEGATIVE_TRANSCRIPTS_DOC.relative_to(ROOT).as_posix(),
            "implementation_boundary_doc": IMPLEMENTATION_BOUNDARY_DOC.relative_to(ROOT).as_posix(),
            "fixture_plan_doc": FIXTURE_PLAN_DOC.relative_to(ROOT).as_posix(),
            "preimplementation": preimplementation,
            "implementation_gate": implementation_gate,
            "tool_surface": tool_surface,
            "no_new_powers": no_new_powers,
        },
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.release.summary review-handoff check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.release.summary",
        "scope: implemented_source_review_handoff",
        "implementation_allowed: true",
        "runtime_changes_allowed: true",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"runtime_implemented: {str(report.get('runtime_implemented')).lower()}",
        "future_runtime_implementation_allowed: "
        f"{str(report.get('future_runtime_implementation_allowed')).lower()}",
        f"new_power_classes_allowed: {str(report.get('new_power_classes_allowed')).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
