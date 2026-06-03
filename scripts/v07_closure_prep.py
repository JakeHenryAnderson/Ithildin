"""Validate v0.7 external-review closure prep docs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_review_closure_gate

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/codex/v0.7-external-review-closure-charter.md",
    "docs/codex/v0.6-final-packet-sanity-review.md",
    "docs/codex/v0.7-external-review-row-partition.md",
)
REQUIRED_COMMANDS = (
    "make release-check",
    "make v06-final-handoff",
    "make external-review-closure-gate",
    "make capability-decision-report",
)
REQUIRED_BATCHES = (
    "Patch apply recheck",
    "Filesystem/platform",
    "HTTP fetch",
    "Signed evidence/audit",
    "Policy/registry",
    "MCP ingress",
    "Review console/admin",
    "Release/evidence automation",
    "Docs/claims/public-preview wording",
)
REQUIRED_STATUS_PHRASES = (
    "external handoff: go",
    "source-review closure: focused lanes closed",
    "capability expansion: no-go",
    "public/security-product positioning: no-go",
    "no new governed tool powers",
)
FORBIDDEN_LINES = (
    "Capability expansion: go",
    "Public/security-product positioning: go",
    "Source-review closure: complete",
    "External/source review closure: complete",
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
    docs: dict[str, str] = {}
    for relative in REQUIRED_DOCS:
        path = repo_root / relative
        if not path.exists():
            failures.append(f"required v0.7 closure-prep doc missing: {relative}")
            continue
        docs[relative] = path.read_text(encoding="utf-8")

    combined = "\n".join(docs.values())
    combined_lower = combined.lower()
    for phrase in REQUIRED_STATUS_PHRASES:
        if phrase not in combined_lower:
            failures.append(f"v0.7 closure-prep docs missing required status: {phrase}")
    lines = {line.strip() for line in combined.splitlines()}
    for line in FORBIDDEN_LINES:
        if line in lines:
            failures.append(f"v0.7 closure-prep docs contain forbidden line: {line}")

    charter = docs.get("docs/codex/v0.7-external-review-closure-charter.md", "")
    for command in REQUIRED_COMMANDS:
        if command not in charter:
            failures.append(f"v0.7 closure charter missing required command: {command}")
    for required in (
        "v0.6 final no-go packet",
        "33cb2fd282342e4ca3d3cb823322e6a23af0d2cc",
        "var/review-packets/v0.2/GPT-5.5-Pro-consolidated",
        "not a capability sprint",
    ):
        if required not in charter:
            failures.append(f"v0.7 closure charter missing required baseline: {required}")

    sanity = docs.get("docs/codex/v0.6-final-packet-sanity-review.md", "")
    for required in (
        "historical v0.2 output paths are explained",
        "public preview is blocked",
        "capability expansion is blocked",
        "packet redaction scan",
        "docs guardrails",
    ):
        if required not in sanity.lower():
            failures.append(f"v0.6 packet sanity review missing check: {required}")

    partition = docs.get("docs/codex/v0.7-external-review-row-partition.md", "")
    for batch in REQUIRED_BATCHES:
        if batch not in partition:
            failures.append(f"row partition missing review batch: {batch}")
    closure_report = external_review_closure_gate.build_report(repo_root)
    pending_rows = closure_report["pending_external_review_rows"]
    for row in pending_rows:
        if row not in partition:
            failures.append(f"row partition missing pending external row: {row}")

    if closure_report["external_closure_complete"]:
        failures.append("v0.7 closure prep expected external closure to remain incomplete")
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_doc_count": len(REQUIRED_DOCS),
        "pending_external_review_rows": len(pending_rows),
        "externally_closed_rows": len(closure_report["externally_closed_rows"]),
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.7 external-review closure prep check",
        f"valid: {str(report['valid']).lower()}",
        f"required_doc_count: {report['required_doc_count']}",
        f"pending_external_review_rows: {report['pending_external_review_rows']}",
        f"externally_closed_rows: {report['externally_closed_rows']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
