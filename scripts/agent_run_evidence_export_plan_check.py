"""Validate the Agent Run evidence export implementation-planning packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import agent_run_evidence_export_check, no_new_powers_guardrail, review_docs

ROOT = Path(__file__).resolve().parents[1]
PLAN_DOC = ROOT / "docs/codex/agent-run-evidence-export-implementation-plan.md"
REQUIRED_PHRASES = [
    "Status: implementation-planning only",
    "does not add runtime behavior",
    "Implementation state: blocked",
    "GET /runs/{run_id}/evidence-export",
    "admin bearer token only",
    "additionalProperties: false",
    "Allowed top-level output fields",
    "Allowed `run` fields",
    "Allowed `timeline` fields",
    "Fixture Plan",
    "clean run",
    "approval-required run",
    "denied action run",
    "patch-diagnostic run",
    "signed-export-referenced run",
    "Negative Case Plan",
    "unknown `run_id`",
    "oversized timeline",
    "absent signed evidence",
    "redaction boundary excludes prompts",
    "raw tool arguments",
    "file contents",
    "diffs",
    "response bodies",
    "secrets",
    "Review Prompt",
    "EXT-RUN-EXPORT-###",
    "Required Future Gates",
    "does not approve implementation",
    "make agent-run-evidence-export-plan-check",
]
FORBIDDEN_PHRASES = [
    "implementation is approved",
    "runtime behavior is added",
    "this planning sprint adds an endpoint",
    "this planning sprint adds an api",
    "this planning sprint adds mcp exposure",
    "this planning sprint adds a siem adapter",
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
    rel_path = PLAN_DOC.relative_to(ROOT).as_posix()
    plan_path = repo_root / rel_path
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs/codex/agent-run-observability-and-sandbox-roadmap.md").read_text(
        encoding="utf-8"
    )

    if not plan_path.exists():
        failures.append("Agent Run evidence export implementation plan is missing")
        text = ""
    else:
        text = plan_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"implementation plan is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"implementation plan contains forbidden phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Agent Run evidence export implementation plan is missing from review docs")
    if rel_path not in docs_site:
        failures.append(
            "Agent Run evidence export implementation plan is missing from docs-site inputs"
        )
    if "agent-run-evidence-export-plan-check:" not in makefile:
        failures.append("Make target is missing: agent-run-evidence-export-plan-check")
    if "make agent-run-evidence-export-plan-check" not in readme:
        failures.append("README is missing agent-run-evidence-export-plan-check")
    if "agent-run-evidence-export-implementation-plan.md" not in roadmap:
        failures.append("Agent Run roadmap is missing the export implementation plan link")

    export_design = agent_run_evidence_export_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(
        f"agent-run-evidence-export: {failure}" for failure in export_design["failures"]
    )
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "plan": rel_path,
        "scope": "implementation_planning_only",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "tool_count": no_new_powers.get("tool_count"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Agent Run evidence export implementation-plan check",
        f"valid: {str(report['valid']).lower()}",
        f"plan: {report['plan']}",
        "scope: implementation_planning_only",
        "implementation_allowed: false",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        f"tool_count: {report.get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
