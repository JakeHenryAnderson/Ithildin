"""Validate the sandbox/VM live POC external response intake template."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-external-response-intake.md"
DOC_NAME = "sandbox-vm-live-poc-external-response-intake.md"

REQUIRED_PHRASES = [
    "Status: response-intake template for blocked `ERG-004`.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status before reviewer disposition: `blocked`.",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-LIVE-POC-###`.",
    "Reviewed area for normalization: `sandbox-vm-live-poc`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-LIVE-POC-###",
    "--area sandbox-vm-live-poc",
    "mutates_findings: false",
    "closes_external_review: false",
    "approve_limited_operator_managed_poc_planning",
    "Only a later committed triage update may move `ERG-004` away from `blocked`",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the live POC decision packet",
    "Does the reviewer agree `ERG-004` remains blocked",
    "Are the live POC preconditions complete enough",
    "Is the operator-managed VM/container profile boundary clear enough",
    "Are the cleanup transcript and failure transcript requirements sufficient",
    "Are the cross-source evidence fields sufficient",
    "Are there any critical/high findings",
    "may a later committed decision record consider",
    "avoid approving runtime implementation",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "implementation planning without a later committed decision record",
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "local model invocation",
    "Mission Control runtime behavior",
    "trusted-host promotion",
    "network expansion",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "implementation planning is approved",
    "runtime implementation is approved",
    "live VM control is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
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
    decision_packet = (repo_root / "docs/codex/sandbox-vm-live-poc-decision-packet.md").read_text(
        encoding="utf-8"
    )
    preconditions_map = (
        repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md"
    ).read_text(encoding="utf-8")
    packet_script = (repo_root / "scripts/sandbox_vm_live_poc_decision_packet.py").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("sandbox/VM live POC external response intake doc is missing")
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

    if "sandbox-vm-live-poc" not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks sandbox-vm-live-poc area")
    elif external_response_normalize.AREA_NAMESPACES["sandbox-vm-live-poc"] != "LIVE-POC":
        failures.append("external response normalizer uses wrong live POC namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("sandbox/VM live POC intake doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("sandbox/VM live POC intake doc is missing from docs-site inputs")
    if DOC_REL not in packet_script:
        failures.append("live POC decision packet does not bundle intake doc")
    if DOC_NAME not in decision_packet:
        failures.append("live POC decision packet doc does not point to external response intake")
    if DOC_NAME not in preconditions_map:
        failures.append("live POC preconditions map does not point to external response intake")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing live POC external response intake pointer")
    if DOC_NAME not in gap_matrix:
        failures.append(
            "enterprise gap matrix is missing live POC external response intake pointer"
        )
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing live POC external response intake")
    if "Sandbox/VM Live POC External Response Intake" not in review_index:
        failures.append("review-docs index is missing live POC external response intake entry")
    if "sandbox-vm-live-poc-external-response-intake-check:" not in makefile:
        failures.append(
            "Make target is missing: sandbox-vm-live-poc-external-response-intake-check"
        )
    if "sandbox-vm-live-poc-external-response-intake-check" not in release_check_body:
        failures.append(
            "sandbox-vm-live-poc-external-response-intake-check missing from release-check"
        )
    if "make sandbox-vm-live-poc-external-response-intake-check" not in readme:
        failures.append("README is missing sandbox/VM live POC intake command")
    if DOC_REL not in readme:
        failures.append("README is missing sandbox/VM live POC intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": "sandbox-vm-live-poc",
        "finding_namespace": "EXT-LIVE-POC-###",
        "erg_004_status": "blocked",
        "mutates_findings": False,
        "closes_external_review": False,
        "implementation_planning_allowed": False,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC external response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
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
