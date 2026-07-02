"""Validate the ERG-004 live sandbox/VM POC runtime proposal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, sandbox_vm_live_poc_implementation_plan_check

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-proposal.md"
DOC_NAME = "sandbox-vm-live-poc-runtime-proposal.md"
TARGET = "sandbox-vm-live-poc-runtime-proposal-check"

REQUIRED_PHRASES = [
    "Status: runtime-proposal-only packet for `ERG-004`.",
    "Current `ERG-004` status: `ready_for_runtime_proposal_review`.",
    "Current governed tool count: `24`.",
    "make sandbox-vm-live-poc-runtime-proposal-check",
    "operator-managed VM proof of concept",
    "Ithildin would not start,",
    "or otherwise manage the VM",
    "descriptor_source: operator_supplied",
    "vm_lifecycle_source: operator_managed",
    "ithildin_live_inspection_performed: false",
    "ithildin_lifecycle_control_performed: false",
    "mission_control_runtime_authority_used: false",
    "trusted_host_promotion_performed: false",
    "The reviewer must decide whether a bounded runtime implementation ticket may be drafted",
    "This proposal does not make that decision.",
    "Stop Conditions",
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
    "shell/Docker/Kubernetes/browser execution",
    "raw secret, prompt, model response, file content, diff, transcript, dependency name, package",
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
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    readiness = _read(repo_root / "docs/codex/enterprise-sandbox-control-plane-readiness.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    implementation_plan = sandbox_vm_live_poc_implementation_plan_check.build_report(repo_root)

    if not doc_path.exists():
        failures.append("sandbox/VM live POC runtime proposal is missing")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"runtime proposal is missing phrase: {phrase}")
    for field in REQUIRED_FIELDS:
        if field not in text:
            failures.append(f"runtime proposal is missing evidence field: {field}")
    for negative in REQUIRED_NEGATIVES:
        if negative not in text:
            failures.append(f"runtime proposal is missing negative case: {negative}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"runtime proposal contains forbidden phrase: {phrase}")

    if not implementation_plan["valid"]:
        failures.append("implementation plan check is not valid")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("runtime proposal is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("runtime proposal is missing from docs-site inputs")
    if "Sandbox/VM Live POC Runtime Proposal" not in review_index:
        failures.append("review-docs index is missing live POC runtime proposal")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("runtime proposal check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require runtime proposal check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing live POC runtime proposal command")
    for label, source in [
        ("enterprise runway", runway),
        ("enterprise gap matrix", gap_matrix),
        ("post-RC decision register", decision_register),
        ("enterprise sandbox readiness", readiness),
    ]:
        if DOC_NAME not in source:
            failures.append(f"{label} is missing {DOC_NAME}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runtime_proposal_doc": DOC_REL,
        "implementation_plan_valid": bool(implementation_plan["valid"]),
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_proposal_review",
        "vm_first": True,
        "operator_managed": True,
        "container_profiles_deferred": True,
        "runtime_proposal_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "runtime_ticket_allowed": False,
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
        "Ithildin sandbox/VM live POC runtime proposal check",
        f"valid: {str(report['valid']).lower()}",
        f"runtime_proposal_doc: {report['runtime_proposal_doc']}",
        f"implementation_plan_valid: {str(report['implementation_plan_valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"vm_first: {str(report['vm_first']).lower()}",
        f"operator_managed: {str(report['operator_managed']).lower()}",
        f"runtime_proposal_allowed: {str(report['runtime_proposal_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"runtime_ticket_allowed: {str(report['runtime_ticket_allowed']).lower()}",
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
