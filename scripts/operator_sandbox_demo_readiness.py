"""Validate operator-managed sandbox demo readiness without adding runtime powers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    demo_scenario_pack,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/codex/operator-managed-sandbox-demo-guide.md"

REQUIRED_GUIDE_PHRASES = [
    "Status: demo/readiness guide",
    "operator-managed workspace or sandbox",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "uv run python -m ithildin_mcp_server",
    "Agent Run filters and summary chips",
    "Export Run Evidence",
    "GET /runs/{run_id}/evidence-export",
    "make negative-review-transcripts",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
    "Ithildin only mediates",
    "does not add runtime behavior",
    "does not add sandbox lifecycle",
    "The wrong conclusion",
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
    roadmap = (repo_root / "docs/codex/agent-run-observability-and-sandbox-roadmap.md").read_text(
        encoding="utf-8"
    )
    backlog = (repo_root / "docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(
        f"demo-scenario-pack: {failure}" for failure in demo_scenario_pack.validate_scenario_pack()
    )
    failures.extend(
        _validate_guide(
            repo_root=repo_root,
            readme=readme,
            docs_site=docs_site,
            roadmap=roadmap,
            backlog=backlog,
        )
    )

    if "operator-sandbox-demo-readiness:" not in makefile:
        failures.append("Make target is missing: operator-sandbox-demo-readiness")
    if "operator-sandbox-demo-readiness" not in release_check_body:
        failures.append("operator-sandbox-demo-readiness is missing from release-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
    }


def _validate_guide(
    *,
    repo_root: Path,
    readme: str,
    docs_site: str,
    roadmap: str,
    backlog: str,
) -> list[str]:
    failures: list[str] = []
    rel_path = GUIDE.relative_to(ROOT).as_posix()
    doc_path = repo_root / rel_path
    if not doc_path.exists():
        failures.append("Operator-managed sandbox demo guide is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_GUIDE_PHRASES:
        if phrase not in text:
            failures.append(f"Operator-managed sandbox demo guide is missing phrase: {phrase}")
    for phrase in [
        "Ithildin starts containers or VMs",
        "Ithildin mounts a Docker socket",
        "Ithildin runs shell commands as a governed tool",
        "Ithildin manages Kubernetes or browser automation",
    ]:
        if phrase not in text:
            failures.append(f"Operator-managed sandbox demo guide is missing non-claim: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Operator-managed sandbox demo guide is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Operator-managed sandbox demo guide is missing from docs-site inputs")
    if "operator-managed-sandbox-demo-guide.md" not in readme:
        failures.append("README is missing operator-managed sandbox demo guide")
    if "operator-managed-sandbox-demo-guide.md" not in roadmap:
        failures.append("Agent Run roadmap is missing operator-managed sandbox demo guide")
    if "281 - Operator-managed sandbox demo guide | Done" not in backlog:
        failures.append("Backlog is missing Task 281")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin operator-managed sandbox demo readiness gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "sandbox_orchestration_allowed: false",
        "siem_adapter_behavior_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
