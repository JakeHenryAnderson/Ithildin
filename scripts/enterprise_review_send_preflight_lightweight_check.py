"""Validate the enterprise send preflight stays lightweight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_REL = "scripts/enterprise_review_send_preflight.py"
DOC_REL = "docs/codex/enterprise-review-send-preflight.md"

FORBIDDEN_SOURCE_FRAGMENTS = [
    "enterprise_review_send_readiness",
    "enterprise_dual_review_outbox",
    "enterprise_review_send_manifest",
    "enterprise_review_send_checklist",
    "enterprise_review_submission_prompt",
    "enterprise_review_send_receipt_template",
    "enterprise_dual_response_inbox",
    "enterprise_review_handoff_drill",
]

REQUIRED_SOURCE_FRAGMENTS = [
    "EXPECTED_ARTIFACTS",
    "_artifact_hashes_match_files",
    "enterprise_operator_next_action",
    "enterprise_dual_response_readiness",
    "enterprise_response_status_board",
    "enterprise_handoff_consistency_check",
]

REQUIRED_DOC_FRAGMENTS = [
    "For speed, the preflight does not recursively rebuild every component.",
    "checks the current operator state, response state, handoff consistency, required",
    "generated files, and artifact hashes.",
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
    script = _read(repo_root / SCRIPT_REL)
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")

    if not script:
        failures.append(f"missing script: {SCRIPT_REL}")
    if not doc:
        failures.append(f"missing doc: {DOC_REL}")

    for fragment in FORBIDDEN_SOURCE_FRAGMENTS:
        if fragment in script:
            failures.append(f"preflight source imports or references heavy builder: {fragment}")
    for fragment in REQUIRED_SOURCE_FRAGMENTS:
        if fragment not in script:
            failures.append(f"preflight source is missing lightweight fragment: {fragment}")
    for fragment in REQUIRED_DOC_FRAGMENTS:
        if fragment not in doc:
            failures.append(f"preflight doc is missing lightweight contract: {fragment}")

    target = "enterprise-review-send-preflight-lightweight-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in makefile.partition("release-check:")[2]:
        failures.append(f"{target} is missing from release-check")
    if target not in release_guardrails:
        failures.append(f"{target} is missing from release guardrails")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "script": SCRIPT_REL,
        "doc": DOC_REL,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "records_external_review": False,
        "normalizes_responses": False,
        "closes_enterprise_lanes": False,
        "forbidden_heavy_builders": FORBIDDEN_SOURCE_FRAGMENTS,
        "required_lightweight_fragments": REQUIRED_SOURCE_FRAGMENTS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send preflight lightweight check",
        f"valid: {str(report['valid']).lower()}",
        f"script: {report['script']}",
        f"doc: {report['doc']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"records_external_review: {str(report['records_external_review']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"closes_enterprise_lanes: {str(report['closes_enterprise_lanes']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
