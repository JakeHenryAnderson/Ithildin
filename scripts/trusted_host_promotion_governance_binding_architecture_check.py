"""Validate the proposed ERG-005 governance-binding architecture packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/trusted-host-promotion-governance-binding-architecture.md"

REQUIRED_PHRASES = [
    (
        "Status: proposed architecture decision for `ERG-005`; explicit implementation "
        "approval required."
    ),
    "Decision ID: `PRD-TRUSTED-HOST-BINDING-001`.",
    "Current governed tool count: `24`.",
    "Proposed decision outcome: `approve_governance_binding_implementation_plan`.",
    "PromotionAuthoritySnapshot",
    "AdminPrincipalContext",
    "TrustedHostDescriptorRegistry",
    "RuntimeCandidateRecord",
    "server-derived requesting principal",
    "The proposal body must no longer accept `principal`",
    "Accepting and ignoring a legacy",
    "The generic approval decision contract also removes `decided_by`",
    "Gateway resolves exactly one active",
    "descriptor_schema_version: \"2\"",
    "tool count other than `24` fail closed",
    "`trusted_host.promotion.stage`, without adding it to `tool-manifests.lock.json`",
    "Any manifest digest or tool-count change makes an existing proposal stale.",
    "supports only the canonical local-preview YAML engine",
    "unsupported_policy_engine_for_promotion",
    "`unreviewed_local`",
    "RuntimeCandidateVerifier",
    "metadata record alone cannot assert reviewed status",
    "reviewed_inventory_digest",
    "The digest domains must be detached and acyclic.",
    "This is an intentional breaking change for clients that send `principal`.",
    "terminal `authority_stale`",
    "label every pre-version-2",
    "technically fence downgrade",
    "it rebuilds the proposal, approval, and attempt tables",
    "cannot approve or deny a version-2 approval",
    "Descriptor-relative destination placement",
    "placement_evidence_recovery_required",
    "Fail-Closed State And Reason Matrix",
    "Adversarial Validation Matrix",
    "At least one test must change each authority component after approval",
    "Bounded Implementation Slices",
    "Implementation Acceptance Gates",
    "Explicit Non-Goals And Stop Lines",
    "The current decision remains `proposed_for_explicit_approval`.",
    "Approve PRD-TRUSTED-HOST-BINDING-001 for bounded implementation",
    (
        "Until that approval is recorded, runtime API, schema, policy, persistence, "
        "and placement behavior"
    ),
    "make trusted-host-promotion-governance-binding-architecture-check",
]

FORBIDDEN_PHRASES = [
    "implementation is approved",
    "erg-005 is closed",
    "trusted-host promotion is production ready",
    "node-side placement is approved",
    "tool count: `25`",
    "arbitrary host writes are approved",
    "production iam is approved",
    "enterprise rbac is approved",
    "runtime postgres is approved",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(
        f"tool surface: {failure}" for failure in tool_surface["failures"]
    )
    failures.extend(
        f"no-new-powers: {failure}" for failure in no_new_powers["failures"]
    )

    text = ""
    if not doc_path.is_file():
        failures.append("governance-binding architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    f"governance-binding architecture doc is missing phrase: {phrase}"
                )
        lowered = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(
                    f"governance-binding architecture doc contains forbidden phrase: {phrase}"
                )

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("governance-binding architecture doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("governance-binding architecture doc is missing from docs site")
    if "Trusted-Host Promotion Governance-Binding Architecture" not in review_index:
        failures.append("review docs index is missing governance-binding architecture")
    target = "trusted-host-promotion-governance-binding-architecture-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append(f"{target} is missing from release-check")
    if f"make {target}" not in readme:
        failures.append("README is missing governance-binding architecture command")
    if DOC_REL not in readme:
        failures.append("README is missing governance-binding architecture doc")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": DOC_REL,
        "decision_id": "PRD-TRUSTED-HOST-BINDING-001",
        "decision_status": "proposed_for_explicit_approval",
        "tool_count": tool_surface["tool_count"],
        "tool_surface_valid": tool_surface["valid"],
        "no_new_powers_valid": no_new_powers["valid"],
        "runtime_changes_allowed": False,
        "public_contract_changes_allowed": False,
        "database_migration_allowed": False,
        "trusted_host_promotion_expansion_allowed": False,
        "node_side_placement_allowed": False,
        "new_power_classes_allowed": no_new_powers["new_power_classes_allowed"],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host governance-binding architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"decision_id: {report['decision_id']}",
        f"decision_status: {report['decision_status']}",
        f"tool_count: {report['tool_count']}",
        f"tool_surface_valid: {str(report['tool_surface_valid']).lower()}",
        f"no_new_powers_valid: {str(report['no_new_powers_valid']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "public_contract_changes_allowed: "
        f"{str(report['public_contract_changes_allowed']).lower()}",
        f"database_migration_allowed: {str(report['database_migration_allowed']).lower()}",
        "trusted_host_promotion_expansion_allowed: "
        f"{str(report['trusted_host_promotion_expansion_allowed']).lower()}",
        f"node_side_placement_allowed: {str(report['node_side_placement_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
