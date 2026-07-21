"""Validate the bounded PIS-003 SD-PG-001 implementation-gate candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_pis_003_entry_internal_review_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-gate.md"
DOC_NAME = "production-identity-storage-pis-003-sd-pg-001-implementation-gate.md"
DOC_TITLE = "Production Identity And Storage PIS-003 SD-PG-001 Implementation Gate"
DOC_SHA256 = "42bb379ab0afee8507555e971febecd55904f41695bec16d7ceb2e91112a51f7"
CONTRACT_REL = "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-gate.json"
CONTRACT_SHA256 = "b670118ca53b6701a30bbb0b4692f15caf704267ebd468a7db3843d769e2e1fd"
TARGET = "production-identity-storage-pis-003-sd-pg-001-implementation-gate-check"
BASELINE_COMMIT = "ebb656ac8e5b0f428641092135d7e99b5845fa85"

EXPECTED_DIRECT_REQUIREMENTS = [
    "SQLAlchemy==2.0.51",
    "alembic==1.18.5",
    "psycopg==3.3.4",
]

EXPECTED_ADDED_PACKAGES = [
    {"name": "alembic", "version": "1.18.5", "license": "MIT", "marker": "all"},
    {
        "name": "greenlet",
        "version": "3.5.3",
        "license": "MIT AND PSF-2.0",
        "marker": "sqlalchemy platform marker",
    },
    {"name": "mako", "version": "1.3.12", "license": "MIT", "marker": "all"},
    {
        "name": "markupsafe",
        "version": "3.0.3",
        "license": "BSD-3-Clause",
        "marker": "all",
    },
    {
        "name": "psycopg",
        "version": "3.3.4",
        "license": "LGPL-3.0-only",
        "marker": "all",
    },
    {"name": "sqlalchemy", "version": "2.0.51", "license": "MIT", "marker": "all"},
    {
        "name": "tzdata",
        "version": "2026.3",
        "license": "Apache-2.0",
        "marker": "sys_platform == 'win32'",
    },
]

EXPECTED_IMPLEMENTATION_PATHS = [
    "Makefile",
    "README.md",
    "apps/api/src/ithildin_api/storage_import.py",
    "apps/api/src/ithildin_api/storage_schema.py",
    "db/alembic/alembic.ini",
    "db/alembic/env.py",
    "db/alembic/script.py.mako",
    "db/alembic/versions/0001_sandbox_descriptors.py",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-authority.json",
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-record.md",
    "docs/codex/review-docs-index.md",
    "pyproject.toml",
    "scripts/build_docs_site.py",
    "scripts/production_identity_storage_pis_003_sd_pg_001_implementation_check.py",
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
    "tests/test_storage_schema_import.py",
    "uv.lock",
]

EXPECTED_REQUIRED_EVIDENCE = [
    "exact_dependency_lock_url_hash_marker_license_and_graph_inventory",
    "lock_preview_hash_reproduced_without_existing_version_change",
    "sqlalchemy_core_only_no_orm_session_async_pool_or_runtime_import",
    "single_alembic_head_and_deterministic_offline_postgresql_sql",
    "sandbox_descriptor_schema_constraint_jsonb_digest_timestamp_and_index_contract",
    "canonical_payload_digest_and_strict_utc_timestamp_round_trip",
    "malformed_duplicate_unknown_status_digest_mismatch_naive_time_and_non_object_rejection",
    "caller_owned_connection_and_explicit_outer_transaction_contract",
    "no_embedded_persisted_or_logged_url_or_credentials",
    "no_startup_migration_runtime_pool_runtime_import_or_second_aggregate",
    "current_sqlite_schema_runtime_api_audit_and_authority_invariance",
    "policy_manifest_and_24_tool_invariance",
    "rollback_plan_bound_before_database_connection",
    "test_harness_is_not_executed_and_driver_is_not_loaded",
    "phase_aware_predecessor_and_exact_dependency_transition_evidence",
    "focused_lint_mypy_docs_agent_workflow_release_and_review_candidate_gates",
    "exact_candidate_source_review_with_zero_open_findings",
]

EXPECTED_DEFERRED_CONNECTION_EVIDENCE = [
    "separate_connection_evidence_gate_with_exact_authority",
    "plain_sync_psycopg_system_libpq_tls_and_sbom_receipt_before_connection",
    "externally_supplied_isolated_test_dsn_without_repo_controlled_service_lifecycle",
    "rollback_plan_and_target_identity_bound_before_database_connection",
    "secret_safe_tls_and_driver_failure_evidence",
    "real_empty_quarantined_target_import_and_semantic_verification",
    "isolated_target_discard_proved_before_activation_or_runtime_use",
]

EXPECTED_PROTECTED_HASHES = {
    "apps/api/src/ithildin_api/app.py": (
        "2cd6cb4304165de300b4418c73308d7cd15d9c5ac36c2869ada1b7f7d28fc0d4"
    ),
    "apps/api/src/ithildin_api/config.py": (
        "53f9c609adb0e033ffd7c8a9a4cf10187dd3303702521439c67e4e99abec6891"
    ),
    "apps/api/src/ithildin_api/sandbox_descriptors.py": (
        "30aa57adffe7b981cf5f5a92786b33ae0da5ea1c611cd0806cb780ec6d603bec"
    ),
    "apps/api/src/ithildin_api/storage.py": (
        "74825cf8d3b4cfdb19efbda3174c8df1dcedbecd62dede8f1d052b5fb9b955fe"
    ),
    "docs/codex/production-identity-storage-pis-003-entry-internal-source-review.md": (
        "939082ddd7c247227889dc974cdab5957687a52e60920d12f969fb0a5145db6c"
    ),
    "docs/codex/production-identity-storage-pis-003-entry-review-authority.json": (
        "455f9f1cacbc0c91a2776cb0bd9bf6a58c70ae9b6be0e54325dce83227019379"
    ),
    "pyproject.toml": "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d",
    "scripts/production_identity_storage_pis_003_entry_internal_review_check.py": (
        "01c63d6fde3ab658a5dd78ccfd453765b05ab0f673b2b22fce956507c6ddc747"
    ),
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
}

EXPECTED_AUTHORITY = {
    "pis_003_sd_pg_001_implementation_gate_recorded": True,
    "pis_003_sd_pg_001_candidate_selected": True,
    "exact_candidate_source_review_required": True,
    "pis_003_sd_pg_001_implementation_allowed": False,
    "dependency_changes_allowed": False,
    "sqlalchemy_core_use_allowed": False,
    "alembic_offline_use_allowed": False,
    "psycopg_plain_sync_use_allowed": False,
    "offline_schema_artifact_implementation_allowed": False,
    "offline_migration_artifact_implementation_allowed": False,
    "isolated_importer_implementation_allowed": False,
    "test_harness_implementation_allowed": False,
    "isolated_test_connection_allowed": False,
    "migration_execution_allowed": False,
    "database_connections_allowed": False,
    "postgres_service_allowed": False,
    "runtime_behavior_changes_allowed": False,
    "public_api_changes_allowed": False,
    "current_sqlite_schema_changes_allowed": False,
    "audit_ordering_changes_allowed": False,
    "runtime_postgres_allowed": False,
    "production_identity_allowed": False,
    "enterprise_rbac_allowed": False,
    "remote_admin_allowed": False,
    "backup_restore_runtime_allowed": False,
    "retention_enforcement_allowed": False,
    "new_power_classes_allowed": False,
    "public_security_product_positioning_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
    "uat_required_now": False,
    "connection_evidence_gate_required": True,
}

EXPECTED_POST_REVIEW_AUTHORITY_CEILING = {
    "pis_003_sd_pg_001_implementation_allowed": True,
    "dependency_changes_allowed": True,
    "sqlalchemy_core_use_allowed": True,
    "alembic_offline_use_allowed": True,
    "psycopg_plain_sync_dependency_allowed": True,
    "psycopg_plain_sync_use_allowed": False,
    "offline_schema_artifact_implementation_allowed": True,
    "offline_migration_artifact_implementation_allowed": True,
    "isolated_importer_implementation_allowed": True,
    "test_harness_implementation_allowed": True,
    "isolated_test_connection_allowed": False,
    "migration_execution_allowed": False,
    "database_connections_allowed": False,
    "postgres_service_allowed": False,
    "runtime_behavior_changes_allowed": False,
    "public_api_changes_allowed": False,
    "current_sqlite_schema_changes_allowed": False,
    "audit_ordering_changes_allowed": False,
    "runtime_postgres_allowed": False,
    "production_identity_allowed": False,
    "enterprise_rbac_allowed": False,
    "remote_admin_allowed": False,
    "backup_restore_runtime_allowed": False,
    "retention_enforcement_allowed": False,
    "new_power_classes_allowed": False,
    "public_security_product_positioning_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
    "uat_required_now": False,
    "connection_evidence_gate_required": True,
}

EXPECTED_IMPLEMENTATION_TRANSITION = {
    "preimplementation_state": (
        "baseline_pyproject_and_uv_lock_hashes_with_selected_dependencies_absent"
    ),
    "post_review_state": "exact_preview_hashes_with_valid_durable_gate_review_authority",
    "predecessor_validation_mode": (
        "historical_git_object_identity_not_mutable_head_dependency_absence"
    ),
    "unapproved_dependency_or_lock_drift_allowed": False,
    "gate_review_validator_module": (
        "scripts.production_identity_storage_pis_003_sd_pg_001_"
        "implementation_gate_internal_review_check"
    ),
    "required_gate_review_artifacts": [
        (
            "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
            "implementation-gate-internal-source-review.md"
        ),
        (
            "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
            "implementation-gate-review-authority.json"
        ),
        (
            "scripts/production_identity_storage_pis_003_sd_pg_001_"
            "implementation_gate_internal_review_check.py"
        ),
    ],
    "post_review_preview_pyproject_sha256": (
        "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627"
    ),
    "post_review_preview_uv_lock_sha256": (
        "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb"
    ),
}

REQUIRED_PHRASES = [
    (
        "Status: committed implementation-gate candidate pending exact-candidate source review; "
        "no implementation authority is active."
    ),
    "Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE`.",
    "Parent review: `PRD-PROD-IAM-STORAGE-PIS-003-ENTRY-REVIEW`.",
    f"Gate baseline commit: `{BASELINE_COMMIT}`.",
    "Implementation slice: `PIS-003-SD-PG-001`.",
    "Gate outcome: `select_exact_bounded_candidate_pending_gate_review`.",
    "Current governed tool count: `24`.",
    "The preview changed only `pyproject.toml` and `uv.lock`",
    "The complete added package set is SQLAlchemy `2.0.51`",
    "The preview does not upgrade typing-extensions",
    "No supported system `libpq` is present",
    "The importer accepts a caller-owned SQLAlchemy `Connection` only.",
    "`offline_implementation_complete_connection_evidence_gate_pending`",
    "`revert_exact_candidate_and_discard_isolated_target_before_activation`",
    "`pis_003_sd_pg_001_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`database_connections_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`uat_required_now: false`",
    "`test_harness_implementation_allowed: true`",
    "`isolated_test_connection_allowed: false`",
    "`connection_evidence_gate_required: true`",
    "`review_pis_003_sd_pg_001_implementation_gate_exact_candidate`",
    f"make {TARGET}",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(r"\bimplementation (?:is|has been) (?:approved|authorized)\b"),
    re.compile(r"\bdependencies? may now be (?:added|changed|installed)\b"),
    re.compile(r"\bpostgres(?:ql)? may now (?:connect|run|serve|start)\b"),
    re.compile(r"\b(?:release|production promotion|uat) (?:is|has been) (?:approved|complete)\b"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def validate_gate_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    failures = [
        f"PIS-003 implementation gate is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]
    failures.extend(
        f"PIS-003 implementation gate contains forbidden authority pattern: {pattern.pattern}"
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS
        if pattern.search(lowered)
    )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "gate_id",
        "parent_review",
        "gate_baseline_commit",
        "implementation_slice",
        "gate_outcome",
        "tool_count",
        "lock_preview",
        "implementation_transition",
        "implementation_boundary",
        "connection_contract",
        "offline_required_evidence",
        "deferred_connection_evidence_requirements",
        "rollback",
        "protected_hashes",
        "post_review_authority_ceiling",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 implementation gate top-level keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "gate_id": "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE",
        "parent_review": "PRD-PROD-IAM-STORAGE-PIS-003-ENTRY-REVIEW",
        "gate_baseline_commit": BASELINE_COMMIT,
        "implementation_slice": "PIS-003-SD-PG-001",
        "gate_outcome": "select_exact_bounded_candidate_pending_gate_review",
        "tool_count": 24,
        "next_required_action": ("review_pis_003_sd_pg_001_implementation_gate_exact_candidate"),
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 implementation gate field {key} is not {expected!r}")
    if type(contract.get("tool_count")) is not int:
        failures.append("PIS-003 implementation gate tool_count must be an exact integer")

    preview = contract.get("lock_preview")
    if not isinstance(preview, dict):
        failures.append("PIS-003 lock preview must be an object")
    else:
        expected_preview = {
            "uv_version": "0.11.12",
            "python_version": "3.12.13",
            "dependency_group": "pis3",
            "dependency_group_default_enabled": False,
            "direct_requirements": EXPECTED_DIRECT_REQUIREMENTS,
            "added_packages": EXPECTED_ADDED_PACKAGES,
            "changed_existing_packages": [],
            "removed_packages": [],
            "pyproject_added_lines": 5,
            "uv_lock_added_lines": 217,
            "preview_pyproject_sha256": (
                "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627"
            ),
            "preview_uv_lock_sha256": (
                "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb"
            ),
            "index": "https://pypi.org/simple",
            "forbidden_packages": ["psycopg-c", "psycopg-binary", "psycopg-pool", "asyncpg"],
            "psycopg_flavor": "plain_sync_pure_python_psycopg_impl_python",
            "current_environment_libpq": (
                "absent_connection_evidence_blocked_until_exact_environment_receipt"
            ),
        }
        if preview != expected_preview:
            failures.append("PIS-003 dependency lock preview is not exact")

    if contract.get("implementation_transition") != EXPECTED_IMPLEMENTATION_TRANSITION:
        failures.append("PIS-003 implementation transition is not exact")

    boundary = contract.get("implementation_boundary")
    if not isinstance(boundary, dict):
        failures.append("PIS-003 implementation boundary must be an object")
    else:
        if boundary.get("implementation_allowed_paths") != EXPECTED_IMPLEMENTATION_PATHS:
            failures.append("PIS-003 implementation path boundary is not exact")
        expected_boundary_values = {
            "selected_aggregate": "sandbox_descriptors",
            "protected_paths": [
                "apps/api/src/ithildin_api/app.py",
                "apps/api/src/ithildin_api/config.py",
                "apps/api/src/ithildin_api/sandbox_descriptors.py",
                "apps/api/src/ithildin_api/storage.py",
                "tool-manifests.lock.json",
            ],
            "runtime_imports_allowed": False,
            "second_aggregate_allowed": False,
            "current_sqlite_changes_allowed": False,
            "audit_ordering_changes_allowed": False,
        }
        for key, expected in expected_boundary_values.items():
            if boundary.get(key) != expected:
                failures.append(f"PIS-003 implementation boundary {key} is not exact")

    connection = contract.get("connection_contract")
    if not isinstance(connection, dict):
        failures.append("PIS-003 connection contract must be an object")
    else:
        expected_false = {
            "importer_accepts_dsn",
            "importer_creates_engine_or_pool",
            "importer_commits_or_rolls_back",
            "dsn_or_credentials_persisted_or_logged",
            "alembic_offline_requires_connection_or_url",
            "transparent_retries_allowed",
        }
        if any(connection.get(key) is not False for key in expected_false):
            failures.append("PIS-003 connection contract false boundaries are not exact")
        if connection.get("importer_input") != "caller_owned_sqlalchemy_connection":
            failures.append("PIS-003 importer input is not caller-owned Connection only")
        if connection.get("test_harness_pool") != "sqlalchemy_nullpool":
            failures.append("PIS-003 test harness pool is not NullPool")
        if connection.get("test_harness_code_accepts_external_dsn_parameter") is not True:
            failures.append("PIS-003 test harness DSN parameter boundary is not exact")
        if connection.get("test_harness_execution_with_external_dsn_allowed") is not False:
            failures.append("PIS-003 test harness execution boundary is not fail-closed")
        if connection.get("test_harness_owns_connection_and_outer_transaction") is not True:
            failures.append("PIS-003 outer transaction ownership is not exact")

    if contract.get("offline_required_evidence") != EXPECTED_REQUIRED_EVIDENCE:
        failures.append("PIS-003 offline required evidence is not exact")
    if (
        contract.get("deferred_connection_evidence_requirements")
        != EXPECTED_DEFERRED_CONNECTION_EVIDENCE
    ):
        failures.append("PIS-003 deferred connection evidence is not exact")
    rollback = contract.get("rollback")
    expected_rollback = {
        "disposition": "revert_exact_candidate_and_discard_isolated_target_before_activation",
        "bound_before_connection": True,
        "source_sqlite_modified": False,
        "reverse_import_allowed": False,
        "dual_write_allowed": False,
        "in_place_repair_allowed": False,
        "activation_allowed": False,
    }
    if rollback != expected_rollback:
        failures.append("PIS-003 rollback contract is not exact")
    if contract.get("protected_hashes") != EXPECTED_PROTECTED_HASHES:
        failures.append("PIS-003 protected hash inventory is not exact")
    post_review_ceiling = contract.get("post_review_authority_ceiling")
    if (
        post_review_ceiling != EXPECTED_POST_REVIEW_AUTHORITY_CEILING
        or not isinstance(post_review_ceiling, dict)
        or any(type(value) is not bool for value in post_review_ceiling.values())
    ):
        failures.append("PIS-003 post-review authority ceiling is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 implementation gate authority is not the exact Boolean map")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 implementation gate is not UTF-8")
    failures.extend(validate_gate_text(doc_text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 implementation gate bytes do not match the closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 implementation gate contract bytes do not match the closed digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_exists:
        failures.append("PIS-003 implementation-gate baseline commit is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 implementation-gate baseline is not an ancestor of HEAD")

    protected_hashes_match = True
    for path, expected_hash in EXPECTED_PROTECTED_HASHES.items():
        actual_hash = hashlib.sha256(_git_bytes(repo_root, BASELINE_COMMIT, path)).hexdigest()
        if actual_hash != expected_hash:
            protected_hashes_match = False
            failures.append(f"PIS-003 protected baseline path hash mismatch: {path}")

    entry_review = production_identity_storage_pis_003_entry_internal_review_check.build_report(
        repo_root
    )
    entry_review_valid = bool(
        entry_review.get("valid")
        and entry_review.get("pis_003_entry_source_review_complete")
        and entry_review.get("pis_003_entry_decision_cleared")
        and entry_review.get("pis_003_sd_pg_001_implementation_gate_preparation_allowed")
        and not entry_review.get("pis_003_sd_pg_001_implementation_allowed")
        and not entry_review.get("dependency_changes_allowed")
        and not entry_review.get("database_connections_allowed")
    )
    if not entry_review_valid:
        failures.append("PIS-003 entry review does not authorize implementation-gate preparation")

    dependency_transition_state = _dependency_transition_state(repo_root)
    if dependency_transition_state == "invalid":
        failures.append("PIS-003 dependency transition is not an exact authorized state")
    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-003 implementation gate tool count is {tool_count}, expected 24")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 implementation gate wiring is incomplete")

    gate_valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(gate_valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": gate_valid,
        "failures": failures,
        "gate_document": DOC_REL,
        "gate_document_sha256": doc_hash,
        "gate_document_hash_matches": doc_hash == DOC_SHA256,
        "gate_contract": CONTRACT_REL,
        "gate_contract_sha256": contract_hash,
        "gate_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "gate_id": contract.get("gate_id") if gate_valid else "invalid",
        "gate_outcome": contract.get("gate_outcome") if gate_valid else "invalid",
        "gate_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "protected_hashes_match": protected_hashes_match,
        "entry_review_valid": entry_review_valid,
        "dependency_transition_state": dependency_transition_state,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (
            contract.get("next_required_action") if gate_valid else "invalid_gate"
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "gate_document",
        "gate_id",
        "gate_outcome",
        "gate_baseline_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "gate_document_hash_matches",
        "gate_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "entry_review_valid",
        "dependency_transition_state",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 implementation gate check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _selected_dependencies_absent(repo_root: Path) -> bool:
    try:
        project = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
        lock = tomllib.loads((repo_root / "uv.lock").read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return False
    groups = project.get("dependency-groups")
    if isinstance(groups, dict) and "pis3" in groups:
        return False
    packages = lock.get("package")
    if not isinstance(packages, list):
        return False
    names = {package.get("name", "").lower() for package in packages if isinstance(package, dict)}
    return not {"sqlalchemy", "alembic", "psycopg"}.intersection(names)


def _selected_dependencies_exact(repo_root: Path) -> bool:
    try:
        project = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
        lock = tomllib.loads((repo_root / "uv.lock").read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return False
    groups = project.get("dependency-groups")
    if not isinstance(groups, dict) or groups.get("pis3") != EXPECTED_DIRECT_REQUIREMENTS:
        return False
    packages = lock.get("package")
    if not isinstance(packages, list):
        return False
    versions = {
        str(package.get("name", "")).lower(): str(package.get("version", ""))
        for package in packages
        if isinstance(package, dict)
    }
    expected = {item["name"]: item["version"] for item in EXPECTED_ADDED_PACKAGES}
    if any(versions.get(name) != version for name, version in expected.items()):
        return False
    forbidden = {"psycopg-c", "psycopg-binary", "psycopg-pool", "asyncpg"}
    return not forbidden.intersection(versions)


def _dependency_transition_state(repo_root: Path) -> str:
    pyproject_hash = hashlib.sha256(_read_bytes(repo_root / "pyproject.toml")).hexdigest()
    lock_hash = hashlib.sha256(_read_bytes(repo_root / "uv.lock")).hexdigest()
    return classify_dependency_transition(
        pyproject_hash=pyproject_hash,
        lock_hash=lock_hash,
        dependencies_absent=_selected_dependencies_absent(repo_root),
        dependencies_exact=_selected_dependencies_exact(repo_root),
        post_review_authority_valid=_post_review_authority_valid(repo_root),
    )


def classify_dependency_transition(
    *,
    pyproject_hash: str,
    lock_hash: str,
    dependencies_absent: bool,
    dependencies_exact: bool,
    post_review_authority_valid: bool,
) -> str:
    baseline = (
        pyproject_hash == EXPECTED_PROTECTED_HASHES["pyproject.toml"]
        and lock_hash == EXPECTED_PROTECTED_HASHES["uv.lock"]
        and dependencies_absent
        and not dependencies_exact
    )
    if baseline:
        return "preimplementation"
    reviewed_preview = (
        pyproject_hash == EXPECTED_IMPLEMENTATION_TRANSITION["post_review_preview_pyproject_sha256"]
        and lock_hash == EXPECTED_IMPLEMENTATION_TRANSITION["post_review_preview_uv_lock_sha256"]
        and not dependencies_absent
        and dependencies_exact
        and post_review_authority_valid
    )
    return "post_review_implementation" if reviewed_preview else "invalid"


def _post_review_authority_valid(repo_root: Path) -> bool:
    module_name = str(EXPECTED_IMPLEMENTATION_TRANSITION["gate_review_validator_module"])
    try:
        module = importlib.import_module(module_name)
        report = module.build_report(repo_root)
    except (AttributeError, ImportError, ModuleNotFoundError):
        return False
    if not isinstance(report, dict) or report.get("valid") is not True:
        return False
    if report.get("review_disposition") != "cleared_for_offline_implementation_only":
        return False
    finding_fields = (
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
        "open_findings",
    )
    if any(report.get(field) != 0 for field in finding_fields):
        return False
    if any(
        report.get(field) is not expected
        for field, expected in EXPECTED_POST_REVIEW_AUTHORITY_CEILING.items()
    ):
        return False
    return report.get("next_required_action") == "implement_pis_003_sd_pg_001_offline_candidate"


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    return all(
        (
            f"{TARGET}:" in makefile,
            f"release-check: {TARGET}" in makefile,
            f"make {TARGET}" in readme,
            DOC_REL in readme,
            CONTRACT_REL in readme,
            DOC_REL in docs_site,
            DOC_TITLE in review_index,
            TARGET in release_guardrails,
            DOC_REL in review_docs.REVIEW_DOCS,
            "Current PIS-003 SD-PG-001 implementation gate" in register,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 implementation gate contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 implementation gate contract has {exc}"]
        return {}, ["PIS-003 implementation gate contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 implementation gate contract must be a JSON object"]
    return payload, []


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _git_bytes(repo_root: Path, commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else b""


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return -1
    manifests = payload.get("manifests")
    return len(manifests) if isinstance(manifests, list) else -1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


if __name__ == "__main__":
    raise SystemExit(main())
