"""Validate the v1.0 local-preview RC readiness umbrella."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    agent_workflow_check,
    capability_decision_report,
    next_capability_readiness,
    no_new_powers_guardrail,
    packet_redaction_scan,
    read_only_capability_inventory_gate,
    review_docs,
    tool_surface_invariant_gate,
    v1_assurance_closure_check,
    v1_operator_quickstart_check,
    v1_rc_roadmap_check,
    v1_rc_status_check,
    v1_workbench_evidence_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-rc-readiness-gate.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview release-candidate readiness gate.",
    "Gate Inputs",
    "RC Interpretation",
    "Packet",
    "make v1-rc-readiness",
    "make v1-rc-packet",
    "make release-check",
    "make review-candidate",
    "governed tool count remains `23`",
    "latest implemented tool remains `project.risk.summary`",
    "no next capability is selected",
    "capability expansion remains blocked",
    "public/security-product positioning remains blocked",
    "external/source-review pending rows remain visible",
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
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    reports = {
        "status": v1_rc_status_check.build_report(repo_root),
        "roadmap": v1_rc_roadmap_check.build_report(repo_root),
        "operator_quickstart": v1_operator_quickstart_check.build_report(repo_root),
        "workbench_evidence": v1_workbench_evidence_check.build_report(repo_root),
        "assurance": v1_assurance_closure_check.build_report(repo_root),
        "agent_workflow": agent_workflow_check.build_report(repo_root),
        "tool_surface": tool_surface_invariant_gate.build_report(repo_root),
        "no_new_powers": no_new_powers_guardrail.build_report(repo_root),
        "read_only_inventory": read_only_capability_inventory_gate.build_report(repo_root),
        "next_capability": next_capability_readiness.build_report(repo_root),
        "capability_decision": capability_decision_report.build_report(repo_root),
        "packet_redaction": packet_redaction_scan.scan_packet_paths(
            packet_redaction_scan.discover_default_packet_paths(repo_root)
        ).as_dict(),
    }
    for name, report in reports.items():
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
        failures.extend(f"{name}: {failure}" for failure in report.get("hard_failures", []))

    status = reports["status"]
    assurance = reports["assurance"]
    packet_redaction = reports["packet_redaction"]
    packet_redaction_findings = len(packet_redaction.get("findings", []))
    if status["tool_count"] != 23:
        failures.append("v1 RC readiness requires tool count 23")
    if status["latest_implemented_tool"] != "project.risk.summary":
        failures.append("v1 RC readiness requires project.risk.summary as latest tool")
    if status["selected_capability"] != "not selected":
        failures.append("v1 RC readiness requires no selected next capability")
    if status["capability_expansion_allowed"] is not False:
        failures.append("v1 RC readiness requires capability expansion blocked")
    if status["public_security_product_positioning_allowed"] is not False:
        failures.append("v1 RC readiness requires public/security-product positioning blocked")
    if assurance["external_closure_complete"] is not False:
        failures.append("v1 RC readiness must not claim external closure complete")
    if assurance["pending_external_review_rows"] <= 0:
        failures.append("v1 RC readiness expects pending external rows to remain visible")
    if packet_redaction_findings != 0:
        failures.append("v1 RC readiness requires packet redaction findings: 0")

    if not doc_path.exists():
        failures.append("v1.0 RC readiness gate doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC readiness doc is missing phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC readiness doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC readiness doc is missing from docs-site inputs")
    if "v1-rc-readiness:" not in makefile:
        failures.append("Make target is missing: v1-rc-readiness")
    if "v1-rc-packet:" not in makefile:
        failures.append("Make target is missing: v1-rc-packet")
    if "v1-rc-readiness" not in release_check_body:
        failures.append("v1-rc-readiness is missing from release-check")
    if "make v1-rc-readiness" not in readme or "make v1-rc-packet" not in readme:
        failures.append("README is missing v1.0 RC readiness command references")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "readiness_doc": doc_rel,
        "tool_count": status["tool_count"],
        "latest_implemented_tool": status["latest_implemented_tool"],
        "selected_capability": status["selected_capability"],
        "pending_external_review_rows": assurance["pending_external_review_rows"],
        "packet_redaction_findings": packet_redaction_findings,
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC readiness check",
        f"valid: {str(report['valid']).lower()}",
        f"readiness_doc: {report['readiness_doc']}",
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
