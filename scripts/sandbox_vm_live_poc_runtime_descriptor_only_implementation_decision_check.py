"""Validate the ERG-004 runtime descriptor-only implementation decision draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    review_docs,
    sandbox_vm_live_poc_runtime_descriptor_only_implementation_ticket_check,
    sandbox_vm_live_poc_runtime_descriptor_only_plan_check,
    sandbox_vm_live_poc_runtime_gate_readiness_decision_record_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision.md"
)
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Implementation Decision"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check"

REQUIRED_PHRASES = [
    "Status: planning-only implementation decision draft for the future `ERG-004`",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `ready_for_descriptor_only_runtime_implementation_decision`.",
    "Current selected capability: `not selected`.",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check",
    "Future Runtime Surfaces Under Consideration",
    "Required Descriptor Facts",
    "Required Future Acceptance Evidence",
    "Explicit Non-Approvals",
    "Stop Conditions",
    "closed Pydantic descriptor schema",
    "local SQLite-backed descriptor record table",
    "admin-protected descriptor submission/status API",
    "read-only review-console rendering",
    "Agent Run correlation fields",
    "safe audit metadata",
    "negative transcript generation",
    "source-review handoff packet using `EXT-LIVE-DESC-###`",
    "descriptor_source: operator_supplied",
    "vm_lifecycle_source: operator_managed",
    "ithildin_live_inspection_performed: false",
    "ithildin_lifecycle_control_performed: false",
    "mission_control_runtime_authority_used: false",
    "trusted_host_promotion_performed: false",
]

REQUIRED_ACCEPTANCE_EVIDENCE = [
    "closed descriptor schema validation rejects unknown fields",
    "descriptors with forbidden authority claims fail closed",
    "outputs contain only labels, hashes, timestamps, enums, booleans, correlation IDs, "
    "status codes",
    "negative transcripts cover all rejected descriptor categories",
    "no API/MCP profile loading",
    "no governed tool count change occurs unless a separate explicit capability gate approves it",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation in this checkpoint",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "trusted-host promotion",
    "host writes or artifact promotion",
    "network expansion",
    "API/MCP profile loading",
    "SIEM adapter runtime behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "compliance automation",
    "shell, Docker, Kubernetes, or browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "plugin SDK behavior",
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
    text = _read(doc_path)
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    decision_record = sandbox_vm_live_poc_runtime_gate_readiness_decision_record_check.build_report(
        repo_root
    )
    descriptor_plan = sandbox_vm_live_poc_runtime_descriptor_only_plan_check.build_report(
        repo_root
    )
    implementation_ticket = (
        sandbox_vm_live_poc_runtime_descriptor_only_implementation_ticket_check.build_report(
            repo_root
        )
    )

    if not doc_path.exists():
        failures.append("runtime descriptor-only implementation decision doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(
                f"runtime descriptor-only implementation decision is missing phrase: {phrase}"
            )
    for phrase in REQUIRED_ACCEPTANCE_EVIDENCE:
        if phrase not in text:
            failures.append(
                "runtime descriptor-only implementation decision is missing "
                f"acceptance evidence: {phrase}"
            )
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(
                "runtime descriptor-only implementation decision is missing "
                f"non-approval: {phrase}"
            )
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                "runtime descriptor-only implementation decision contains forbidden phrase: "
                + phrase
            )

    if not decision_record["valid"]:
        failures.append("runtime gate-readiness decision record check is not valid")
    if decision_record.get("decision_outcome") != (
        "approved_for_descriptor_only_runtime_implementation_planning"
    ):
        failures.append("runtime gate-readiness decision outcome is not descriptor-only planning")
    if not descriptor_plan["valid"]:
        failures.append("runtime descriptor-only plan check is not valid")
    if not implementation_ticket["valid"]:
        failures.append("runtime descriptor-only implementation ticket check is not valid")
    if implementation_ticket.get("descriptor_only_implementation_ticket_ready") is not True:
        failures.append("runtime descriptor-only implementation ticket is not ready")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append(
            "runtime descriptor-only implementation decision is missing from review docs"
        )
    if DOC_REL not in docs_site:
        failures.append(
            "runtime descriptor-only implementation decision is missing from docs-site inputs"
        )
    if DOC_TITLE not in review_index:
        failures.append(
            "review-docs index is missing runtime descriptor-only implementation decision"
        )
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append(
            "runtime descriptor-only implementation decision check missing from release-check"
        )
    if TARGET not in release_guardrails:
        failures.append(
            "release guardrails do not require runtime descriptor-only implementation "
            "decision check"
        )
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime descriptor-only implementation decision command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime descriptor-only implementation decision doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runtime_descriptor_only_implementation_decision_doc": DOC_REL,
        "tool_count": 24,
        "erg_004_status": "ready_for_descriptor_only_runtime_implementation_decision",
        "decision_outcome": "descriptor_only_runtime_implementation_decision_draft_ready",
        "descriptor_only_planning_allowed": True,
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
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime descriptor-only implementation decision check",
        f"valid: {str(report['valid']).lower()}",
        "runtime_descriptor_only_implementation_decision_doc: "
        f"{report['runtime_descriptor_only_implementation_decision_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"decision_outcome: {report['decision_outcome']}",
        "descriptor_only_planning_allowed: "
        f"{str(report['descriptor_only_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        "live_vm_inspection_allowed: "
        f"{str(report['live_vm_inspection_allowed']).lower()}",
        "vm_container_lifecycle_allowed: "
        f"{str(report['vm_container_lifecycle_allowed']).lower()}",
        "sandbox_orchestration_allowed: "
        f"{str(report['sandbox_orchestration_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "local_model_invocation_allowed: "
        f"{str(report['local_model_invocation_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"host_writes_allowed: {str(report['host_writes_allowed']).lower()}",
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
