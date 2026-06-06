"""Validate Agent Run evidence readiness without adding runtime powers."""

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
    agent_run_evidence_export_check,
    agent_run_evidence_export_implementation_gate,
    agent_run_evidence_export_plan_check,
    agent_run_timeline_readiness,
    dashboard_evidence_checklist_check,
    incident_reconstruction_check,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GATE_DOC = ROOT / "docs/codex/agent-run-evidence-readiness-gate.md"
REQUIRED_GATE_PHRASES = [
    "Status: release-readiness gate",
    "does not add runtime behavior",
    "make agent-run-evidence-readiness",
    "agent-run-evidence-contract-check",
    "agent-run-evidence-export-check",
    "agent-run-evidence-export-plan-check",
    "agent-run-evidence-export-implementation-gate",
    "agent-run-timeline-readiness",
    "incident-reconstruction-check",
    "dashboard-evidence-checklist-check",
    "no-new-powers-guardrail",
    "tool-surface-invariant-gate",
    "tool count remains `13`",
    "run export runtime behavior is not allowed",
    "secret-free",
    "design-only",
    "mediated actions only",
    "SIEM custody",
    "compliance automation",
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

    contract = agent_run_evidence_contract_check.build_report(repo_root)
    export = agent_run_evidence_export_check.build_report(repo_root)
    export_plan = agent_run_evidence_export_plan_check.build_report(repo_root)
    export_implementation = agent_run_evidence_export_implementation_gate.build_report(repo_root)
    timeline = agent_run_timeline_readiness.build_report(repo_root)
    reconstruction = incident_reconstruction_check.build_report(repo_root)
    dashboard = dashboard_evidence_checklist_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    failures.extend(f"agent-run-evidence-contract: {failure}" for failure in contract["failures"])
    failures.extend(f"agent-run-evidence-export: {failure}" for failure in export["failures"])
    failures.extend(
        f"agent-run-evidence-export-plan: {failure}" for failure in export_plan["failures"]
    )
    failures.extend(
        f"agent-run-evidence-export-implementation: {failure}"
        for failure in export_implementation["failures"]
    )
    failures.extend(f"agent-run-timeline: {failure}" for failure in timeline["failures"])
    failures.extend(f"incident-reconstruction: {failure}" for failure in reconstruction["failures"])
    failures.extend(f"dashboard-evidence: {failure}" for failure in dashboard["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(_validate_doc(repo_root=repo_root, docs_site=docs_site, readme=readme))

    if "agent-run-evidence-readiness:" not in makefile:
        failures.append("Make target is missing: agent-run-evidence-readiness")
    if "agent-run-evidence-readiness" not in release_check_body:
        failures.append("agent-run-evidence-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "agent_run_evidence_contract_valid": contract["valid"],
        "agent_run_evidence_export_valid": export["valid"],
        "agent_run_evidence_export_plan_valid": export_plan["valid"],
        "agent_run_evidence_export_implementation_valid": export_implementation["valid"],
        "agent_run_timeline_readiness_valid": timeline["valid"],
        "incident_reconstruction_valid": reconstruction["valid"],
        "dashboard_evidence_checklist_valid": dashboard["valid"],
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_export_runtime_behavior_allowed": False,
    }


def _validate_doc(*, repo_root: Path, docs_site: str, readme: str) -> list[str]:
    failures: list[str] = []
    rel_path = GATE_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append("Agent Run evidence readiness gate doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_GATE_PHRASES:
        if phrase not in text:
            failures.append(f"Agent Run evidence readiness gate is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Agent Run evidence readiness gate is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Agent Run evidence readiness gate is missing from docs-site inputs")
    if "agent-run-evidence-readiness-gate.md" not in readme:
        failures.append("README is missing agent-run-evidence-readiness-gate.md")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Agent Run evidence readiness gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "run_export_runtime_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
