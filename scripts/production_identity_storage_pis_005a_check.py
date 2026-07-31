"""Validate the bounded PIS-005A local Node workload-identity lane."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast

from ithildin_api.trusted_host_promotion_v2_migration import (
    expected_pis005a_schema_fingerprint,
)
from ithildin_schemas import JsonObject

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path(
    "docs/codex/production-identity-storage-pis-005a-entry-and-implementation-contract.json"
)
DOC_REL = Path(
    "docs/codex/production-identity-storage-pis-005a-node-workload-identity-foundation.md"
)
NEXT_TICKET_REL = Path(
    "docs/codex/production-identity-storage-pis-005a-remote-transport-next-ticket.md"
)
REVIEW_RECORD_REL = Path("docs/codex/production-identity-storage-pis-005a-independent-review.md")
BRANCH = "codex/enterprise-e2-pis005a-review-repair-6"
SOURCE_COMMIT = "e8e6a75ca3d76a233243f5e890091f3c95731da9"
SOURCE_TREE = "1a5a6c818bf3fd5e17bcffedaae4cf5497e1e6f2"
SECURITY_PREREQUISITE_COMMIT = "83db1196213b0e4e7de5d97ab0fb37b934ca4ab7"
SECURITY_PREREQUISITE_TREE = "86731324feec59596146a1149cdde69f47dd58d0"
REPAIR_BASE_BRANCH = "codex/enterprise-e2-pis005a-review-repair-5"
REPAIR_BASE_COMMIT = "cedcf5d0bf3baeab12f54600a247a61a4671d7f9"
REPAIR_BASE_TREE = "6e4c4097680c97c77913ba10054dbb5e234abe4c"
_ORIGINAL_BRANCH = "codex/enterprise-e2-pis005a-node-identity"
_ORIGINAL_COMMIT = "fce0a3668db5150cf0aa75de1fd914b296a2e099"
_ORIGINAL_TREE = "331adb70f2c2c24def540c3576fc6876e33c478c"
_REPAIR_2_BRANCH = "codex/enterprise-e2-pis005a-review-repair-2"
_REPAIR_2_COMMIT = "1542bd0469e18a0ae52cc48920f30b4e41518513"
_REPAIR_2_TREE = "ba9a40e929ff330c15c6c23766006eb1c26878ef"
_REPAIR_3_BRANCH = "codex/enterprise-e2-pis005a-review-repair-3"
_REPAIR_3_COMMIT = "afd13f98440d4cd9c032b6a996db133bdf78055d"
_REPAIR_3_TREE = "49e958caeba4f3bce51feaa4e842f8f622c00d4a"
_REPAIR_4_BRANCH = "codex/enterprise-e2-pis005a-review-repair-4"
_REPAIR_4_COMMIT = "22566cae4a1bc84dca20747d7bd1531d77d7f025"
_REPAIR_4_TREE = "44952292c183b4a481f15dc691e6c04e90e45d55"
_PREDECESSOR_REFS = (
    ("codex/enterprise-e2-pis004a-review-repair", SOURCE_COMMIT, SOURCE_TREE),
    (_ORIGINAL_BRANCH, _ORIGINAL_COMMIT, _ORIGINAL_TREE),
    (_REPAIR_2_BRANCH, _REPAIR_2_COMMIT, _REPAIR_2_TREE),
    (_REPAIR_3_BRANCH, _REPAIR_3_COMMIT, _REPAIR_3_TREE),
    (_REPAIR_4_BRANCH, _REPAIR_4_COMMIT, _REPAIR_4_TREE),
    (REPAIR_BASE_BRANCH, REPAIR_BASE_COMMIT, REPAIR_BASE_TREE),
)
_REPAIR_PARENT_CHAIN = (
    (_REPAIR_2_COMMIT, _ORIGINAL_COMMIT),
    (_REPAIR_3_COMMIT, _REPAIR_2_COMMIT),
    (_REPAIR_4_COMMIT, _REPAIR_3_COMMIT),
    (REPAIR_BASE_COMMIT, _REPAIR_4_COMMIT),
)
REJECTED_CANDIDATE_COMMITS = {
    _ORIGINAL_COMMIT,
    _REPAIR_2_COMMIT,
    _REPAIR_3_COMMIT,
    _REPAIR_4_COMMIT,
    REPAIR_BASE_COMMIT,
}
TOOL_COUNT = 24
TOOL_LOCK_SHA256 = "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
PIS005A_SCHEMA_FINGERPRINT = (
    "sha256:d42147d48ab2cf7f193c340a7c60302dd61ec1fdd2112d072ebcd50bd5cccd82"
)

_TOP_LEVEL_KEYS = {
    "allowed_paths",
    "authority",
    "base",
    "candidate_procedure",
    "cryptographic_contract",
    "decision_id",
    "dependency_gate",
    "independent_review",
    "next_action",
    "nonclaims",
    "persistence",
    "rollback",
    "safety_contract",
    "schema_version",
    "standing_authority",
    "status",
    "title",
    "validation",
    "work_packages",
}
_AUTHORITY_TRUE = {
    "atomic_node_principal_membership_and_binding_allowed",
    "bounded_implementation_allowed",
    "certificate_and_application_key_proof_of_possession_allowed",
    "digest_only_one_use_enrollment_allowed",
    "fixture_certificate_profile_conformance_allowed",
    "fixture_only",
    "local_sqlite_schema_migration_allowed",
    "loopback_local_preview_only",
    "revocation_and_replace_not_restore_allowed",
    "server_owned_deployment_and_node_ids_allowed",
    "snapshot_only_request_verification_allowed",
    "synthetic_fixture_certificate_generation_allowed",
}
_AUTHORITY_FALSE = {
    "dependency_changes_allowed",
    "effect_execution_allowed",
    "external_credentials_allowed",
    "external_network_allowed",
    "feature_default_enabled",
    "human_uat_completion_allowed",
    "live_mtls_allowed",
    "live_certificate_issuance_allowed",
    "live_tls_listener_allowed",
    "manager_ca_private_key_custody_allowed",
    "manager_node_private_key_custody_allowed",
    "multi_tenant_hosting_allowed",
    "new_api_route_allowed",
    "new_governed_tool_allowed",
    "production_identity_allowed",
    "production_promotion_allowed",
    "release_allowed",
    "remote_administration_allowed",
    "remote_transport_allowed",
    "runtime_postgres_allowed",
}
_EXPECTED_WORK_PACKAGES = [
    {
        "id": "E2-NODE-001",
        "status": "authorized_in_pis_005a",
        "scope": "server_owned_deployment_and_one_use_enrollment_transaction",
    },
    {
        "id": "E2-NODE-002",
        "status": "authorized_fixture_only",
        "scope": "dedicated_node_ca_certificate_profile_and_dual_proof_of_possession",
    },
    {
        "id": "E2-NODE-003",
        "status": "authorized_in_pis_005a",
        "scope": "atomic_certificate_application_key_principal_membership_cross_binding",
    },
    {
        "id": "E2-NODE-004",
        "status": "authorized_non_serving_only",
        "scope": "current_generation_request_verification_replay_and_revocation_snapshot",
    },
    {
        "id": "E2-NODE-005",
        "status": "blocked_separate_next_ticket",
        "scope": "live_tls13_mtls_ca_custody_remote_transport_and_rotation",
    },
]
_EXPECTED_ALLOWED_PATHS = [
    "Makefile",
    "README.md",
    "apps/api/src/ithildin_api/database_migration_backup.py",
    "apps/api/src/ithildin_api/enterprise_node_identity.py",
    "apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
    CONTRACT_REL.as_posix(),
    REVIEW_RECORD_REL.as_posix(),
    DOC_REL.as_posix(),
    NEXT_TICKET_REL.as_posix(),
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    "scripts/enterprise_e2_preparation_check.py",
    "scripts/local_v1_lv1_003_o4_attempt008_node_identity_reconciliation.py",
    "scripts/production_identity_storage_pis_004a_check.py",
    "scripts/production_identity_storage_pis_005a_check.py",
    "scripts/review_docs.py",
    "tests/test_enterprise_e2_preparation.py",
    "tests/test_local_v1_lv1_003_o4_attempt008_node_identity_reconciliation.py",
    "tests/test_mission_database_migration.py",
    "tests/test_pis004a_database_migration.py",
    "tests/test_pis004a_contract.py",
    "tests/test_pis005a_contract.py",
    "tests/test_pis005a_database_migration.py",
    "tests/test_pis005a_enrollment.py",
    "tests/test_pis005a_request_conformance.py",
    "tests/test_trusted_host_promotion_v2_migration.py",
    "tests/test_api_service.py",
]
_EXPECTED_FOCUSED_TESTS = [
    "tests/test_pis004a_contract.py",
    "tests/test_pis005a_contract.py",
    "tests/test_pis005a_database_migration.py",
    "tests/test_pis005a_enrollment.py",
    "tests/test_pis005a_request_conformance.py",
]
_EXPECTED_NEGATIVE_CASES = [
    "noncanonical_application_public_key",
    "same_certificate_and_application_key",
    "wrong_or_retired_enrollment_digest_key_generation",
    "expired_revoked_or_replayed_enrollment",
    "wrong_trust_anchor_or_certificate_signature",
    "certificate_inner_outer_algorithm_identifier_mismatch",
    "certificate_ca_server_auth_key_usage_or_san_profile_drift",
    "certificate_not_yet_valid_expired_or_overlong",
    "certificate_or_application_proof_mismatch",
    "certificate_application_key_clone",
    "organization_workspace_deployment_or_node_mismatch",
    "stale_deployment_generation",
    "stale_identity_certificate_application_or_configuration_generation",
    "application_signature_or_request_digest_mismatch",
    "request_timestamp_and_nonce_replay",
    "request_nonce_exact_boundary_restart_and_concurrent_pruning",
    "persisted_trust_anchor_same_key_ca_reissue_and_application_key_id_drift",
    "concurrent_enrollment_replay",
    "concurrent_request_replay",
    "revocation_race_and_replace_not_restore",
    "replacement_enrollment_expiry_retry_and_concurrent_issue",
    "security_time_sampled_after_database_lock",
    "migration_exact_ddl_constraint_index_and_foreign_key_drift",
    "migration_interruption_backup_reuse_and_old_writer_refusal",
    "migration_locked_source_substituted_backup_provenance_mismatch",
    "migration_guard_timing_windows_and_commit_outcome_classification",
    "migration_dual_alias_canonical_anchor_substitution_and_exact_repair",
    "migration_partial_publication_crash_retry_and_competitor_preservation",
    "migration_marker_receipt_native_legacy_restart_state_classification",
    "migration_symlink_temp_permission_owner_link_count_and_competing_anchor_attacks",
    "migration_child_process_precommit_and_postcommit_crash_schedules",
    "migration_post_finalization_same_uid_mutation_detected_on_restart_nonclaim",
    "migration_passive_fifo_nonblocking_artifact_rejection",
    "candidate_exact_one_commit_topology_and_predecessor_ref_drift",
    "pis004a_detached_successor_exact_topology",
    "replacement_preserves_original_revocation_cause",
    "authority_anchor_and_review_lifecycle_gate_mutation",
    "safe_evidence_vocabulary_and_validation_error_redaction",
    "raw_secret_private_key_signature_certificate_or_request_body_evidence_leak",
]
_EXPECTED_NONCLAIMS = [
    "live TLS listener",
    "live mTLS",
    "certificate issuance or CA private-key custody",
    "Node private-key custody or non-exportability",
    "remote Node transport",
    "production identity",
    "remote administration",
    "multi-tenant hosting",
    "runtime PostgreSQL",
    "enterprise RBAC",
    "effect execution authority",
    "supported scale or performance certification",
    "atomic filesystem and SQLite commit",
    "continuous protection against an indefinitely active same-UID database-directory writer",
    "immutable backup anchors",
    "automatic database restore",
    "human UAT completion",
    "release acceptance",
    "production promotion",
]
_STANDING_DIGEST_FIELDS = {
    "architecture_path": "architecture_sha256",
    "threat_model_path": "threat_model_sha256",
    "e2_preparation_path": "e2_preparation_sha256",
    "e2_contract_path": "e2_contract_sha256",
    "e1_contract_path": "e1_contract_sha256",
    "pis003_authority_path": "pis003_authority_sha256",
    "pis004a_contract_path": "pis004a_contract_sha256",
    "pis004a_review_path": "pis004a_review_sha256",
}
_EXPECTED_STANDING_AUTHORITY = {
    "architecture_path": "docs/codex/production-identity-storage-architecture.md",
    "architecture_sha256": ("f8c53dfa9d8fb2ef041f5f489a1adfa9e4a40e6a3cc40002b66c1f0283df9748"),
    "threat_model_path": (
        "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
    ),
    "threat_model_sha256": ("c01372edba661536a2bf5f799ef84c7ede285e4b1ee681ff21bf106abc1c116d"),
    "e2_preparation_path": "docs/codex/enterprise-e2-production-identity-preparation.md",
    "e2_preparation_sha256": ("e95dea1703efa506d07425d9deacf4b98d1e7690170083fdc04fc59acc2f7c14"),
    "e2_contract_path": "docs/codex/enterprise-e2-preparation-contract.json",
    "e2_contract_sha256": ("06555530e395baa0a3f7aba5321a6b20c95085eebb6560f3fbd7cca2d4411d27"),
    "e1_contract_path": "docs/codex/enterprise-e1-completion-contract.json",
    "e1_contract_sha256": ("cfcf463cf294b6db2e8bb70c2e7e5d6f9dad4bb740a5c290947403f8a49e256a"),
    "pis003_authority_path": (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-evidence-collection-authority.json"
    ),
    "pis003_authority_sha256": ("95ec69aeaff0284ab54b2e894804b309a5db83c3a4bbf83a6ccba4ddc01a0def"),
    "pis004a_contract_path": (
        "docs/codex/production-identity-storage-pis-004a-entry-and-implementation-contract.json"
    ),
    "pis004a_contract_sha256": ("91593a8cd511748def473f60db58cb6dda19ebb6fa76824fd4e7548b6681fb82"),
    "pis004a_review_path": (
        "docs/codex/production-identity-storage-pis-004a-independent-review.md"
    ),
    "pis004a_review_sha256": ("bc67ea5064ca9e94230b8d153bbef61f2ba97c19151a98727382f89c1cacaad7"),
    "pis003_next_action": (
        "await_external_operator_target_and_signed_receipt_inputs_"
        "before_separate_collection_action_authority"
    ),
    "pis003_operational_collection_action_effective": False,
    "standing_architecture_reused": True,
    "competing_architecture_created": False,
}
_EXPECTED_SAFE_EVIDENCE_ALLOWED_FIELDS = [
    "node_id",
    "deployment_id",
    "organization_id",
    "workspace_id",
    "principal_id",
    "certificate_fingerprint",
    "application_key_fingerprint",
    "deployment_generation",
    "identity_generation",
    "certificate_generation",
    "application_key_generation",
    "configuration_generation",
    "request_digest",
    "nonce_outcome",
    "validation_error_count",
    "reason_code",
    "timestamp",
]
_EXPECTED_SAFE_EVIDENCE_FORBIDDEN_FIELDS = [
    "enrollment_secret",
    "digest_key",
    "certificate_der",
    "certificate_private_key",
    "application_private_key",
    "signature",
    "request_body",
    "customer_name",
    "credential",
    "connection_string",
    "private_path",
    "raw_pydantic_validation_error",
]
_EXPECTED_POST_REVIEW_PATHS = {
    CONTRACT_REL.as_posix(),
    REVIEW_RECORD_REL.as_posix(),
    DOC_REL.as_posix(),
}
_EXPECTED_ROLLBACK = {
    "feature": "remain_unimported_and_default_off_or_disable_before_reverting_code",
    "database": "stop_the_schema_7_writer_and_restore_the_verified_pre_v7_backup",
    "data_loss": (
        "no_destructive_table_removal_or_automatic_downgrade_post_migration_fixture_state_"
        "is_discarded_only_by_explicit_restore"
    ),
    "compatibility": (
        "schema_7_raises_minimum_writer_to_7_and_schema_6_backup_is_restore_only_after_"
        "schema_7_writes"
    ),
    "external_system_effect": False,
}
_EXPECTED_NEXT_ACTION_BY_STATUS = {
    "authorized_implementation_in_progress": (
        "implement_and_independently_review_local_fixture_only_pis_005a_"
        "then_stop_before_e2_node_005"
    ),
    "candidate_independent_review_pending": (
        "independently_review_exact_pushed_pis_005a_candidate_then_stop_before_e2_node_005"
    ),
    "candidate_independent_review_complete": "stop_before_separate_e2_node_005_entry_decision",
}
_DEPENDENCY_FILES = ("pyproject.toml", "uv.lock")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_contract(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(payload, dict):
        raise ValueError("PIS-005A contract must be an object")
    return cast(dict[str, object], payload)


def validate_contract(contract: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if set(contract) != _TOP_LEVEL_KEYS:
        failures.append("PIS-005A top-level contract keys are not closed")
    if (
        contract.get("schema_version") != "1"
        or contract.get("decision_id") != "PIS-005A"
        or contract.get("title")
        != "Local Node Workload Identity And Application-Key Cross-Binding Foundation"
    ):
        failures.append("PIS-005A contract identity is invalid")
    if contract.get("status") not in {
        "authorized_implementation_in_progress",
        "candidate_independent_review_pending",
        "candidate_independent_review_complete",
    }:
        failures.append("PIS-005A implementation status is invalid")
    _validate_base(contract.get("base"), failures)
    _validate_standing_authority(contract.get("standing_authority"), failures)
    _validate_authority(contract.get("authority"), failures)
    if contract.get("work_packages") != _EXPECTED_WORK_PACKAGES:
        failures.append("PIS-005A work-package scope is invalid")
    _validate_dependency_gate(contract.get("dependency_gate"), failures)
    _validate_crypto(contract.get("cryptographic_contract"), failures)
    _validate_persistence(contract.get("persistence"), failures)
    _validate_safety(contract.get("safety_contract"), failures)
    if contract.get("allowed_paths") != _EXPECTED_ALLOWED_PATHS:
        failures.append("PIS-005A allowed paths are not exact and ordered")
    _validate_validation(contract.get("validation"), failures)
    _validate_rollback(contract.get("rollback"), failures)
    _validate_candidate_procedure(contract.get("candidate_procedure"), failures)
    _validate_independent_review(
        contract.get("independent_review"),
        status=contract.get("status"),
        failures=failures,
    )
    if contract.get("nonclaims") != _EXPECTED_NONCLAIMS:
        failures.append("PIS-005A nonclaims are not exact and ordered")
    expected_next_action = _EXPECTED_NEXT_ACTION_BY_STATUS.get(str(contract.get("status")))
    if contract.get("next_action") != expected_next_action:
        failures.append("PIS-005A next action is invalid")
    return failures


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    return cast(dict[str, object], value)


def _validate_base(value: object, failures: list[str]) -> None:
    base = _mapping(value)
    if base is None:
        failures.append("PIS-005A base identity is invalid")
        return
    expected = {
        "source_branch": "origin/codex/enterprise-e2-pis004a-review-repair",
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "pis004a_reviewed_candidate_commit": "ff358753c50037c2bc936b761f249cf5c9115749",
        "pis004a_reviewed_candidate_tree": "0fff4fe145ca0b2b9db8fa874396486bba5eb6c7",
        "canonical_key_prerequisite_commit": SECURITY_PREREQUISITE_COMMIT,
        "canonical_key_prerequisite_tree": SECURITY_PREREQUISITE_TREE,
        "implementation_baseline_commit": SECURITY_PREREQUISITE_COMMIT,
        "implementation_baseline_tree": SECURITY_PREREQUISITE_TREE,
        "repair_source_branch": f"origin/{REPAIR_BASE_BRANCH}",
        "repair_source_commit": REPAIR_BASE_COMMIT,
        "repair_source_tree": REPAIR_BASE_TREE,
        "branch": BRANCH,
        "rejected_predecessors": [
            {
                "branch": _ORIGINAL_BRANCH,
                "commit": _ORIGINAL_COMMIT,
                "tree": _ORIGINAL_TREE,
            },
            {
                "branch": _REPAIR_2_BRANCH,
                "commit": _REPAIR_2_COMMIT,
                "tree": _REPAIR_2_TREE,
            },
            {
                "branch": _REPAIR_3_BRANCH,
                "commit": _REPAIR_3_COMMIT,
                "tree": _REPAIR_3_TREE,
            },
            {
                "branch": _REPAIR_4_BRANCH,
                "commit": _REPAIR_4_COMMIT,
                "tree": _REPAIR_4_TREE,
            },
            {
                "branch": REPAIR_BASE_BRANCH,
                "commit": REPAIR_BASE_COMMIT,
                "tree": REPAIR_BASE_TREE,
            },
        ],
        "e1_human_uat_complete": False,
    }
    if base != expected:
        failures.append("PIS-005A source and prerequisite identities are not exact")


def _validate_standing_authority(value: object, failures: list[str]) -> None:
    standing = _mapping(value)
    if standing is None:
        failures.append("PIS-005A standing authority is invalid")
        return
    if standing != _EXPECTED_STANDING_AUTHORITY:
        failures.append("PIS-005A standing authority is not the exact protected inventory")


def _validate_authority(value: object, failures: list[str]) -> None:
    authority = _mapping(value)
    if authority is None or set(authority) != _AUTHORITY_TRUE | _AUTHORITY_FALSE:
        failures.append("PIS-005A authority keys are not closed")
        return
    if any(authority.get(key) is not True for key in _AUTHORITY_TRUE):
        failures.append("PIS-005A required bounded authority is missing")
    if any(authority.get(key) is not False for key in _AUTHORITY_FALSE):
        failures.append("PIS-005A authority ceiling permits forbidden behavior")


def _validate_dependency_gate(value: object, failures: list[str]) -> None:
    dependency = _mapping(value)
    expected = {
        "decision": "reuse_existing_cryptography_only",
        "pyproject_requirement": "cryptography>=48.0.0",
        "locked_package": "cryptography",
        "locked_version": "48.0.0",
        "dependency_delta_allowed": False,
        "lock_delta_allowed": False,
        "general_purpose_http_surface_allowed": False,
        "tls_runtime_or_server_library_allowed": False,
        "ca_or_kms_sdk_allowed": False,
        "rollback": "no_dependency_or_lock_change_to_revert",
    }
    if dependency != expected:
        failures.append("PIS-005A dependency gate is invalid")


def _validate_crypto(value: object, failures: list[str]) -> None:
    crypto = _mapping(value)
    if crypto is None:
        failures.append("PIS-005A cryptographic contract is invalid")
        return
    legacy_key_id = "sha256:c13217bb5694185919fa9b0bb7d18759c8dd4006aa0de169d29e9480d38f7bcd"
    raw_key_fingerprint = "sha256:630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd"
    expected_scalars = {
        "certificate_public_key_algorithm": "ed25519",
        "application_public_key_algorithm": "ed25519",
        "certificate_algorithm_identifier_contract": (
            "inner_outer_and_spki_exact_parameter_absent_ed25519"
        ),
        "certificate_and_application_keys_must_differ": True,
        "legacy_application_key_id_scheme": "sha256_of_canonical_padded_base64_text",
        "legacy_application_key_ids_changed": False,
        "application_key_fingerprint_scheme": "ed25519_raw_sha256_v1",
        "application_key_fingerprint_value": "sha256_of_32_raw_ed25519_public_key_bytes",
        "certificate_fingerprint_value": "sha256_of_exact_leaf_der",
        "canonical_fixture_public_key": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=",
        "canonical_fixture_legacy_key_id": legacy_key_id,
        "canonical_fixture_raw_key_fingerprint": raw_key_fingerprint,
        "noncanonical_base64_allowed": False,
        "private_keys_or_enrollment_secrets_persisted": False,
    }
    if set(crypto) != {*expected_scalars, "certificate_profile"}:
        failures.append("PIS-005A cryptographic-contract keys are not closed")
    if any(crypto.get(key) != expected for key, expected in expected_scalars.items()):
        failures.append("PIS-005A cryptographic identity or compatibility contract is invalid")
    profile = _mapping(crypto.get("certificate_profile"))
    if profile != {
        "trust_anchor": "explicit_injected_fixture_only_dedicated_node_ca",
        "leaf_subject": "empty",
        "basic_constraints_ca": False,
        "extension_inventory": [
            "basicConstraints",
            "keyUsage",
            "extendedKeyUsage",
            "subjectAltName",
        ],
        "critical_extensions": [
            "basicConstraints",
            "keyUsage",
            "subjectAltName",
        ],
        "unknown_extensions_allowed": False,
        "extended_key_usage": ["clientAuth"],
        "key_usage": ["digitalSignature"],
        "exact_san_bindings": [
            "node_id",
            "organization_id",
            "workspace_id",
            "deployment_id",
            "enrollment_transaction_id",
        ],
        "san_general_name_type": "uniformResourceIdentifier",
        "san_exact_cardinality": 5,
        "san_set_semantics": "exact_set_order_independent",
        "duplicate_unknown_or_non_uri_general_names_allowed": False,
        "workspace_id_encoding": "existing_ascii_unreserved_workspace_identifier",
        "workspace_id_pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$",
        "san_uri_templates": [
            "urn:ithildin:node:{node_id}",
            "urn:ithildin:organization:{organization_id}",
            "urn:ithildin:workspace:{workspace_id}",
            "urn:ithildin:deployment:{deployment_id}",
            "urn:ithildin:enrollment:{enrollment_transaction_id}",
        ],
        "trusted_clock_required": True,
        "maximum_fixture_lifetime_seconds": 86400,
    }:
        failures.append("PIS-005A fixture certificate profile is invalid")


def _validate_persistence(value: object, failures: list[str]) -> None:
    persistence = _mapping(value)
    required = {
        "backend": "local_sqlite_only",
        "coordinated_schema_target": "7",
        "schema_fingerprint": PIS005A_SCHEMA_FINGERPRINT,
        "schema_fingerprint_status": "exact_ddl_bound",
        "schema_fingerprint_domain": "ITHILDIN-PIS005A-SCHEMA-V1",
        "minimum_writer_after_activation": "7",
        "migration_mode": (
            "sqlite_transactional_offline_local_startup_with_separate_durable_artifact_protocol"
        ),
        "pre_migration_backup_required": True,
        "pre_migration_backup_caller_owned_guard_required": True,
        "pre_migration_backup_locked_source_logical_match_required": True,
        "pre_migration_backup_stable_descriptor_lifetime_through_finalization_required": True,
        "pre_migration_backup_dual_hardlink_aliases_required": True,
        "pre_migration_backup_canonical_anchor_same_inode_required": True,
        "pre_migration_backup_device_inode_receipt_binding_required": True,
        "pre_migration_backup_no_clobber_initial_publication_required": True,
        "pre_migration_receipt_precommit_only": True,
        "migration_commit_marker_table": "app_metadata",
        "migration_commit_marker_keys": [
            "migration_backup_receipt_pre_v4_v1",
            "migration_backup_receipt_pre_v7_v1",
        ],
        "migration_backup_guard_owns_commit": True,
        "migration_outcome_error_classes": [
            "DatabaseBackupError",
            "DatabaseMigrationOutcomeUnknown",
            "DatabaseBackupRecoveryRequired",
        ],
        "database_directory_trust": (
            "current_user_owned_real_directory_not_group_or_world_writable"
        ),
        "unsupported_no_follow_or_hardlink_semantics_fail_closed": True,
        "postcommit_exact_inode_one_alias_repair_allowed": True,
        "backup_equivalent_byte_copy_auto_recovery_allowed": False,
        "receipt_projection_restore_from_exact_marker_allowed": True,
        "committed_restart_self_describing_exact_object_identity_required": True,
        "atomic_filesystem_and_sqlite_commit_claimed": False,
        "continuous_protection_against_indefinitely_active_same_uid_directory_writer_claimed": (
            False
        ),
        "automatic_down_migration_allowed": False,
        "new_object_prefix": "node_workload_",
        "table_inventory": [
            "node_workload_enrollment_digest_key_generations",
            "node_workload_deployments",
            "node_workload_enrollment_transactions",
            "node_workload_public_keys",
            "node_workload_identities",
            "node_workload_request_nonces",
        ],
        "index_inventory": [
            "node_workload_enrollment_digest_key_generations_one_active_idx",
            "node_workload_deployments_scope_status_idx",
            "node_workload_enrollment_transactions_status_expiry_idx",
            "node_workload_enrollment_transactions_one_pending_replacement_idx",
            "node_workload_public_keys_node_status_idx",
            "node_workload_identities_scope_status_idx",
            "node_workload_request_nonces_expiry_idx",
        ],
        "legacy_nodes_tables_repurposed_as_enterprise_authority": False,
        "raw_enrollment_secret_persisted": False,
        "enrollment_secret_lookup_digest": "generation_indexed_keyed_hmac_sha256",
        "certificate_der_persisted": False,
        "certificate_private_key_persisted": False,
        "application_private_key_persisted": False,
        "request_nonce_digest": "sha256",
        "schema_removal_posture": "restore_pre_migration_backup_only",
    }
    if persistence != required:
        failures.append("PIS-005A persistence or rollback boundary is invalid")


def _validate_safety(value: object, failures: list[str]) -> None:
    safety = _mapping(value)
    if safety is None:
        failures.append("PIS-005A safety contract is invalid")
        return
    required_true = {
        "certificate_and_application_pop_cover_same_canonical_binding",
        "certificate_application_key_clone_denied",
        "deployment_generation_revalidation_required",
        "enrollment_atomic_one_use_required",
        "enrollment_digest_key_generation_fail_closed",
        "expired_replacement_terminalized_before_retry",
        "ordinary_expired_enrollment_terminalized_before_failure",
        "global_cross_role_public_key_registry_required",
        "identity_certificate_application_configuration_generations_independent",
        "one_pending_replacement_per_revoked_node",
        "organization_workspace_deployment_cross_binding_required",
        "replacement_completion_recorded_separately",
        "replacement_preserves_original_revocation_cause",
        "replacement_requires_new_node_id_and_both_new_keys",
        "request_current_state_revalidation_required",
        "request_persisted_trust_anchor_and_application_key_id_revalidation_required",
        "request_nonce_atomic_one_use_required",
        "request_nonce_strict_older_pruning_required",
        "revocation_disables_principal_and_memberships",
        "revocation_increments_authority_generations",
        "server_preallocates_deployment_id",
        "server_preallocates_node_id",
        "security_time_sampled_after_write_lock",
        "safe_evidence_reason_codes_server_owned",
        "safe_validation_error_summary_required",
        "validation_errors_hide_input_values",
    }
    expected_keys = required_true | {
        "enrollment_secret_minimum_entropy_bits",
        "enrollment_maximum_lifetime_seconds",
        "certificate_der_maximum_bytes",
        "human_approval_by_node_allowed",
        "organization_roles",
        "principal_type",
        "request_effect_authority",
        "request_maximum_clock_skew_seconds",
        "request_nonce_retention_seconds",
        "request_body_maximum_bytes",
        "raw_pydantic_validation_errors_allowed_in_evidence",
        "revoked_or_replaced_identity_restoration_allowed",
        "safe_evidence_allowed_fields",
        "safe_evidence_forbidden_fields",
        "workspace_roles",
    }
    if set(safety) != expected_keys:
        failures.append("PIS-005A safety-contract keys are not closed")
    if any(safety.get(key) is not True for key in required_true):
        failures.append("PIS-005A safety contract weakens a required control")
    if (
        safety.get("request_effect_authority") is not False
        or safety.get("revoked_or_replaced_identity_restoration_allowed") is not False
        or safety.get("human_approval_by_node_allowed") is not False
        or safety.get("raw_pydantic_validation_errors_allowed_in_evidence") is not False
    ):
        failures.append("PIS-005A safety contract permits forbidden authority")
    if safety.get("enrollment_secret_minimum_entropy_bits") != 256:
        failures.append("PIS-005A enrollment-secret entropy floor is invalid")
    if (
        safety.get("enrollment_maximum_lifetime_seconds") != 3600
        or safety.get("certificate_der_maximum_bytes") != 65536
        or safety.get("request_maximum_clock_skew_seconds") != 300
        or safety.get("request_nonce_retention_seconds") != 600
        or safety.get("request_body_maximum_bytes") != 1048576
    ):
        failures.append("PIS-005A local fixture resource bounds are invalid")
    if (
        safety.get("principal_type") != "node"
        or safety.get("organization_roles") != ["member", "node_operator"]
        or safety.get("workspace_roles") != ["node"]
    ):
        failures.append("PIS-005A server-owned Node role contract is invalid")
    allowed = safety.get("safe_evidence_allowed_fields")
    forbidden = safety.get("safe_evidence_forbidden_fields")
    if (
        allowed != _EXPECTED_SAFE_EVIDENCE_ALLOWED_FIELDS
        or forbidden != _EXPECTED_SAFE_EVIDENCE_FORBIDDEN_FIELDS
        or not isinstance(allowed, list)
        or not isinstance(forbidden, list)
        or not set(allowed).isdisjoint(forbidden)
    ):
        failures.append("PIS-005A safe-evidence vocabulary is invalid")


def _validate_validation(value: object, failures: list[str]) -> None:
    validation = _mapping(value)
    if validation is None or set(validation) != {
        "focused_tests",
        "make_target",
        "negative_inventory",
    }:
        failures.append("PIS-005A validation contract keys are not closed")
        return
    if (
        validation.get("make_target") != "production-identity-storage-pis-005a-check"
        or validation.get("focused_tests") != _EXPECTED_FOCUSED_TESTS
    ):
        failures.append("PIS-005A focused validation inventory is invalid")
    if validation.get("negative_inventory") != _EXPECTED_NEGATIVE_CASES:
        failures.append("PIS-005A negative-test inventory is incomplete")


def _validate_rollback(value: object, failures: list[str]) -> None:
    rollback = _mapping(value)
    if rollback != _EXPECTED_ROLLBACK:
        failures.append("PIS-005A rollback and compatibility contract is invalid")


def _validate_candidate_procedure(value: object, failures: list[str]) -> None:
    candidate = _mapping(value)
    expected = {
        "focused_command": "make production-identity-storage-pis-005a-check",
        "independent_review_template": (
            f"git fetch origin refs/heads/{BRANCH}:refs/heads/{BRANCH} "
            f"refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH} && "
            "git worktree add --detach /tmp/ithildin-pis005a-review <candidate_commit> && "
            "cd /tmp/ithildin-pis005a-review && "
            "make production-identity-storage-pis-005a-check"
        ),
        "candidate_must_be_clean": True,
        "independent_review_required": True,
        "release_or_promotion_authorized_by_candidate": False,
    }
    if candidate != expected:
        failures.append("PIS-005A candidate procedure is invalid")


def _validate_independent_review(
    value: object,
    *,
    status: object,
    failures: list[str],
) -> None:
    review = _mapping(value)
    if review is None:
        failures.append("PIS-005A independent-review contract is invalid")
        return
    expected_keys = {
        "clean_detached_worktree_verified",
        "critical_findings",
        "focused_gate_passed",
        "high_findings",
        "human_uat_complete",
        "implementation_review_complete",
        "live_remote_transport_authorized",
        "low_findings",
        "medium_findings",
        "open_findings",
        "record_path",
        "release_or_promotion_authorized",
        "remote_identity_verified",
        "review_method",
        "reviewed_candidate_commit",
        "reviewed_candidate_tree",
    }
    if set(review) != expected_keys:
        failures.append("PIS-005A independent-review keys are not closed")
    if (
        review.get("record_path") != REVIEW_RECORD_REL.as_posix()
        or review.get("review_method") != "independent_read_only_codex_review"
    ):
        failures.append("PIS-005A independent-review metadata is invalid")
    forbidden_true = {
        "human_uat_complete",
        "live_remote_transport_authorized",
        "release_or_promotion_authorized",
    }
    if any(review.get(key) is not False for key in forbidden_true):
        failures.append("PIS-005A independent review permits forbidden authority")
    expected_pending = {
        "reviewed_candidate_commit": None,
        "reviewed_candidate_tree": None,
        "clean_detached_worktree_verified": False,
        "remote_identity_verified": False,
        "focused_gate_passed": False,
        "critical_findings": None,
        "high_findings": None,
        "medium_findings": None,
        "low_findings": None,
        "open_findings": None,
        "implementation_review_complete": False,
    }
    if status == "authorized_implementation_in_progress":
        if any(review.get(key) != expected for key, expected in expected_pending.items()):
            failures.append("PIS-005A pending independent-review state is invalid")
    elif status == "candidate_independent_review_pending":
        if any(review.get(key) != expected for key, expected in expected_pending.items()):
            failures.append("PIS-005A pending independent-review state is invalid")
    elif status == "candidate_independent_review_complete":
        commit = review.get("reviewed_candidate_commit")
        tree = review.get("reviewed_candidate_tree")
        if (
            not isinstance(commit, str)
            or len(commit) != 40
            or any(character not in "0123456789abcdef" for character in commit)
            or not isinstance(tree, str)
            or len(tree) != 40
            or any(character not in "0123456789abcdef" for character in tree)
            or any(
                review.get(key) is not True
                for key in (
                    "clean_detached_worktree_verified",
                    "remote_identity_verified",
                    "focused_gate_passed",
                    "implementation_review_complete",
                )
            )
            or any(
                review.get(key) != 0
                for key in (
                    "critical_findings",
                    "high_findings",
                    "medium_findings",
                    "low_findings",
                    "open_findings",
                )
            )
        ):
            failures.append("PIS-005A completed independent-review disposition is invalid")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_or_none(root: Path, *arguments: str) -> str | None:
    try:
        return _git(root, *arguments)
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_blob(root: Path, revision: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _changed_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for arguments in (
        ("diff", "--name-only", f"{SECURITY_PREREQUISITE_COMMIT}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        output = _git(root, *arguments)
        paths.update(line for line in output.splitlines() if line)
    return paths


def _post_review_changed_paths(root: Path, reviewed_candidate_commit: str) -> set[str]:
    paths: set[str] = set()
    for arguments in (
        ("diff", "--name-only", f"{reviewed_candidate_commit}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        output = _git(root, *arguments)
        paths.update(line for line in output.splitlines() if line)
    return paths


def _observed_tool_count(root: Path) -> int | None:
    try:
        lock = json.loads((root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
        manifests = lock["manifests"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(manifests, list):
        return None
    return len(manifests)


def _runtime_import_failures(root: Path) -> list[str]:
    failures: list[str] = []
    module_path = root / "apps/api/src/ithildin_api/enterprise_node_identity.py"
    runtime_roots = (
        root / "apps/api/src/ithildin_api",
        root / "apps/node/src/ithildin_node",
    )
    for runtime_root in runtime_roots:
        for path in runtime_root.rglob("*.py"):
            if path == module_path:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError):
                failures.append(f"PIS-005A runtime import inventory cannot parse {path}")
                continue
            for node in ast.walk(tree):
                if _imports_enterprise_node_identity(node):
                    relative = path.relative_to(root).as_posix()
                    failures.append(f"PIS-005A introduced a runtime import in {relative}")
                    break
    return failures


def _imports_enterprise_node_identity(node: ast.AST) -> bool:
    target = "ithildin_api.enterprise_node_identity"
    if isinstance(node, ast.Import):
        return any(
            alias.name == target or alias.name.startswith(f"{target}.") for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module in {"enterprise_node_identity", target} or module.startswith(f"{target}."):
            return True
        imported_names = {alias.name for alias in node.names}
        return (
            "enterprise_node_identity" in imported_names
            and (
                not module
                or module == "ithildin_api"
                or module.endswith(".ithildin_api")
            )
        )
    if isinstance(node, ast.Call) and node.args:
        first_argument = node.args[0]
        if not isinstance(first_argument, ast.Constant) or not isinstance(
            first_argument.value,
            str,
        ):
            return False
        called_name = ""
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            called_name = node.func.attr
        return (
            called_name in {"__import__", "import_module"}
            and (
                first_argument.value == target
                or first_argument.value.startswith(f"{target}.")
            )
        )
    return False


def _candidate_checkout_failures(
    root: Path,
    *,
    status: object,
    review: dict[str, object] | None,
) -> list[str]:
    branch = _git_or_none(root, "branch", "--show-current")
    head_name = _git_or_none(root, "rev-parse", "--abbrev-ref", "HEAD")
    head = _git_or_none(root, "rev-parse", "HEAD^{commit}")
    head_tree = _git_or_none(root, "rev-parse", "HEAD^{tree}")
    if branch is None or head_name is None or head is None or head_tree is None:
        return ["PIS-005A checkout identity cannot be verified"]
    topology_commit = head
    if status == "candidate_independent_review_complete" and review is not None:
        reviewed_commit = review.get("reviewed_candidate_commit")
        if isinstance(reviewed_commit, str):
            topology_commit = reviewed_commit
    parent_line = _git_or_none(root, "show", "-s", "--format=%P", topology_commit)
    parents = tuple(parent_line.split()) if parent_line is not None else None
    parent_tree = (
        _git_or_none(root, "rev-parse", f"{parents[0]}^{{tree}}")
        if parents is not None and len(parents) == 1
        else None
    )
    failures = _candidate_identity_failures(
        branch=branch,
        head_name=head_name,
        head=head,
        head_tree=head_tree,
        local=_git_or_none(root, "rev-parse", f"refs/heads/{BRANCH}^{{commit}}"),
        local_tree=_git_or_none(root, "rev-parse", f"refs/heads/{BRANCH}^{{tree}}"),
        remote=_git_or_none(
            root,
            "rev-parse",
            f"refs/remotes/origin/{BRANCH}^{{commit}}",
        ),
        remote_tree=_git_or_none(
            root,
            "rev-parse",
            f"refs/remotes/origin/{BRANCH}^{{tree}}",
        ),
        candidate_commit=topology_commit,
        candidate_parents=parents,
        candidate_parent_tree=parent_tree,
        predecessor_topology_valid=_predecessor_topology_is_exact(root),
        shallow_state=_git_or_none(root, "rev-parse", "--is-shallow-repository"),
        porcelain=_git_or_none(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
    )
    if status == "candidate_independent_review_complete" and review is not None:
        reviewed_commit = review.get("reviewed_candidate_commit")
        reviewed_tree = review.get("reviewed_candidate_tree")
        try:
            if (
                not isinstance(reviewed_commit, str)
                or reviewed_commit == head
                or _git(root, "rev-parse", f"{reviewed_commit}^{{commit}}") != reviewed_commit
                or _git(root, "rev-parse", f"{reviewed_commit}^{{tree}}") != reviewed_tree
            ):
                failures.append("PIS-005A reviewed candidate tree identity changed")
            else:
                subprocess.run(
                    ["git", "merge-base", "--is-ancestor", reviewed_commit, "HEAD"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                post_review_paths = _post_review_changed_paths(root, reviewed_commit)
                if post_review_paths != _EXPECTED_POST_REVIEW_PATHS:
                    unexpected = sorted(post_review_paths - _EXPECTED_POST_REVIEW_PATHS)
                    missing = sorted(_EXPECTED_POST_REVIEW_PATHS - post_review_paths)
                    if unexpected:
                        failures.append(
                            "PIS-005A post-review record changed implementation paths: "
                            + ", ".join(unexpected)
                        )
                    if missing:
                        failures.append(
                            "PIS-005A post-review record inventory is incomplete: "
                            + ", ".join(missing)
                        )
        except (OSError, subprocess.CalledProcessError):
            failures.append("PIS-005A reviewed candidate is unavailable or not an ancestor of HEAD")
    return failures


def _candidate_identity_failures(
    *,
    branch: str,
    head_name: str,
    head: str,
    head_tree: str,
    local: str | None,
    local_tree: str | None,
    remote: str | None,
    remote_tree: str | None,
    candidate_commit: str,
    candidate_parents: tuple[str, ...] | None,
    candidate_parent_tree: str | None,
    predecessor_topology_valid: bool,
    shallow_state: str | None,
    porcelain: str | None,
) -> list[str]:
    failures: list[str] = []
    if shallow_state != "false":
        failures.append("PIS-005A candidate repository is shallow or unverifiable")
    if branch not in {"", BRANCH}:
        failures.append("PIS-005A is not on its exact isolated branch or detached for review")
    if branch == BRANCH and head_name != BRANCH:
        failures.append("PIS-005A named candidate branch identity is inconsistent")
    if branch == "" and head_name != "HEAD":
        failures.append("PIS-005A detached candidate identity is inconsistent")
    if porcelain is None:
        failures.append("PIS-005A candidate worktree cleanliness is unavailable")
    elif porcelain.strip():
        failures.append("PIS-005A candidate worktree is not clean")
    if local is None or local_tree is None:
        failures.append("PIS-005A exact local candidate identity is unavailable")
    if remote is None or remote_tree is None:
        failures.append("PIS-005A fetched candidate identity is unavailable")
    if (
        local is not None
        and local_tree is not None
        and remote is not None
        and remote_tree is not None
        and (
            head != local
            or head != remote
            or head_tree != local_tree
            or head_tree != remote_tree
        )
    ):
        failures.append(
            "PIS-005A checkout does not match the fetched authorized commit and tree"
        )
    if (
        candidate_commit in REJECTED_CANDIDATE_COMMITS
        or candidate_parents != (REPAIR_BASE_COMMIT,)
        or candidate_parent_tree != REPAIR_BASE_TREE
    ):
        failures.append("PIS-005A candidate is not the exact direct child of repair-5")
    if not predecessor_topology_valid:
        failures.append("PIS-005A accepted or rejected predecessor identity changed")
    return failures


def _predecessor_topology_is_exact(root: Path) -> bool:
    for branch, commit, tree in _PREDECESSOR_REFS:
        if _git_or_none(root, "rev-parse", f"{commit}^{{tree}}") != tree:
            return False
        for ref in (f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
            if (
                _git_or_none(root, "rev-parse", f"{ref}^{{commit}}") != commit
                or _git_or_none(root, "rev-parse", f"{ref}^{{tree}}") != tree
            ):
                return False
    for child, parent in _REPAIR_PARENT_CHAIN:
        if _git_or_none(root, "show", "-s", "--format=%P", child) != parent:
            return False
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", SOURCE_COMMIT, _ORIGINAL_COMMIT],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _live_stop_line_failures(root: Path) -> list[str]:
    failures: list[str] = []
    try:
        e1 = json.loads(
            (root / "docs/codex/enterprise-e1-completion-contract.json").read_text(encoding="utf-8")
        )
        pis003 = json.loads(
            (
                root / "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
                "environment-evidence-collection-authority.json"
            ).read_text(encoding="utf-8")
        )
        e1_qualification = e1["qualification"]
        e1_wait = e1["pis_wait"]
        pis003_post_review = pis003["post_review_authority_ceiling"]
        pis003_authority = pis003["authority"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return ["PIS-005A live E1 or PIS-003 stop line cannot be loaded"]
    wait_action = (
        "await_external_operator_target_and_signed_receipt_inputs_"
        "before_separate_collection_action_authority"
    )
    if (
        not isinstance(e1_qualification, dict)
        or e1_qualification.get("human_uat_complete") is not False
        or not isinstance(e1_wait, dict)
        or e1_wait.get("next_action") != wait_action
        or e1_wait.get("external_inputs_present") is not False
        or e1_wait.get("collection_action_authority") is not False
    ):
        failures.append("PIS-005A does not preserve the E1 human-UAT or PIS wait stop line")
    if (
        pis003.get("next_required_action") != wait_action
        or not isinstance(pis003_post_review, dict)
        or not isinstance(pis003_authority, dict)
        or pis003_authority.get("operational_collection_action_effective") is not False
        or pis003_post_review.get("runtime_postgres_allowed") is not False
        or pis003_post_review.get("production_identity_allowed") is not False
    ):
        failures.append("PIS-005A routes around the PIS-003 external-input wait")
    return failures


def _repository_failures(root: Path, contract: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for path_key, digest_key in _STANDING_DIGEST_FIELDS.items():
        relative = cast(str, _EXPECTED_STANDING_AUTHORITY[path_key])
        expected_digest = cast(str, _EXPECTED_STANDING_AUTHORITY[digest_key])
        path = root / relative
        if not path.is_file() or _sha256(path) != expected_digest:
            failures.append(f"PIS-005A changed protected standing authority: {relative}")
    try:
        if _git(root, "rev-parse", f"{SOURCE_COMMIT}^{{tree}}") != SOURCE_TREE:
            failures.append("PIS-005A source tree identity changed")
        if (
            _git(root, "rev-parse", f"{SECURITY_PREREQUISITE_COMMIT}^{{tree}}")
            != SECURITY_PREREQUISITE_TREE
        ):
            failures.append("PIS-005A security-prerequisite tree identity changed")
        if _git(root, "rev-parse", f"{REPAIR_BASE_COMMIT}^{{tree}}") != REPAIR_BASE_TREE:
            failures.append("PIS-005A repair-base tree identity changed")
        if (
            _git(
                root,
                "rev-parse",
                f"refs/remotes/origin/{REPAIR_BASE_BRANCH}^{{commit}}",
            )
            != REPAIR_BASE_COMMIT
        ):
            failures.append("PIS-005A fetched repair-base identity changed")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", SECURITY_PREREQUISITE_COMMIT, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", REPAIR_BASE_COMMIT, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        failures.append("PIS-005A exact source or prerequisite commit is unavailable")
    lock_path = root / "tool-manifests.lock.json"
    if _observed_tool_count(root) != TOOL_COUNT or _sha256(lock_path) != TOOL_LOCK_SHA256:
        failures.append("PIS-005A changed the exact 24-tool manifest lock")
    if expected_pis005a_schema_fingerprint() != PIS005A_SCHEMA_FINGERPRINT:
        failures.append("PIS-005A schema fingerprint does not match the exact migration DDL")
    try:
        unexpected = sorted(_changed_paths(root) - set(_EXPECTED_ALLOWED_PATHS))
    except (OSError, subprocess.CalledProcessError):
        failures.append("PIS-005A changed-path inventory cannot be verified")
    else:
        if unexpected:
            failures.append(
                "PIS-005A changed paths outside its exact lane: " + ", ".join(unexpected)
            )
    for relative in _DEPENDENCY_FILES:
        try:
            if (root / relative).read_bytes() != _git_blob(
                root,
                SECURITY_PREREQUISITE_COMMIT,
                relative,
            ):
                failures.append(f"PIS-005A dependency delta is forbidden: {relative}")
        except (OSError, subprocess.CalledProcessError):
            failures.append(f"PIS-005A dependency baseline is unavailable: {relative}")
    failures.extend(_runtime_import_failures(root))
    failures.extend(_live_stop_line_failures(root))
    failures.extend(
        _candidate_checkout_failures(
            root,
            status=contract.get("status"),
            review=_mapping(contract.get("independent_review")),
        )
    )
    module_path = root / "apps/api/src/ithildin_api/enterprise_node_identity.py"
    if module_path.exists():
        module_text = module_path.read_text(encoding="utf-8")
        for forbidden in (
            "import socket",
            "from socket",
            "import httpx",
            "from httpx",
            "import requests",
            "from requests",
            "FastAPI",
            "APIRouter",
            "uvicorn",
        ):
            if forbidden in module_text:
                failures.append(
                    f"PIS-005A local fixture module contains forbidden runtime surface: {forbidden}"
                )
    docs = {
        DOC_REL: (
            "exactly `24`",
            "`effect_authority: false`",
            "There is no global key-ID migration.",
            "restore-only",
            "After an exact candidate is independently reviewed, PIS-005A stops.",
        ),
        NEXT_TICKET_REL: (
            "Status: blocked; no implementation authority.",
            "do not add a TLS listener",
            "runtime PostgreSQL",
            "production promotion",
        ),
    }
    status = contract.get("status")
    for document_relative, phrases in docs.items():
        text = (root / document_relative).read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"PIS-005A document is missing required phrase: {phrase}")
    foundation_text = (root / DOC_REL).read_text(encoding="utf-8")
    status_lines = {
        "authorized_implementation_in_progress": (
            "Status: bounded implementation authorized and in progress."
        ),
        "candidate_independent_review_pending": (
            "Status: exact implementation candidate frozen; independent review pending."
        ),
        "candidate_independent_review_complete": (
            "Status: independent implementation review complete; no open findings."
        ),
    }
    expected_status_line = status_lines.get(str(status))
    if (
        expected_status_line is None
        or expected_status_line not in foundation_text
        or any(
            line in foundation_text
            for line in status_lines.values()
            if line != expected_status_line
        )
    ):
        failures.append("PIS-005A foundation status projection is invalid")
    review = _mapping(contract.get("independent_review"))
    review_text = (
        (root / REVIEW_RECORD_REL).read_text(encoding="utf-8")
        if (root / REVIEW_RECORD_REL).is_file()
        else ""
    )
    failures.extend(
        _review_record_failures(
            review_text,
            status=status,
            review=review,
        )
    )
    if contract.get("status") == "candidate_independent_review_complete":
        reviewed_commit = review.get("reviewed_candidate_commit") if review else None
        reviewed_tree = review.get("reviewed_candidate_tree") if review else None
        if any(
            identity not in foundation_text
            for identity in (str(reviewed_commit), str(reviewed_tree))
        ):
            failures.append(
                "PIS-005A foundation does not bind the exact reviewed candidate identity"
            )
    registration_sources: tuple[tuple[str, str], ...] = (
        ("README.md", DOC_REL.as_posix()),
        ("scripts/review_docs.py", DOC_REL.as_posix()),
        ("scripts/review_docs.py", NEXT_TICKET_REL.as_posix()),
        ("scripts/review_docs.py", REVIEW_RECORD_REL.as_posix()),
        ("scripts/build_docs_site.py", DOC_REL.as_posix()),
        ("scripts/build_docs_site.py", NEXT_TICKET_REL.as_posix()),
        ("scripts/build_docs_site.py", REVIEW_RECORD_REL.as_posix()),
        ("docs/codex/review-docs-index.md", DOC_REL.name),
        ("docs/codex/review-docs-index.md", NEXT_TICKET_REL.name),
        ("docs/codex/review-docs-index.md", REVIEW_RECORD_REL.name),
        ("Makefile", "production-identity-storage-pis-005a-check:"),
    )
    for source, needle in registration_sources:
        if needle not in (root / source).read_text(encoding="utf-8"):
            failures.append(f"PIS-005A document or gate is missing from {source}")
    return failures


def _review_record_failures(
    review_text: str,
    *,
    status: object,
    review: dict[str, object] | None,
) -> list[str]:
    failures: list[str] = []
    expected_fields = {
        "Review method": "independent read-only Codex review in a clean detached worktree.",
        "Human UAT complete": "`false`.",
        "Live remote transport authorized": "`false`.",
        "Release or promotion authorized": "`false`.",
        "E2-NODE-005 status": "blocked; separate entry decision required.",
        "Current governed tool count": "exactly `24`.",
    }
    if status == "candidate_independent_review_complete":
        reviewed_commit = review.get("reviewed_candidate_commit") if review else None
        reviewed_tree = review.get("reviewed_candidate_tree") if review else None
        expected_fields.update(
            {
                "Status": "independent implementation review complete; no open findings.",
                "Reviewed exact implementation commit": f"`{reviewed_commit}`.",
                "Reviewed exact tree": f"`{reviewed_tree}`.",
                "Candidate freeze complete": "`true`.",
                "Clean detached worktree verified": "`true`.",
                "Remote identity verified": "`true`.",
                "Focused gate passed": "`true`.",
                "Implementation review complete": "`true`.",
                "Critical findings": "`0`.",
                "High findings": "`0`.",
                "Medium findings": "`0`.",
                "Low findings": "`0`.",
                "Open findings": "`0`.",
            }
        )
        narrative_required = (
            "The exact implementation candidate was independently reviewed "
            "in a clean detached worktree."
        )
        narrative_forbidden = (
            "The implementation candidate has not yet been frozen or reviewed.",
            "The exact implementation candidate is frozen and awaits independent review.",
        )
    else:
        expected_fields.update(
            {
                "Status": (
                    "independent implementation review pending; "
                    "no review disposition recorded."
                ),
                "Reviewed exact implementation commit": "pending.",
                "Reviewed exact tree": "pending.",
                "Clean detached worktree verified": "`false`.",
                "Remote identity verified": "`false`.",
                "Focused gate passed": "`false`.",
                "Implementation review complete": "`false`.",
                "Critical findings": "pending.",
                "High findings": "pending.",
                "Medium findings": "pending.",
                "Low findings": "pending.",
                "Open findings": "pending.",
            }
        )
        if status == "candidate_independent_review_pending":
            expected_fields["Candidate freeze complete"] = "`true`."
            narrative_required = (
                "The exact implementation candidate is frozen and awaits independent review."
            )
            narrative_forbidden = (
                "The implementation candidate has not yet been frozen or reviewed.",
                "The exact implementation candidate was independently reviewed "
                "in a clean detached worktree.",
            )
        else:
            expected_fields["Candidate freeze complete"] = "`false`."
            narrative_required = (
                "The implementation candidate has not yet been frozen or reviewed."
            )
            narrative_forbidden = (
                "The exact implementation candidate is frozen and awaits independent review.",
                "The exact implementation candidate was independently reviewed "
                "in a clean detached worktree.",
            )
    if narrative_required not in review_text:
        failures.append(f"PIS-005A {status} review record is missing lifecycle narrative")
    for phrase in narrative_forbidden:
        if phrase in review_text:
            failures.append(
                f"PIS-005A {status} review record contains stale lifecycle narrative"
            )
    observed_fields: dict[str, list[str]] = {label: [] for label in expected_fields}
    for line in review_text.splitlines():
        for label in observed_fields:
            prefix = f"{label}: "
            if line.startswith(prefix):
                observed_fields[label].append(line.removeprefix(prefix))
    for label, expected in expected_fields.items():
        if observed_fields[label] != [expected]:
            failures.append(
                f"PIS-005A {status} review field {label} is not exact and singular"
            )
    return failures


def build_report(root: Path = ROOT) -> JsonObject:
    failures: list[str] = []
    try:
        contract = load_contract(root / CONTRACT_REL)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return cast(
            JsonObject,
            {
                "valid": False,
                "decision_id": "PIS-005A",
                "failures": [f"PIS-005A contract cannot be loaded: {exc}"],
            },
        )
    failures.extend(validate_contract(contract))
    failures.extend(_repository_failures(root, contract))
    observed_tool_count = _observed_tool_count(root)
    return cast(
        JsonObject,
        {
            "valid": not failures,
            "decision_id": "PIS-005A",
            "status": contract.get("status"),
            "tool_count": observed_tool_count,
            "source_commit": SOURCE_COMMIT,
            "security_prerequisite_commit": SECURITY_PREREQUISITE_COMMIT,
            "failures": failures,
        },
    )


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
