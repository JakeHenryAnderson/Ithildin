"""Validate the bounded PIS-003 SD-PG-001 connection-evidence gate candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_pis_003_sd_pg_001_implementation_internal_review_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate.md"
)
DOC_NAME = "production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate.md"
DOC_TITLE = (
    "Production Identity And Storage PIS-003 SD-PG-001 Connection Evidence Gate"
)
DOC_SHA256 = "43a40e958eb5c12768adbf825eed38e3952b8b73a6959c7ea983e2546c8540b5"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate.json"
)
CONTRACT_SHA256 = "502367304bb9fd7272a9201219ae03d5eb5b28c021f79f69ecc63ef6dcfd0f17"
TARGET = (
    "production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate-check"
)
BASELINE_COMMIT = "bf26418b5f27b1fcd08552758e4387867b5eafe0"
REVIEWED_OFFLINE_COMMIT = "ba60478ede66abce519e134981fcabcb3f68482f"
CANDIDATE_COMMIT = "86b2074493410019914b8190e1cc9e079c0ce929"

EXPECTED_GATE_CANDIDATE_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate.json",
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-connection-evidence-gate.md",
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_check.py",
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
}
EXPECTED_GATE_CANDIDATE_PATH_INVENTORY = sorted(EXPECTED_GATE_CANDIDATE_PATHS)

EXPECTED_IMPLEMENTATION_PATHS = [
    "Makefile",
    "README.md",
    "db/alembic/env.py",
    "docs/codex/post-rc-decision-register.md",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-implementation-authority.json"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-implementation-record.md"
    ),
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "connection_evidence.py"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "connection_evidence_implementation_check.py"
    ),
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
    "tests/test_storage_schema_import.py",
]

EXPECTED_PROTECTED_PATHS = [
    "apps/api/src/ithildin_api/app.py",
    "apps/api/src/ithildin_api/config.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/storage.py",
    "apps/api/src/ithildin_api/storage_import.py",
    "apps/api/src/ithildin_api/storage_schema.py",
    "db/alembic/versions/0001_sandbox_descriptors.py",
    "pyproject.toml",
    "uv.lock",
    "tool-manifests.lock.json",
]

EXPECTED_IMPLEMENTATION_BOUNDARY = {
    "implementation_allowed_paths": EXPECTED_IMPLEMENTATION_PATHS,
    "protected_paths": EXPECTED_PROTECTED_PATHS,
    "runtime_imports_allowed": False,
    "runtime_configuration_changes_allowed": False,
    "current_sqlite_changes_allowed": False,
    "audit_ordering_changes_allowed": False,
    "second_aggregate_allowed": False,
    "importer_or_schema_changes_allowed": False,
}

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
    "apps/api/src/ithildin_api/storage_import.py": (
        "854ac31a7c23c4f3c680daa0bc3f16507cacb5003fc61d7632e16b7c36cfb65d"
    ),
    "apps/api/src/ithildin_api/storage_schema.py": (
        "5e1e087f532e40b725a00ed87475a3d52093dbea33e2b5eacb8540ebadad62c4"
    ),
    "db/alembic/versions/0001_sandbox_descriptors.py": (
        "40daefdf8882de79bd6ac68f19b0733c32877f19540c8bab1cb784534c93178e"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "implementation-internal-source-review.md"
    ): "aec09c328470b4352b097e89c3d8f3068745a4fc72c0daa284040c8c113918af",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "implementation-review-authority.json"
    ): "e5d573a28272fc25046fa3c7c7810d03770fde485fb5aa5ad4d7860d5d668602",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "implementation_internal_review_check.py"
    ): "8bd8df04c199dd52aba319cca8b5fb5f05ad490880e95dcc19254efd0f17917d",
    "pyproject.toml": (
        "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627"
    ),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

EXPECTED_REQUIRED_RECEIPTS = [
    "exact_reviewed_harness_artifact_hashes",
    "preconnection_rollback_receipt",
    "nonproduction_quarantine_and_empty_target_attestation",
    "target_owner_and_discard_owner_receipt",
    "python_sqlalchemy_alembic_psycopg_version_receipt",
    "system_libpq_source_version_patch_architecture_and_digest_receipt",
    "native_tls_backend_source_version_patch_architecture_path_and_digest_receipt",
    "psycopg_impl_python_receipt",
    "tls_root_source_path_and_sha256_receipt",
    "python_and_native_dependency_sbom_and_license_receipt",
    "synthetic_immutable_sqlite_source_and_expected_record_digest_receipt",
    "dsn_tls_posture_assertion_without_connection_fields",
    "external_receipt_verifier_trust_record",
    "secret_scan_marker_commitment",
]

EXPECTED_REQUIRED_EVIDENCE = [
    "zero_finding_exact_connection_gate_review",
    "zero_finding_exact_harness_implementation_review",
    "valid_environment_specific_execution_preflight_before_driver_load",
    "exact_plain_sync_psycopg_python_and_system_libpq_identity",
    "exact_loaded_native_tls_backend_identity",
    "exact_tls_root_source_and_digest",
    "exact_dependency_sbom_license_and_lock_identity",
    "preconnection_rollback_target_and_discard_owner_binding",
    "synthetic_frozen_sqlite_source_digest_unchanged_before_and_after",
    "caller_owned_online_alembic_migration_on_isolated_target",
    "empty_quarantined_target_verified_before_import",
    "semantic_import_readback_digest_and_stable_order_verification",
    "outer_transaction_continuity_and_no_commit_receipt",
    "explicit_outer_transaction_rollback",
    "post_rollback_application_row_absence",
    "tls_auth_unavailable_nonempty_migration_semantic_and_transaction_failure_categories",
    "secret_safe_failure_evidence_without_raw_driver_or_server_text",
    "complete_output_tree_secret_scan",
    "dsn_target_hmac_binding_and_ambient_libpq_rejection",
    "external_ed25519_receipt_and_trust_record_verification",
    "connection_attempt_budgets_and_separate_negative_run_manifests",
    "isolated_target_discard_receipt_after_last_connection",
    "protected_artifact_and_runtime_import_invariance",
    "policy_manifest_and_24_tool_invariance",
    "focused_lint_mypy_docs_agent_workflow_release_and_review_candidate_gates",
]

EXPECTED_FAILURE_CATEGORIES = [
    "preflight_invalid",
    "receipt_authenticity_failed",
    "dsn_binding_failed",
    "native_library_identity_mismatch",
    "connection_attempt_budget_exhausted",
    "tls_verification_failed",
    "authentication_or_authorization_failed",
    "target_unavailable",
    "target_not_empty",
    "migration_failed",
    "semantic_verification_failed",
    "transaction_state_lost",
    "ambiguous_commit",
]

EXPECTED_IMPLEMENTATION_CONTRACT = {
    "harness_location": (
        "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py"
    ),
    "harness_scope": "test_only_not_runtime_importable",
    "dsn_source": "environment_variable_ITHILDIN_PIS3_TEST_DSN_only",
    "target_binding_key_source": (
        "environment_variable_ITHILDIN_PIS3_TARGET_BINDING_KEY_only"
    ),
    "dsn_command_line_allowed": False,
    "dsn_file_or_repository_config_allowed": False,
    "dsn_or_credentials_persisted_or_logged": False,
    "engine": "synchronous_sqlalchemy_engine_with_nullpool",
    "engine_owner": "test_harness",
    "connection_owner": "test_harness",
    "outer_transaction_owner": "test_harness",
    "commit_allowed": False,
    "rollback_required": True,
    "online_alembic_input": "caller_owned_sqlalchemy_connection_via_config_attributes",
    "alembic_accepts_url_or_constructs_engine": False,
    "source": "synthetic_frozen_sqlite_immutable_read_only_snapshot",
    "source_digest_verified_before_and_after": True,
    "pool": "sqlalchemy_nullpool",
    "transparent_retry_allowed": False,
    "target_creation_or_drop_allowed": False,
    "role_or_grant_management_allowed": False,
    "service_or_container_lifecycle_allowed": False,
    "target_activation_allowed": False,
}

EXPECTED_EXECUTION_PREFLIGHT = {
    "required_before_driver_load": True,
    "freshness_minutes": 15,
    "manifest_binds_exact_reviewed_implementation_commit": True,
    "manifest_binds_exact_target_label": True,
    "manifest_binds_exact_source_digest": True,
    "manifest_binds_external_trust_record_sha256_and_issuer_fingerprint": True,
    "required_receipts": EXPECTED_REQUIRED_RECEIPTS,
    "forbidden_driver_packages": [
        "psycopg-c",
        "psycopg-binary",
        "psycopg-pool",
        "asyncpg",
    ],
    "psycopg_impl": "python",
    "missing_invalid_or_stale_receipt_disposition": (
        "refuse_before_driver_load_or_dsn_read"
    ),
}

EXPECTED_DSN_BINDING_CONTRACT = {
    "validation_stage": "after_signed_receipts_before_driver_load",
    "dsn_scheme": "postgresql+psycopg",
    "single_host_required": True,
    "explicit_numeric_port_required": True,
    "single_database_path_segment_required": True,
    "explicit_user_and_password_required": True,
    "fragment_allowed": False,
    "allowed_query_parameters": [
        "application_name",
        "connect_timeout",
        "sslmode",
        "sslrootcert",
    ],
    "required_query_values": {
        "application_name": "ithildin-pis3-evidence",
        "connect_timeout": "5",
        "sslmode": "verify-full",
        "sslrootcert": "exact_approved_tls_root_path",
    },
    "forbidden_connection_features": [
        "multi_host",
        "unix_socket",
        "ipv6_zone_identifier",
        "service",
        "passfile",
        "options",
        "client_certificate_or_key",
        "gss_or_kerberos",
        "alternate_tls_root",
        "unknown_query_parameter",
        "implicit_or_default_connection_field",
    ],
    "ambient_environment_key_rejection_regex": "^PG[A-Z0-9_]+$",
    "ambient_environment_key_allowlist": [],
    "uri_parsing_contract": {
        "raw_uri_encoding": (
            "ascii_with_canonical_uppercase_percent_encoded_utf8_components"
        ),
        "duplicate_userinfo_delimiter_rejected": True,
        "duplicate_query_keys_rejected": True,
        "empty_query_key_or_value_rejected": True,
        "malformed_or_noncanonical_percent_encoding_rejected": True,
        "decoded_text_normalization": "unicode_nfc",
        "hostname_form": (
            "lowercase_ascii_dns_name_without_percent_encoding_trailing_dot_or_ip_literal"
        ),
        "idna_conversion_performed": False,
        "port_form": "decimal_integer_1_through_65535_without_leading_zero",
        "database_user_and_password_form": (
            "strict_utf8_nfc_then_exact_canonical_percent_reencoding"
        ),
        "database_slash_after_decoding_allowed": False,
        "query_keys_raw_ascii_only": True,
        "query_values_strict_utf8_nfc_and_canonical_percent_reencoding": True,
        "component_raw_safe_ascii": (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        ),
        "non_safe_utf8_byte_encoding": (
            "percent_sign_plus_two_uppercase_hex_digits"
        ),
        "percent_encoded_unreserved_byte_rejected": True,
        "raw_reserved_or_non_ascii_component_byte_rejected": True,
        "userinfo_delimiters": "one_literal_colon_then_one_literal_at_sign",
        "query_delimiters": "literal_equals_and_ampersand_only",
        "query_pair_order": [
            "application_name",
            "connect_timeout",
            "sslmode",
            "sslrootcert",
        ],
    },
    "binding_algorithm": "hmac-sha256",
    "binding_key_encoding": "base64url_no_padding_32_bytes",
    "binding_domain": "ITHILDIN-PIS3-DSN-BINDING-V1\n",
    "binding_payload_schema_version": "1",
    "binding_payload_exact_keys": [
        "application_name",
        "connect_timeout_seconds",
        "database_utf8",
        "hostname_ascii_lower",
        "password_utf8",
        "port",
        "reviewed_candidate_commit",
        "run_id",
        "schema_version",
        "scheme",
        "sslmode",
        "sslrootcert_realpath",
        "sslrootcert_sha256",
        "target_label",
        "user_utf8",
    ],
    "binding_payload_field_types": {
        "application_name": "string",
        "connect_timeout_seconds": "integer",
        "database_utf8": "string",
        "hostname_ascii_lower": "string",
        "password_utf8": "string",
        "port": "integer",
        "reviewed_candidate_commit": "string",
        "run_id": "string",
        "schema_version": "string",
        "scheme": "string",
        "sslmode": "string",
        "sslrootcert_realpath": "string",
        "sslrootcert_sha256": "string",
        "target_label": "string",
        "user_utf8": "string",
    },
    "binding_payload_constraints": {
        "application_name": "exact_ithildin-pis3-evidence",
        "connect_timeout_seconds": "exact_integer_5_boolean_rejected",
        "database_utf8": "utf8_byte_length_1_to_63_no_control_or_slash",
        "hostname_ascii_lower": (
            "ascii_dns_name_length_1_to_253_no_trailing_dot_or_ip_literal"
        ),
        "password_utf8": "utf8_byte_length_1_to_1024_no_nul",
        "port": "integer_1_through_65535_boolean_rejected",
        "reviewed_candidate_commit": "40_lowercase_hex",
        "run_id": "pis3run_underscore_plus_32_lowercase_hex",
        "schema_version": "exact_1",
        "scheme": "exact_postgresql+psycopg",
        "sslmode": "exact_verify-full",
        "sslrootcert_realpath": (
            "absolute_system_path_utf8_byte_length_1_to_1024_no_control"
        ),
        "sslrootcert_sha256": "sha256_colon_plus_64_lowercase_hex",
        "target_label": "safe_label_ascii_length_3_to_64",
        "user_utf8": "utf8_byte_length_1_to_63_no_control",
    },
    "binding_serialization": (
        "domain_ascii_plus_ithildin_canonical_json_utf8_no_bom_no_newline"
    ),
    "binding_output_encoding": "hmac-sha256_colon_plus_64_lowercase_hex",
    "binding_comparison": "constant_time",
    "plain_unkeyed_dsn_hash_allowed": False,
    "binding_key_or_normalized_fields_persisted": False,
    "binding_key_ephemeral_harness_disclosure_allowed": True,
    "binding_key_retained_after_comparison": False,
    "primary_positive_connection_attempt_budget": 2,
    "negative_scenario_connection_attempt_budget": 1,
    "negative_scenarios_require_separate_signed_manifests_runs_targets_and_dsns": True,
}

EXPECTED_RECEIPT_AUTHENTICITY_CONTRACT = {
    "signature_algorithm": "ed25519",
    "signature_domain": "ITHILDIN-PIS3-CONNECTION-RECEIPT-V1\n",
    "signed_encoding": (
        "domain_ascii_plus_ithildin_canonical_json_utf8_payload_no_bom_no_newline"
    ),
    "canonical_json_algorithm": (
        "json_sort_keys_true_separators_comma_colon_ensure_ascii_false_utf8"
    ),
    "signature_envelope_exact_keys": ["payload", "signature"],
    "signature_metadata_exact_keys": [
        "algorithm",
        "key_id",
        "signature_base64url",
    ],
    "signature_metadata_constants": {"algorithm": "Ed25519"},
    "signature_envelope_field_types": {
        "payload": "object",
        "signature": "object",
    },
    "signature_metadata_field_types": {
        "algorithm": "string",
        "key_id": "string",
        "signature_base64url": "string",
    },
    "signature_encoding": "base64url_no_padding_64_bytes",
    "json_parsing_contract": {
        "encoding": "strict_utf8_no_bom",
        "duplicate_object_members_rejected": True,
        "nonfinite_json_constants_rejected": True,
        "extra_object_members_rejected": True,
        "integer_fields_reject_boolean": True,
        "canonical_round_trip_equality_required": True,
    },
    "required_signed_receipt_types": [
        "preconnection_rollback_receipt",
        "target_owner_quarantine_receipt",
        "target_discard_receipt",
    ],
    "receipt_payload_exact_keys": [
        "schema_version",
        "receipt_type",
        "issuer_id",
        "issued_at",
        "expires_at",
        "provenance",
        "run_id",
        "target_label",
        "reviewed_candidate_commit",
        "source_digest",
        "assertion",
    ],
    "receipt_payload_field_types": {
        "schema_version": "string",
        "receipt_type": "string",
        "issuer_id": "string",
        "issued_at": "string",
        "expires_at": "string",
        "provenance": "string",
        "run_id": "string",
        "target_label": "string",
        "reviewed_candidate_commit": "string",
        "source_digest": "string",
        "assertion": "object",
    },
    "receipt_payload_patterns": {
        "schema_version": "^1$",
        "issuer_id": "^[a-z][a-z0-9._-]{2,63}$",
        "issued_at_and_expires_at": (
            "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
            "[0-9]{2}\\+00:00$"
        ),
        "run_id": "^pis3run_[0-9a-f]{32}$",
        "target_label": "^[a-z0-9][a-z0-9._-]{2,63}$",
        "reviewed_candidate_commit": "^[0-9a-f]{40}$",
        "source_digest": "^sha256:[0-9a-f]{64}$",
    },
    "receipt_payload_limits": {
        "provenance_utf8_bytes": "1_to_64",
        "assertion_max_canonical_json_bytes": 4096,
    },
    "receipt_provenance_by_type": {
        "preconnection_rollback_receipt": "external_target_owner_attestation",
        "target_owner_quarantine_receipt": "external_target_owner_attestation",
        "target_discard_receipt": "external_target_discard_owner_attestation",
    },
    "receipt_time_relationships": [
        "issued_at_strictly_before_expires_at",
        "expires_at_no_more_than_15_minutes_after_issued_at",
        "verification_time_within_issued_at_and_expires_at",
    ],
    "receipt_binding_relationships": [
        (
            "run_id_target_label_reviewed_candidate_commit_and_source_digest_"
            "equal_execution_manifest"
        ),
        "receipt_type_matches_exact_assertion_schema",
        "receipt_type_is_allowed_by_verified_issuer_trust_record",
        (
            "target_discard_receipt_issuer_id_equals_target_owner_quarantine_"
            "receipt_assertion_discard_owner_id"
        ),
    ],
    "receipt_specific_required_assertions": {
        "preconnection_rollback_receipt": {
            "exact_keys": [
                "activation_allowed",
                "bound_before_connection",
                "rollback_disposition",
                "source_unchanged",
            ],
            "field_types": {
                "activation_allowed": "boolean",
                "bound_before_connection": "boolean",
                "rollback_disposition": "string",
                "source_unchanged": "boolean",
            },
            "fixed_values": {
                "activation_allowed": False,
                "bound_before_connection": True,
                "rollback_disposition": (
                    "revert_exact_candidate_and_discard_isolated_target_before_activation"
                ),
                "source_unchanged": True,
            },
        },
        "target_owner_quarantine_receipt": {
            "exact_keys": [
                "connection_attempt_budget",
                "dedicated_nonproduction_purpose",
                "discard_owner_id",
                "target_binding_hmac_sha256_commitment",
                "target_empty",
                "target_quarantined",
            ],
            "field_types": {
                "connection_attempt_budget": "integer",
                "dedicated_nonproduction_purpose": "string",
                "discard_owner_id": "string",
                "target_binding_hmac_sha256_commitment": "string",
                "target_empty": "boolean",
                "target_quarantined": "boolean",
            },
            "fixed_values": {
                "dedicated_nonproduction_purpose": "pis3_connection_evidence_only",
                "target_empty": True,
                "target_quarantined": True,
            },
            "patterns": {
                "discard_owner_id": "^[a-z][a-z0-9._-]{2,63}$",
                "target_binding_hmac_sha256_commitment": (
                    "^hmac-sha256:[0-9a-f]{64}$"
                ),
            },
            "connection_attempt_budget_relationship": (
                "2_for_primary_positive_run_or_1_for_exact_negative_scenario_run"
            ),
        },
        "target_discard_receipt": {
            "exact_keys": [
                "activation_never_occurred",
                "last_connection_closed_at",
                "target_discarded",
                "target_discarded_at",
            ],
            "field_types": {
                "activation_never_occurred": "boolean",
                "last_connection_closed_at": "string",
                "target_discarded": "boolean",
                "target_discarded_at": "string",
            },
            "fixed_values": {
                "activation_never_occurred": True,
                "target_discarded": True,
            },
            "time_pattern": (
                "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
                "[0-9]{2}\\+00:00$"
            ),
            "time_relationship": (
                "target_discarded_at_strictly_after_last_connection_closed_at"
            ),
            "issuance_relationship": (
                "last_connection_closed_at_before_target_discarded_at_at_or_before_issued_at"
            ),
        },
    },
    "trust_record_exact_keys": [
        "issuer_id",
        "ed25519_public_key",
        "public_key_fingerprint",
        "allowed_receipt_types",
        "valid_from",
        "valid_until",
    ],
    "trust_record_field_types": {
        "issuer_id": "string",
        "ed25519_public_key": "string",
        "public_key_fingerprint": "string",
        "allowed_receipt_types": "array_of_unique_strings",
        "valid_from": "string",
        "valid_until": "string",
    },
    "trust_record_encodings": {
        "ed25519_public_key": "base64url_no_padding_32_bytes",
        "public_key_fingerprint": (
            "sha256_colon_plus_64_lowercase_hex_of_raw_32_byte_public_key"
        ),
        "signature_key_id": "must_equal_public_key_fingerprint",
    },
    "trust_record_patterns": {
        "issuer_id": "^[a-z][a-z0-9._-]{2,63}$",
        "valid_from_and_valid_until": (
            "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
            "[0-9]{2}\\+00:00$"
        ),
    },
    "trust_record_relationships": [
        "issuer_id_matches_receipt_issuer_id",
        "allowed_receipt_types_nonempty_subset_of_closed_required_receipt_types",
        "valid_from_strictly_before_valid_until",
        "receipt_and_verification_times_within_trust_record_window",
    ],
    "execution_manifest_binds_trust_record_sha256_and_issuer_fingerprint": True,
    "receipts_and_trust_record_origin": (
        "read_only_external_paths_outside_repository_and_output_root"
    ),
    "ed25519_private_key_custody": "never_enters_ithildin",
    "hmac_key_custody": (
        "external_generation_then_ephemeral_harness_disclosure_for_"
        "constant_time_comparison_only"
    ),
    "harness_receipt_creation_edit_or_overwrite_allowed": False,
    "harness_trust_record_generation_or_substitution_allowed": False,
    "discard_receipt_issued_after_last_connection_required": True,
    "separate_finalizer_verification_required": True,
}

EXPECTED_NATIVE_DEPENDENCY_IDENTITY_CONTRACT = {
    "preflight_binds_libpq_and_tls_backend": True,
    "required_identity_fields": [
        "distribution_source",
        "package_receipt",
        "version",
        "patch_provenance",
        "architecture",
        "loaded_library_realpath",
        "library_sha256",
        "license",
    ],
    "post_driver_load_identity_confirmation_required": True,
    "post_driver_load_confirmation_before_first_sql_statement": True,
    "loaded_libpq_and_tls_backend_must_match_preflight": True,
    "native_dependency_closure_in_sbom_and_license_receipt_required": True,
    "python_lock_alone_sufficient": False,
}

EXPECTED_SAFE_EVIDENCE_CONTRACT = {
    "run_label": "isolated_nonproduction_connection_evidence_only",
    "allowed_values": [
        "safe_target_label",
        "fixed_failure_category",
        "fixed_failure_stage",
        "boolean_posture",
        "artifact_package_certificate_and_source_sha256",
        "native_library_system_realpath",
        "external_receipt_issuer_and_public_key_fingerprint",
        "counts",
        "descriptor_ids",
        "canonical_utc_times",
        "ithildin_owned_semantic_digests",
    ],
    "forbidden_values": [
        "dsn",
        "credential",
        "hostname_or_address",
        "database_name",
        "role_name",
        "certificate_subject",
        "raw_sql_parameters",
        "payload_json",
        "environment_dump",
        "target_binding_key_or_normalized_connection_tuple",
        "raw_driver_server_or_alembic_exception_text",
    ],
    "raw_exception_chaining_allowed_at_evidence_boundary": False,
    "secret_scan_required": True,
}

EXPECTED_AUTHORITY = {
    "pis_003_sd_pg_001_connection_evidence_gate_recorded": True,
    "connection_evidence_candidate_selected": True,
    "offline_candidate_review_prerequisite_satisfied": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": False,
    "connection_evidence_implementation_allowed": False,
    "environment_receipt_implementation_allowed": False,
    "test_harness_implementation_allowed": False,
    "synthetic_snapshot_reader_implementation_allowed": False,
    "online_alembic_caller_connection_implementation_allowed": False,
    "failure_evidence_implementation_allowed": False,
    "execution_preflight_implementation_allowed": False,
    "psycopg_plain_sync_use_allowed": False,
    "external_dsn_consumption_allowed": False,
    "test_harness_execution_allowed": False,
    "isolated_test_connection_allowed": False,
    "database_connections_allowed": False,
    "migration_execution_allowed": False,
    "postgres_service_allowed": False,
    "container_lifecycle_allowed": False,
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
    "connection_execution_authority_required": True,
}

EXPECTED_POST_REVIEW_CEILING = {
    **EXPECTED_AUTHORITY,
    "pis_003_sd_pg_001_connection_evidence_gate_recorded": None,
    "connection_evidence_candidate_selected": None,
    "offline_candidate_review_prerequisite_satisfied": None,
    "exact_candidate_source_review_required": None,
    "exact_candidate_source_review_complete": None,
    "connection_evidence_implementation_allowed": True,
    "environment_receipt_implementation_allowed": True,
    "test_harness_implementation_allowed": True,
    "synthetic_snapshot_reader_implementation_allowed": True,
    "online_alembic_caller_connection_implementation_allowed": True,
    "failure_evidence_implementation_allowed": True,
    "execution_preflight_implementation_allowed": True,
}
EXPECTED_POST_REVIEW_CEILING = {
    key: value for key, value in EXPECTED_POST_REVIEW_CEILING.items() if value is not None
}

REQUIRED_PHRASES = [
    (
        "Status: committed connection-evidence-gate candidate pending exact-candidate source "
        "review; no connection implementation or execution authority is active."
    ),
    "Gate ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE`.",
    f"Reviewed offline candidate: `{REVIEWED_OFFLINE_COMMIT}`.",
    f"Gate baseline commit: `{BASELINE_COMMIT}`.",
    "Current governed tool count: `24`.",
    "The gate candidate itself changes exactly eleven paths",
    "No single green validator flips both implementation and execution authority.",
    "No system-`libpq` source/version/patch receipt",
    "`ITHILDIN_PIS3_TEST_DSN`",
    "`PSYCOPG_IMPL=python`",
    "`ambiguous_commit`",
    "`revert_exact_candidate_and_discard_isolated_target_before_activation`",
    "`connection_evidence_implementation_allowed: false`",
    "`external_dsn_consumption_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`review_pis_003_sd_pg_001_connection_evidence_gate_exact_candidate`",
    f"make {TARGET}",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(r"\bconnections? (?:are|is|have been) (?:approved|authorized)\b"),
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
        f"PIS-003 connection-evidence gate is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]
    failures.extend(
        "PIS-003 connection-evidence gate contains forbidden authority pattern: "
        f"{pattern.pattern}"
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
        "reviewed_offline_candidate_commit",
        "gate_baseline_commit",
        "evidence_slice",
        "gate_outcome",
        "tool_count",
        "gate_candidate_path_inventory",
        "current_environment_observation",
        "implementation_boundary",
        "implementation_contract",
        "execution_preflight",
        "dsn_binding_contract",
        "receipt_authenticity_contract",
        "native_dependency_identity_contract",
        "required_connection_evidence",
        "safe_evidence_contract",
        "failure_categories",
        "rollback",
        "protected_hashes",
        "post_review_authority_ceiling",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 connection-evidence gate top-level keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "gate_id": "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE",
        "parent_review": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION-REVIEW"
        ),
        "reviewed_offline_candidate_commit": REVIEWED_OFFLINE_COMMIT,
        "gate_baseline_commit": BASELINE_COMMIT,
        "evidence_slice": "PIS-003-SD-PG-001-CONNECTION-EVIDENCE",
        "gate_outcome": "select_bounded_connection_evidence_candidate_pending_gate_review",
        "tool_count": 24,
        "next_required_action": (
            "review_pis_003_sd_pg_001_connection_evidence_gate_exact_candidate"
        ),
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 connection-evidence gate field {key} is not exact")
    if type(contract.get("tool_count")) is not int:
        failures.append("PIS-003 connection-evidence tool_count must be an exact integer")
    if contract.get("gate_candidate_path_inventory") != (
        EXPECTED_GATE_CANDIDATE_PATH_INVENTORY
    ):
        failures.append("PIS-003 connection gate contract path inventory is not exact")

    environment = contract.get("current_environment_observation")
    expected_environment = {
        "observation_date": "2026-07-21",
        "operating_system": "macos-26.5.2",
        "architecture": "arm64",
        "repository_python": "3.12.13",
        "uv_version": "0.11.12",
        "docker_cli_present": True,
        "pg_config_present": False,
        "psql_present": False,
        "postgres_present": False,
        "initdb_present": False,
        "system_libpq_receipt_present": False,
        "tls_root_observed_path": "/etc/ssl/cert.pem",
        "target_selected": False,
        "dsn_present_or_consumed": False,
        "driver_loaded": False,
        "database_connection_attempted": False,
        "environment_execution_ready": False,
        "container_or_service_lifecycle_allowed": False,
    }
    if environment != expected_environment:
        failures.append("PIS-003 current environment observation is not exact")

    if contract.get("implementation_boundary") != EXPECTED_IMPLEMENTATION_BOUNDARY:
        failures.append("PIS-003 connection implementation boundary is not exact")

    if contract.get("implementation_contract") != EXPECTED_IMPLEMENTATION_CONTRACT:
        failures.append("PIS-003 connection implementation contract is not exact")
    if contract.get("execution_preflight") != EXPECTED_EXECUTION_PREFLIGHT:
        failures.append("PIS-003 execution preflight is not exact")
    if contract.get("dsn_binding_contract") != EXPECTED_DSN_BINDING_CONTRACT:
        failures.append("PIS-003 DSN binding contract is not exact")
    if (
        contract.get("receipt_authenticity_contract")
        != EXPECTED_RECEIPT_AUTHENTICITY_CONTRACT
    ):
        failures.append("PIS-003 receipt authenticity contract is not exact")
    if (
        contract.get("native_dependency_identity_contract")
        != EXPECTED_NATIVE_DEPENDENCY_IDENTITY_CONTRACT
    ):
        failures.append("PIS-003 native dependency identity contract is not exact")

    if contract.get("required_connection_evidence") != EXPECTED_REQUIRED_EVIDENCE:
        failures.append("PIS-003 required connection evidence is not exact")
    if contract.get("failure_categories") != EXPECTED_FAILURE_CATEGORIES:
        failures.append("PIS-003 safe failure categories are not exact")

    if contract.get("safe_evidence_contract") != EXPECTED_SAFE_EVIDENCE_CONTRACT:
        failures.append("PIS-003 safe evidence contract is not exact")

    expected_rollback = {
        "disposition": "revert_exact_candidate_and_discard_isolated_target_before_activation",
        "bound_before_connection": True,
        "outer_transaction_rollback_required": True,
        "post_rollback_absence_required": True,
        "source_sqlite_modified": False,
        "target_discard_receipt_required": True,
        "target_discard_after_last_connection_required": True,
        "reverse_import_allowed": False,
        "dual_write_allowed": False,
        "in_place_repair_allowed": False,
        "migration_downgrade_allowed": False,
        "activation_allowed": False,
    }
    if contract.get("rollback") != expected_rollback:
        failures.append("PIS-003 connection rollback contract is not exact")
    if contract.get("protected_hashes") != EXPECTED_PROTECTED_HASHES:
        failures.append("PIS-003 connection protected hash inventory is not exact")

    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 connection gate authority is not the exact Boolean map")
    ceiling = contract.get("post_review_authority_ceiling")
    if (
        ceiling != EXPECTED_POST_REVIEW_CEILING
        or not isinstance(ceiling, dict)
        or any(type(value) is not bool for value in ceiling.values())
    ):
        failures.append("PIS-003 connection gate post-review ceiling is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 connection-evidence gate is not UTF-8")
    failures.extend(validate_gate_text(doc_text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 connection-evidence gate bytes do not match the closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append(
            "PIS-003 connection-evidence gate contract bytes do not match the closed digest"
        )

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, CANDIDATE_COMMIT)
    candidate_is_ancestor = _is_ancestor(repo_root, CANDIDATE_COMMIT, "HEAD")
    if not baseline_exists:
        failures.append("PIS-003 connection gate baseline commit is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 connection gate baseline is not an ancestor of candidate")
    if not candidate_is_ancestor:
        failures.append("PIS-003 connection gate candidate is not an ancestor of HEAD")

    candidate_paths = _candidate_paths(repo_root)
    candidate_inventory_exact = candidate_paths == EXPECTED_GATE_CANDIDATE_PATHS
    if not candidate_inventory_exact:
        failures.append("PIS-003 connection gate candidate path inventory is not exact")

    reviewed_offline_exists = _commit_exists(repo_root, REVIEWED_OFFLINE_COMMIT)
    reviewed_offline_is_ancestor = _is_ancestor(repo_root, REVIEWED_OFFLINE_COMMIT, "HEAD")
    if not reviewed_offline_exists or not reviewed_offline_is_ancestor:
        failures.append("PIS-003 reviewed offline candidate lineage is unavailable")

    protected_hashes_match = True
    for path, expected_hash in EXPECTED_PROTECTED_HASHES.items():
        actual_hash = hashlib.sha256(_read_bytes(repo_root / path)).hexdigest()
        if actual_hash != expected_hash:
            protected_hashes_match = False
            failures.append(f"PIS-003 connection protected path hash mismatch: {path}")

    prerequisite = (
        production_identity_storage_pis_003_sd_pg_001_implementation_internal_review_check.build_report(
            repo_root
        )
    )
    prerequisite_valid = bool(
        prerequisite.get("valid")
        and prerequisite.get("reviewed_commit") == REVIEWED_OFFLINE_COMMIT
        and prerequisite.get("exact_candidate_source_review_complete")
        and prerequisite.get("connection_evidence_gate_preparation_allowed")
        and not prerequisite.get("psycopg_plain_sync_use_allowed")
        and not prerequisite.get("database_connections_allowed")
        and not prerequisite.get("migration_execution_allowed")
        and not prerequisite.get("postgres_service_allowed")
        and not prerequisite.get("runtime_postgres_allowed")
    )
    if not prerequisite_valid:
        failures.append(
            "PIS-003 offline implementation review does not authorize connection-gate preparation"
        )

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-003 connection gate tool count is {tool_count}, expected 24")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 connection gate wiring is incomplete")

    valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "gate_document": DOC_REL,
        "gate_document_sha256": doc_hash,
        "gate_document_hash_matches": doc_hash == DOC_SHA256,
        "gate_contract": CONTRACT_REL,
        "gate_contract_sha256": contract_hash,
        "gate_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "gate_id": contract.get("gate_id") if valid else "invalid",
        "gate_outcome": contract.get("gate_outcome") if valid else "invalid",
        "gate_baseline_commit": BASELINE_COMMIT,
        "candidate_commit": CANDIDATE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_is_ancestor": candidate_is_ancestor,
        "candidate_path_count": len(candidate_paths),
        "candidate_inventory_exact": candidate_inventory_exact,
        "reviewed_offline_candidate_commit": REVIEWED_OFFLINE_COMMIT,
        "reviewed_offline_exists": reviewed_offline_exists,
        "reviewed_offline_is_ancestor": reviewed_offline_is_ancestor,
        "protected_hashes_match": protected_hashes_match,
        "offline_review_prerequisite_valid": prerequisite_valid,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (
            contract.get("next_required_action") if valid else "invalid_gate"
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "gate_document",
        "gate_id",
        "gate_outcome",
        "gate_baseline_commit",
        "candidate_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "candidate_is_ancestor",
        "candidate_path_count",
        "candidate_inventory_exact",
        "reviewed_offline_candidate_commit",
        "reviewed_offline_exists",
        "reviewed_offline_is_ancestor",
        "gate_document_hash_matches",
        "gate_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "offline_review_prerequisite_valid",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 connection-evidence gate check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read_text(repo_root / "Makefile")
    readme = _read_text(repo_root / "README.md")
    review_docs = _read_text(repo_root / "scripts/review_docs.py")
    docs_site = _read_text(repo_root / "scripts/build_docs_site.py")
    guardrails = _read_text(repo_root / "scripts/release_guardrails.py")
    index = _read_text(repo_root / "docs/codex/review-docs-index.md")
    return bool(
        f".PHONY: {TARGET}" in makefile
        and f"{TARGET}:" in makefile
        and "production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_check.py"
        in makefile
        and TARGET in readme
        and DOC_REL in review_docs
        and DOC_REL in docs_site
        and TARGET in guardrails
        and DOC_NAME in index
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    try:
        loaded = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"PIS-003 connection gate contract cannot be loaded: {exc}"]
    if not isinstance(loaded, dict):
        failures.append("PIS-003 connection gate contract root must be an object")
        return {}, failures
    return loaded, failures


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _candidate_paths(repo_root: Path) -> set[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", f"{BASELINE_COMMIT}..{CANDIDATE_COMMIT}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.returncode != 0:
        return set()
    return {
        line.strip()
        for line in tracked.stdout.splitlines()
        if line.strip()
    }


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return -1
    manifests = payload.get("manifests") if isinstance(payload, dict) else None
    return len(manifests) if isinstance(manifests, list) else -1


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
