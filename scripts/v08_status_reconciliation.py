"""Validate v0.8 status-source-of-truth docs and generated-packet framing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_DOC = ROOT / "docs/codex/v0.8-status-source-of-truth.md"
REQUIRED_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex/v0.6-closure-handoff.md",
    ROOT / "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md",
    ROOT / "docs/codex/v0.8-roadmap-prompt.md",
    ROOT / "docs/codex/v0.8-status-source-of-truth.md",
]
REQUIRED_PHRASES = [
    "focused implementation lanes",
    "closed for v0.1 local preview",
    "accepted-risk rows",
    "dispositioned",
    "product-decision rows",
    "conditional_go",
    "limited public-preview sharing",
    "public/security-product positioning",
    "blocked",
    "capability implementation",
    "no new governed tool powers",
    "capability design",
    "pending v0.8 decision",
]
FALSE_STATUS_PHRASES = [
    "review console/admin pending",
    "release automation pending",
    "all review is complete",
    "capability implementation allowed",
    "public/security-product positioning allowed",
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
    checked_docs: list[str] = []
    status_doc = repo_root / STATUS_DOC.relative_to(ROOT)
    if not status_doc.exists():
        return _report(["v0.8 status source-of-truth doc is missing"], checked_docs)

    status_text = status_doc.read_text(encoding="utf-8").lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in status_text:
            failures.append(f"status source-of-truth is missing phrase: {phrase}")

    for doc in REQUIRED_DOCS:
        real_path = repo_root / doc.relative_to(ROOT)
        checked_docs.append(real_path.relative_to(repo_root).as_posix())
        if not real_path.exists():
            failures.append(f"required v0.8 status doc is missing: {checked_docs[-1]}")
            continue
        text = real_path.read_text(encoding="utf-8").lower()
        if "v0.8 roadmap/product-risk consultation" not in text:
            failures.append(f"{checked_docs[-1]} is missing current v0.8 status framing")
        for phrase in FALSE_STATUS_PHRASES:
            if phrase in text:
                failures.append(f"{checked_docs[-1]} contains false status phrase: {phrase}")

    return _report(failures, checked_docs)


def _report(failures: list[str], checked_docs: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checked_docs": checked_docs,
        "focused_lanes_closed_for_local_preview": True,
        "accepted_risk_rows_dispositioned": True,
        "product_decision_rows_pending": True,
        "public_security_product_positioning_allowed": False,
        "capability_implementation_allowed": False,
        "capability_design_decision": "pending",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.8 status reconciliation",
        f"valid: {str(report['valid']).lower()}",
        "focused_lanes_closed_for_local_preview: true",
        "accepted_risk_rows_dispositioned: true",
        "product_decision_rows_pending: true",
        "public_security_product_positioning_allowed: false",
        "capability_implementation_allowed: false",
        "capability_design_decision: pending",
        f"checked_docs: {len(report['checked_docs'])}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
