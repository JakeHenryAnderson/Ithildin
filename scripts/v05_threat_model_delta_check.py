"""Validate the v0.5 threat-model delta document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v0.5-threat-model-delta.md"
REQUIRED_PHRASES = [
    "v0.1 local-preview runtime boundary",
    "No new governed tool powers",
    "External/source review remains pending",
    "Accepted risks remain local-preview only",
    "not a sandbox",
    "not production identity",
    "not external notarization",
    "Capability expansion remains blocked",
    "Task 152 through Task 175",
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
        return {"schema_version": "1", "valid": False, "failures": ["delta missing"]}
    text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"threat-model delta missing phrase: {phrase}")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_phrase_count": len(REQUIRED_PHRASES),
        "runtime_boundary_changed": False,
        "new_powers_added": False,
        "external_review_closed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.5 threat-model delta check",
        f"valid: {str(report['valid']).lower()}",
        f"required_phrase_count: {report.get('required_phrase_count', 0)}",
        "runtime_boundary_changed: false",
        "new_powers_added: false",
        "external_review_closed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
