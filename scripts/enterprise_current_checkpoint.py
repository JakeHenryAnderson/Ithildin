"""Validate the current enterprise-readiness checkpoint summary."""

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
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    next_capability_readiness,
    review_docs,
    v1_progress_assessment,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-current-checkpoint.md"
DOC_TITLE = "Enterprise Current Checkpoint"
PRE_DISPOSITION_ACTION = "send_erg_003_and_erg_002"
POST_DISPOSITION_ACTION = "prepare_erg004_runtime_implementation_gate"
DESCRIPTOR_ONLY_PLANNING_ACTION = "prepare_erg004_descriptor_only_runtime_planning"
ERG005_TRUSTED_HOST_ACTION = "prepare_erg005_trusted_host_promotion_review"
PIS_ARCHITECTURE_REVIEW_ACTION = (
    "prepare_erg006_erg007_production_identity_storage_architecture_review"
)
ALLOWED_NEXT_ACTIONS = {
    PRE_DISPOSITION_ACTION,
    POST_DISPOSITION_ACTION,
    DESCRIPTOR_ONLY_PLANNING_ACTION,
    ERG005_TRUSTED_HOST_ACTION,
    PIS_ARCHITECTURE_REVIEW_ACTION,
}

REQUIRED_PHRASES = [
    "Status: checked operator checkpoint",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "make enterprise-current-checkpoint",
    "v1.0 local-preview RC packet generation is ready through `make review-candidate`",
    "Capability expansion remains blocked",
    "Runtime changes remain blocked",
    "Public/security-product positioning remains blocked",
    "Enterprise response evidence is not present yet",
    "`ERG-004`: descriptor-only sandbox/VM live POC runtime source review is locally dispositioned",
    "`ERG-005`: staging-only trusted-host promotion runtime source findings are dispositioned",
    "`ERG-006`/`ERG-007`: production identity/storage architecture review is next",
    "make production-identity-storage-architecture-check",
    "make production-identity-storage-disposition-packet-check",
    "make production-identity-storage-external-review-bundle-check",
    "make production-identity-storage-response-kit-check",
    "The historical ERG-003/ERG-002 dual-send commands remain available only for "
    "lineage and fallback.",
    "What This Checkpoint Does Not Approve",
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
    "enterprise-ready",
    "production-ready",
    "approved for live VM",
    "Mission Control may execute",
    "sandbox orchestration allowed",
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

    progress = v1_progress_assessment.build_report(repo_root)
    send_readiness = enterprise_review_send_readiness.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)
    capability = next_capability_readiness.build_report(repo_root)
    operator_next_action = enterprise_operator_next_action.build_report(repo_root)

    failures.extend(f"v1-progress-assessment: {failure}" for failure in progress["failures"])
    failures.extend(
        f"enterprise-review-send-readiness: {failure}"
        for failure in send_readiness["failures"]
    )
    failures.extend(
        f"enterprise-response-status-board: {failure}"
        for failure in response_status["failures"]
    )
    failures.extend(f"next-capability-readiness: {failure}" for failure in capability["failures"])
    failures.extend(
        f"enterprise-operator-next-action: {failure}"
        for failure in operator_next_action["failures"]
    )

    doc_path = repo_root / DOC_REL
    doc = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if progress.get("tool_count") != 24:
        failures.append("progress assessment tool count is not 24")
    if send_readiness.get("tool_count") != 24:
        failures.append("send-readiness tool count is not 24")
    if response_status.get("tool_count") != 24:
        failures.append("response-status tool count is not 24")
    if capability.get("next_candidate") != "not selected":
        failures.append("next capability candidate is selected")
    next_action = operator_next_action.get("next_action")
    post_disposition_mode = next_action == POST_DISPOSITION_ACTION
    descriptor_only_mode = next_action == DESCRIPTOR_ONLY_PLANNING_ACTION
    erg005_mode = next_action == ERG005_TRUSTED_HOST_ACTION
    pis_mode = next_action == PIS_ARCHITECTURE_REVIEW_ACTION
    if (
        not post_disposition_mode
        and send_readiness.get("recommended_now") != ["ERG-003", "ERG-002"]
    ):
        failures.append("recommended enterprise send set must remain ERG-003 then ERG-002")
    if descriptor_only_mode and operator_next_action.get("recommended_send_set") != [
        "ERG-004"
    ]:
        failures.append("operator next action must recommend ERG-004 in descriptor-only mode")
    if erg005_mode and operator_next_action.get("recommended_send_set") != ["ERG-005"]:
        failures.append(
            "operator next action must recommend ERG-005 after descriptor-only disposition"
        )
    if pis_mode and operator_next_action.get("recommended_send_set") != [
        "ERG-006",
        "ERG-007",
    ]:
        failures.append(
            "operator next action must recommend ERG-006/ERG-007 after ERG-005 source disposition"
        )
    if next_action not in ALLOWED_NEXT_ACTIONS:
        failures.append("operator next action is not an allowed enterprise flow")
    if response_status.get("response_present_count") != 0:
        failures.append(
            "enterprise responses are present; intake them before using this checkpoint"
        )
    if response_status.get("closure_ready_count") != 0:
        failures.append("enterprise closures are ready; run lane-specific closure flow")

    boundary_flags = {
        "capability_expansion_allowed": False,
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
    if progress.get("capability_expansion_allowed") is not False:
        failures.append("progress assessment allows capability expansion")
    if progress.get("runtime_changes_allowed") is not False:
        failures.append("progress assessment allows runtime changes")
    if progress.get("public_security_product_positioning_allowed") is not False:
        failures.append("progress assessment allows public/security-product positioning")
    for key, expected in boundary_flags.items():
        if key in send_readiness and send_readiness[key] is not expected:
            failures.append(f"send-readiness boundary flag drifted: {key}")
        if key in response_status and response_status[key] is not expected:
            failures.append(f"response-status boundary flag drifted: {key}")

    for phrase in REQUIRED_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise checkpoint doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise checkpoint doc is missing blocked phrase: {phrase}")
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"enterprise checkpoint doc contains forbidden phrase: {phrase}")

    if "enterprise-current-checkpoint:" not in makefile:
        failures.append("Make target is missing: enterprise-current-checkpoint")
    if "enterprise-current-checkpoint" not in release_check_body:
        failures.append("enterprise-current-checkpoint is missing from release-check")
    if "make enterprise-current-checkpoint" not in readme:
        failures.append("README is missing enterprise-current-checkpoint command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise current checkpoint doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise current checkpoint is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise current checkpoint is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise current checkpoint")
    if "enterprise-current-checkpoint" not in release_guardrails:
        failures.append("release guardrails do not require enterprise current checkpoint")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checkpoint_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": capability.get("next_candidate"),
        "recommended_send_set": operator_next_action.get(
            "recommended_send_set",
            send_readiness.get("recommended_now"),
        ),
        "recommended_next_enterprise_review": progress.get(
            "recommended_next_enterprise_review"
        ),
        "next_action": next_action,
        "action_commands": operator_next_action.get("action_commands", []),
        "next_after_send_commands": operator_next_action.get(
            "next_after_send_commands", []
        ),
        "handoff_artifacts": operator_next_action.get("handoff_artifacts", []),
        "operator_next_action_doc": operator_next_action.get("next_action_doc"),
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise current checkpoint",
        f"valid: {str(report['valid']).lower()}",
        f"checkpoint_doc: {report['checkpoint_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: "
        + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"next_action: {report.get('next_action', 'unknown')}",
        "action_commands:",
        *[f"- {command}" for command in report.get("action_commands", [])],
        "next_after_send_commands:",
        *[
            f"- {command}"
            for command in report.get("next_after_send_commands", [])
        ],
        "handoff_artifacts:",
        *[
            f"- {artifact['label']}: {artifact['path']}"
            for artifact in report.get("handoff_artifacts", [])
        ],
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
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
