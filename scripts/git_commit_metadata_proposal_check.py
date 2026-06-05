"""Validate the git.show.commit_metadata design-only capability proposal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import v09_design_only_gate

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_DOC = ROOT / "docs/codex/capability-proposals/git-show-commit-metadata.md"
REQUIRED_PHRASES = [
    "Status: design-only proposal",
    "does not add a tool manifest",
    "git.show.commit_metadata",
    "executor contract",
    "policy fixtures",
    "audit fields",
    "UI/review evidence",
    "negative transcripts",
    "resource limits",
    "accepted-risk impact",
    "no-new-powers analysis",
    "external/source review",
    "Ref Resolution Policy",
    "--end-of-options",
    "reject arbitrary Git revision syntax",
    "HEAD~1",
    "HEAD@{1}",
    ":/message",
    "remote-tracking refs",
    "Changed-File Summary Contract",
    "NUL-delimited",
    "rename/copy records",
    "submodules/gitlinks",
    "binary `numstat` values",
    "include_emails",
    "Email handling must be explicit",
    "include_emails=false",
    "include_body=false",
    "Sensitive path text should be redacted by default",
    "social-engineering",
    "refs/heads/<name>",
    "refs/tags/<name>",
    "Negative Transcript Sketches",
    "Must not expose",
]
FORBIDDEN_PHRASES = [
    "implementation allowed",
    "add a manifest",
    "add an executor",
    "expose through MCP now",
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
        return _report(["git.show.commit_metadata proposal is missing"], {})

    text = proposal_path.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower:
            failures.append(f"proposal is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            failures.append(f"proposal contains forbidden implementation phrase: {phrase}")

    design_gate = v09_design_only_gate.build_report(repo_root)
    failures.extend(f"v0.9 design-only gate: {failure}" for failure in design_gate["failures"])

    return _report(
        failures,
        {
            "proposal_path": PROPOSAL_DOC.relative_to(ROOT).as_posix(),
            "v09_baseline_commit": design_gate["evidence"].get("v09_baseline_commit"),
            "tool_count": design_gate["evidence"].get("tool_count"),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "proposal": "git.show.commit_metadata",
        "scope": "design_only",
        "implementation_allowed": False,
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin git.show.commit_metadata proposal check",
        f"valid: {str(report['valid']).lower()}",
        "proposal: git.show.commit_metadata",
        "scope: design_only",
        "implementation_allowed: false",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
