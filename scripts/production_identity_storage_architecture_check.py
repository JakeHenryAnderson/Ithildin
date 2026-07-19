"""Validate the production identity and storage architecture packet."""

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
DOC = ROOT / "docs/codex/production-identity-storage-architecture.md"
CONTRACT_START = "<!-- production-identity-storage-contract:start -->"
CONTRACT_END = "<!-- production-identity-storage-contract:end -->"
ORDERED_WORK_PACKAGES = [f"PIS-{index:03d}" for index in range(1, 9)]

REQUIRED_PHRASES = [
    "Status: design-only architecture packet for `ERG-006` and `ERG-007`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-006`: production identity and multi-user authorization.",
    "`ERG-007`: durable runtime storage and retention.",
    "local principal labels, not enterprise authentication",
    "SQLite runtime storage, not runtime Postgres",
    "Phase 1 Self-Hosted Candidate",
    "single-organization, self-hosted Manager",
    "OIDC Authorization Code with PKCE",
    "tokens are consumed during callback validation and are not persisted",
    "immutable external identity key is `(organization_id, normalized issuer, subject)`",
    "pre-provisioned subject mappings",
    "Roles and workspace memberships are server-owned records",
    "An external receipt may anchor a recovery discontinuity; it cannot substitute",
    "Node Workload Identity And Transport",
    "mTLS is additive to, not a replacement for, the current Ed25519",
    "PostgreSQL is the only candidate production runtime backend",
    "Audit And Evidence In A Multi-Process Runtime",
    "Domain mutation, the authoritative audit event, and an export-outbox record",
    "derived, signed, checkpoint-bound export",
    "offline, verify-before-activate cutover",
    "Dual write is forbidden",
    "Only one Manager deployment epoch may hold write authority",
    "multiple Manager API processes within one active deployment epoch",
    "Candidate Work-Package Order",
    "`PIS-001`",
    "`PIS-008`",
    "Future Identity Architecture Questions",
    "Future Storage Architecture Questions",
    "Disaster-Recovery Candidate Contract",
    "replace a lost Node; do not restore its private",
    "Stale-Restore And Split-Brain Rule",
    "monotonic recovery watermark held outside the restored database",
    "reserve-anchor-finalize ordering",
    "sealed, exported, signed, independently verified segment",
    "Required Recovery Proof",
    "Evidence Contract",
    "Required Before Implementation",
    "external architecture review",
    "The current decision is `planning_only`.",
    "Planning Status Axes",
    "Runtime implementation remains blocked",
    "make production-identity-storage-architecture-check",
]

REQUIRED_SAFE_EVIDENCE_PHRASES = [
    "authenticated subject label and Ithildin principal ID",
    "tenant/team/workspace labels",
    "storage backend label and schema version",
    "migration state",
    "backup/restore status labels",
    "retention-policy label",
    "safe error labels for identity or storage failures",
    "retired Node credential replay",
    "reconciliation_failed",
    "fenced",
]

FORBIDDEN_PHRASES = [
    "production IAM is implemented",
    "enterprise RBAC is implemented",
    "runtime Postgres is enabled",
    "remote admin use is approved",
    "custody-grade audit is implemented",
    "compliance automation is approved",
    "public security product approved",
    "hosted control plane is implemented",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    contract: dict[str, Any] = {}
    if not doc_path.exists():
        failures.append("production identity/storage architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    "production identity/storage architecture doc is missing phrase: "
                    f"{phrase}"
                )
        for phrase in REQUIRED_SAFE_EVIDENCE_PHRASES:
            if phrase not in text:
                failures.append(
                    "production identity/storage architecture doc is missing safe evidence "
                    f"phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "production identity/storage architecture doc contains forbidden phrase: "
                    f"{phrase}"
                )
        try:
            contract = _contract(text)
        except ValueError as exc:
            failures.append(f"production identity/storage contract is invalid: {exc}")

    expected_contract: dict[str, Any] = {
        "document_type": "phase_1_candidate_architecture",
        "schema_version": "1",
        "tool_count": _tool_count(repo_root, failures),
        "decision_status": "planning_only",
        "deployment_scope": "single_organization_self_hosted",
        "organization_id_required": True,
        "multi_tenant_hosted_authorized": False,
        "human_identity_protocol": "oidc_authorization_code_pkce_bff",
        "human_subject_key": ["organization_id", "issuer", "subject"],
        "human_provisioning": "preprovisioned_no_jit_admin",
        "caller_identity_or_roles_authorized": False,
        "server_owned_memberships_required": True,
        "session_model": "opaque_server_side_cookie",
        "session_handle_storage": "keyed_digest_only",
        "session_digest_key_custody": "external_kms_hsm_or_equivalent",
        "session_digest_key_rotation": "invalidates_bound_sessions",
        "oidc_token_persistence_authorized": False,
        "csrf_protection_required": True,
        "recent_authentication_for_sensitive_operations_required": True,
        "remote_admin_tls_required": True,
        "remote_admin_bearer_token_authorized": False,
        "break_glass_scope": "loopback_fencing_isolation_recovery_orchestration_only",
        "node_transport": "tls13_mtls_plus_ed25519_request_signatures",
        "node_private_key_backup_authorized": False,
        "node_private_key_production_custody": "non_exportable_os_keystore_or_equivalent",
        "production_storage_candidate": "postgresql",
        "sqlite_production_authorized": False,
        "dual_write_authorized": False,
        "migration_mode": "offline_verify_before_activate",
        "legacy_local_authority_import_authorized": False,
        "manager_writer_topology": "single_active_deployment_multi_process_fenced",
        "domain_audit_outbox_atomic": True,
        "production_audit_canonical_store": "postgresql_append_only_hash_chain",
        "audit_head_serialization": "segment_head_for_update",
        "jsonl_production_role": "derived_signed_export_only",
        "external_recovery_watermark_required": True,
        "external_watermark_protocol": "reserve_anchor_finalize",
        "external_watermark_provider_selected": False,
        "external_key_custody_decision_required": True,
        "key_custody_provider_selected": False,
        "retention_deletion_unit": "sealed_audit_segment_only",
        "ordered_work_packages": ORDERED_WORK_PACKAGES,
        "runtime_implementation_authorized": False,
        "production_identity_authorized": False,
        "runtime_postgres_authorized": False,
        "remote_node_transport_authorized": False,
        "release_authorized": False,
        "uat_required_now": False,
    }
    for key, expected in expected_contract.items():
        if contract.get(key) != expected:
            failures.append(
                "production identity/storage contract has unexpected "
                f"{key}: {contract.get(key)!r}"
            )
    unexpected_contract_keys = sorted(set(contract) - set(expected_contract))
    if unexpected_contract_keys:
        failures.append(
            "production identity/storage contract has unreviewed keys: "
            + ", ".join(unexpected_contract_keys)
        )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("production identity/storage architecture doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("production identity/storage architecture doc is missing from docs site")
    if "Production Identity And Storage Architecture" not in review_index:
        failures.append("review docs index is missing production identity/storage architecture")
    if "production-identity-storage-architecture-check:" not in makefile:
        failures.append("Make target is missing: production-identity-storage-architecture-check")
    if "production-identity-storage-architecture-check" not in release_check_body:
        failures.append(
            "production-identity-storage-architecture-check is missing from release-check"
        )
    if "make production-identity-storage-architecture-check" not in readme:
        failures.append("README is missing production identity/storage architecture command")
    if "production-identity-storage-architecture.md" not in readme:
        failures.append("README is missing production identity/storage architecture doc")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "production-identity-storage-architecture.md" not in container_text:
            failures.append(
                f"{container_name} is missing production identity/storage architecture pointer"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": doc_rel,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "tool_count": 24,
        "phase_1_candidate_specified": bool(contract),
        "deployment_scope": contract.get("deployment_scope"),
        "ordered_work_packages": contract.get("ordered_work_packages", []),
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "runtime_postgres_allowed": False,
        "remote_admin_allowed": False,
        "hosted_control_plane_allowed": False,
        "custody_grade_audit_allowed": False,
        "compliance_claims_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin production identity/storage architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"erg_006_status: {report['erg_006_status']}",
        f"erg_007_status: {report['erg_007_status']}",
        f"tool_count: {report['tool_count']}",
        "phase_1_candidate_specified: "
        f"{str(report['phase_1_candidate_specified']).lower()}",
        f"deployment_scope: {report['deployment_scope']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"enterprise_rbac_allowed: {str(report['enterprise_rbac_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"remote_admin_allowed: {str(report['remote_admin_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _contract(text: str) -> dict[str, Any]:
    if text.count(CONTRACT_START) != 1 or text.count(CONTRACT_END) != 1:
        raise ValueError("contract markers must each occur exactly once")
    start_index = text.index(CONTRACT_START)
    end_index = text.index(CONTRACT_END)
    if start_index >= end_index:
        raise ValueError("contract start marker must precede end marker")
    payload_start = start_index + len(CONTRACT_START)
    payload = text[payload_start:end_index].strip()
    try:
        document = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("contract must be valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("contract must be a JSON object")
    return document


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate contract key: {key}")
        document[key] = value
    return document


def _tool_count(repo_root: Path, failures: list[str]) -> int:
    lock_path = repo_root / "tool-manifests.lock.json"
    try:
        lock = json.loads(
            lock_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError):
        failures.append("tool manifest lock is unavailable or ambiguous")
        return -1
    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    if not isinstance(manifests, list):
        failures.append("tool manifest lock has no manifest list")
        return -1
    if len(manifests) != 24:
        failures.append(f"actual governed tool count changed: {len(manifests)}")
    return len(manifests)


if __name__ == "__main__":
    raise SystemExit(main())
