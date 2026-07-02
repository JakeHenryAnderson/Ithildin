"""Validate the enterprise progress model and its release-readiness wiring."""

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
    enterprise_readiness_gap_matrix_check,
    enterprise_response_status_board,
    next_capability_readiness,
    review_docs,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-progress-model.md"
DOC_TITLE = "Ithildin Enterprise Progress Model"
ALLOWED_NEXT_ACTIONS = {
    "send_erg_003_and_erg_002",
    "prepare_erg004_runtime_implementation_gate",
}

REQUIRED_PHRASES = [
    "Status: checked progress model",
    "Governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Recommended next enterprise review: `ERG-004`",
    "Recommended send set: `ERG-004`",
    "Enterprise response evidence present: `0`",
    "Enterprise closure-ready lanes: `0`",
    "Capability expansion: blocked",
    "Runtime changes: blocked",
    "Public/security-product positioning: blocked",
    "Local governed tool gateway | `92-96%`",
    "v1.0 local-preview RC | `84-90%`",
    "Operator workbench and demo path | `78-86%`",
    "Mission Control display/import path | `50-65%`",
    "Sandbox/VM governed agent workflow | `45-60%`",
    "Enterprise control-plane architecture | `35-50%`",
    "Long-term governed-agent workbench vision | `55-65%`",
    "Checkpoint A: v1.0 Local-Preview RC",
    "Checkpoint B: Mission Control Display Integration",
    "Checkpoint C: Sandbox/VM Static Preflight Disposition",
    "Checkpoint D: Live Sandbox/VM Proof Of Concept",
    "Checkpoint E: Trusted-Host Promotion",
    "Checkpoint F: Enterprise Architecture Lanes",
    "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
    "make sandbox-vm-live-poc-runtime-implementation-gate-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
    "Do not manually promote a lane",
]

BLOCKED_PHRASES = [
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "SIEM adapter runtime behavior",
    "production identity or enterprise RBAC",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP hosting",
    "compliance automation",
    "public/security-product positioning",
    "new governed tool powers",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "secure sandbox",
    "compliance-grade",
    "tamper-proof",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
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

    capability = next_capability_readiness.build_report(repo_root)
    operator_next_action = enterprise_operator_next_action.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)
    progress = v1_progress_assessment.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)

    failures.extend(f"next-capability-readiness: {failure}" for failure in capability["failures"])
    failures.extend(
        f"enterprise-operator-next-action: {failure}"
        for failure in operator_next_action["failures"]
    )
    failures.extend(
        f"enterprise-response-status-board: {failure}"
        for failure in response_status["failures"]
    )
    failures.extend(f"v1-progress-assessment: {failure}" for failure in progress["failures"])
    failures.extend(f"enterprise-gap-matrix: {failure}" for failure in gap_matrix["failures"])

    doc_path = repo_root / DOC_REL
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if capability.get("tool_count") != 24:
        failures.append("next capability readiness tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability selected candidate is not blocked")
    next_action = operator_next_action.get("next_action")
    if next_action not in ALLOWED_NEXT_ACTIONS:
        failures.append("operator next action is not an allowed enterprise flow")
    if response_status.get("response_present_count") != 0:
        failures.append("enterprise responses are present; use response application flow")
    if response_status.get("closure_ready_count") != 0:
        failures.append("enterprise closure-ready lanes exist; use lane-specific closure flow")
    if progress.get("progress_bands", {}).get("v1_local_preview_rc") != "84-90%":
        failures.append("v1 local-preview RC progress band drifted")
    if progress.get("progress_bands", {}).get("operator_workbench_demo") != "78-86%":
        failures.append("operator workbench progress band drifted")
    if progress.get("progress_bands", {}).get("enterprise_security_product_readiness") != "35-50%":
        failures.append("enterprise progress band drifted")
    if gap_matrix.get("gap_count") != 10:
        failures.append("enterprise gap count is not 10")

    boundary_flags = {
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }
    for key, expected in boundary_flags.items():
        if key in response_status and response_status.get(key) is not expected:
            failures.append(f"response status boundary flag drifted: {key}")

    if not doc_path.exists():
        failures.append("enterprise progress model doc is missing")
        doc = ""
    else:
        doc = doc_path.read_text(encoding="utf-8")
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in doc:
                failures.append(f"enterprise progress model is missing phrase: {phrase}")
        for phrase in BLOCKED_PHRASES:
            if phrase not in doc:
                failures.append(f"enterprise progress model is missing blocked phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"enterprise progress model contains forbidden phrase: {phrase}")

    if "enterprise-progress-model:" not in makefile:
        failures.append("Make target is missing: enterprise-progress-model")
    if "enterprise-progress-model" not in release_check_body:
        failures.append("enterprise-progress-model is missing from release-check")
    if "make enterprise-progress-model" not in readme:
        failures.append("README is missing enterprise-progress-model command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise progress model doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise progress model is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise progress model is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise progress model")
    if "enterprise-progress-model" not in release_guardrails:
        failures.append("release guardrails do not require enterprise progress model")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "progress_model_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": capability.get("next_candidate"),
        "recommended_send_set": operator_next_action.get("recommended_send_set", []),
        "recommended_next_enterprise_review": operator_next_action.get(
            "recommended_next_enterprise_review"
        ),
        "next_action": next_action,
        "action_commands": operator_next_action.get("action_commands", []),
        "handoff_artifacts": operator_next_action.get("handoff_artifacts", []),
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "enterprise_gap_count": gap_matrix.get("gap_count"),
        "progress_bands": {
            "local_governed_tool_gateway": "92-96%",
            "v1_local_preview_rc": "84-90%",
            "operator_workbench_demo": "78-86%",
            "mission_control_display_import": "50-65%",
            "sandbox_vm_governed_workflow": "45-60%",
            "enterprise_control_plane_architecture": "35-50%",
            "long_term_governed_agent_workbench": "55-65%",
        },
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise progress model",
        f"valid: {str(report['valid']).lower()}",
        f"progress_model_doc: {report['progress_model_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: "
        + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"next_action: {report.get('next_action', 'unknown')}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands", [])],
        "handoff_artifacts:",
        *[
            f"- {artifact['label']}: {artifact['path']}"
            for artifact in report.get("handoff_artifacts", [])
        ],
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"enterprise_gap_count: {report.get('enterprise_gap_count', 'unknown')}",
        "progress_bands:",
    ]
    lines.extend(
        f"- {name}: {band}" for name, band in report["progress_bands"].items()
    )
    lines.extend(
        [
            f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
            "mission_control_runtime_allowed: "
            f"{str(report['mission_control_runtime_allowed']).lower()}",
            "live_vm_inspection_allowed: "
            f"{str(report['live_vm_inspection_allowed']).lower()}",
            "sandbox_orchestration_allowed: "
            f"{str(report['sandbox_orchestration_allowed']).lower()}",
            "trusted_host_promotion_allowed: "
            f"{str(report['trusted_host_promotion_allowed']).lower()}",
            f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
            "compliance_automation_allowed: "
            f"{str(report['compliance_automation_allowed']).lower()}",
            "public_security_product_positioning_allowed: "
            f"{str(report['public_security_product_positioning_allowed']).lower()}",
            f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        ]
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
