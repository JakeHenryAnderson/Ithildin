"""Validate the v0.8 design-only capability decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import accepted_risk_register, no_new_powers_guardrail

ROOT = Path(__file__).resolve().parents[1]
DECISION_DOC = ROOT / "docs/codex/v0.8-capability-design-decision.md"
FORBIDDEN_IMPLEMENTATION_SURFACE_PREFIXES = (
    "apps/api/",
    "apps/mcp-server/",
    "ithildin_api/",
    "ithildin_mcp_server/",
    "policies/",
    "tool-manifests/",
)
FORBIDDEN_IMPLEMENTATION_SURFACE_FILES = {
    "tool-manifests.lock.json",
}
REQUIRED_PHRASES = [
    "Capability design-only exploration",
    "conditional_go",
    "Capability implementation",
    "no_go",
    "New governed tool powers",
    "Tool count remains 10",
    "executor contract",
    "policy fixtures",
    "audit fields",
    "UI/review evidence",
    "negative transcripts",
    "resource limits",
    "accepted-risk impact analysis",
    "external/source review requirement before implementation",
]
FORBIDDEN_DESIGN_UNLOCKS = [
    "implementation allowed",
    "new governed tool powers allowed",
    "tool manifests may be added",
    "executors may be implemented",
    "mcp exposure may be added",
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
    doc_path = repo_root / DECISION_DOC.relative_to(ROOT)
    if not doc_path.exists():
        return _report(["v0.8 capability-design decision doc is missing"], {})

    text = doc_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"capability-design decision is missing phrase: {phrase}")
    for phrase in FORBIDDEN_DESIGN_UNLOCKS:
        if phrase in lower:
            failures.append(f"capability-design decision contains forbidden unlock: {phrase}")

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    accepted_risks = accepted_risk_register.build_report(repo_root)
    failures.extend(no_new_powers["failures"])
    failures.extend(accepted_risks["failures"])
    failures.extend(_forbidden_working_tree_implementation_changes(repo_root))

    return _report(
        failures,
        {
            "tool_count": no_new_powers["tool_count"],
            "accepted_deferred_risks": len(accepted_risks["accepted_deferred_ids"]),
            "accepted_risks_constraining_design": len(
                accepted_risks["blocks_capability_design_ids"]
            ),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "capability_design_only": "conditional_go",
        "capability_implementation": "no_go",
        "new_governed_tool_powers": "no_go",
        "evidence": evidence,
    }


def _forbidden_working_tree_implementation_changes(repo_root: Path) -> list[str]:
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return []
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ["could not inspect working-tree diff for capability-design implementation drift"]
    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    forbidden = [
        path
        for path in changed
        if path in FORBIDDEN_IMPLEMENTATION_SURFACE_FILES
        or path.startswith(FORBIDDEN_IMPLEMENTATION_SURFACE_PREFIXES)
    ]
    return [
        "capability-design work changed implementation surfaces: " + ", ".join(forbidden)
    ] if forbidden else []


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.8 capability-design gate",
        f"valid: {str(report['valid']).lower()}",
        "capability_design_only: conditional_go",
        "capability_implementation: no_go",
        "new_governed_tool_powers: no_go",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
        "accepted_risks_constraining_design: "
        f"{report['evidence'].get('accepted_risks_constraining_design', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
