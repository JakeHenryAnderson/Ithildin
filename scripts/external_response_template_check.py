"""Validate the v0.5 external review response intake template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/codex/external-review-response-intake-template-v2.md"
REQUIRED_PHRASES = [
    "Overall judgment",
    "Blockers",
    "Should-fix before broader distribution",
    "Documentation and positioning risks",
    "Technical hardening priorities",
    "Packet gaps",
    "v0.6 or next-roadmap recommendations",
    "Do-not-add-yet list",
    "Finding Extraction Table",
    "EXT-###",
    "source-review-closure-matrix.md",
    "reviewer-finding-template.md",
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
    path = repo_root / TEMPLATE.relative_to(ROOT)
    failures: list[str] = []
    if not path.exists():
        return {"schema_version": "1", "valid": False, "failures": ["template missing"]}
    text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"template missing required phrase: {phrase}")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_phrase_count": len(REQUIRED_PHRASES),
        "template_path": TEMPLATE.relative_to(ROOT).as_posix(),
        "mutates_findings": False,
        "closes_external_review": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin external response template check",
        f"valid: {str(report['valid']).lower()}",
        f"required_phrase_count: {report.get('required_phrase_count', 0)}",
        "mutates_findings: false",
        "closes_external_review: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
