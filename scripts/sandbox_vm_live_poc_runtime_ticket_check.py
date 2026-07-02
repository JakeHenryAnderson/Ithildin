"""Validate the ERG-004 live sandbox/VM POC runtime ticket draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_runtime_proposal_check

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-ticket.md"
DOC_NAME = "sandbox-vm-live-poc-runtime-ticket.md"
TARGET = "sandbox-vm-live-poc-runtime-ticket-check"

REQUIRED_PHRASES = [
    "Status: draft-only implementation ticket for a later `ERG-004` runtime gate.",
    "Current governed tool count: `24`.",
    "Current `ERG-004` status: `ready_for_runtime_ticket_draft`.",
    "make sandbox-vm-live-poc-runtime-ticket-check",
    "approve_draft_runtime_ticket",
    "does not approve runtime implementation",
    (
        "Ithildin must not start, stop, pause, snapshot, shell into, inspect, "
        "or otherwise manage the VM"
    ),
    "descriptor_source: operator_supplied",
    "vm_lifecycle_source: operator_managed",
    "ithildin_live_inspection_performed: false",
    "ithildin_lifecycle_control_performed: false",
    "mission_control_runtime_authority_used: false",
    "trusted_host_promotion_performed: false",
    "future runtime work remains blocked until a separate implementation gate",
]

REQUIRED_INPUTS = [
    "sandbox-vm-live-poc-decision-record.md",
    "sandbox-vm-live-poc-implementation-plan.md",
    "sandbox-vm-live-poc-runtime-proposal.md",
    "sandbox-vm-live-poc-runtime-proposal-review-bundle.md",
    "sandbox-vm-live-poc-evidence-contract.md",
    "sandbox-vm-live-poc-preconditions-map.md",
    "sandbox-vm-live-poc-prerequisite-disposition-dry-run.md",
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-proposal-review/",
]

REQUIRED_FIELDS = [
    "operator_intent_id",
    "principal_id",
    "workspace_id",
    "run_id",
    "sandbox_id",
    "sandbox_profile_id",
    "vm_profile_label",
    "vm_profile_hash",
    "mount_root_label",
    "workspace_mount_label",
    "network_posture_label",
    "model_client_label",
    "model_request_hash",
    "tool_call_correlation_id",
    "approval_correlation_id",
    "audit_head_hash",
    "signed_export_hash",
    "cleanup_plan_hash",
    "cleanup_transcript_hash",
    "failure_transcript_hash",
    "mission_control_display_packet_hash",
    "promotion_status: not_promoted",
]

REQUIRED_NEGATIVES = [
    "attempted VM/container lifecycle management by Ithildin",
    "attempted live VM/container inspection by Ithildin",
    "attempted local model invocation by Ithildin",
    "attempted Mission Control execution, approval, policy, or audit authority",
    "attempted trusted-host promotion",
    "attempted host write or artifact promotion",
    "arbitrary network expansion",
    "API/MCP profile loading",
    "shell/Docker/Kubernetes/browser execution",
    "raw secret, prompt, model response, file content, diff, transcript, dependency name, package",
]

REQUIRED_NON_GOALS = [
    "runtime implementation",
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
    "new governed tool powers are approved",
    "public security product approved",
]


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
    runtime_proposal = sandbox_vm_live_poc_runtime_proposal_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("sandbox/VM live POC runtime ticket is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"runtime ticket is missing phrase: {phrase}")
    for phrase in REQUIRED_INPUTS:
        if phrase not in text:
            failures.append(f"runtime ticket is missing input reference: {phrase}")
    for field in REQUIRED_FIELDS:
        if field not in text:
            failures.append(f"runtime ticket is missing descriptor field: {field}")
    for negative in REQUIRED_NEGATIVES:
        if negative not in text:
            failures.append(f"runtime ticket is missing negative case: {negative}")
    for non_goal in REQUIRED_NON_GOALS:
        if non_goal not in text:
            failures.append(f"runtime ticket is missing non-goal: {non_goal}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"runtime ticket contains forbidden phrase: {phrase}")

    if not runtime_proposal["valid"]:
        failures.append("runtime proposal check is not valid")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime ticket is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("runtime ticket is missing from docs-site inputs")
    if "Sandbox/VM Live POC Runtime Ticket" not in review_index:
        failures.append("review-docs index is missing live POC runtime ticket")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("runtime ticket check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require runtime ticket check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing live POC runtime ticket command")
    if DOC_REL not in readme:
        failures.append("README is missing live POC runtime ticket doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runtime_ticket_doc": DOC_REL,
        "runtime_proposal_valid": bool(runtime_proposal["valid"]),
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_ticket_draft",
        "ticket_draft_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "runtime_ticket_is_implementation_gate": False,
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
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime ticket check",
        f"valid: {str(report['valid']).lower()}",
        f"runtime_ticket_doc: {report['runtime_ticket_doc']}",
        f"runtime_proposal_valid: {str(report['runtime_proposal_valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"ticket_draft_allowed: {str(report['ticket_draft_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        "runtime_ticket_is_implementation_gate: "
        f"{str(report['runtime_ticket_is_implementation_gate']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "external_review_required_before_runtime: "
        f"{str(report['external_review_required_before_runtime']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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


if __name__ == "__main__":
    raise SystemExit(main())
