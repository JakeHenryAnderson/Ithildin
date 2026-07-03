"""Validate the ERG-004 runtime gate-readiness response intake template."""

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
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md"
DOC_NAME = "sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md"
AREA = "sandbox-vm-live-poc-runtime-gate-readiness"
NAMESPACE = "LIVE-GATE"

REQUIRED_PHRASES = [
    "Status: response-intake template for `ERG-004` runtime gate-readiness review.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status before reviewer disposition: "
    "`ready_for_runtime_implementation_gate_review`.",
    "Current selected capability: `not selected`.",
    "Finding namespace: `EXT-LIVE-GATE-###`.",
    "Reviewed area for normalization: `sandbox-vm-live-poc-runtime-gate-readiness`.",
    "Required Disposition Answers",
    "Finding Extraction Table",
    "EXT-LIVE-GATE-###",
    "--area sandbox-vm-live-poc-runtime-gate-readiness",
    "mutates_findings: false",
    "closes_external_review: false",
    "approved_for_descriptor_only_runtime_implementation_planning",
    "Only a later committed decision record may move `ERG-004`",
]

REQUIRED_QUESTIONS = [
    "Did the reviewer inspect the runtime gate-readiness packet",
    "Does the reviewer agree the packet preserves operator-managed VM lifecycle",
    "Does the reviewer agree the descriptor contract stays closed",
    "Do the negative fixtures block lifecycle control",
    "Does the reviewer agree source review remains required",
    "Are there any critical/high findings",
    "may a later committed decision record consider",
    "avoid approving runtime implementation",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "host writes",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "host writes are approved",
    "network expansion is approved",
    "API/MCP profile loading is approved",
    "new governed tool powers are approved",
    "public security product approved",
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
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    bundle_doc = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md"
    )
    skeleton_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"
    )
    checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    active_route = _read(repo_root / "docs/codex/enterprise-active-route-clarity.md")
    decision_record = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("runtime gate-readiness response intake doc is missing")
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

    if AREA not in external_response_normalize.AREA_NAMESPACES:
        failures.append("external response normalizer lacks runtime gate-readiness area")
    elif external_response_normalize.AREA_NAMESPACES[AREA] != NAMESPACE:
        failures.append("external response normalizer uses wrong runtime gate namespace")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime gate-readiness response intake is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("runtime gate-readiness response intake is missing from docs-site inputs")
    if "Sandbox/VM Live POC Runtime Gate Readiness Response Intake" not in review_index:
        failures.append("review-docs index is missing runtime gate-readiness intake")
    if DOC_NAME not in bundle_doc:
        failures.append("runtime gate-readiness bundle doc is missing response intake pointer")
    if DOC_NAME not in skeleton_doc:
        failures.append("runtime gate-readiness skeleton is missing response intake pointer")
    if not decision_record:
        if DOC_NAME not in checkpoint:
            failures.append("enterprise current checkpoint is missing response intake pointer")
        if DOC_NAME not in active_route:
            failures.append("enterprise active route is missing response intake pointer")
    if "sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check:" not in makefile:
        failures.append("Make target is missing: runtime gate-readiness response intake")
    if "sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check" not in (
        release_check_body
    ):
        failures.append("runtime gate-readiness response intake check missing from release-check")
    if "sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check" not in (
        release_guardrails
    ):
        failures.append("release guardrails do not require runtime gate-readiness intake")
    if "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check" not in (
        readme
    ):
        failures.append("README is missing runtime gate-readiness response intake command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime gate-readiness response intake doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "intake_doc": DOC_REL,
        "tool_count": 24,
        "area": AREA,
        "finding_namespace": "EXT-LIVE-GATE-###",
        "erg_004_status": "ready_for_runtime_implementation_gate_review",
        "mutates_findings": False,
        "closes_external_review": False,
        "descriptor_only_planning_allowed": False,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime gate-readiness response intake check",
        f"valid: {str(report['valid']).lower()}",
        f"intake_doc: {report['intake_doc']}",
        f"tool_count: {report['tool_count']}",
        f"area: {report['area']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"mutates_findings: {str(report['mutates_findings']).lower()}",
        f"closes_external_review: {str(report['closes_external_review']).lower()}",
        "descriptor_only_planning_allowed: "
        f"{str(report['descriptor_only_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
