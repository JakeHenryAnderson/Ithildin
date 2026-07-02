"""Validate the technical MVP ticket map and release-readiness wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_operator_next_action,
    next_capability_readiness,
    review_docs,
    tool_surface_invariant_gate,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/technical-mvp-ticket-map.md"
DOC_TITLE = "Ithildin Technical MVP Ticket Map"
ALLOWED_NEXT_ENTERPRISE_REVIEWS = {"ERG-003", "ERG-004"}
ALLOWED_NEXT_ACTIONS = {
    "send_erg_003_and_erg_002",
    "prepare_erg004_runtime_ticket_review",
}

REQUIRED_PHRASES = [
    "Status: checked technical-MVP ticket map",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Latest implemented tool: `sandbox.artifact.write_text`",
    "Technical MVP Boundary",
    "`MVP-001`",
    "`MVP-002`",
    "`MVP-003`",
    "`MVP-004`",
    "`MVP-005`",
    "`MVP-006`",
    "`MVP-007`",
    "`MVP-008`",
    "`MVP-009`",
    "`MVP-010`",
    "make release-check",
    "make review-candidate",
    "make enterprise-review-send-refresh",
    "`ERG-003`: static sandbox/VM preflight disposition",
    "`ERG-002`: Mission Control display/import planning review",
    "What Remains Beyond Technical MVP",
]

BLOCKED_PHRASES = [
    "production deployment readiness",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "Mission Control execution authority",
    "Ithildin-managed VM/container lifecycle",
    "trusted-host promotion",
    "SIEM custody",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

REQUIRED_TARGETS = [
    "tool-surface-invariant-gate",
    "no-new-powers-guardrail",
    "policy-parity",
    "read-only-capability-inventory-gate",
    "read-only-project-intelligence",
    "next-capability-readiness",
    "review-candidate",
    "packet-redaction-scan",
    "workbench-readiness",
    "demo-flow-readiness",
    "demo-evidence-readiness",
    "mission-control-display-external-review-bundle",
    "sandbox-vm-static-preflight-external-review-bundle",
    "sandbox-vm-live-poc-decision-packet",
    "trusted-host-promotion-external-review-bundle",
    "production-identity-storage-architecture-check",
    "siem-export-adapter-architecture-check",
    "compliance-mapping-architecture-check",
    "public-positioning-external-review-bundle",
]

FORBIDDEN_PHRASES = [
    "enterprise-ready product",
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "Mission Control may execute",
    "approved for live VM",
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
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)
    progress = v1_progress_assessment.build_report(repo_root)
    next_action = enterprise_operator_next_action.build_report(repo_root)

    for label, report in [
        ("tool-surface-invariant-gate", tool_surface),
        ("next-capability-readiness", capability),
        ("v1-progress-assessment", progress),
        ("enterprise-operator-next-action", next_action),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if not doc:
        failures.append("technical MVP ticket map doc is missing")
    else:
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in doc:
                failures.append(f"technical MVP ticket map is missing phrase: {phrase}")
        for phrase in BLOCKED_PHRASES:
            if phrase not in doc:
                failures.append(f"technical MVP ticket map is missing blocked phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"technical MVP ticket map contains forbidden phrase: {phrase}")

    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    if progress.get("recommended_next_enterprise_review") not in ALLOWED_NEXT_ENTERPRISE_REVIEWS:
        failures.append("recommended next enterprise review is not allowed")
    if next_action.get("next_action") not in ALLOWED_NEXT_ACTIONS:
        failures.append("operator next action is not an allowed enterprise flow")
    if next_action.get("response_present_count") != 0:
        failures.append("enterprise response evidence is present; use response intake flow")

    for target in REQUIRED_TARGETS:
        if f"{target}:" not in makefile and f".PHONY: {target}" not in makefile:
            failures.append(f"referenced Make target is missing: {target}")

    if "technical-mvp-ticket-map:" not in makefile:
        failures.append("Make target is missing: technical-mvp-ticket-map")
    if "technical-mvp-ticket-map" not in release_check_body:
        failures.append("technical-mvp-ticket-map is missing from release-check")
    if "make technical-mvp-ticket-map" not in readme:
        failures.append("README is missing technical MVP ticket map command")
    if DOC_REL not in readme:
        failures.append("README is missing technical MVP ticket map doc")
    if DOC_REL not in docs_site:
        failures.append("technical MVP ticket map is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("technical MVP ticket map is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing technical MVP ticket map")
    if "technical-mvp-ticket-map" not in release_guardrails:
        failures.append("release guardrails do not require technical MVP ticket map")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ticket_map_doc": DOC_REL,
        "tool_count": tool_surface.get("tool_count"),
        "latest_implemented_tool": "sandbox.artifact.write_text",
        "selected_capability": capability.get("next_candidate"),
        "technical_mvp_ticket_count": 10,
        "recommended_next_enterprise_review": progress.get(
            "recommended_next_enterprise_review"
        ),
        "next_action": next_action.get("next_action"),
        "response_present_count": next_action.get("response_present_count"),
        "capability_expansion_allowed": False,
        "runtime_changes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin technical MVP ticket map",
        f"valid: {str(report['valid']).lower()}",
        f"ticket_map_doc: {report['ticket_map_doc']}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"technical_mvp_ticket_count: {report['technical_mvp_ticket_count']}",
        "recommended_next_enterprise_review: "
        f"{report['recommended_next_enterprise_review']}",
        f"next_action: {report['next_action']}",
        f"response_present_count: {report['response_present_count']}",
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
