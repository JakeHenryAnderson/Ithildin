"""Validate the committed ERG-005 trusted-host promotion decision record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    review_docs,
    trusted_host_descriptor_contract_check,
    trusted_host_promotion_decision_intake_check,
    trusted_host_promotion_disposition_closure_check,
    trusted_host_promotion_implementation_plan_check,
    trusted_host_promotion_internal_review_check,
    trusted_host_promotion_negative_fixtures_check,
    trusted_host_promotion_source_review_packet,
    trusted_host_promotion_state_machine_check,
    trusted_host_promotion_zone_contract_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-decision-record.md"
DOC_NAME = "trusted-host-promotion-decision-record.md"
TARGET = "trusted-host-promotion-decision-record-check"

REQUIRED_PHRASES = [
    "Status: committed decision record for `ERG-005` implementation-planning-only continuation.",
    "Decision ID: `PRD-TRUSTED-HOST-001`.",
    "Current governed tool count: `24`.",
    "Previous `ERG-005` status: `blocked`.",
    "Recorded `ERG-005` status: `ready_for_implementation_planning_only`.",
    "Current selected capability: `not selected`.",
    "make trusted-host-promotion-decision-record-check",
    "Reviewer: Codex internal design/source review.",
    "Reviewed commit: `71fb9d6339033369a4edfee4ea9524b2ab7b1a51`.",
    "var/review-packets/v3/trusted-host-promotion-external-review",
    "docs/codex/v3-trusted-host-promotion-internal-review.md",
    "docs/codex/trusted-host-descriptor-contract.md",
    "make trusted-host-promotion-internal-review-check",
    "approved_for_implementation_planning_only",
    "ERG-005: blocked -> ready_for_implementation_planning_only",
    "Release gates must continue to pass with no live normalized response present.",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "trusted-host promotion",
    "direct host writes",
    "overwrite/delete/move behavior",
    "broad archive extraction",
    "automatic promotion",
    "promotion without exact artifact hash binding",
    "promotion without approval evidence",
    "Mission Control runtime behavior",
    "local model invocation",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "SIEM adapter behavior",
    "production identity",
    "runtime Postgres",
    "hosted telemetry",
    "remote MCP",
    "shell/Docker/Kubernetes/browser governed powers",
    "arbitrary HTTP",
    "broad filesystem writes",
    "compliance automation",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "trusted-host promotion is approved",
    "direct host writes are approved",
    "automatic promotion is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "sandbox orchestration is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


def build_report(repo_root: Path) -> dict[str, object]:
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

    if not doc_path.exists():
        failures.append("trusted-host promotion decision record is missing")
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"decision record is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"decision record is missing blocked boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"decision record contains forbidden phrase: {phrase}")

    descriptor = trusted_host_descriptor_contract_check.build_report(repo_root)
    intake = trusted_host_promotion_decision_intake_check.build_report(repo_root)
    state_machine = trusted_host_promotion_state_machine_check.build_report(repo_root)
    negative_fixtures = trusted_host_promotion_negative_fixtures_check.build_report(repo_root)
    zone_contract = trusted_host_promotion_zone_contract_check.build_report(repo_root)
    implementation_plan = trusted_host_promotion_implementation_plan_check.build_report(repo_root)
    source_packet = trusted_host_promotion_source_review_packet.build_check_report(repo_root)
    internal_review = trusted_host_promotion_internal_review_check.build_report(repo_root)
    closure_gate = trusted_host_promotion_disposition_closure_check.build_report(repo_root)

    for label, report in [
        ("descriptor", descriptor),
        ("decision-intake", intake),
        ("state-machine", state_machine),
        ("negative-fixtures", negative_fixtures),
        ("zone-contract", zone_contract),
        ("implementation-plan", implementation_plan),
        ("source-review-packet", source_packet),
        ("internal-review", internal_review),
        ("closure-gate", closure_gate),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report["failures"])

    if closure_gate.get("normalized_response_present") is not False:
        failures.append("decision record expects no live normalized trusted-host response")
    if closure_gate.get("closure_ready") is not False:
        failures.append("closure gate should remain false without live normalized response")
    if internal_review.get("finding_count") != 0:
        failures.append("internal review finding count is not zero")
    if internal_review.get("disposition") != "continue_design_only":
        failures.append("internal review disposition is not continue_design_only")
    if state_machine.get("current_runtime_state") != "not_promoted":
        failures.append("state machine current runtime state is not not_promoted")
    if negative_fixtures.get("negative_cases_rejected") != 24:
        failures.append("negative fixture rejection count is not 24")

    for linked_text, source_name in [
        (readme, "README"),
        (docs_site, "docs site"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (decision_register, "post-RC decision register"),
        (readiness, "enterprise sandbox readiness"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{source_name} is missing {DOC_NAME}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("decision record is missing from review docs")
    if "Trusted-Host Promotion Decision Record" not in review_index:
        failures.append("review-docs index is missing trusted-host decision record")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body:
        failures.append("trusted-host decision record check missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require trusted-host decision record check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing trusted-host decision record command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_doc": DOC_REL,
        "tool_count": 24,
        "erg_005_status": "ready_for_implementation_planning_only",
        "decision_outcome": "approved_for_implementation_planning_only",
        "implementation_planning_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_005": False,
    }


def render_report(report: dict[str, object]) -> str:
    lines = [
        "Ithildin trusted-host promotion decision record check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_doc: {report['decision_record_doc']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"decision_outcome: {report['decision_outcome']}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    failures = report["failures"]
    if isinstance(failures, list) and failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
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
