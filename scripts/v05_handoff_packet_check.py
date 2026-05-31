"""Validate the v0.5 handoff packet and go/no-go seed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v0.5-handoff-packet.md"
REQUIRED_PHRASES = [
    "v0.5 handoff packet",
    "Go for external/source review",
    "No-go for capability expansion",
    "No-go for broader public/security-product positioning",
    "make v05-review-candidate",
    "make release-check",
    "Tasks 152-180 are complete",
    "external/source review remains pending",
    "does not add governed tool powers",
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
        return {"schema_version": "1", "valid": False, "failures": ["handoff missing"]}
    text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"handoff packet missing phrase: {phrase}")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "external_handoff_go": True,
        "capability_expansion_go": False,
        "broader_distribution_go": False,
        "tasks_complete": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.5 handoff packet check",
        f"valid: {str(report['valid']).lower()}",
        "external_handoff_go: true",
        "capability_expansion_go: false",
        "broader_distribution_go: false",
        "tasks_complete: true",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
