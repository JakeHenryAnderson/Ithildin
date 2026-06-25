"""Validate the trusted-host promotion internal source-review disposition."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    no_new_powers_guardrail,
    review_docs,
    sandbox_promotion_evidence_contract_check,
    tool_surface_invariant_gate,
    trusted_host_promotion_decision_intake_check,
    trusted_host_promotion_implementation_plan_check,
    trusted_host_promotion_negative_fixtures_check,
    trusted_host_promotion_source_review_packet,
    trusted_host_promotion_state_machine_check,
    trusted_host_promotion_zone_contract_check,
)

ROOT = Path(__file__).resolve().parents[1]
INTERNAL_REVIEW_DOC = "docs/codex/v3-trusted-host-promotion-internal-review.md"
SOURCE_REVIEW_DOC = "docs/codex/trusted-host-promotion-source-review.md"
MATRIX_DOC = "docs/codex/source-review-closure-matrix.md"
REQUIRED_PHRASES = [
    "Status: internal design/source-review pass complete for continued design-only planning.",
    "No critical, high, medium, low, or informational implementation findings were recorded",
    "The lane may continue as design-only planning and reviewer handoff.",
    "Runtime implementation remains blocked",
    "External/source review remains pending",
    "trusted-host promotion allowed: false",
    "direct_host_writes_allowed: false",
    "EXT-TRUSTED-HOST-###",
    "promotion_status: not_promoted",
]
FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "host promotion is approved",
    "direct host writes are approved",
    "trusted-host promotion allowed: `true`",
    "runtime changes allowed: `true`",
    "external/source review is closed",
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
    promotion_evidence = sandbox_promotion_evidence_contract_check.build_report(repo_root)
    decision_intake = trusted_host_promotion_decision_intake_check.build_report(repo_root)
    state_machine = trusted_host_promotion_state_machine_check.build_report(repo_root)
    negative_fixtures = trusted_host_promotion_negative_fixtures_check.build_report(repo_root)
    zone_contract = trusted_host_promotion_zone_contract_check.build_report(repo_root)
    implementation_plan = trusted_host_promotion_implementation_plan_check.build_report(repo_root)
    source_packet = trusted_host_promotion_source_review_packet.build_check_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    for label, report in [
        ("promotion-evidence", promotion_evidence),
        ("decision-intake", decision_intake),
        ("state-machine", state_machine),
        ("negative-fixtures", negative_fixtures),
        ("zone-contract", zone_contract),
        ("implementation-plan", implementation_plan),
        ("source-review-packet", source_packet),
        ("tool-surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report["failures"])

    doc_path = repo_root / INTERNAL_REVIEW_DOC
    text = ""
    if not doc_path.exists():
        failures.append("trusted-host internal review doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"internal review doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lower:
                failures.append(f"internal review doc contains forbidden phrase: {phrase}")

    source_review = (repo_root / SOURCE_REVIEW_DOC).read_text(encoding="utf-8")
    matrix = (repo_root / MATRIX_DOC).read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    enterprise = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    if INTERNAL_REVIEW_DOC not in review_docs.REVIEW_DOCS:
        failures.append("internal review doc is missing from review-doc metadata")
    if INTERNAL_REVIEW_DOC not in docs_site:
        failures.append("internal review doc is missing from docs-site inputs")
    if "Trusted-Host Promotion Internal Source Review" not in review_index:
        failures.append("review-doc index is missing trusted-host internal review")
    if "trusted-host-promotion-internal-review-check:" not in makefile:
        failures.append("Make target is missing: trusted-host-promotion-internal-review-check")
    if "trusted-host-promotion-internal-review-check" not in release_check_body:
        failures.append("internal review check missing from release-check")
    if "make trusted-host-promotion-internal-review-check" not in readme:
        failures.append("README is missing trusted-host internal review command")
    if "v3-trusted-host-promotion-internal-review.md" not in source_review:
        failures.append("source-review handoff is missing internal-review pointer")
    if "Trusted-host promotion planning lane" not in matrix:
        failures.append("closure matrix is missing trusted-host promotion planning lane")
    if (
        "internal reviewed; implementation blocked pending external/source disposition"
        not in matrix
    ):
        failures.append("closure matrix does not preserve trusted-host internal disposition")
    if "v3-trusted-host-promotion-internal-review.md" not in enterprise:
        failures.append("enterprise runway is missing trusted-host internal review pointer")

    boundary_flags = {
        "runtime_changes_allowed": False,
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
    }
    for key, expected in boundary_flags.items():
        for label, report in [
            ("decision-intake", decision_intake),
            ("implementation-plan", implementation_plan),
            ("source-review-packet", source_packet),
        ]:
            if report.get(key) is not expected:
                failures.append(f"{label} reports {key}: {report.get(key)!r}")
    if state_machine.get("current_runtime_state") != "not_promoted":
        failures.append("state machine current runtime state is not not_promoted")
    if negative_fixtures.get("negative_cases_rejected") != 24:
        failures.append("negative fixture rejection count is not 24")
    if zone_contract.get("zone_prefixes") != [
        "sandbox://",
        "host-staging://",
        "approved://",
        "evidence://",
    ]:
        failures.append("zone contract prefixes changed unexpectedly")
    if tool_surface.get("tool_count") != 24:
        failures.append("tool surface tool count is not 24")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "review_doc": INTERNAL_REVIEW_DOC,
        "scope": "internal_design_source_review",
        "disposition": "continue_design_only",
        "finding_count": 0,
        "critical_high_findings_open": 0,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "implementation_approved": False,
        "external_source_review_closed": False,
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion internal review check",
        f"valid: {str(report['valid']).lower()}",
        f"review_doc: {report['review_doc']}",
        f"scope: {report['scope']}",
        f"disposition: {report['disposition']}",
        f"finding_count: {report['finding_count']}",
        f"critical_high_findings_open: {report['critical_high_findings_open']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        f"implementation_approved: {str(report['implementation_approved']).lower()}",
        "external_source_review_closed: "
        f"{str(report['external_source_review_closed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
