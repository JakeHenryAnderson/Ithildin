"""Validate the pending PRD-TRUSTED-HOST-BINDING-001 authorization record."""

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
    trusted_host_promotion_governance_binding_architecture_check,
    trusted_host_promotion_governance_binding_implementation_tickets_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-governance-binding-authorization-record.md"
DOC_TITLE = "Trusted-Host Promotion Governance-Binding Authorization Record"
TARGET = "trusted-host-promotion-governance-binding-authorization-record-check"

REQUIRED_PHRASES = [
    "Status: pending explicit user authorization for `PRD-TRUSTED-HOST-BINDING-001`.",
    "Decision ID: `PRD-TRUSTED-HOST-BINDING-001`.",
    "Decision status: `awaiting_explicit_user_approval`.",
    "Approval recorded: `false`.",
    "Current governed tool count: `24`.",
    f"make {TARGET}",
    "Approve PRD-TRUSTED-HOST-BINDING-001 for bounded implementation",
    "version-2 public request contracts",
    "SQLite table-rebuild migration",
    "TGB-001` through `TGB-006",
    "one artifact, create-exclusive, staging-only, Manager-local",
    "implementation_authorized: false",
    "runtime_changes_allowed: false",
    "public_contract_changes_allowed: false",
    "database_migration_allowed: false",
    "policy_changes_allowed: false",
    "placement_changes_allowed: false",
    "trusted_host_promotion_allowed: false",
    "node_side_placement_allowed: false",
    "new_power_classes_allowed: false",
    "uat_required_now: false",
    "approved_for_bounded_implementation",
    "Promotion remains unavailable through `TGB-004`",
    "implementation_candidate_ready_for_independent_re_review",
    "Sol Ultra is not used without the user's prior approval.",
    "No human UAT is required",
]

FORBIDDEN_PHRASES = [
    "Approval recorded: `true`.",
    "Decision status: `approved_for_bounded_implementation`.",
    "implementation_authorized: true",
    "runtime_changes_allowed: true",
    "public_contract_changes_allowed: true",
    "database_migration_allowed: true",
    "policy_changes_allowed: true",
    "placement_changes_allowed: true",
    "trusted_host_promotion_allowed: true",
    "node_side_placement_allowed: true",
    "new_power_classes_allowed: true",
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
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    architecture = (
        trusted_host_promotion_governance_binding_architecture_check.build_report(repo_root)
    )
    tickets = (
        trusted_host_promotion_governance_binding_implementation_tickets_check.build_report(
            repo_root
        )
    )
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    if not doc_path.is_file():
        failures.append("governance-binding authorization record is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"authorization record is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            failures.append(f"pending authorization record contains forbidden phrase: {phrase}")

    for label, report in [
        ("architecture", architecture),
        ("tickets", tickets),
        ("tool surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if architecture.get("decision_status") != "proposed_for_explicit_approval":
        failures.append("architecture is not awaiting explicit approval")
    if tickets.get("decision_status") != "proposed_for_explicit_approval":
        failures.append("ticket packet is not awaiting explicit approval")
    if tickets.get("implementation_authorized") is not False:
        failures.append("ticket packet unexpectedly reports implementation authorized")
    if tool_surface.get("tool_count") != 24:
        failures.append("live governed tool count is not 24")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers gate unexpectedly allows new power classes")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("authorization record is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("authorization record is missing from docs site")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing authorization record")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("authorization record check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require authorization record check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing authorization record command")
    if DOC_REL not in readme:
        failures.append("README is missing authorization record document")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "authorization_record": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-BINDING-001",
        "decision_status": "awaiting_explicit_user_approval",
        "approval_recorded": False,
        "tool_count": tool_surface.get("tool_count"),
        "tool_surface_valid": tool_surface.get("valid"),
        "no_new_powers_valid": no_new_powers.get("valid"),
        "implementation_authorized": False,
        "runtime_changes_allowed": False,
        "public_contract_changes_allowed": False,
        "database_migration_allowed": False,
        "policy_changes_allowed": False,
        "placement_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "node_side_placement_allowed": False,
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host governance-binding authorization record check",
        f"valid: {str(report['valid']).lower()}",
        f"authorization_record: {report['authorization_record']}",
        f"decision_id: {report['decision_id']}",
        f"decision_status: {report['decision_status']}",
        f"approval_recorded: {str(report['approval_recorded']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"tool_surface_valid: {str(report['tool_surface_valid']).lower()}",
        f"no_new_powers_valid: {str(report['no_new_powers_valid']).lower()}",
        f"implementation_authorized: {str(report['implementation_authorized']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_contract_changes_allowed: "
        f"{str(report['public_contract_changes_allowed']).lower()}",
        f"database_migration_allowed: {str(report['database_migration_allowed']).lower()}",
        f"policy_changes_allowed: {str(report['policy_changes_allowed']).lower()}",
        f"placement_changes_allowed: {str(report['placement_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"node_side_placement_allowed: {str(report['node_side_placement_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"uat_required_now: {str(report['uat_required_now']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
