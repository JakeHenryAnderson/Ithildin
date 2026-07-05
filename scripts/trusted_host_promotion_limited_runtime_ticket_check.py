"""Validate the ERG-005 trusted-host limited runtime implementation ticket."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
    trusted_host_promotion_implementation_gate_decision_check,
    trusted_host_promotion_limited_runtime_plan_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-limited-runtime-ticket.md"
DOC_TITLE = "Trusted-Host Promotion Limited Runtime Ticket"
TARGET = "trusted-host-promotion-limited-runtime-ticket-check"

REQUIRED_PHRASES = [
    "Status: limited-runtime implementation-ticket skeleton for `ERG-005`.",
    "Decision ID: `PRD-TRUSTED-HOST-LIMITED-RUNTIME-TICKET-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `ready_for_limited_runtime_ticket_skeleton`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-limited-runtime-ticket-check",
    (
        "one stored sandbox artifact -> one operator-approved host staging placement -> "
        "one read-only evidence record"
    ),
    "Do not keep adding documentation, gates, or packet polish",
    "ready_for_limited_runtime_implementation_plan",
    "Future Implementation Boundary",
    "Required Future Runtime Surfaces",
    "Required Evidence Binding",
    "Required Future Negative Tests",
    "Required Future Acceptance Evidence",
    "Explicit Non-Approvals",
    "Stop Conditions",
    "stored promotion proposal",
    "one-time approval binding",
    "promotion attempt store",
    "trusted host descriptor destination-label resolver",
    "staging-only placement function",
    "post-placement hash verification",
    "read-only diagnostics function",
    "safe audit metadata shape",
    "EXT-TRUSTED-HOST-RUNTIME-###",
]

REQUIRED_NEGATIVES = [
    "missing approval",
    "expired approval",
    "replayed approval",
    "approval scope mismatch",
    "wrong tool name",
    "wrong principal",
    "disabled or unknown principal",
    "disabled workspace",
    "stale artifact hash",
    "changed destination label",
    "changed trusted host descriptor hash",
    "policy drift",
    "manifest drift",
    "schema/tool input drift",
    "path traversal",
    "encoded traversal",
    "absolute path",
    "hidden/sensitive destination",
    "`.git` destination",
    "symlink",
    "hardlink",
    "directory target",
    "existing destination conflict",
    "overwrite/delete/move attempt",
    "archive extraction attempt",
    "oversized artifact",
    "binary or unsupported artifact label",
    "raw path leakage attempt",
    "file-content leakage attempt",
]

REQUIRED_NON_APPROVALS = [
    "runtime implementation in this checkpoint",
    "runtime trusted-host promotion",
    "direct host writes",
    "overwrite/delete/move behavior",
    "broad archive extraction",
    "automatic promotion",
    "promotion without exact artifact hash binding",
    "promotion without approval evidence",
    "arbitrary host paths",
    "raw host path exposure",
    "Mission Control runtime behavior",
    "local model invocation by Ithildin",
    "VM/container lifecycle management",
    "sandbox orchestration",
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
    "trusted-host promotion is approved",
    "direct host writes are approved",
    "automatic promotion is approved",
    "Mission Control runtime behavior is approved",
    "sandbox orchestration is approved",
    "new governed tool powers are approved",
    "public security product approved",
    "production ready",
    "enterprise ready",
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
    operator_next = _read(repo_root / "docs/codex/enterprise-operator-next-action.md")
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    decision_report = trusted_host_promotion_implementation_gate_decision_check.build_report(
        repo_root
    )
    limited_plan_report = trusted_host_promotion_limited_runtime_plan_check.build_report(
        repo_root
    )
    tool_surface_report = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers_report = no_new_powers_guardrail.build_report(repo_root)

    if not doc_path.exists():
        failures.append("trusted-host limited runtime ticket doc is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"limited runtime ticket is missing phrase: {phrase}")
    for phrase in REQUIRED_NEGATIVES:
        if phrase not in text:
            failures.append(f"limited runtime ticket is missing negative case: {phrase}")
    for phrase in REQUIRED_NON_APPROVALS:
        if phrase not in text:
            failures.append(f"limited runtime ticket is missing non-approval: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"limited runtime ticket contains forbidden phrase: {phrase}")

    for label, report in [
        ("implementation-gate-decision", decision_report),
        ("limited-runtime-plan", limited_plan_report),
        ("tool-surface", tool_surface_report),
        ("no-new-powers", no_new_powers_report),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if decision_report.get("goal_c_outcome") != "ready_for_limited_runtime_implementation_plan":
        failures.append("Goal C decision does not allow limited runtime planning")
    if limited_plan_report.get("erg_005_status") != "ready_for_limited_runtime_implementation_plan":
        failures.append("limited runtime plan status does not match expected status")
    if limited_plan_report.get("runtime_implementation_allowed") is not False:
        failures.append("limited runtime plan unexpectedly allows runtime implementation")
    if limited_plan_report.get("trusted_host_promotion_allowed") is not False:
        failures.append("limited runtime plan unexpectedly allows trusted-host promotion")
    if tool_surface_report.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    for source_name, linked_text in [
        ("README", readme),
        ("docs site", docs_site),
        ("enterprise operator next action", operator_next),
        ("enterprise current checkpoint", current_checkpoint),
    ]:
        if DOC_REL not in linked_text and doc_path.name not in linked_text:
            failures.append(f"{source_name} is missing {doc_path.name}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("limited runtime ticket is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing limited runtime ticket")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("limited runtime ticket check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require limited runtime ticket check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing limited runtime ticket command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "limited_runtime_ticket_doc": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-LIMITED-RUNTIME-TICKET-001",
        "tool_count": 24,
        "erg_005_status": "ready_for_limited_runtime_ticket_skeleton",
        "goal_c_outcome": decision_report.get("goal_c_outcome"),
        "limited_runtime_plan_valid": bool(limited_plan_report.get("valid")),
        "limited_runtime_ticket_ready": True,
        "next_allowed_step": "focused_runtime_source_review_or_implementation_gate_skeleton",
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "stop_and_reassess_required_on_ambiguity": True,
        "closes_erg_005": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion limited runtime ticket check",
        f"valid: {str(report['valid']).lower()}",
        f"limited_runtime_ticket_doc: {report['limited_runtime_ticket_doc']}",
        f"decision_id: {report['decision_id']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"goal_c_outcome: {report['goal_c_outcome']}",
        f"limited_runtime_plan_valid: {str(report['limited_runtime_plan_valid']).lower()}",
        f"limited_runtime_ticket_ready: {str(report['limited_runtime_ticket_ready']).lower()}",
        f"next_allowed_step: {report['next_allowed_step']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "stop_and_reassess_required_on_ambiguity: "
        f"{str(report['stop_and_reassess_required_on_ambiguity']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
