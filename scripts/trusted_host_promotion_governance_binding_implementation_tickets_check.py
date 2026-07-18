"""Validate the approved ERG-005 governance-binding implementation tickets."""

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
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-governance-binding-implementation-tickets.md"
DOC_TITLE = "Trusted-Host Promotion Governance-Binding Implementation Tickets"
TARGET = "trusted-host-promotion-governance-binding-implementation-tickets-check"

REQUIRED_PHRASES = [
    (
        "Status: approved bounded execution packet for "
        "`PRD-TRUSTED-HOST-BINDING-001`."
    ),
    "Current governed tool count: `24`.",
    "Current decision status: `approved_for_bounded_implementation`.",
    "make trusted-host-promotion-governance-binding-implementation-tickets-check",
    "The direct user instruction recorded on `2026-07-18`",
    "The user does not need to",
    "repeat a technical approval formula",
    "TGB-001 — Authority Foundation And Verified Candidate",
    "TGB-002 — Version-2 Contracts And Transactional Migration",
    "TGB-003 — YAML Policy And Approval-Scope Binding",
    "TGB-004 — Atomic Revalidation And Descriptor-Relative Placement",
    "TGB-005 — Evidence, Diagnostics, And UI Consumer",
    "TGB-006 — Adversarial Proof And Exact-Candidate Review",
    "AdminPrincipalContext",
    "PromotionAuthoritySnapshot",
    "TrustedHostDescriptorRegistry",
    "RuntimeCandidateRecord",
    "schemas/runtime-candidate-authorization.schema.json",
    "scripts/runtime_candidate_authorization_record.py",
    "Settings.runtime_candidate_authorization_path",
    "/run/ithildin-authority/api-candidate.json:ro",
    "apps/api/verified_launch.py",
    "before importing `ithildin_api.app`",
    "unreviewed_local",
    "caller-controlled identity/approval attribution",
    "Remove `principal` from `TrustedHostPromotionProposalInput`",
    "Remove `decided_by` from `ApprovalDecisionPayload`",
    "Rebuild proposal, approval, and attempt tables in one `BEGIN IMMEDIATE`",
    "previous API artifact",
    "unsupported_policy_engine_for_promotion",
    "trusted_host.promotion.stage",
    "v2_approved",
    "v2_approval_required",
    "placement_evidence_recovery_required",
    "descriptor-relative",
    "Promotion stays disabled until `TGB-005`",
    "implementation_candidate_ready_for_independent_re_review",
    "independent reviewer",
    "database.initialize_database",
    "Required Cross-Ticket Test Matrix",
    "Explicit Non-Goals",
    "UAT Boundary",
    "No human UAT is required to execute `TGB-001` through `TGB-006`.",
    "Sol Ultra is not used without the user's prior approval.",
    "No ticket changes `tool-manifests.lock.json`",
    "implementation path is authorized and reviewable",
]

REQUIRED_SOURCE_PATHS = [
    ".dockerignore",
    ".gitignore",
    "apps/api/src/ithildin_api/app.py",
    "apps/api/src/ithildin_api/approvals.py",
    "apps/api/src/ithildin_api/auth.py",
    "apps/api/src/ithildin_api/config.py",
    "apps/api/src/ithildin_api/database.py",
    "apps/api/src/ithildin_api/filesystem_contract.py",
    "apps/api/src/ithildin_api/identity.py",
    "apps/api/src/ithildin_api/policy.py",
    "apps/api/src/ithildin_api/registry.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/trusted_host_promotions.py",
    "apps/api/src/ithildin_api/trusted_host_placement.py",
    "apps/api/src/ithildin_api/workspaces.py",
    "apps/ui/src/App.tsx",
    "apps/ui/src/App.test.tsx",
    "packages/schemas/src/ithildin_schemas/models.py",
    "deploy/Dockerfile.api",
    "deploy/README.md",
    "deploy/docker-compose.yml",
    "policies/default.yaml",
    "policies/tests/default.yaml",
    "principals/local.yaml",
    "tool-manifests.lock.json",
    "uv.lock",
    "workspaces/local.yaml",
    "tests/test_api_service.py",
    "tests/test_approval_workflow.py",
    "tests/test_core_schemas.py",
    "tests/test_governed_tool_calls.py",
    "tests/test_mcp_integration_flow.py",
    "tests/test_identity.py",
    "tests/test_security_regressions.py",
    "tests/test_trusted_host_placement.py",
    "tests/test_workspaces.py",
]

SOURCE_ANCHORS = {
    "apps/api/src/ithildin_api/auth.py": ["def require_admin_token("],
    "apps/api/src/ithildin_api/trusted_host_promotions.py": [
        "class TrustedHostPromotionProposalInput",
        "class TrustedHostPromotionStore",
        "class TrustedHostPromotionService",
        "def apply_approved(",
        "def reserve_execution(",
    ],
    "apps/api/src/ithildin_api/trusted_host_placement.py": [
        "class TrustedHostPlacement",
        "def descriptor_relative_placement_supported(",
        "def _open_or_create_directory(",
    ],
    "apps/api/src/ithildin_api/approvals.py": [
        "class ApprovalStore",
        "class ApprovalService",
        "def compare_and_set_status(",
        "def begin_execution(",
    ],
    "apps/api/src/ithildin_api/database.py": [
        "SCHEMA_VERSION =",
        "def initialize_database(",
    ],
    "packages/schemas/src/ithildin_schemas/models.py": [
        "class ApprovalRequest(",
        "class ApprovalDecision(",
    ],
    "apps/api/src/ithildin_api/app.py": [
        "def create_trusted_host_promotion_proposal(",
        "def apply_trusted_host_promotion(",
        "class ApprovalDecisionPayload",
        "def approve_approval(",
        "def deny_approval(",
    ],
    "apps/ui/src/App.tsx": ["async function decideApproval("],
}

FORBIDDEN_PHRASES = [
    "implementation has started",
    "erg-005 is closed",
    "ext-trusted-host-runtime-002 is fixed",
    "ext-trusted-host-runtime-006 is fixed",
    "trusted-host promotion is production ready",
    "node-side placement is approved",
    "tool count: `25`",
    "opa-backed promotion is approved",
    "runtime postgres is approved",
    "enterprise rbac is approved",
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
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    lowered = text.lower()
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    architecture = (
        trusted_host_promotion_governance_binding_architecture_check.build_report(repo_root)
    )
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    if not doc_path.is_file():
        failures.append("governance-binding implementation ticket packet is missing")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"implementation ticket packet is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"implementation ticket packet contains forbidden phrase: {phrase}")

    for source_path in REQUIRED_SOURCE_PATHS:
        if not (repo_root / source_path).is_file():
            failures.append(f"required current source path is missing: {source_path}")
        if source_path not in text:
            failures.append(f"implementation ticket packet omits source path: {source_path}")

    for source_path, anchors in SOURCE_ANCHORS.items():
        source_text = _read(repo_root / source_path)
        for anchor in anchors:
            if anchor not in source_text:
                failures.append(f"current source anchor is missing: {source_path}: {anchor}")

    for label, report in [
        ("architecture", architecture),
        ("tool surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if architecture.get("decision_status") != "approved_for_bounded_implementation":
        failures.append("architecture decision status is not approved_for_bounded_implementation")
    if architecture.get("runtime_changes_allowed") is not True:
        failures.append("architecture does not authorize bounded runtime changes")
    if tool_surface.get("tool_count") != 24:
        failures.append("live governed tool count is not 24")
    if no_new_powers.get("new_power_classes_allowed") is not False:
        failures.append("no-new-powers gate unexpectedly allows new power classes")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("implementation ticket packet is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("implementation ticket packet is missing from docs site")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing implementation ticket packet")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("implementation ticket packet check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require implementation ticket packet check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing implementation ticket packet command")
    if DOC_REL not in readme:
        failures.append("README is missing implementation ticket packet document")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ticket_packet": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-BINDING-001",
        "decision_status": "approved_for_bounded_implementation",
        "ticket_count": 6,
        "source_path_count": len(REQUIRED_SOURCE_PATHS),
        "source_anchor_count": sum(len(anchors) for anchors in SOURCE_ANCHORS.values()),
        "tool_count": tool_surface.get("tool_count"),
        "tool_surface_valid": tool_surface.get("valid"),
        "no_new_powers_valid": no_new_powers.get("valid"),
        "implementation_authorized": True,
        "runtime_changes_allowed": True,
        "public_contract_changes_allowed": True,
        "database_migration_allowed": True,
        "policy_changes_allowed": True,
        "placement_changes_allowed": True,
        "trusted_host_promotion_allowed": False,
        "node_side_placement_allowed": False,
        "new_power_classes_allowed": no_new_powers.get("new_power_classes_allowed"),
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host governance-binding implementation tickets check",
        f"valid: {str(report['valid']).lower()}",
        f"ticket_packet: {report['ticket_packet']}",
        f"decision_id: {report['decision_id']}",
        f"decision_status: {report['decision_status']}",
        f"ticket_count: {report['ticket_count']}",
        f"source_path_count: {report['source_path_count']}",
        f"source_anchor_count: {report['source_anchor_count']}",
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
