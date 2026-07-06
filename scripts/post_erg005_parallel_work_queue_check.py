"""Validate the post-ERG-005 parallel-work queue stays bounded and wired."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/post-erg005-parallel-work-queue.md"
DOC_TITLE = "Post-ERG-005 Parallel Work Queue"
TARGET = "post-erg005-parallel-work-queue-check"

REQUIRED_PHRASES = [
    "Status: bounded work queue",
    "does not change runtime authority",
    "Operator Walkthrough Polish",
    "Command Center Integration Prep",
    "Enterprise Evidence Clarity",
    "Next-ERG Planning",
    "Dev-Speed Optimization",
    "Stop Conditions",
    "ERG-005 walkthrough remains ready for the user",
    "not replace it or claim it has already been performed",
]

FORBIDDEN_APPROVAL_PHRASES = [
    "new governed tools are approved",
    "broader trusted-host promotion is approved",
    "Command Center enforcement authority is approved",
    "sandbox/VM orchestration is approved",
    "SIEM adapters are approved",
    "compliance automation is approved",
    "public/security-product positioning is approved",
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
    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    readme = _read(repo_root / "README.md")
    makefile = _read(repo_root / "Makefile")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc:
        failures.append("post-ERG-005 parallel work queue doc is missing")
    normalized_doc = " ".join(doc.split())
    for phrase in REQUIRED_PHRASES:
        if phrase not in normalized_doc:
            failures.append(f"parallel work queue doc is missing phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase.lower() in doc.lower():
            failures.append(f"parallel work queue doc contains forbidden phrase: {phrase}")

    wiring = [
        ("Make target", f"{TARGET}:", makefile),
        ("release-check", TARGET, release_check_body),
        ("README", DOC_REL, readme),
        ("docs-site", DOC_REL, docs_site),
        ("review docs", DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        ("review index", DOC_TITLE, review_index),
        ("release guardrails", TARGET, release_guardrails),
    ]
    for label, needle, haystack in wiring:
        if needle not in haystack:
            failures.append(f"{label} missing: {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "doc": DOC_REL,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "command_center_runtime_authority_allowed": False,
        "trusted_host_promotion_expansion_allowed": False,
        "walkthrough_required_for_promotion_claims": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin post-ERG-005 parallel work queue check",
        f"valid: {str(report['valid']).lower()}",
        f"doc: {report['doc']}",
        f"tool_count: {report['tool_count']}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "command_center_runtime_authority_allowed: false",
        "trusted_host_promotion_expansion_allowed: false",
        "walkthrough_required_for_promotion_claims: true",
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
