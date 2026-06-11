"""Validate the guided local demo flow wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/guided-demo-readiness.md"
REQUIRED_DOC_PHRASES = [
    "Status: release-readiness gate",
    "make guided-demo",
    "make demo-state-report",
    "GUIDED_DEMO_TRANSCRIPT.md",
    "DEMO_STATE_REPORT.md",
    "does not start Compose",
    "does not call governed tools",
    "tool count remains `13`",
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
    review_docs = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    ui = (repo_root / "apps/ui/src/App.tsx").read_text(encoding="utf-8")
    ui_tests = (repo_root / "apps/ui/src/App.test.tsx").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    if not DOC.exists():
        failures.append("guided demo readiness doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"guided demo readiness doc is missing phrase: {phrase}")

    for target in ["guided-demo:", "demo-state-report:", "guided-demo-readiness:"]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "guided-demo-readiness" not in release_check_body:
        failures.append("guided-demo-readiness is missing from release-check")
    if "$(MAKE) guided-demo" not in makefile.partition("review-candidate:")[2]:
        failures.append("guided-demo is missing from review-candidate")
    if "$(MAKE) demo-state-report" not in makefile.partition("demo-workbench:")[2]:
        failures.append("demo-state-report is missing from demo-workbench")

    rel_path = "docs/codex/guided-demo-readiness.md"
    for label, text in [("README", readme), ("reproduction map", reproduction_map)]:
        for phrase in ["make guided-demo", "make demo-state-report", "make guided-demo-readiness"]:
            if phrase not in text:
                failures.append(f"{label} is missing command: {phrase}")
    if rel_path not in docs_site:
        failures.append("guided demo readiness doc is missing from docs-site inputs")
    if rel_path not in review_docs:
        failures.append("guided demo readiness doc is missing from review docs")

    for phrase in [
        "No recorded agent runs. Run make demo-seed",
        "Export appears after selecting a run",
        "Preflight",
        "Seed/run",
        "Cleanup",
    ]:
        if phrase not in ui:
            failures.append(f"Review console guided demo surface is missing phrase: {phrase}")
    for phrase in [
        "No recorded agent runs. Run make demo-seed",
        "Export appears after selecting a run",
        "Preflight",
        "Seed/run",
        "Cleanup",
    ]:
        if phrase not in ui_tests:
            failures.append(f"UI guided demo tests are missing phrase: {phrase}")

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


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin guided demo readiness gate",
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
