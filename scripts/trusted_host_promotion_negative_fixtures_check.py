"""Validate the trusted-host promotion negative fixture contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-negative-fixtures.md"
DOC_NAME = "trusted-host-promotion-negative-fixtures.md"

REQUIRED_FIXTURES = [f"TRUSTED-PROMOTION-NEG-{number:03d}" for number in range(1, 25)]

REQUIRED_PHRASES = [
    "Status: design-only negative fixture contract for `ERG-005` and `PRD-TRUSTED-HOST-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-005` status: `blocked`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-negative-fixtures-check",
    "Fixture Scope",
    "Required Negative Fixtures",
    "Required Transcript Shape",
    "Safe Error Expectations",
    "Current Implementation Boundary",
    "promotion_status: not_promoted",
    "runtime_promotion_performed",
    "auto_promotion_performed",
    "trusted_host_write_performed",
    "safe_metadata_only",
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

REQUIRED_REASON_LABELS = [
    "unsupported schema",
    "unsupported state",
    "invalid transition",
    "missing artifact hash",
    "missing approval evidence",
    "missing scope evidence",
    "missing governance evidence",
    "approval scope mismatch",
    "expired approval",
    "replay denied",
    "stale source artifact",
    "stale governance evidence",
    "target conflict",
    "unsupported operation",
    "unsafe label",
    "unsafe target",
    "missing review acknowledgement",
    "stale review packet",
    "sensitive payload",
    "authority overclaim",
    "product-boundary overclaim",
    "promotion_recovery_required",
    "current-boundary overclaim",
]

FORBIDDEN_PHRASES = [
    "trusted-host promotion is implemented",
    "trusted-host promotion is approved",
    "host writes are approved",
    "automatic promotion is approved",
    "overwrite is approved",
    "delete is approved",
    "archive extraction is approved",
    "promotion implementation is approved",
    "production-ready",
    "secure sandbox",
    "compliance-grade",
]

SAFE_REASON_PATTERN = re.compile(r"^[a-z0-9_]+$")


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
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if not doc_path.exists():
        failures.append("trusted-host promotion negative fixture doc is missing")
        text = ""
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for fixture_id in REQUIRED_FIXTURES:
            if f"`{fixture_id}`" not in text:
                failures.append(
                    f"trusted-host promotion negative fixture is missing: {fixture_id}"
                )
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"trusted-host promotion negative fixtures missing phrase: {phrase}"
                )
        for reason in REQUIRED_REASON_LABELS:
            if reason not in text:
                failures.append(
                    f"trusted-host promotion negative fixtures missing reason: {reason}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "trusted-host promotion negative fixtures contain forbidden phrase: "
                    f"{phrase}"
                )
        if "reason_label\": \"invalid_transition\"" not in text:
            failures.append("trusted-host promotion transcript example lacks safe reason label")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host promotion negative fixtures missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("trusted-host promotion negative fixtures missing from docs-site inputs")
    if DOC_NAME not in readme:
        failures.append("README is missing trusted-host promotion negative fixtures doc")
    if "make trusted-host-promotion-negative-fixtures-check" not in readme:
        failures.append("README is missing trusted-host promotion negative fixtures command")
    if "trusted-host-promotion-negative-fixtures-check:" not in makefile:
        failures.append("Make target is missing: trusted-host-promotion-negative-fixtures-check")
    if "trusted-host-promotion-negative-fixtures-check" not in release_check_body:
        failures.append("trusted-host promotion negative fixture check missing from release-check")
    if "trusted-host-promotion-negative-fixtures-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted-host negative fixtures")
    if DOC_NAME not in enterprise:
        failures.append("enterprise runway is missing trusted-host negative fixture pointer")
    if DOC_NAME not in gap_matrix:
        failures.append("enterprise gap matrix is missing trusted-host negative fixture pointer")
    if DOC_NAME not in decision_register:
        failures.append(
            "post-RC decision register is missing trusted-host negative fixture pointer"
        )
    if DOC_NAME not in intake:
        failures.append("trusted-host decision intake is missing negative fixture pointer")
    if DOC_NAME not in state_machine:
        failures.append("trusted-host state machine is missing negative fixture pointer")
    if "Trusted-Host Promotion Negative Fixtures" not in review_index:
        failures.append("review docs index is missing trusted-host negative fixture entry")

    fixture_results = _fixture_results()
    for result in fixture_results:
        if result["accepted"]:
            failures.append(f"trusted-host negative fixture was accepted: {result['id']}")
        if not SAFE_REASON_PATTERN.match(result["reason_label"]):
            failures.append(
                f"trusted-host negative fixture reason is not a safe label: {result['id']}"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "fixture_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "negative_case_count": len(fixture_results),
        "negative_cases_rejected": sum(
            1 for result in fixture_results if not result["accepted"]
        ),
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
        "cases": fixture_results,
    }


def _fixture_results() -> list[dict[str, Any]]:
    reasons = [
        "unsupported_schema",
        "unsupported_state",
        "invalid_transition",
        "missing_artifact_hash",
        "missing_approval_evidence",
        "missing_scope_evidence",
        "missing_governance_evidence",
        "approval_scope_mismatch",
        "approval_scope_mismatch",
        "expired_approval",
        "replay_denied",
        "stale_source_artifact",
        "stale_governance_evidence",
        "target_conflict",
        "unsupported_operation",
        "unsafe_label",
        "unsafe_target",
        "missing_review_acknowledgement",
        "stale_review_packet",
        "sensitive_payload",
        "authority_overclaim",
        "product_boundary_overclaim",
        "promotion_recovery_required",
        "current_boundary_overclaim",
    ]
    return [
        {
            "id": fixture_id,
            "accepted": False,
            "reason_label": reasons[index],
            "promotion_status": "not_promoted"
            if fixture_id != "TRUSTED-PROMOTION-NEG-023"
            else "promotion_recovery_required",
            "runtime_promotion_performed": False,
            "auto_promotion_performed": False,
            "trusted_host_write_performed": False,
            "safe_metadata_only": True,
        }
        for index, fixture_id in enumerate(REQUIRED_FIXTURES)
    ]


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion negative fixture check",
        f"valid: {str(report['valid']).lower()}",
        f"fixture_doc: {report['fixture_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"negative_case_count: {report['negative_case_count']}",
        f"negative_cases_rejected: {report['negative_cases_rejected']}",
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
