"""Validate the read-only Agent Run operations dashboard surface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = ROOT / "docs/codex/agent-run-operations-readiness-gate.md"
REQUIRED_DOC_PHRASES = [
    "Status: release-readiness gate",
    "read-only operations dashboard",
    "GET /runs",
    "principal_id",
    "workspace_id",
    "status",
    "tool_name",
    "session_id",
    "summary",
    "Export Run Evidence",
    "no run controls",
    "no sandbox orchestration",
    "no SIEM adapters",
    "tool count remains `24`",
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
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    api = (repo_root / "apps/api/src/ithildin_api/app.py").read_text(encoding="utf-8")
    agent_runs = (repo_root / "apps/api/src/ithildin_api/agent_runs.py").read_text(
        encoding="utf-8"
    )
    ui = (repo_root / "apps/ui/src/App.tsx").read_text(encoding="utf-8")
    ui_tests = (repo_root / "apps/ui/src/App.test.tsx").read_text(encoding="utf-8")
    api_tests = (repo_root / "tests/test_api_service.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    for phrase in [
        "principal_id",
        "workspace_id",
        "status",
        "tool_name",
        "session_id",
        "unsupported query parameter",
        "invalid filter value",
        "agent_run_store.query_runs",
    ]:
        if phrase not in api:
            failures.append(f"API route is missing phrase: {phrase}")
    for phrase in ["class AgentRunFilters", "def query_runs", '"summary"', "_runs_summary"]:
        if phrase not in agent_runs:
            failures.append(f"AgentRunStore is missing phrase: {phrase}")
    for phrase in [
        "run-filter-bar",
        "RunSummary",
        "runListPath",
        "timelineStatus",
        "timelineWarnings",
        "Export Run Evidence",
    ]:
        if phrase not in ui:
            failures.append(f"Review console is missing phrase: {phrase}")
    for phrase in [
        "filters agent runs with a bounded authenticated query",
        "principal_id=agent%3Amcp-local",
        "summary",
    ]:
        if phrase not in ui_tests:
            failures.append(f"UI tests are missing phrase: {phrase}")
    for phrase in [
        "test_run_list_filters_and_denies_bad_queries_safely",
        "unsupported query parameter",
        "invalid limit",
        "invalid filter value",
    ]:
        if phrase not in api_tests:
            failures.append(f"API tests are missing phrase: {phrase}")

    failures.extend(_validate_doc(repo_root=repo_root, docs_site=docs_site, readme=readme))
    if "agent-run-operations-readiness:" not in makefile:
        failures.append("Make target is missing: agent-run-operations-readiness")
    if "agent-run-operations-readiness" not in release_check_body:
        failures.append("agent-run-operations-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def _validate_doc(*, repo_root: Path, docs_site: str, readme: str) -> list[str]:
    failures: list[str] = []
    rel_path = GATE_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append("Agent Run operations readiness gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in text:
            failures.append(f"Agent Run operations readiness gate is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Agent Run operations readiness gate is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Agent Run operations readiness gate is missing from docs-site inputs")
    if "agent-run-operations-readiness-gate.md" not in readme:
        failures.append("README is missing agent-run-operations-readiness-gate.md")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Agent Run operations readiness gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "run_control_behavior_allowed: false",
        "siem_adapter_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
