"""Validate Agent Run timeline readiness without adding runtime powers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    agent_run_evidence_contract_check,
    dashboard_evidence_checklist_check,
    no_new_powers_guardrail,
    operator_action_states_check,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = ROOT / "docs/codex/agent-run-timeline-readiness-gate.md"
REQUIRED_GATE_PHRASES = [
    "Status: release-readiness gate",
    "does not add runtime behavior",
    "make agent-run-timeline-readiness",
    "agent-run-evidence-contract-check",
    "agent-run-timeline-packet",
    "operator-action-states-check",
    "dashboard-evidence-checklist-check",
    "AgentRunStore",
    "GET /runs",
    "GET /runs/{run_id}",
    "governed-call audit correlation",
    "approval correlation evidence",
    "review-console Agent Runs panel",
    "no-new-powers-guardrail",
    "tool-surface-invariant-gate",
    "tool count remains `14`",
    "admin-only and read-only",
    "secret-free",
    "design-only",
    "no new powerful tool classes",
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

    evidence = agent_run_evidence_contract_check.build_report(repo_root)
    operator_actions = operator_action_states_check.build_report(repo_root)
    dashboard = dashboard_evidence_checklist_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"agent-run-evidence: {failure}" for failure in evidence["failures"])
    failures.extend(
        f"operator-action-states: {failure}" for failure in operator_actions["failures"]
    )
    failures.extend(f"dashboard-evidence: {failure}" for failure in dashboard["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(_validate_doc(repo_root=repo_root, docs_site=docs_site, readme=readme))
    failures.extend(_validate_source_and_tests(repo_root))

    if "agent-run-timeline-readiness:" not in makefile:
        failures.append("Make target is missing: agent-run-timeline-readiness")
    if "agent-run-timeline-readiness" not in release_check_body:
        failures.append("agent-run-timeline-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "agent_run_evidence_contract_valid": evidence["valid"],
        "operator_action_states_valid": operator_actions["valid"],
        "dashboard_evidence_checklist_valid": dashboard["valid"],
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
    }


def _validate_doc(*, repo_root: Path, docs_site: str, readme: str) -> list[str]:
    failures: list[str] = []
    rel_path = GATE_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append("Agent Run timeline readiness gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_GATE_PHRASES:
        if phrase not in text:
            failures.append(f"Agent Run timeline readiness gate is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Agent Run timeline readiness gate is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Agent Run timeline readiness gate is missing from docs-site inputs")
    if "agent-run-timeline-readiness-gate.md" not in readme:
        failures.append("README is missing agent-run-timeline-readiness-gate.md")
    return failures


def _validate_source_and_tests(repo_root: Path) -> list[str]:
    failures: list[str] = []
    agent_runs = (repo_root / "apps/api/src/ithildin_api/agent_runs.py").read_text(
        encoding="utf-8"
    )
    app = (repo_root / "apps/api/src/ithildin_api/app.py").read_text(encoding="utf-8")
    tool_calls = (repo_root / "apps/api/src/ithildin_api/tool_calls.py").read_text(
        encoding="utf-8"
    )
    api_tests = (repo_root / "tests/test_api_service.py").read_text(encoding="utf-8")
    governed_tests = (repo_root / "tests/test_governed_tool_calls.py").read_text(
        encoding="utf-8"
    )
    ui_tests = (repo_root / "apps/ui/src/App.test.tsx").read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/agent_run_timeline_packet.py").read_text(
        encoding="utf-8"
    )

    required_sources = [
        ("agent run store", "class AgentRunStore", agent_runs),
        ("run list endpoint", '@api.get("/runs"', app),
        ("run detail endpoint", '@api.get("/runs/{run_id}"', app),
        ("agent run metadata", "_agent_run_metadata", tool_calls),
        ("agent run metadata merge", "_metadata_with_agent_run", tool_calls),
        ("agent session audit", "AuditEventType.AGENT_SESSION_STARTED", tool_calls),
        ("API run tests", "/runs", api_tests),
        ("governed-call run tests", "track_runs=True", governed_tests),
        ("UI Agent Runs tests", "Agent Runs", ui_tests),
        ("packet script", "EXT-RUN-###", packet_script),
    ]
    for label, phrase, text in required_sources:
        if phrase not in text:
            failures.append(f"missing Agent Run timeline evidence: {label}")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Agent Run timeline readiness gate",
        f"valid: {str(report['valid']).lower()}",
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
