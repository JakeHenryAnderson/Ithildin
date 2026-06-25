"""Validate the v1.0 RC final handoff map and packet wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
    v1_assurance_closure_check,
    v1_rc_external_review_prompt_check,
    v1_rc_feature_freeze_check,
    v1_rc_readiness_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-rc-final-handoff.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview final handoff map.",
    "Local-preview RC handoff: go",
    "Technical local-preview sharing with the warning packet: conditional go.",
    "Capability expansion: blocked by the v1.0 RC feature freeze.",
    "Public/security-product positioning: no-go.",
    "Production/security/compliance positioning: no-go.",
    "External/source-review closure: incomplete while pending rows remain visible.",
    "governed tool count remains `24`",
    "latest implemented governed tool remains `sandbox.artifact.write_text`",
    "no next capability is selected",
    "feature freeze remains active",
    "packet redaction findings must remain `0`",
    "external-pending rows must stay visible instead of being called closed",
    "make review-candidate",
    "var/review-packets/v1.0/rc/",
    "12_V1_RC_FINAL_HANDOFF.md",
    "13_V1_RC_POST_REVIEW_TRIAGE.md",
    "14_V1_RC_ARTIFACTS.md",
    "15_V1_RC_COMMANDS.md",
    "v1-rc-artifact-hashes.json",
    "make v1-rc-final-handoff-check",
    "v1.0 RC Post-Review Triage",
    "git status --short",
    "What This Handoff Proves",
    "What This Handoff Does Not Prove",
    "Next Post-Handoff Options",
    "Stop Conditions",
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
        "external_prompt": v1_rc_external_review_prompt_check.build_report(repo_root),
        "assurance": v1_assurance_closure_check.build_report(repo_root),
    }
    for name, report in reports.items():
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))

    readiness = reports["readiness"]
    assurance = reports["assurance"]
    if readiness.get("tool_count") != 24:
        failures.append("final handoff requires tool count 24")
    if readiness.get("latest_implemented_tool") != "sandbox.artifact.write_text":
        failures.append("final handoff requires sandbox.artifact.write_text as latest tool")
    if readiness.get("selected_capability") != "not selected":
        failures.append("final handoff requires no selected next capability")
    if readiness.get("packet_redaction_findings") != 0:
        failures.append("final handoff requires packet redaction findings 0")
    if readiness.get("capability_expansion_allowed") is not False:
        failures.append("final handoff requires capability expansion blocked")
    if readiness.get("public_security_product_positioning_allowed") is not False:
        failures.append("final handoff requires public/security-product positioning blocked")
    if assurance.get("external_closure_complete") is not False:
        failures.append("final handoff must not claim external closure complete")
    if assurance.get("pending_external_review_rows", 0) <= 0:
        failures.append("final handoff expects pending external rows to remain visible")
    if assurance.get("open_critical_high_findings") != 0:
        failures.append("final handoff requires no open critical/high findings")

    if not doc_path.exists():
        failures.append("v1.0 RC final handoff doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC final handoff doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 RC final handoff doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC final handoff doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC final handoff doc is missing from docs-site inputs")
    if doc_rel not in packet_script:
        failures.append("v1.0 RC packet is missing the final handoff doc")
    if "v1-rc-final-handoff-check:" not in makefile:
        failures.append("Make target is missing: v1-rc-final-handoff-check")
    if "v1-rc-final-handoff-check" not in release_check_body:
        failures.append("v1-rc-final-handoff-check is missing from release-check")
    if "make v1-rc-final-handoff-check" not in readme:
        failures.append("README is missing v1.0 RC final handoff command reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "handoff_doc": doc_rel,
        "tool_count": readiness.get("tool_count"),
        "latest_implemented_tool": readiness.get("latest_implemented_tool"),
        "selected_capability": readiness.get("selected_capability"),
        "pending_external_review_rows": assurance.get("pending_external_review_rows"),
        "packet_redaction_findings": readiness.get("packet_redaction_findings"),
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC final handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"handoff_doc: {report['handoff_doc']}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"pending_external_review_rows: {report['pending_external_review_rows']}",
        f"packet_redaction_findings: {report['packet_redaction_findings']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
        "runtime_changes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
