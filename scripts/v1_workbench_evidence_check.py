"""Validate v1.0 workbench/evidence closure wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    agent_run_evidence_readiness,
    agent_run_operations_readiness,
    agent_run_timeline_readiness,
    demo_evidence_readiness,
    review_docs,
    tool_surface_invariant_gate,
    workbench_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-workbench-evidence-closure.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview workbench/evidence closure map.",
    "Operator Questions",
    "Current Workbench Surfaces",
    "Evidence Reading Order",
    "Evidence Commands",
    "Closure Criteria",
    "Non-Goals",
    "System Trust panel",
    "Agent Runs panel",
    "Approval review panel",
    "Audit surfaces",
    "locally signed evidence",
    "make agent-run-timeline-readiness",
    "make agent-run-evidence-readiness",
    "make agent-run-operations-readiness",
    "make workbench-readiness",
    "make demo-evidence-readiness",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
    "make negative-review-transcripts",
    "make workbench-evidence-packet",
    "make review-candidate",
    "packet redaction reports `findings: 0`",
    "mediated actions only",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    reports = {
        "agent_run_timeline": agent_run_timeline_readiness.build_report(repo_root),
        "agent_run_evidence": agent_run_evidence_readiness.build_report(repo_root),
        "agent_run_operations": agent_run_operations_readiness.build_report(repo_root),
        "workbench": workbench_readiness.build_report(repo_root),
        "demo_evidence": demo_evidence_readiness.build_report(repo_root),
        "tool_surface": tool_surface_invariant_gate.build_report(repo_root),
    }
    for name, report in reports.items():
        failures.extend(f"{name}: {failure}" for failure in report["failures"])

    if not doc_path.exists():
        failures.append("v1.0 workbench/evidence closure doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 workbench/evidence doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 workbench/evidence doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 workbench/evidence doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 workbench/evidence doc is missing from docs-site inputs")
    if "v1-workbench-evidence-check:" not in makefile:
        failures.append("Make target is missing: v1-workbench-evidence-check")
    if "v1-workbench-evidence-check" not in release_check_body:
        failures.append("v1-workbench-evidence-check is missing from release-check")
    if "v1.0 workbench/evidence closure" not in readme:
        failures.append("README is missing v1.0 workbench/evidence closure reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "closure_doc": doc_rel,
        "tool_count": reports["tool_surface"].get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 workbench/evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_doc: {report['closure_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "run_control_behavior_allowed: false",
        "sandbox_orchestration_allowed: false",
        "siem_adapter_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
