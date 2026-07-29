"""Validate the bounded PIS-004A local identity implementation lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path(
    "docs/codex/production-identity-storage-pis-004a-entry-and-implementation-contract.json"
)
DOC_REL = Path("docs/codex/production-identity-storage-pis-004a-local-identity-foundation.md")
SOURCE_COMMIT = "e86f5a19e4e067d73141246f78304597e6cc28a0"
SOURCE_TREE = "6dbbcf0bef3320dfdfa4142f2d30b798b01511d0"
BRANCH = "codex/enterprise-e2-pis004a-local-identity"
PIS_WAIT_ACTION = (
    "await_external_operator_target_and_signed_receipt_inputs_before_separate_"
    "collection_action_authority"
)
NEXT_ACTION = (
    "implement_and_validate_pis_004a_local_default_off_candidate_then_stop_for_"
    "independent_review"
)
IMPLEMENTATION_STATUSES = {
    "implementation_authorized",
    "candidate_implemented_review_required",
}
PROTECTED_HASHES = {
    "docs/codex/production-identity-storage-architecture.md": (
        "f8c53dfa9d8fb2ef041f5f489a1adfa9e4a40e6a3cc40002b66c1f0283df9748"
    ),
    "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md": (
        "c01372edba661536a2bf5f799ef84c7ede285e4b1ee681ff21bf106abc1c116d"
    ),
    "docs/codex/enterprise-e2-production-identity-preparation.md": (
        "e95dea1703efa506d07425d9deacf4b98d1e7690170083fdc04fc59acc2f7c14"
    ),
    "docs/codex/enterprise-e2-preparation-contract.json": (
        "06555530e395baa0a3f7aba5321a6b20c95085eebb6560f3fbd7cca2d4411d27"
    ),
    "docs/codex/enterprise-e1-completion-contract.json": (
        "cfcf463cf294b6db2e8bb70c2e7e5d6f9dad4bb740a5c290947403f8a49e256a"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-evidence-collection-authority.json"
    ): "95ec69aeaff0284ab54b2e894804b309a5db83c3a4bbf83a6ccba4ddc01a0def",
}
EXPECTED_BASE = {
    "source_branch": "origin/codex/enterprise-e2-production-identity-prep",
    "source_commit": SOURCE_COMMIT,
    "source_tree": SOURCE_TREE,
    "e1_handoff_commit": "9df7a04cec197fd4953de692793a32e69c107b49",
    "e1_candidate_commit": "02e39d57a6d38a14d959bb88a32da79fe34e4e13",
    "local_v1_candidate_commit": "ab4162d8f4b6d3f45a68f33316f4b765a45765db",
    "branch": BRANCH,
    "e1_human_uat_complete": False,
}
EXPECTED_AUTHORITY = {
    "bounded_implementation_allowed": True,
    "provider_neutral_identity_domain_allowed": True,
    "opaque_local_session_store_allowed": True,
    "organization_workspace_authorization_allowed": True,
    "fixture_only_oidc_conformance_allowed": True,
    "local_sqlite_schema_migration_allowed": True,
    "exact_dependency_delta_allowed": True,
    "additive_default_off_local_api_integration_allowed": True,
    "feature_default_enabled": False,
    "loopback_local_preview_only": True,
    "live_idp_allowed": False,
    "external_network_allowed": False,
    "external_credentials_allowed": False,
    "client_secret_or_signing_key_custody_allowed": False,
    "operator_target_allowed": False,
    "dsn_or_binding_key_consumption_allowed": False,
    "runtime_postgres_allowed": False,
    "remote_administration_allowed": False,
    "multi_tenant_hosting_allowed": False,
    "production_identity_allowed": False,
    "enterprise_production_claim_allowed": False,
    "new_governed_tool_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "human_uat_completion_allowed": False,
}
EXPECTED_WORK_PACKAGES = [
    {
        "id": "E2-ID-001",
        "status": "authorized_in_pis_004a",
        "scope": "provider_neutral_identity_domain",
    },
    {
        "id": "E2-ID-002",
        "status": "authorized_in_pis_004a",
        "scope": "server_owned_preauthentication_and_opaque_sessions",
    },
    {
        "id": "E2-ID-003",
        "status": "authorized_fixture_only",
        "scope": "zero_network_oidc_conformance",
    },
    {
        "id": "E2-ID-004",
        "status": "authorized_in_pis_004a",
        "scope": "organization_workspace_authorization",
    },
    {
        "id": "E2-ID-005",
        "status": "blocked_on_e1_human_uat",
        "scope": "next_ticket_and_acceptance_contract_only",
    },
]
EXPECTED_ALLOWED_PATHS = [
    "Makefile",
    "README.md",
    "apps/api/src/ithildin_api/database_migration_backup.py",
    "apps/api/src/ithildin_api/enterprise_authorization.py",
    "apps/api/src/ithildin_api/enterprise_identity.py",
    "apps/api/src/ithildin_api/enterprise_sessions.py",
    "apps/api/src/ithildin_api/oidc_fixture_conformance.py",
    "apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
    "docs/codex/production-identity-storage-pis-004a-e2-id-005-next-ticket.md",
    "docs/codex/production-identity-storage-pis-004a-entry-and-implementation-contract.json",
    "docs/codex/production-identity-storage-pis-004a-local-identity-foundation.md",
    "docs/codex/review-docs-index.md",
    "pyproject.toml",
    "scripts/build_docs_site.py",
    "scripts/enterprise_e2_preparation_check.py",
    "scripts/production_identity_storage_pis_004a_check.py",
    "scripts/review_docs.py",
    "tests/fixtures/pis004a_oidc/callback.json",
    "tests/fixtures/pis004a_oidc/discovery.json",
    "tests/fixtures/pis004a_oidc/jwks.json",
    "tests/fixtures/pis004a_oidc/tokens.json",
    "tests/test_pis004a_authorization.py",
    "tests/test_pis004a_contract.py",
    "tests/test_pis004a_database_migration.py",
    "tests/test_pis004a_identity.py",
    "tests/test_pis004a_oidc_fixtures.py",
    "tests/test_pis004a_sessions.py",
    "tests/test_api_service.py",
    "tests/test_mission_database_migration.py",
    "tests/test_trusted_host_promotion_v2_migration.py",
    "uv.lock",
]
EXPECTED_NEGATIVE_INVENTORY = [
    "caller_authority_spoofing",
    "exact_issuer_mismatch",
    "subject_remap",
    "session_handle_or_audit_id_confusion",
    "idle_and_absolute_expiry",
    "rotation_replay_and_family_revocation",
    "identity_and_membership_generation_drift",
    "preauthentication_replay",
    "origin_and_csrf_mismatch",
    "digest_key_generation_unavailable",
    "cross_organization_and_workspace_access",
    "node_or_service_human_approval",
    "separation_of_duty_and_self_approval",
    "cross_workspace_list_and_bulk_enumeration",
    "oidc_state_nonce_pkce_redirect_and_issuer_mismatch",
    "oidc_algorithm_kid_audience_exp_iat_nbf_skew_and_replay",
    "oidc_malformed_input_and_network_attempt",
    "raw_identity_or_token_material_in_audit",
]
EXPECTED_NONCLAIMS = [
    "live IdP integration",
    "production identity",
    "enterprise RBAC",
    "remote administration",
    "multi-tenant hosting",
    "runtime PostgreSQL",
    "production credential or signing-key custody",
    "supported scale or performance certification",
    "human UAT completion",
    "release acceptance",
    "enterprise-production readiness",
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


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    contract = load_contract(root / CONTRACT_REL, failures)
    failures.extend(validate_contract(contract))
    _validate_repository(root, contract, failures)
    return {
        "valid": not failures,
        "failures": failures,
        "decision_id": contract.get("decision_id"),
        "status": contract.get("status"),
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "branch": _git_one(root, "branch", "--show-current"),
        "tool_count": _tool_count(root),
        "pis003_next_action": PIS_WAIT_ACTION,
        "e1_human_uat_complete": False,
        "live_idp_allowed": False,
        "runtime_postgres_allowed": False,
        "next_action": contract.get("next_action"),
    }


def load_contract(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"PIS-004A contract cannot be loaded: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append("PIS-004A contract must be an object")
        return {}
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    _require_keys(
        contract,
        {
            "schema_version",
            "decision_id",
            "title",
            "status",
            "base",
            "standing_authority",
            "authority",
            "work_packages",
            "dependency_gate",
            "persistence",
            "safety_contract",
            "allowed_paths",
            "validation",
            "rollback",
            "candidate_procedure",
            "nonclaims",
            "next_action",
        },
        "contract",
        failures,
    )
    if contract.get("schema_version") != "1" or contract.get("decision_id") != "PIS-004A":
        failures.append("PIS-004A contract identity is invalid")
    if contract.get("status") not in IMPLEMENTATION_STATUSES:
        failures.append("PIS-004A implementation status is invalid")
    if contract.get("base") != EXPECTED_BASE:
        failures.append("PIS-004A source and candidate identities are not exact")
    if contract.get("authority") != EXPECTED_AUTHORITY:
        failures.append("PIS-004A authority ceiling is invalid")
    if contract.get("work_packages") != EXPECTED_WORK_PACKAGES:
        failures.append("PIS-004A work-package scope is invalid")
    if contract.get("allowed_paths") != EXPECTED_ALLOWED_PATHS:
        failures.append("PIS-004A allowed paths are not exact and ordered")
    if contract.get("nonclaims") != EXPECTED_NONCLAIMS:
        failures.append("PIS-004A nonclaims are not exact and ordered")
    if contract.get("next_action") != NEXT_ACTION:
        failures.append("PIS-004A next action is invalid")
    _validate_standing_authority(contract.get("standing_authority"), failures)
    _validate_dependency_gate(contract.get("dependency_gate"), failures)
    _validate_persistence(contract.get("persistence"), failures)
    _validate_safety_contract(contract.get("safety_contract"), failures)
    validation = contract.get("validation")
    if not isinstance(validation, dict) or set(validation) != {
        "make_target",
        "focused_tests",
        "negative_inventory",
    }:
        failures.append("PIS-004A validation contract keys are not closed")
    elif (
        validation.get("make_target") != "production-identity-storage-pis-004a-check"
        or validation.get("negative_inventory") != EXPECTED_NEGATIVE_INVENTORY
        or validation.get("focused_tests")
        != [
            "tests/test_pis004a_contract.py",
            "tests/test_pis004a_database_migration.py",
            "tests/test_pis004a_identity.py",
            "tests/test_pis004a_sessions.py",
            "tests/test_pis004a_authorization.py",
            "tests/test_pis004a_oidc_fixtures.py",
        ]
    ):
        failures.append("PIS-004A focused validation inventory is invalid")
    rollback = contract.get("rollback")
    if not isinstance(rollback, dict) or set(rollback) != {
        "feature",
        "dependency",
        "database",
        "data_loss",
        "compatibility",
        "external_system_effect",
    }:
        failures.append("PIS-004A rollback contract keys are not closed")
    elif rollback.get("external_system_effect") is not False:
        failures.append("PIS-004A rollback contract permits an external effect")
    candidate = contract.get("candidate_procedure")
    if not isinstance(candidate, dict) or set(candidate) != {
        "focused_command",
        "independent_review_template",
        "candidate_must_be_clean",
        "independent_review_required",
        "human_uat_required_for_e2_id_005",
        "release_or_promotion_authorized_by_candidate",
    }:
        failures.append("PIS-004A candidate procedure keys are not closed")
    elif candidate != {
        "focused_command": "make production-identity-storage-pis-004a-check",
        "independent_review_template": (
            "git worktree add --detach /tmp/ithildin-pis004a-review "
            "<candidate_commit> && make production-identity-storage-pis-004a-check"
        ),
        "candidate_must_be_clean": True,
        "independent_review_required": True,
        "human_uat_required_for_e2_id_005": True,
        "release_or_promotion_authorized_by_candidate": False,
    }:
        failures.append("PIS-004A candidate procedure is invalid")
    return failures


def _validate_standing_authority(value: object, failures: list[str]) -> None:
    if not isinstance(value, dict) or set(value) != {
        "architecture_path",
        "architecture_sha256",
        "threat_model_path",
        "threat_model_sha256",
        "e2_preparation_path",
        "e2_preparation_sha256",
        "e2_contract_path",
        "e2_contract_sha256",
        "e1_contract_path",
        "e1_contract_sha256",
        "pis003_authority_path",
        "pis003_authority_sha256",
        "pis003_next_action",
        "pis003_operational_collection_action_effective",
        "standing_architecture_reused",
        "competing_architecture_created",
    }:
        failures.append("PIS-004A standing-authority keys are not closed")
        return
    path_hash_pairs = (
        ("architecture_path", "architecture_sha256"),
        ("threat_model_path", "threat_model_sha256"),
        ("e2_preparation_path", "e2_preparation_sha256"),
        ("e2_contract_path", "e2_contract_sha256"),
        ("e1_contract_path", "e1_contract_sha256"),
        ("pis003_authority_path", "pis003_authority_sha256"),
    )
    for path_key, hash_key in path_hash_pairs:
        path_value = value.get(path_key)
        if not isinstance(path_value, str) or value.get(hash_key) != PROTECTED_HASHES.get(
            path_value
        ):
            failures.append(f"PIS-004A standing-authority digest is invalid: {path_key}")
    if (
        value.get("pis003_next_action") != PIS_WAIT_ACTION
        or value.get("pis003_operational_collection_action_effective") is not False
        or value.get("standing_architecture_reused") is not True
        or value.get("competing_architecture_created") is not False
    ):
        failures.append("PIS-004A standing authority competes with or bypasses PIS")


def _validate_dependency_gate(value: object, failures: list[str]) -> None:
    if not isinstance(value, dict) or set(value) != {
        "decision",
        "checked_at",
        "authlib",
        "joserfc",
        "expected_new_locked_packages",
        "existing_cryptography_floor_satisfies_candidate",
        "exact_version_vulnerability_screen",
        "vulnerability_screen_limit",
        "general_purpose_http_surface_allowed",
        "authlib_client_integration_allowed",
        "live_discovery_or_jwk_fetch_allowed",
        "dynamic_registration_allowed",
        "framework_session_authority_allowed",
        "hand_rolled_oidc_fallback_allowed",
        "rollback",
    }:
        failures.append("PIS-004A dependency-gate keys are not closed")
        return
    expected_packages = {
        "authlib": {
            "version": "1.7.2",
            "python_requirement": ">=3.10",
            "license": "BSD-3-Clause",
            "wheel_sha256": (
                "3e1faedc9d87e7d56a164eca3ccb6ace0d61b94abe83e92242f8dc8bba9b4a9f"
            ),
            "sdist_sha256": (
                "2cea25fefcd4e7173bdf1372c0afc265c8034b23a8cd5dcb6a9164b826c64231"
            ),
            "source": "https://github.com/authlib/authlib/tree/v1.7.2",
        },
        "joserfc": {
            "version": "1.7.4",
            "python_requirement": ">=3.10",
            "license": "BSD-3-Clause",
            "wheel_sha256": (
                "32d46c2cd5e3203c13e87a6c61333cab310b1ba80cd54b4c4f386a848a122463"
            ),
            "sdist_sha256": (
                "b3bc561672ae541b17a9237053b48a03dacddd92d68047b3ecdfb4b5714a88ed"
            ),
            "source": "https://github.com/authlib/joserfc/tree/v1.7.4",
        },
    }
    if (
        value.get("decision") != "approved_for_fixture_adapter_only"
        or value.get("checked_at") != "2026-07-29"
        or value.get("authlib") != expected_packages["authlib"]
        or value.get("joserfc") != expected_packages["joserfc"]
        or value.get("expected_new_locked_packages") != ["authlib", "joserfc"]
        or value.get("existing_cryptography_floor_satisfies_candidate") is not True
        or value.get("exact_version_vulnerability_screen") != "no_advisories_observed"
        or value.get("rollback") != "remove_exact_lock_delta_and_disable_fixture_adapter"
    ):
        failures.append("PIS-004A dependency provenance is invalid")
    for key in (
        "general_purpose_http_surface_allowed",
        "authlib_client_integration_allowed",
        "live_discovery_or_jwk_fetch_allowed",
        "dynamic_registration_allowed",
        "framework_session_authority_allowed",
        "hand_rolled_oidc_fallback_allowed",
    ):
        if value.get(key) is not False:
            failures.append(f"PIS-004A dependency gate permits forbidden behavior: {key}")


def _validate_persistence(value: object, failures: list[str]) -> None:
    if not isinstance(value, dict) or set(value) != {
        "backend",
        "coordinated_schema_target",
        "migration_mode",
        "minimum_writer_after_activation",
        "pre_migration_backup_required",
        "automatic_down_migration_allowed",
        "raw_oidc_code_persisted",
        "raw_access_token_persisted",
        "raw_id_token_persisted",
        "raw_refresh_token_persisted",
        "raw_claims_persisted",
        "raw_session_handle_persisted",
        "session_lookup_digest",
        "schema_removal_posture",
    }:
        failures.append("PIS-004A persistence contract keys are not closed")
        return
    if (
        value.get("backend") != "local_sqlite_only"
        or value.get("coordinated_schema_target") != "5"
        or value.get("minimum_writer_after_activation") != "5"
        or value.get("pre_migration_backup_required") is not True
        or value.get("session_lookup_digest") != "keyed_hmac_sha256"
        or value.get("schema_removal_posture") != "restore_pre_migration_backup_only"
    ):
        failures.append("PIS-004A persistence boundary is invalid")
    for key in (
        "automatic_down_migration_allowed",
        "raw_oidc_code_persisted",
        "raw_access_token_persisted",
        "raw_id_token_persisted",
        "raw_refresh_token_persisted",
        "raw_claims_persisted",
        "raw_session_handle_persisted",
    ):
        if value.get(key) is not False:
            failures.append(f"PIS-004A persistence permits forbidden material: {key}")


def _validate_safety_contract(value: object, failures: list[str]) -> None:
    if not isinstance(value, dict) or set(value) != {
        "identity_key",
        "principal_ids",
        "memberships",
        "identity_and_membership_generations",
        "caller_authority_fields_rejected",
        "session_handle",
        "session_audit_id_authenticates",
        "idle_and_absolute_expiry_required",
        "rotation_and_family_revocation_required",
        "generation_invalidation_required",
        "preauthentication_atomic_one_use_required",
        "allowed_origin_and_session_bound_csrf_required",
        "digest_key_generation_fail_closed",
        "authorization_server_state_only",
        "human_approval_by_node_or_service_allowed",
        "cross_organization_or_workspace_access_allowed",
        "cross_workspace_listing_or_bulk_enumeration_allowed",
        "safe_audit_forbidden_fields",
    }:
        failures.append("PIS-004A safety-contract keys are not closed")
        return
    if value.get("identity_key") != [
        "organization_id",
        "provider_configuration_id",
        "exact_issuer",
        "subject",
    ]:
        failures.append("PIS-004A exact identity key is invalid")
    required_true = (
        "idle_and_absolute_expiry_required",
        "rotation_and_family_revocation_required",
        "generation_invalidation_required",
        "preauthentication_atomic_one_use_required",
        "allowed_origin_and_session_bound_csrf_required",
        "digest_key_generation_fail_closed",
        "authorization_server_state_only",
    )
    if any(value.get(key) is not True for key in required_true):
        failures.append("PIS-004A safety contract weakens a required control")
    required_false = (
        "session_audit_id_authenticates",
        "human_approval_by_node_or_service_allowed",
        "cross_organization_or_workspace_access_allowed",
        "cross_workspace_listing_or_bulk_enumeration_allowed",
    )
    if any(value.get(key) is not False for key in required_false):
        failures.append("PIS-004A safety contract permits forbidden authority")


def _validate_repository(
    root: Path,
    contract: dict[str, Any],
    failures: list[str],
) -> None:
    if _git_one(root, "branch", "--show-current") != BRANCH:
        failures.append("PIS-004A is not on its exact isolated branch")
    if not _git_ok(root, "cat-file", "-e", f"{SOURCE_COMMIT}^{{commit}}"):
        failures.append("PIS-004A source commit is unavailable")
    elif _git_one(root, "rev-parse", f"{SOURCE_COMMIT}^{{tree}}") != SOURCE_TREE:
        failures.append("PIS-004A source tree identity changed")
    elif not _git_ok(root, "merge-base", "--is-ancestor", SOURCE_COMMIT, "HEAD"):
        failures.append("PIS-004A source commit is not an ancestor of HEAD")

    for relative, expected_hash in PROTECTED_HASHES.items():
        if _sha256(root / relative) != expected_hash:
            failures.append(f"PIS-004A changed protected standing authority: {relative}")

    e1 = _load_json(root / "docs/codex/enterprise-e1-completion-contract.json", failures)
    qualification = e1.get("qualification") if isinstance(e1, dict) else None
    if (
        not isinstance(qualification, dict)
        or qualification.get("human_uat_complete") is not False
        or e1.get("next_action") != "stop_for_human_uat"
    ):
        failures.append("PIS-004A does not preserve the E1 human-UAT stop line")

    pis_path = (
        root
        / "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-evidence-collection-authority.json"
    )
    pis = _load_json(pis_path, failures)
    pis_authority = pis.get("authority") if isinstance(pis, dict) else None
    if (
        pis.get("next_required_action") != PIS_WAIT_ACTION
        or not isinstance(pis_authority, dict)
        or pis_authority.get("operational_collection_action_effective") is not False
        or pis_authority.get("production_identity_allowed") is not False
        or pis_authority.get("runtime_postgres_allowed") is not False
        or pis_authority.get("database_connections_allowed") is not False
    ):
        failures.append("PIS-004A routes around the PIS-003 external-input wait")

    if _sha256(root / "tool-manifests.lock.json") != (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ) or _tool_count(root) != 24:
        failures.append("PIS-004A changed the exact 24-tool manifest lock")
    _validate_dependency_lock(root, failures)

    changed = _changed_paths(root)
    unexpected = sorted(changed - set(EXPECTED_ALLOWED_PATHS))
    if unexpected:
        failures.append("PIS-004A changed paths outside its exact lane: " + ", ".join(unexpected))

    doc = _read(root / DOC_REL, failures)
    for phrase in (
        "Status: bounded implementation authorized; implementation in progress.",
        "Current governed tool count: exactly `24`.",
        PIS_WAIT_ACTION,
        "E1 contract still records `human_uat_complete: false`",
        "not live IdP integration",
        "make production-identity-storage-pis-004a-check",
    ):
        if phrase not in doc:
            failures.append(f"PIS-004A document is missing required phrase: {phrase}")
    doc_name = DOC_REL.as_posix()
    for source_name, relative, expected in (
        ("README", "README.md", doc_name),
        ("review docs", "scripts/review_docs.py", doc_name),
        ("docs site", "scripts/build_docs_site.py", doc_name),
        ("review index", "docs/codex/review-docs-index.md", DOC_REL.name),
        ("Makefile", "Makefile", "production-identity-storage-pis-004a-check:"),
    ):
        if expected not in _read(root / relative, failures):
            failures.append(f"PIS-004A document or gate is missing from {source_name}")

    standing = contract.get("standing_authority")
    if not isinstance(standing, dict) or standing.get("pis003_next_action") != PIS_WAIT_ACTION:
        failures.append("PIS-004A repository contract changed the standing PIS route")


def _validate_dependency_lock(root: Path, failures: list[str]) -> None:
    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        source_pyproject = tomllib.loads(
            _git_output(root, "show", f"{SOURCE_COMMIT}:pyproject.toml")
        )
        source_lock = tomllib.loads(
            _git_output(root, "show", f"{SOURCE_COMMIT}:uv.lock")
        )
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        failures.append(f"PIS-004A dependency files cannot be loaded: {exc}")
        return

    expected_direct = {
        "authlib==1.7.2",
        "joserfc==1.7.4",
    }
    current_direct = set(pyproject.get("project", {}).get("dependencies", []))
    source_direct = set(source_pyproject.get("project", {}).get("dependencies", []))
    if (
        current_direct - source_direct != expected_direct
        or source_direct - current_direct
    ):
        failures.append("PIS-004A pyproject dependency delta is not exact")

    current_packages = _packages_by_name(lock)
    source_packages = _packages_by_name(source_lock)
    if (
        set(current_packages) - set(source_packages) != {"authlib", "joserfc"}
        or set(source_packages) - set(current_packages)
    ):
        failures.append("PIS-004A locked package delta is not exactly Authlib and JOSERFC")
        return
    for name, source_package in source_packages.items():
        if name == "ithildin":
            continue
        if current_packages.get(name) != source_package:
            failures.append(f"PIS-004A changed inherited locked package: {name}")

    authlib = current_packages.get("authlib", {})
    joserfc = current_packages.get("joserfc", {})
    if (
        authlib.get("version") != "1.7.2"
        or authlib.get("source") != {"registry": "https://pypi.org/simple"}
        or _package_hashes(authlib)
        != {
            "sha256:2cea25fefcd4e7173bdf1372c0afc265c8034b23a8cd5dcb6a9164b826c64231",
            "sha256:3e1faedc9d87e7d56a164eca3ccb6ace0d61b94abe83e92242f8dc8bba9b4a9f",
        }
        or _dependency_names(authlib) != {"cryptography", "joserfc"}
        or joserfc.get("version") != "1.7.4"
        or joserfc.get("source") != {"registry": "https://pypi.org/simple"}
        or _package_hashes(joserfc)
        != {
            "sha256:b3bc561672ae541b17a9237053b48a03dacddd92d68047b3ecdfb4b5714a88ed",
            "sha256:32d46c2cd5e3203c13e87a6c61333cab310b1ba80cd54b4c4f386a848a122463",
        }
        or _dependency_names(joserfc) != {"cryptography"}
    ):
        failures.append("PIS-004A locked dependency provenance is not exact")

    current_root = current_packages.get("ithildin")
    source_root = source_packages.get("ithildin")
    if not isinstance(current_root, dict) or not isinstance(source_root, dict):
        failures.append("PIS-004A root lock package is unavailable")
        return
    normalized_root = json.loads(json.dumps(current_root))
    dependencies = normalized_root.get("dependencies")
    metadata = normalized_root.get("metadata")
    if not isinstance(dependencies, list) or not isinstance(metadata, dict):
        failures.append("PIS-004A root lock package is malformed")
        return
    source_dependencies = source_root.get("dependencies")
    if (
        not isinstance(source_dependencies, list)
        or {
            str(item["name"])
            for item in dependencies
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        - {
            str(item["name"])
            for item in source_dependencies
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        != {"authlib", "joserfc"}
    ):
        failures.append("PIS-004A root dependency linkage is not exact")
    normalized_root["dependencies"] = [
        item
        for item in dependencies
        if not isinstance(item, dict) or item.get("name") not in {"authlib", "joserfc"}
    ]
    requires_dist = metadata.get("requires-dist")
    if not isinstance(requires_dist, list):
        failures.append("PIS-004A root lock metadata is malformed")
        return
    source_metadata = source_root.get("metadata")
    source_requires_dist = (
        source_metadata.get("requires-dist")
        if isinstance(source_metadata, dict)
        else None
    )
    if (
        not isinstance(source_requires_dist, list)
        or {
            (str(item["name"]), str(item.get("specifier", "")))
            for item in requires_dist
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        - {
            (str(item["name"]), str(item.get("specifier", "")))
            for item in source_requires_dist
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        != {("authlib", "==1.7.2"), ("joserfc", "==1.7.4")}
    ):
        failures.append("PIS-004A root dependency metadata is not exact")
    metadata["requires-dist"] = [
        item
        for item in requires_dist
        if not isinstance(item, dict) or item.get("name") not in {"authlib", "joserfc"}
    ]
    if normalized_root != source_root:
        failures.append("PIS-004A root lock delta exceeds the exact dependency pins")


def _packages_by_name(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = lock.get("package")
    if not isinstance(packages, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            return {}
        name = str(package["name"])
        if name in result:
            return {}
        result[name] = package
    return result


def _dependency_names(package: dict[str, Any]) -> set[str]:
    dependencies = package.get("dependencies")
    if not isinstance(dependencies, list):
        return set()
    return {
        str(item["name"])
        for item in dependencies
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def _package_hashes(package: dict[str, Any]) -> set[str]:
    hashes: set[str] = set()
    sdist = package.get("sdist")
    if isinstance(sdist, dict) and isinstance(sdist.get("hash"), str):
        hashes.add(str(sdist["hash"]))
    wheels = package.get("wheels")
    if isinstance(wheels, list):
        hashes.update(
            str(item["hash"])
            for item in wheels
            if isinstance(item, dict) and isinstance(item.get("hash"), str)
        )
    return hashes


def _require_keys(
    value: dict[str, Any],
    expected: set[str],
    label: str,
    failures: list[str],
) -> None:
    if set(value) != expected:
        failures.append(f"PIS-004A {label} keys are not closed")


def _changed_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only", f"{SOURCE_COMMIT}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        paths.update(line for line in _git_output(root, *args).splitlines() if line)
    return paths


def _tool_count(root: Path) -> int:
    lock = _load_json(root / "tool-manifests.lock.json", [])
    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    return len(manifests) if isinstance(manifests, list) else -1


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"required JSON cannot be loaded: {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"required JSON is not an object: {path.name}")
        return {}
    return value


def _read(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"required text cannot be loaded: {path.name}: {exc}")
        return ""


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _git_ok(root: Path, *args: str) -> bool:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    ).returncode == 0


def _git_one(root: Path, *args: str) -> str:
    return _git_output(root, *args).strip()


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin PIS-004A local identity foundation check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_id: {report['decision_id']}",
        f"status: {report['status']}",
        f"source_commit: {report['source_commit']}",
        f"source_tree: {report['source_tree']}",
        f"branch: {report['branch']}",
        f"tool_count: {report['tool_count']}",
        f"pis003_next_action: {report['pis003_next_action']}",
        "e1_human_uat_complete: false",
        "live_idp_allowed: false",
        "runtime_postgres_allowed: false",
        f"next_action: {report['next_action']}",
    ]
    lines.extend(f"failure: {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
