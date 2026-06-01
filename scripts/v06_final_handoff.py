"""Validate v0.6 final decision and handoff docs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import v06_lane_status

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/codex/v0.6-public-preview-readiness-decision.md",
    "docs/codex/v0.6-capability-decision-v2.md",
    "docs/codex/operator-quickstart-v2.md",
    "docs/codex/diagnostics-bundle-v2.md",
    "docs/codex/external-review-recheck-loop.md",
    "docs/codex/release-candidate-naming-cleanup.md",
    "docs/codex/v0.6-public-preview-packet.md",
    "docs/codex/v0.7-design-only-capability-rubric.md",
    "docs/codex/candidate-capability-triage.md",
    "docs/codex/security-claims-freeze.md",
    "docs/codex/v0.6-final-go-no-go-packet.md",
    "docs/codex/v0.7-boundary-decision-seed.md",
    "docs/codex/v0.6-retrospective.md",
    "docs/codex/review-artifact-minimization-pass.md",
    "docs/codex/v0.6-handoff-to-user.md",
)
REQUIRED_PHRASES = (
    "Capability expansion: no-go",
    "Public/security-product positioning: no-go",
    "External/source review closure: incomplete",
    "No new governed tool powers",
)


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
    lane_board = v06_lane_status.build_lane_status(repo_root)
    docs = []
    for relative in REQUIRED_DOCS:
        path = repo_root / relative
        if not path.exists():
            failures.append(f"required v0.6 final handoff doc missing: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        docs.append(text)

    combined = "\n".join(docs)
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"v0.6 final docs are missing required phrase: {phrase}")
    forbidden_lines = (
        "Capability expansion: go",
        "Public/security-product positioning: go",
        "External/source review closure: complete",
    )
    lines = {line.strip() for line in combined.splitlines()}
    for phrase in forbidden_lines:
        if phrase in lines:
            failures.append(f"v0.6 final docs contain forbidden go/closure phrase: {phrase}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_doc_count": len(REQUIRED_DOCS),
        "external_review_received": lane_board["summary"]["external_review_received"],
        "external_review_closed": lane_board["summary"]["external_review_closed"],
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.6 final handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"required_doc_count: {report['required_doc_count']}",
        f"external_review_received: {report['external_review_received']}",
        f"external_review_closed: {report['external_review_closed']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
