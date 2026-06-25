"""Validate the v1.0 RC post-review triage map."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, v1_rc_feature_freeze_check, v1_rc_readiness_check

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-rc-post-review-triage.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview post-review triage map.",
    "make external-response-normalize FILE=...",
    "mutates_findings: false",
    "closes_external_review: false",
    "Feature freeze remains active throughout post-review triage",
    "Reviewer Finding Template",
    "Source Review Closure Matrix",
    "Critical/high finding",
    "Product-boundary ambiguity",
    "Request for new powers",
    "Allowed Under Feature Freeze",
    "Not Allowed Under Feature Freeze",
    "make reviewer-findings-check",
    "make review-findings-summary",
    "make v1-rc-post-review-triage-check",
    "make release-check",
    "make review-candidate",
    "git status --short",
    "closing external/source-review rows without sufficient reviewer access",
    "a closure update would hide pending external rows",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    reports = {
        "readiness": v1_rc_readiness_check.build_report(repo_root),
        "feature_freeze": v1_rc_feature_freeze_check.build_report(repo_root),
    }
    for name, report in reports.items():
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))

    readiness = reports["readiness"]
    if readiness.get("tool_count") != 24:
        failures.append("post-review triage requires tool count 24")
    if readiness.get("selected_capability") != "not selected":
        failures.append("post-review triage requires no selected next capability")
    if readiness.get("capability_expansion_allowed") is not False:
        failures.append("post-review triage requires capability expansion blocked")
    if readiness.get("public_security_product_positioning_allowed") is not False:
        failures.append("post-review triage requires public/security-product positioning blocked")

    if not doc_path.exists():
        failures.append("v1.0 RC post-review triage doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC post-review triage doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(
                    f"v1.0 RC post-review triage doc contains forbidden phrase: {phrase}"
                )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC post-review triage doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC post-review triage doc is missing from docs-site inputs")
    if doc_rel not in packet_script:
        failures.append("v1.0 RC packet is missing the post-review triage doc")
    if "v1-rc-post-review-triage-check:" not in makefile:
        failures.append("Make target is missing: v1-rc-post-review-triage-check")
    if "v1-rc-post-review-triage-check" not in release_check_body:
        failures.append("v1-rc-post-review-triage-check is missing from release-check")
    if "make v1-rc-post-review-triage-check" not in readme:
        failures.append("README is missing v1.0 RC post-review triage command reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "triage_doc": doc_rel,
        "tool_count": readiness.get("tool_count"),
        "selected_capability": readiness.get("selected_capability"),
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
        "mutates_findings": False,
        "closes_external_review": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC post-review triage check",
        f"valid: {str(report['valid']).lower()}",
        f"triage_doc: {report['triage_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
        "runtime_changes_allowed: false",
        "mutates_findings: false",
        "closes_external_review: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
