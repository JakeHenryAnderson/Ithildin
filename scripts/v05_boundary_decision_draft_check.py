"""Validate the v0.5 boundary decision draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v0.5-boundary-decision-draft.md"
REQUIRED_PHRASES = [
    "Decision draft: no-go for capability expansion",
    "Go for external/source review handoff",
    "No new governed tool powers",
    "External/source review remains pending",
    "Capability expansion remains blocked",
    "v0.1 local-preview runtime boundary",
    "not production-ready",
    "not a sandbox",
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
    path = repo_root / DOC.relative_to(ROOT)
    failures: list[str] = []
    if not path.exists():
        return {"schema_version": "1", "valid": False, "failures": ["draft missing"]}
    text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"boundary decision draft missing phrase: {phrase}")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "external_handoff_go": True,
        "capability_expansion_go": False,
        "broader_distribution_go": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.5 boundary decision draft check",
        f"valid: {str(report['valid']).lower()}",
        f"external_handoff_go: {str(report.get('external_handoff_go', False)).lower()}",
        "capability_expansion_go: false",
        "broader_distribution_go: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
