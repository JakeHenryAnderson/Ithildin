"""Validate the trusted-host promotion implementation-plan contract."""

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
DOC_REL = "docs/codex/trusted-host-promotion-implementation-plan.md"
DOC_NAME = "trusted-host-promotion-implementation-plan.md"

REQUIRED_PHRASES = [
    "Status: implementation-planning contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `ready_for_implementation_planning_only`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-implementation-plan-check",
    "Required Inputs",
    "Follow-Up Goals",
    "Goal B: source-review/runtime-boundary packet",
    "Goal C: runtime implementation gate decision",
    "Future Runtime Shape",
    "Promotion Request Contract",
    "promotion_request_id",
    "artifact_sha256",
    "output_policy",
    "Zone And Artifact Identity Contract",
    "deterministic normalized label form",
    "expected_staging_sha256",
    "Approval And Evidence Binding Plan",
    "stored-proposal-only semantics",
    "one-time scope hash",
    "Approval consumption must be atomic and one-time",
    "Attempt, Diagnostics, And Audit Plan",
    "promotion_attempt_id",
    "Diagnostic behavior must be read-only unless a separate decision record approves mutating",
    "Required Future Components",
    "Implementation Gate Preconditions",
    "Product-Boundary Stop Conditions",
    "Current Implementation Boundary",
    "sandbox-promotion-evidence-contract.md",
    "trusted-host-descriptor-contract.md",
    "trusted-host-promotion-decision-intake.md",
    "trusted-host-promotion-state-machine.md",
    "trusted-host-promotion-negative-fixtures.md",
    "trusted-host-promotion-zone-contract.md",
    "sandbox://artifact -> host-staging://artifact -> approved://artifact",
    "one artifact, one approval, one promotion attempt, and one bounded destination label",
    "artifact hash-binding model",
    "approval binding model",
    "attempt store with compare-and-set state transitions",
    "read-only diagnostic model",
    "safe storage resolver",
    "atomic placement model",
    "cannot overwrite, delete, move, chmod, merge directories, or recursively copy",
    "negative transcripts",
    "favorable external/source-review disposition",
    "packet redaction scan",
    "promotion_status: not_promoted",
    "does not implement a tool, endpoint, executor",
    "decision record required: `true`",
    "implementation approved: `false`",
    "runtime changes allowed: `false`",
    "trusted-host promotion allowed: `false`",
    "direct host writes allowed: `false`",
    "overwrite/delete/move allowed: `false`",
    "broad archive extraction allowed: `false`",
    "automatic promotion allowed: `false`",
    "promotion without exact artifact hash binding allowed: `false`",
    "promotion without approval evidence allowed: `false`",
    "Mission Control runtime allowed: `false`",
    "local model invocation allowed: `false`",
    "sandbox orchestration allowed: `false`",
    "SIEM adapter allowed: `false`",
    "new power classes allowed: `false`",
    "public/security-product positioning allowed: `false`",
]

REQUIRED_STOP_CONDITIONS = [
    "arbitrary host paths",
    "raw filesystem path exposure",
    "promotion without staging",
    "promotion without exact hash binding",
    "promotion without approval evidence",
    "automatic",
    "batch",
    "wildcard",
    "recursive",
    "overwrite",
    "delete",
    "move",
    "chmod",
    "directory merge",
    "broad archive extraction",
    "shell",
    "Docker",
    "Kubernetes",
    "browser automation",
    "arbitrary HTTP",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "sandbox orchestration",
    "Mission Control runtime action",
    "local model invocation",
    "SIEM adapter behavior",
    "compliance automation",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "trusted-host promotion is implemented",
    "trusted-host promotion is approved",
    "host writes are approved",
    "automatic promotion is approved",
    "overwrite is approved",
    "delete is approved",
    "archive extraction is approved",
    "implementation approved: `true`",
    "runtime changes allowed: `true`",
    "trusted-host promotion allowed: `true`",
    "direct host writes allowed: `true`",
    "secure sandbox",
    "production-ready",
    "compliance-grade",
]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
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
    intake = (repo_root / "docs/codex/trusted-host-promotion-decision-intake.md").read_text(
        encoding="utf-8"
    )
    state_machine = (repo_root / "docs/codex/trusted-host-promotion-state-machine.md").read_text(
        encoding="utf-8"
    )
    negative_fixtures = (
        repo_root / "docs/codex/trusted-host-promotion-negative-fixtures.md"
    ).read_text(encoding="utf-8")
    zone_contract = (repo_root / "docs/codex/trusted-host-promotion-zone-contract.md").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted-host promotion implementation-plan contract doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    "trusted-host promotion implementation plan missing phrase: "
                    f"{phrase}"
                )
        for phrase in REQUIRED_STOP_CONDITIONS:
            if phrase not in text:
                failures.append(
                    "trusted-host promotion implementation plan missing stop condition: "
                    f"{phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "trusted-host promotion implementation plan contains forbidden phrase: "
                    f"{phrase}"
                )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host implementation plan missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted-host implementation plan missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing trusted-host implementation plan doc")
    if "make trusted-host-promotion-implementation-plan-check" not in readme:
        failures.append("README is missing trusted-host implementation plan command")
    if "trusted-host-promotion-implementation-plan-check:" not in makefile:
        failures.append(
            "Make target is missing: trusted-host-promotion-implementation-plan-check"
        )
    if "trusted-host-promotion-implementation-plan-check" not in release_check_body:
        failures.append("trusted-host implementation plan check missing from release-check")
    if "trusted-host-promotion-implementation-plan-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted-host implementation plan")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing trusted-host implementation plan pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing trusted-host implementation plan pointer")
    if DOC_NAME not in decision_register:
        failures.append("post-RC decision register is missing trusted-host implementation plan")
    if DOC_NAME not in intake:
        failures.append("trusted-host decision intake is missing implementation plan pointer")
    if DOC_NAME not in state_machine:
        failures.append("trusted-host state machine is missing implementation plan pointer")
    if DOC_NAME not in negative_fixtures:
        failures.append("trusted-host negative fixtures are missing implementation plan pointer")
    if DOC_NAME not in zone_contract:
        failures.append("trusted-host zone contract is missing implementation plan pointer")
    if "Trusted-Host Promotion Implementation Plan" not in review_index:
        failures.append("review docs index is missing trusted-host implementation plan entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "implementation_plan_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "ready_for_implementation_planning_only",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "required_artifact_count": 9,
        "stop_condition_count": len(REQUIRED_STOP_CONDITIONS),
        "goal_b_followup_recorded": True,
        "goal_c_followup_recorded": True,
        "promotion_request_contract_present": True,
        "approval_evidence_binding_plan_present": True,
        "diagnostics_plan_read_only": True,
        "decision_record_required": True,
        "implementation_approved": False,
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "promotion_without_exact_artifact_hash_binding_allowed": False,
        "promotion_without_approval_evidence_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion implementation-plan contract check",
        f"valid: {str(report['valid']).lower()}",
        f"implementation_plan_doc: {report['implementation_plan_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"required_artifact_count: {report['required_artifact_count']}",
        f"stop_condition_count: {report['stop_condition_count']}",
        f"goal_b_followup_recorded: {str(report['goal_b_followup_recorded']).lower()}",
        f"goal_c_followup_recorded: {str(report['goal_c_followup_recorded']).lower()}",
        "promotion_request_contract_present: "
        f"{str(report['promotion_request_contract_present']).lower()}",
        "approval_evidence_binding_plan_present: "
        f"{str(report['approval_evidence_binding_plan_present']).lower()}",
        f"diagnostics_plan_read_only: {str(report['diagnostics_plan_read_only']).lower()}",
        f"decision_record_required: {str(report['decision_record_required']).lower()}",
        f"implementation_approved: {str(report['implementation_approved']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "promotion_without_exact_artifact_hash_binding_allowed: "
        f"{str(report['promotion_without_exact_artifact_hash_binding_allowed']).lower()}",
        "promotion_without_approval_evidence_allowed: "
        f"{str(report['promotion_without_approval_evidence_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
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


if __name__ == "__main__":
    raise SystemExit(main())
