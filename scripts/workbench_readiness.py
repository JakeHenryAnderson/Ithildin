"""Validate the local operator workbench readiness surface."""

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
DOC = ROOT / "docs/codex/operator-workbench-readiness.md"
WALKTHROUGH_DOC = ROOT / "docs/codex/operator-demo-walkthrough.md"
REQUIRED_DOC_PHRASES = [
    "Status: release-readiness gate",
    "operator workbench",
    "GET /runs",
    "GET /runs/{run_id}",
    "GET /runs/{run_id}/evidence-export",
    "make demo-workbench",
    "make demo-readiness-summary",
    "make demo-operator-walkthrough",
    "make operator-demo-guide",
    "make demo-state-report",
    "make demo-reset-guide",
    "make demo-workbench-smoke",
    "make workbench-evidence-packet",
    "make live-demo-evidence-summary",
    "make sandbox-artifact-observed-demo",
    "make hello-world-sandbox-observed-demo",
    "make hello-world-mission-control-handoff",
    "make sandbox-promotion-evidence-contract-check",
    "WORKBENCH_DEMO_INDEX.md",
    "DEMO_READINESS_SUMMARY.md",
    "OPERATOR_DEMO_WALKTHROUGH.md",
    "OPERATOR_DEMO_GUIDE.md",
    "DEMO_STATE_REPORT.md",
    "DEMO_FLOW_RESULT.md",
    "DEMO_RESET_GUIDE.md",
    "07_WORKBENCH_DEMO_STORY.md",
    "10_DEMO_RESET_GUIDE.md",
    "12_OPERATOR_DEMO_WALKTHROUGH.md",
    "WORKBENCH_DEMO_SMOKE.md",
    "sandbox-artifact-observed-demo",
    "hello-world-sandbox-observed-demo",
    "hello-world-mission-control-handoff",
    "sandbox-promotion-evidence-contract-check",
    "newest reading order",
    "summary",
    "does not start services",
    "does not add run controls",
    "tool count remains `24`",
    "no-new-powers",
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
    reproduction_map = (repo_root / "docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    ui = (repo_root / "apps/ui/src/App.tsx").read_text(encoding="utf-8")
    ui_tests = (repo_root / "apps/ui/src/App.test.tsx").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    failures.extend(
        _validate_doc(readme=readme, reproduction_map=reproduction_map, docs_site=docs_site)
    )
    for target in [
        "workbench-readiness:",
        "workbench-evidence-packet:",
        "demo-readiness-summary:",
        "demo-operator-walkthrough:",
        "operator-demo-guide:",
        "demo-state-report:",
        "demo-reset-guide:",
        "demo-workbench-smoke:",
        "demo-workbench:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "workbench-readiness" not in release_check_body:
        failures.append("workbench-readiness is missing from release-check")
    if "$(MAKE) workbench-evidence-packet" not in makefile.partition("review-candidate:")[2]:
        failures.append("workbench-evidence-packet is missing from review-candidate")
    if "$(MAKE) demo-workbench-smoke" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-workbench-smoke is missing from demo-workbench")
    if "$(MAKE) sandbox-artifact-observed-demo" not in makefile.partition("demo-workbench:")[2]:
        failures.append("sandbox-artifact-observed-demo is missing from demo-workbench")
    if "$(MAKE) hello-world-sandbox-observed-demo" not in makefile.partition("demo-workbench:")[2]:
        failures.append("hello-world-sandbox-observed-demo is missing from demo-workbench")
    demo_workbench_body = makefile.partition("demo-workbench:")[2]
    if "$(MAKE) hello-world-mission-control-handoff" not in demo_workbench_body:
        failures.append("hello-world-mission-control-handoff is missing from demo-workbench")
    if "$(MAKE) sandbox-promotion-evidence-contract-check" not in demo_workbench_body:
        failures.append("sandbox-promotion-evidence-contract-check is missing from demo-workbench")
    if "$(MAKE) demo-readiness-summary" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-readiness-summary is missing from demo-workbench")
    if "$(MAKE) demo-operator-walkthrough" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-operator-walkthrough is missing from demo-workbench")
    if "$(MAKE) operator-demo-guide" not in makefile.partition("demo-workbench:")[2]:
        failures.append("operator-demo-guide is missing from demo-workbench")
    if "$(MAKE) demo-state-report" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-state-report is missing from demo-workbench")
    if "$(MAKE) demo-reset-guide" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-reset-guide is missing from demo-workbench")

    for phrase in [
        "Agent Runs",
        "Demo Path",
        "Preflight",
        "Seed/run",
        "Cleanup",
        "RunSummary",
        "Run Evidence",
        "DemoLabel",
        "Grouped run evidence",
        "Export Run Evidence",
        "timelineStatus",
        "timelineWarnings",
        "run-filter-bar",
    ]:
        if phrase not in ui:
            failures.append(f"Review console workbench surface is missing phrase: {phrase}")
    for phrase in [
        "filters agent runs with a bounded authenticated query",
        "Demo Path",
        "Evidence Types",
        "Export Run Evidence",
        "runev_123456789",
        "guided_local_demo",
        "summary",
    ]:
        if phrase not in ui_tests:
            failures.append(f"UI workbench tests are missing phrase: {phrase}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "run_control_behavior_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def _validate_doc(*, readme: str, reproduction_map: str, docs_site: str) -> list[str]:
    failures: list[str] = []
    rel_path = DOC.relative_to(ROOT).as_posix()
    if not DOC.exists():
        return ["operator workbench readiness doc is missing"]
    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in text:
            failures.append(f"operator workbench readiness doc is missing phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("operator workbench readiness doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("operator workbench readiness doc is missing from docs-site inputs")
    walkthrough_rel = WALKTHROUGH_DOC.relative_to(ROOT).as_posix()
    if not WALKTHROUGH_DOC.exists():
        failures.append("operator demo walkthrough doc is missing")
    else:
        walkthrough_text = WALKTHROUGH_DOC.read_text(encoding="utf-8")
        for phrase in [
            "make demo-operator-walkthrough",
            "OPERATOR_DEMO_WALKTHROUGH.md",
            "expected review-console screens",
            "does not start services",
            "does not add run controls",
        ]:
            if phrase not in walkthrough_text:
                failures.append(f"operator demo walkthrough doc is missing phrase: {phrase}")
    if walkthrough_rel not in review_docs.REVIEW_DOCS:
        failures.append("operator demo walkthrough doc is missing from review docs")
    if walkthrough_rel not in docs_site:
        failures.append("operator demo walkthrough doc is missing from docs-site inputs")
    for phrase in [
        "make workbench-readiness",
        "make workbench-evidence-packet",
        "make demo-readiness-summary",
        "make demo-operator-walkthrough",
        "make operator-demo-guide",
        "make demo-state-report",
        "make demo-reset-guide",
        "make sandbox-artifact-observed-demo",
        "make demo-workbench-smoke",
        "make demo-workbench",
    ]:
        if phrase not in readme:
            failures.append(f"README is missing command: {phrase}")
        if phrase not in reproduction_map:
            failures.append(f"reproduction map is missing command: {phrase}")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin operator workbench readiness gate",
        f"valid: {str(report['valid']).lower()}",
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
