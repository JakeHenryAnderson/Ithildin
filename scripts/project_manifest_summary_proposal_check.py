"""Validate the project.manifest.summary design-only capability proposal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import read_only_capability_inventory_gate, v09_design_only_gate

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_DOC = ROOT / "docs/codex/capability-proposals/project-manifest-summary.md"
REQUIRED_PHRASES = [
    "Status: design-only proposal",
    "does not add a tool manifest",
    "does not add an executor",
    "does not add policy rules",
    "does not add MCP exposure",
    "does not add API behavior",
    "does not add UI behavior",
    "does not add runtime behavior",
    "project.manifest.summary",
    "Manifest Allowlist",
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "no file contents",
    "no package script values",
    "no dependency names by default",
    "no registry or network access",
    "no shell",
    "response-local manifest IDs",
    "Strict Schema Contract",
    "additionalProperties: false",
    "Parser Contract Sketch",
    "Privacy Policy",
    "Policy Fixtures",
    "Audit Fields",
    "Resource Limits",
    "Negative Transcripts",
    "UI/review Evidence",
    "Accepted-Risk Impact",
    "No-New-Powers Analysis",
    "External/source Review Requirement",
]
FORBIDDEN_PHRASES = [
    "implementation allowed",
    "add a tool manifest now",
    "add an executor now",
    "expose through MCP now",
    "read package script values by default",
    "return dependency names by default",
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
    proposal_path = repo_root / PROPOSAL_DOC.relative_to(ROOT)
    if not proposal_path.exists():
        return _report(["project.manifest.summary proposal is missing"], {})

    text = proposal_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"proposal is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"proposal contains forbidden implementation phrase: {phrase}")

    design_gate = v09_design_only_gate.build_report(repo_root)
    inventory_gate = read_only_capability_inventory_gate.build_report(repo_root)
    failures.extend(f"v0.9 design-only gate: {failure}" for failure in design_gate["failures"])
    failures.extend(f"inventory gate: {failure}" for failure in inventory_gate["failures"])

    return _report(
        failures,
        {
            "proposal_path": PROPOSAL_DOC.relative_to(ROOT).as_posix(),
            "v09_baseline_commit": design_gate["evidence"].get("v09_baseline_commit"),
            "approved_read_only_capabilities": inventory_gate.get("capability_count"),
            "tool_count": inventory_gate.get("tool_count"),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "project.manifest.summary",
        "scope": "design_only",
        "implementation_allowed": False,
        "runtime_changes_allowed": False,
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin project.manifest.summary proposal check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: project.manifest.summary",
        "scope: design_only",
        "implementation_allowed: false",
        "runtime_changes_allowed: false",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
