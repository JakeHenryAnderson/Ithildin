"""Validate demo evidence closure command, docs, packet, and guardrail wiring."""

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
DOC = ROOT / "docs/codex/demo-evidence-closure.md"
REQUIRED_DOC_PHRASES = [
    "Status: release-readiness gate",
    "make demo-flow-result-check",
    "make demo-evidence-packet",
    "make demo-evidence-readiness",
    "DEMO_FLOW_RESULT_CHECK.json",
    "demo-evidence-artifact-hashes.json",
    "not_run",
    "does not add run controls",
    "tool count remains `21`",
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
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    if not DOC.exists():
        failures.append("demo evidence closure doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"demo evidence closure doc is missing phrase: {phrase}")
    rel_path = DOC.relative_to(ROOT).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("demo evidence closure doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("demo evidence closure doc is missing from docs-site inputs")

    for target in [
        "demo-flow-result-check:",
        "demo-evidence-packet:",
        "demo-evidence-readiness:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "demo-evidence-readiness" not in release_check_body:
        failures.append("demo-evidence-readiness is missing from release-check")
    if "$(MAKE) demo-evidence-packet" not in review_candidate_body:
        failures.append("demo-evidence-packet is missing from review-candidate")

    for phrase in [
        "make demo-flow-result-check",
        "make demo-evidence-packet",
        "make demo-evidence-readiness",
    ]:
        if phrase not in readme:
            failures.append(f"README is missing phrase: {phrase}")
        if phrase not in reproduction_map:
            failures.append(f"reproduction map is missing phrase: {phrase}")

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
        "Ithildin demo evidence readiness gate",
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
