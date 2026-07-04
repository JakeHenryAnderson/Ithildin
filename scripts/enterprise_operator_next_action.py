"""Validate the current enterprise operator next action."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-operator-next-action.md"
DOC_TITLE = "Enterprise Operator Next Action"
NORMALIZED_RESPONSE_RELS = [
    "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
    "var/review-runs/mission-control-display/normalized-response.json",
    "var/review-runs/trusted-host-promotion/normalized-response.json",
    "var/review-runs/production-identity-storage/normalized-response.json",
    "var/review-runs/siem-export-adapter/normalized-response.json",
    "var/review-runs/compliance-mapping/normalized-response.json",
    "var/review-runs/sandbox-vm-live-poc/normalized-response.json",
    "var/review-runs/public-security-product-positioning/normalized-response.json",
]

SEND_COMMANDS = [
    "make release-check",
    "make review-candidate",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-now",
]

NEXT_AFTER_SEND_COMMANDS = [
    "make enterprise-review-send-receipt-copy",
    "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
    "make enterprise-response-waiting-room",
    "make enterprise-response-now",
    "make enterprise-response-paste-preflight",
]

RESPONSE_COMMANDS = [
    "make enterprise-response-intake-refresh",
]

POST_ERG003_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-ticket-check",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle-check",
]

RUNTIME_GATE_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
    "make sandbox-vm-live-poc-runtime-implementation-gate-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check",
]

DESCRIPTOR_ONLY_PLANNING_COMMANDS = [
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
]

SEND_ARTIFACTS = [
    {
        "label": "dual_review_outbox",
        "path": "var/review-packets/v3/enterprise-dual-review-outbox",
        "description": "copied ERG-003/ERG-002 attachment set",
    },
    {
        "label": "send_manifest",
        "path": "var/review-packets/v3/enterprise-review-send-manifest",
        "description": "checked manifest with prompt and attachment pointers",
    },
    {
        "label": "send_quickstart",
        "path": "var/review-packets/v3/enterprise-review-send-quickstart",
        "description": "one-page operator index for current send artifacts",
    },
    {
        "label": "submission_prompt",
        "path": "var/review-packets/v3/enterprise-review-submission-prompt",
        "description": "paste-ready external-review submission prompt",
    },
    {
        "label": "send_receipt_template",
        "path": "var/review-packets/v3/enterprise-review-send-receipt-template",
        "description": "operator receipt template to fill after sending",
    },
    {
        "label": "send_receipt_copy",
        "path": (
            "var/review-runs/enterprise-review-send-receipts/"
            "enterprise-review-send-receipt-copy.json"
        ),
        "description": "ignored copied receipt path for the human send step",
    },
    {
        "label": "send_package",
        "path": "var/review-packets/v3/enterprise-review-send-package",
        "description": "compact package index for current send artifacts",
    },
    {
        "label": "upload_staging",
        "path": "var/review-packets/v3/enterprise-review-upload-staging",
        "description": "10-attachment-friendly upload staging batches",
    },
    {
        "label": "dual_response_inbox",
        "path": "var/review-runs/enterprise-dual-response-inbox",
        "description": "ignored raw-response inbox placeholders for ERG-003 and ERG-002",
    },
    {
        "label": "send_session_record",
        "path": "var/review-runs/enterprise-review-send-session-record",
        "description": "local non-authoritative scaffold for operator send details",
    },
]

RESPONSE_ARTIFACTS = [
    {
        "label": "response_inbox",
        "path": "var/review-runs/enterprise-response-inbox",
        "description": "ignored raw-response inbox for pasted reviewer responses",
    },
    {
        "label": "response_status_board",
        "path": "var/review-runs/enterprise-response-status-board",
        "description": "display-only response status board output",
    },
]

POST_ERG003_ARTIFACTS = [
    {
        "label": "dual_response_disposition_record",
        "path": "docs/codex/enterprise-dual-response-disposition-record.md",
        "description": "committed ERG-003/ERG-002 response disposition record",
    },
    {
        "label": "live_poc_runtime_ticket",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-ticket.md",
        "description": "draft-only runtime ticket for a later implementation gate",
    },
    {
        "label": "live_poc_runtime_ticket_review_bundle",
        "path": "var/review-packets/v3/sandbox-vm-live-poc-runtime-ticket-review",
        "description": "focused review packet for the runtime-ticket draft",
    },
]

RUNTIME_GATE_ARTIFACTS = [
    {
        "label": "live_poc_runtime_ticket_internal_review",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md",
        "description": "internal xhigh review record for the runtime-ticket packet",
    },
    {
        "label": "live_poc_runtime_implementation_gate",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md",
        "description": "draft-only runtime implementation gate for a future sprint",
    },
    {
        "label": "live_poc_runtime_descriptor_contract",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md",
        "description": "planning-only descriptor/correlation contract for a future sprint",
    },
    {
        "label": "live_poc_runtime_descriptor_contract_internal_review",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md"
        ),
        "description": "internal xhigh review record for the descriptor/correlation contract",
    },
    {
        "label": "live_poc_runtime_gate_readiness_review_bundle",
        "path": "var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review",
        "description": "focused packet for runtime gate-readiness review",
    },
    {
        "label": "live_poc_runtime_gate_readiness_internal_review",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-gate-readiness-internal-review.md"
        ),
        "description": "internal High review record for the runtime gate-readiness checkpoint",
    },
    {
        "label": "live_poc_runtime_descriptor_only_plan",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md",
        "description": (
            "descriptor-only implementation-planning packet for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_ticket",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md"
        ),
        "description": (
            "descriptor-only implementation ticket for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_ticket_review_bundle",
        "path": (
            "var/review-packets/v3/"
            "sandbox-vm-live-poc-runtime-descriptor-only-ticket-review"
        ),
        "description": (
            "focused review packet for the descriptor-only implementation ticket"
        ),
    },
    {
        "label": "live_poc_runtime_gate_readiness_response_intake",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-gate-readiness-response-intake.md"
        ),
        "description": "response-intake template for future runtime gate-readiness review",
    },
    {
        "label": "live_poc_runtime_gate_readiness_decision_record_skeleton",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton.md"
        ),
        "description": "decision-record skeleton for descriptor-only planning disposition",
    },
]

DESCRIPTOR_ONLY_PLANNING_ARTIFACTS = [
    {
        "label": "live_poc_runtime_gate_readiness_decision_record",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"
        ),
        "description": (
            "internal High proxy decision record for descriptor-only planning"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_plan",
        "path": "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-plan.md",
        "description": (
            "descriptor-only implementation-planning packet for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_ticket",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket.md"
        ),
        "description": (
            "descriptor-only implementation ticket for the next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation_decision",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision.md"
        ),
        "description": (
            "planning-only descriptor-only implementation decision draft for the "
            "next runtime checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_implementation",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-implementation.md"
        ),
        "description": (
            "bounded descriptor-only runtime implementation checkpoint"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_internal_source_review",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review.md"
        ),
        "description": (
            "internal source review for the implemented descriptor-only runtime slice"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_ticket_review_bundle",
        "path": (
            "var/review-packets/v3/"
            "sandbox-vm-live-poc-runtime-descriptor-only-ticket-review"
        ),
        "description": (
            "focused review packet for the descriptor-only implementation ticket"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_source_review_bundle",
        "path": (
            "var/review-packets/v3/"
            "sandbox-vm-live-poc-runtime-descriptor-only-source-review"
        ),
        "description": (
            "focused source-review packet for the implemented descriptor-only runtime slice"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_external_response_intake",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake.md"
        ),
        "description": (
            "response-intake template for the descriptor-only runtime source review"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_inbox",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md"
        ),
        "description": (
            "focused raw-response inbox for descriptor-only runtime source review"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_send_receipt",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md"
        ),
        "description": (
            "operator send receipt scaffold for descriptor-only runtime source review"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_dry_run",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run.md"
        ),
        "description": (
            "response dry-run fixtures for descriptor-only runtime source review"
        ),
    },
    {
        "label": "live_poc_runtime_descriptor_only_response_application_preflight",
        "path": (
            "docs/codex/"
            "sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight.md"
        ),
        "description": (
            "preflight for applying a future real descriptor-only source-review response"
        ),
    },
]

REQUIRED_DOC_PHRASES = [
    "Status: checked read-only operator next-action summary",
    "Current governed tool count: `24`",
    "make enterprise-operator-next-action",
    "Historical Send Fallback",
    "current route after the recorded dispositions",
    "If the dual-response disposition record, runtime-ticket internal review, and runtime",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-now",
    "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
    "handoff_artifacts",
    "`ERG-003`: static sandbox/VM preflight disposition",
    "`ERG-002`: Mission Control display/import planning review",
    "make enterprise-response-intake-refresh",
    "What This Does Not Approve",
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

    response_state = _response_state(repo_root)
    response_present_count = response_state["response_present_count"]
    closure_ready_count = response_state["closure_ready_count"]
    disposition_recorded = _dual_response_disposition_recorded(repo_root)
    internal_review_recorded = _runtime_ticket_internal_review_recorded(repo_root)
    runtime_gate_decision_recorded = _runtime_gate_readiness_decision_recorded(
        repo_root
    )
    next_action = _next_action(
        response_present_count,
        closure_ready_count,
        disposition_recorded=disposition_recorded,
        internal_review_recorded=internal_review_recorded,
        runtime_gate_decision_recorded=runtime_gate_decision_recorded,
    )
    if next_action == "send_erg_003_and_erg_002":
        action_commands = SEND_COMMANDS
        handoff_artifacts = SEND_ARTIFACTS
        recommended_send_set = ["ERG-003", "ERG-002"]
        recommended_next_enterprise_review = "ERG-003"
    elif next_action == "prepare_erg004_runtime_ticket_review":
        action_commands = POST_ERG003_COMMANDS
        handoff_artifacts = POST_ERG003_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    elif next_action == "prepare_erg004_runtime_implementation_gate":
        action_commands = RUNTIME_GATE_COMMANDS
        handoff_artifacts = RUNTIME_GATE_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    elif next_action == "prepare_erg004_descriptor_only_runtime_planning":
        action_commands = DESCRIPTOR_ONLY_PLANNING_COMMANDS
        handoff_artifacts = DESCRIPTOR_ONLY_PLANNING_ARTIFACTS
        recommended_send_set = ["ERG-004"]
        recommended_next_enterprise_review = "ERG-004"
    else:
        action_commands = RESPONSE_COMMANDS
        handoff_artifacts = RESPONSE_ARTIFACTS
        recommended_send_set = ["ERG-003", "ERG-002"]
        recommended_next_enterprise_review = "ERG-003"

    selected_capability = "not selected"

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
        if response_state.get(key) is not expected:
            failures.append(f"response-state boundary flag drifted: {key}")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"enterprise operator next-action doc is missing phrase: {phrase}")
    for phrase in BLOCKED_PHRASES:
        if phrase not in doc:
            failures.append(
                f"enterprise operator next-action doc is missing blocked phrase: {phrase}"
            )
    lowered = doc.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(
                f"enterprise operator next-action doc contains forbidden phrase: {phrase}"
            )

    if "enterprise-operator-next-action:" not in makefile:
        failures.append("Make target is missing: enterprise-operator-next-action")
    if (
        "enterprise-operator-next-action" not in release_check_body
        and "release-check: enterprise-operator-next-action" not in makefile
    ):
        failures.append("enterprise-operator-next-action is missing from release-check")
    if "$(MAKE) enterprise-operator-next-action" not in review_candidate_body:
        failures.append("enterprise-operator-next-action is missing from review-candidate")
    if "make enterprise-operator-next-action" not in readme:
        failures.append("README is missing enterprise operator next-action command")
    if DOC_REL not in readme:
        failures.append("README is missing enterprise operator next-action doc")
    if DOC_REL not in docs_site:
        failures.append("enterprise operator next-action is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise operator next-action is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise operator next action")
    if "enterprise-operator-next-action" not in release_guardrails:
        failures.append("release guardrails do not require enterprise operator next action")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "next_action_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": selected_capability,
        "recommended_send_set": recommended_send_set,
        "recommended_next_enterprise_review": recommended_next_enterprise_review,
        "response_present_count": response_present_count,
        "closure_ready_count": closure_ready_count,
        "dual_response_disposition_recorded": disposition_recorded,
        "runtime_ticket_internal_review_recorded": internal_review_recorded,
        "runtime_gate_readiness_decision_recorded": runtime_gate_decision_recorded,
        "next_action": next_action,
        "action_commands": action_commands,
        "next_after_send_commands": NEXT_AFTER_SEND_COMMANDS,
        "handoff_artifacts": handoff_artifacts,
        "normalized_response_paths": response_state["normalized_response_paths"],
        **boundary_flags,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise operator next action",
        f"valid: {str(report['valid']).lower()}",
        f"next_action_doc: {report['next_action_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report.get('selected_capability', 'unknown')}",
        "recommended_send_set: "
        + ", ".join(report.get("recommended_send_set") or []),
        "recommended_next_enterprise_review: "
        f"{report.get('recommended_next_enterprise_review', 'unknown')}",
        f"response_present_count: {report.get('response_present_count', 'unknown')}",
        f"closure_ready_count: {report.get('closure_ready_count', 'unknown')}",
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


def _next_action(
    response_present_count: int,
    closure_ready_count: int,
    *,
    disposition_recorded: bool,
    internal_review_recorded: bool,
    runtime_gate_decision_recorded: bool,
) -> str:
    if closure_ready_count > 0:
        return "run_lane_specific_closure_playbook"
    if response_present_count > 0:
        return "run_response_intake_preflight"
    if runtime_gate_decision_recorded:
        return "prepare_erg004_descriptor_only_runtime_planning"
    if internal_review_recorded:
        return "prepare_erg004_runtime_implementation_gate"
    if disposition_recorded:
        return "prepare_erg004_runtime_ticket_review"
    return "send_erg_003_and_erg_002"


def _dual_response_disposition_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/enterprise-dual-response-disposition-record.md"
    text = _read(path)
    return (
        "`closed_local_preview_static_preflight`" in text
        and "`ready_for_design_only_decision_record`" in text
        and "EXT-MC-DISPLAY-001" in text
        and "runtime importer behavior" in text
        and "live VM/container inspection" in text
    )


def _runtime_ticket_internal_review_recorded(repo_root: Path) -> bool:
    path = repo_root / "docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md"
    text = _read(path)
    return (
        "approve_internal_runtime_ticket_review" in text
        and "Critical/high findings: none." in text
        and "The next allowed action is to prepare a separate explicit runtime implementation gate."
        in text
        and "make sandbox-vm-live-poc-runtime-ticket-internal-review-check" in text
    )


def _runtime_gate_readiness_decision_recorded(repo_root: Path) -> bool:
    path = (
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-decision-record.md"
    )
    text = _read(path)
    return (
        "Decision ID: `PRD-SANDBOX-LIVE-GATE-001`." in text
        and "Decision outcome: `approved_for_descriptor_only_runtime_implementation_planning`."
        in text
        and "not runtime implementation approval" in text
        and "not\nexternal validation" in text
        and "Finding count: `0`" in text
    )


def _response_state(repo_root: Path) -> dict[str, Any]:
    paths = [
        response_rel
        for response_rel in NORMALIZED_RESPONSE_RELS
        if (repo_root / response_rel).exists()
    ]
    closure_ready_count = 0
    for response_rel in paths:
        try:
            payload = json.loads((repo_root / response_rel).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("closure_ready") is True:
            closure_ready_count += 1
    return {
        "response_present_count": len(paths),
        "closure_ready_count": closure_ready_count,
        "normalized_response_paths": paths,
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


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
