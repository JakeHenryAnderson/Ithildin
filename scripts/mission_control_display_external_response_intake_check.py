"""Validate the Mission Control display external response intake template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import external_response_normalize, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-display-external-response-intake.md"
DOC_NAME = "mission-control-display-external-response-intake.md"

REQUIRED_PHRASES = [
    "Status: response-intake template for planning-only `ERG-002`.",
    "Current governed tool count: `24`.",
    "Current `ERG-002` status before reviewer disposition: `planning_only`.",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-MC-DISPLAY-###`.",
    "Reviewed area for normalization: `mission-control-display`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-MC-DISPLAY-###",
    "--area mission-control-display",
    "mutates_findings: false",
    "closes_external_review: false",
    "continue_design_only",
    "revise_before_more_planning",
    "block_runtime_implementation",
    "Only a later committed triage update may move `ERG-002` away",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the Mission Control display disposition packet",
    "Is the display-only importer boundary coherent enough",
    "Are operator-selected local packet sources",
    "Are display allowlists and hidden-field denylists complete enough",
    "Are Mission Control non-authority boundaries clear",
    "Are there any critical/high findings",
    "may the lane continue design-only Mission Control-side",
    "avoid approving Mission Control runtime importer behavior",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "Mission Control runtime importer behavior",
    "Mission Control execution authority",
    "Mission Control policy authority",
    "Mission Control approval authority",
    "Mission Control audit authority",
    "API callbacks",
    "polling or mutating Ithildin APIs",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "trusted-host promotion",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote delivery",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "Mission Control runtime importer behavior is approved",
    "Mission Control execution authority is approved",
    "Mission Control policy authority is approved",
    "Mission Control approval authority is approved",
    "Mission Control audit authority is approved",
    "API callbacks are approved",
    "polling or mutating Ithildin APIs are approved",
    "local model invocation is approved",
    "sandbox orchestration is approved",
    "trusted-host promotion is approved",
    "SIEM adapter behavior is approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    disposition_packet = (
        repo_root / "docs/codex/mission-control-display-disposition-packet.md"
    ).read_text(encoding="utf-8")
    decision_intake = (
        repo_root / "docs/codex/mission-control-display-decision-intake.md"
    ).read_text(encoding="utf-8")
    packet_script = (
        repo_root / "scripts/mission_control_display_disposition_packet.py"
    ).read_text(encoding="utf-8")
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("Mission Control display external response intake doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"intake doc is missing phrase: {phrase}")
        for phrase in REQUIRED_QUESTIONS:
            if phrase not in text:
                failures.append(f"intake doc is missing disposition question: {phrase}")
        for phrase in REQUIRED_BLOCKED_BOUNDARIES:
            if phrase not in text:
                failures.append(f"intake doc is missing blocked boundary: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"intake doc contains forbidden phrase: {phrase}")

    if "mission-control-display" not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks mission-control-display area")
    elif external_response_normalize.AREA_NAMESPACES["mission-control-display"] != "MC-DISPLAY":
        failures.append("external response normalizer uses wrong Mission Control display namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("Mission Control display intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("Mission Control display intake doc is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("Mission Control display disposition packet does not bundle intake doc")
    if DOC_NAME not in disposition_packet:
        failures.append("Mission Control display disposition doc does not point to intake")
    if DOC_NAME not in decision_intake:
        failures.append("Mission Control display decision intake does not point to response intake")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing Mission Control display intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing Mission Control display intake pointer")
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing Mission Control display intake")
    if "Mission Control Display External Response Intake" not in review_index:
        failures.append("review-docs index is missing Mission Control display intake entry")
    if "mission-control-display-external-response-intake-check:" not in makefile:
        failures.append(
            "Make target is missing: mission-control-display-external-response-intake-check"
        )
    if "mission-control-display-external-response-intake-check" not in release_check_body:
        failures.append(
            "mission-control-display-external-response-intake-check missing from release-check"
        )
    if "mission-control-display-external-response-intake-check" not in release_guardrails:
        failures.append("release guardrails do not require Mission Control display intake check")
    if "make mission-control-display-external-response-intake-check" not in readme:
        failures.append("README is missing Mission Control display intake command")
    if DOC_REL not in readme:
        failures.append("README is missing Mission Control display intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": "mission-control-display",
        "finding_namespace": "EXT-MC-DISPLAY-###",
        "erg_002_status": "planning_only",
        "mutates_findings": False,
        "closes_external_review": False,
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_authority_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "api_callbacks_allowed": False,
        "polling_or_mutating_ithildin_apis_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"api_callbacks_allowed: {str(report['api_callbacks_allowed']).lower()}",
        "polling_or_mutating_ithildin_apis_allowed: "
        f"{str(report['polling_or_mutating_ithildin_apis_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
