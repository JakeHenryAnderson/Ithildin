"""Validate the bounded PIS-003 connection-evidence implementation candidate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    production_identity_storage_pis_003_sd_pg_001_connection_evidence as harness,
)
from scripts import (  # noqa: E402
    production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_internal_review_check,
    review_docs,  # noqa: E402
)

gate_review = (
    production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_internal_review_check
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-implementation-record.md"
)
DOC_SHA256 = "2c7da134e8a01f18b64f5fdc3892ef049d1530b2a1e8babde8735830f990f020"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-implementation-authority.json"
)
CONTRACT_SHA256 = "3c65225f537bc50fa5208a89dfb10b9178625f8fbe690f6361682fde881e14e6"
HARNESS_REL = "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py"
TARGET = "production-identity-storage-pis-003-sd-pg-001-connection-evidence-implementation-check"
BASELINE_COMMIT = "c84c9f9f97ee9716e1466944e26e206e85b4b729"

EXPECTED_PATHS = {
    "Makefile",
    "README.md",
    "db/alembic/env.py",
    "docs/codex/post-rc-decision-register.md",
    CONTRACT_REL,
    DOC_REL,
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    HARNESS_REL,
    ("scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_check.py"),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "connection_evidence_implementation_check.py"
    ),
    ("scripts/production_identity_storage_pis_003_sd_pg_001_implementation_check.py"),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "implementation_internal_review_check.py"
    ),
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
    "tests/test_storage_schema_import.py",
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
    "pyproject.toml": ("8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627"),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}
EXPECTED_IMPLEMENTATION_CONTRACT = {
    "harness_location": HARNESS_REL,
    "harness_scope": "test_only_not_runtime_importable",
    "execution_authority_active": False,
    "main_mode": "check_only",
    "dsn_source": "ITHILDIN_PIS3_TEST_DSN_environment_only_after_future_gate",
    "binding_key_source": ("ITHILDIN_PIS3_TARGET_BINDING_KEY_environment_only_after_future_gate"),
    "driver_import_deferred_until_after_preflight": True,
    "psycopg_impl_required": "python",
    "engine": "synchronous_sqlalchemy_nullpool",
    "caller_owned_alembic_connection": True,
    "caller_owned_outer_transaction": True,
    "commit_allowed": False,
    "explicit_rollback_required": True,
    "post_rollback_absence_check_required": True,
    "immutable_sqlite_source_reader": True,
    "source_digest_before_and_after": True,
    "canonical_dsn_parser": True,
    "hmac_target_binding": True,
    "ambient_libpq_rejection": "all_present_keys_matching_^PG[A-Z0-9_]+$",
    "external_ed25519_receipt_verification": True,
    "named_discard_owner_binding": True,
    "native_libpq_and_tls_probe": True,
    "closed_failure_evidence": True,
    "output_tree_secret_scan": True,
    "negative_scenario_one_attempt_bound": True,
    "original_transaction_identity_revalidated": True,
    "binding_secrets_consumed_before_driver_boundary": True,
    "loaded_tls_symbol_owner_exact": True,
    "marker_commitment_bound_complete_tree_scan": True,
    "public_exception_boundary_closed": True,
    "dsn_identity_control_characters_rejected": True,
    "contextual_receipt_failure_stages": True,
    "loaded_libpq_and_libssl_symbol_owners_exact": True,
    "source_digest_all_engine_outcomes_and_discard": True,
    "service_or_container_lifecycle": False,
    "database_or_role_creation": False,
    "runtime_imports": False,
}
EXPECTED_VALIDATION_EVIDENCE = {
    "storage_schema_import_tests": 78,
    "psycopg_loaded_during_tests": False,
    "database_connection_attempted": False,
    "online_migration_executed": False,
    "driver_environment_read": False,
    "synthetic_receipts_only": True,
    "real_dsn_used": False,
    "tool_count_unchanged": True,
}
EXPECTED_AUTHORITY = {
    "connection_evidence_implementation_recorded": True,
    "connection_evidence_candidate_complete": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": False,
    "environment_receipt_implementation_complete": True,
    "test_harness_implementation_complete": True,
    "synthetic_snapshot_reader_implementation_complete": True,
    "online_alembic_caller_connection_implementation_complete": True,
    "failure_evidence_implementation_complete": True,
    "execution_preflight_implementation_complete": True,
    "native_dependency_probe_implementation_complete": True,
    "target_discard_finalizer_implementation_complete": True,
    "secret_scan_implementation_complete": True,
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
REQUIRED_PHRASES = [
    ("Status: bounded test-only `PIS-003-SD-PG-001` connection-evidence implementation candidate"),
    ("`PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-IMPLEMENTATION`."),
    f"Implementation baseline commit: `{BASELINE_COMMIT}`.",
    "Current governed tool count: `24`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    f"make {TARGET}",
    "`EXECUTION_AUTHORITY_ACTIVE` is `false`.",
    "No real DSN or target-binding key was read.",
    "Psycopg was not imported.",
    "The first exact-candidate review of `7c6b5de5ab8055bfbe1d0384c6b1df0d372f4e03`",
    "The repeat exact-candidate review of `86fa34214f569d7380157f136a3963cb04204575`",
    "The focused storage/schema/import suite contains `78` passing tests.",
    "`connection_evidence_candidate_complete: true`",
    "`exact_candidate_source_review_complete: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`uat_complete: false`",
    "The next required action is",
    "`review_pis_003_sd_pg_001_connection_evidence_candidate_exact_commit`",
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


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "implementation_id",
        "parent_review",
        "implementation_baseline_commit",
        "implementation_outcome",
        "evidence_slice",
        "tool_count",
        "implementation_path_inventory",
        "protected_hashes",
        "implementation_contract",
        "validation_evidence",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 connection implementation contract keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "implementation_id": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-IMPLEMENTATION"
        ),
        "parent_review": ("PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE-REVIEW"),
        "implementation_baseline_commit": BASELINE_COMMIT,
        "implementation_outcome": (
            "test_only_connection_evidence_candidate_complete_exact_review_"
            "pending_execution_blocked"
        ),
        "evidence_slice": "PIS-003-SD-PG-001-CONNECTION-EVIDENCE",
        "tool_count": 24,
        "next_required_action": (
            "review_pis_003_sd_pg_001_connection_evidence_candidate_exact_commit"
        ),
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 connection implementation field {key} is not exact")
    if contract.get("implementation_path_inventory") != sorted(EXPECTED_PATHS):
        failures.append("PIS-003 connection implementation path inventory is not exact")
    if contract.get("protected_hashes") != EXPECTED_PROTECTED_HASHES:
        failures.append("PIS-003 connection implementation protected hashes are not exact")
    implementation = contract.get("implementation_contract")
    if (
        implementation != EXPECTED_IMPLEMENTATION_CONTRACT
        or not isinstance(implementation, dict)
        or any(type(value) not in {str, bool} for value in implementation.values())
    ):
        failures.append("PIS-003 connection implementation facts are not exact")
    evidence = contract.get("validation_evidence")
    if (
        evidence != EXPECTED_VALIDATION_EVIDENCE
        or not isinstance(evidence, dict)
        or any(type(value) not in {int, bool} for value in evidence.values())
    ):
        failures.append("PIS-003 connection validation evidence is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 connection implementation authority is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 connection implementation document is not UTF-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc_text:
            failures.append(f"PIS-003 connection implementation document missing: {phrase}")
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 connection implementation document digest does not match")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 connection implementation contract digest does not match")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)
    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_exists:
        failures.append("PIS-003 connection implementation baseline is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 connection implementation baseline is not an ancestor")
    candidate_paths = _candidate_paths(repo_root)
    candidate_inventory_exact = candidate_paths == EXPECTED_PATHS
    if not candidate_inventory_exact:
        failures.append("PIS-003 connection implementation candidate inventory is not exact")
    protected_hashes_match = all(
        _sha256(repo_root / path) == digest for path, digest in EXPECTED_PROTECTED_HASHES.items()
    )
    if not protected_hashes_match:
        failures.append("PIS-003 connection implementation protected hashes changed")
    gate_report = gate_review.build_report(repo_root)
    gate_review_valid = bool(
        gate_report.get("valid")
        and gate_report.get("connection_evidence_implementation_allowed") is True
        and gate_report.get("database_connections_allowed") is False
        and gate_report.get("test_harness_execution_allowed") is False
    )
    if not gate_review_valid:
        failures.append("PIS-003 connection gate review prerequisite is invalid")
    harness_semantics_valid = _harness_semantics_valid(repo_root)
    if not harness_semantics_valid:
        failures.append("PIS-003 connection harness semantics are invalid")
    alembic_caller_connection_valid = _alembic_caller_connection_valid(repo_root)
    if not alembic_caller_connection_valid:
        failures.append("PIS-003 caller-owned Alembic connection path is invalid")
    runtime_imports_absent = _runtime_imports_absent(repo_root)
    if not runtime_imports_absent:
        failures.append("PIS-003 connection harness leaked into runtime imports")
    harness_check = harness._render_check()
    harness_refuses_execution = bool(
        harness_check.get("valid") is True
        and harness_check.get("execution_authority_active") is False
        and harness_check.get("psycopg_imported") is False
        and harness_check.get("dsn_environment_read") is False
        and harness_check.get("engine_constructed") is False
        and harness_check.get("database_connection_attempted") is False
        and harness_check.get("migration_executed") is False
    )
    if not harness_refuses_execution:
        failures.append("PIS-003 connection harness does not refuse execution")
    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append("PIS-003 connection implementation tool count changed")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 connection implementation wiring is incomplete")
    valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "implementation_document": DOC_REL,
        "implementation_id": contract.get("implementation_id") if valid else "invalid",
        "implementation_outcome": (contract.get("implementation_outcome") if valid else "invalid"),
        "implementation_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_commit": _git_one(repo_root, "rev-parse", "HEAD"),
        "candidate_path_count": len(candidate_paths),
        "candidate_inventory_exact": candidate_inventory_exact,
        "implementation_document_hash_matches": doc_hash == DOC_SHA256,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "protected_hashes_match": protected_hashes_match,
        "gate_review_valid": gate_review_valid,
        "harness_semantics_valid": harness_semantics_valid,
        "alembic_caller_connection_valid": alembic_caller_connection_valid,
        "runtime_imports_absent": runtime_imports_absent,
        "harness_refuses_execution": harness_refuses_execution,
        "psycopg_driver_loaded": "psycopg" in sys.modules,
        "database_connection_attempted": False,
        "online_migration_executed": False,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (
            contract.get("next_required_action") if valid else "invalid_implementation"
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "implementation_document",
        "implementation_id",
        "implementation_outcome",
        "implementation_baseline_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "candidate_commit",
        "candidate_path_count",
        "candidate_inventory_exact",
        "implementation_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "gate_review_valid",
        "harness_semantics_valid",
        "alembic_caller_connection_valid",
        "runtime_imports_absent",
        "harness_refuses_execution",
        "psycopg_driver_loaded",
        "database_connection_attempted",
        "online_migration_executed",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 connection-evidence implementation check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _harness_semantics_valid(repo_root: Path) -> bool:
    source = _read_text(repo_root / HARNESS_REL)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    if any(name == "psycopg" or name.startswith("psycopg.") for name in imports):
        return False
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required_functions = {
        "validate_execution_preflight",
        "read_frozen_snapshot",
        "parse_canonical_dsn",
        "validate_dsn_target_binding",
        "reject_ambient_libpq_environment",
        "verify_external_receipt",
        "execute_connection_evidence",
        "finalize_discard_receipt",
        "scan_output_tree_for_secrets",
        "_validate_loaded_native_identity",
        "_execute_validated_preflight",
        "_run_network_negative_attempt",
        "_run_migration_import_attempt",
        "_rollback_original_transaction",
        "_require_original_transaction",
        "_require_source_unchanged",
        "secret_marker_commitment",
    }
    if not required_functions <= set(functions):
        return False
    execute = functions["execute_connection_evidence"]
    first_statement = execute.body[0] if execute.body else None
    authority_first = bool(
        isinstance(first_statement, ast.Expr)
        and isinstance(first_statement.value, ast.Constant)
        and isinstance(first_statement.value.value, str)
        and len(execute.body) > 1
        and isinstance(execute.body[1], ast.If)
    )
    execute_source = ast.get_source_segment(source, execute) or ""
    implementation_source = "\n".join(
        ast.get_source_segment(source, functions[name]) or ""
        for name in (
            "execute_connection_evidence",
            "_execute_validated_preflight",
            "_run_network_negative_attempt",
            "_run_migration_import_attempt",
            "_rollback_original_transaction",
            "_require_original_transaction",
            "_require_source_unchanged",
            "finalize_discard_receipt",
            "scan_output_tree_for_secrets",
            "secret_marker_commitment",
        )
    )
    return bool(
        authority_first
        and "if not EXECUTION_AUTHORITY_ACTIVE" in execute_source
        and "validate_execution_preflight" in execute_source
        and "reject_ambient_libpq_environment" in implementation_source
        and "poolclass=NullPool" in implementation_source
        and ".rollback()" in implementation_source
        and ".dispose()" in implementation_source
        and ".pop(DSN_ENV" in implementation_source
        and ".pop(BINDING_KEY_ENV" in implementation_source
        and "connection.get_transaction() is not transaction" in implementation_source
        and "NETWORK_NEGATIVE_SCENARIOS" in implementation_source
        and "secret_marker_commitment" in implementation_source
        and "expected_commitment=preflight.secret_scan_marker_commitment" in implementation_source
        and 'raise ConnectionEvidenceError(category, "connection") from None' in execute_source
        and '_loaded_symbol_library_path(declared_libpq_path, "PQlibVersion")' in source
        and '_loaded_symbol_library_path(libpq_path, "SSL_CTX_new")' in source
        and implementation_source.count("_require_source_unchanged(preflight)") >= 2
        and "_contains_control(user)" in source
        and "_contains_control(database)" in source
        and 'category="receipt_authenticity_failed"' in source
        and 'failure_stage="discard"' in source
        and "if path.is_symlink()" in implementation_source
        and "not stat.S_ISREG" in implementation_source
        and "EXECUTION_AUTHORITY_ACTIVE = False" in source
        and 'DSN_ENV = "ITHILDIN_PIS3_TEST_DSN"' in source
        and 'BINDING_KEY_ENV = "ITHILDIN_PIS3_TARGET_BINDING_KEY"' in source
        and "create_engine(" in implementation_source
        and "postgresql://" not in source
    )


def _alembic_caller_connection_valid(repo_root: Path) -> bool:
    source = _read_text(repo_root / "db/alembic/env.py")
    return bool(
        'config.attributes.get("connection")' in source
        and "isinstance(connection, Connection)" in source
        and "connection.in_transaction()" in source
        and "connection.in_nested_transaction()" in source
        and "context.configure(" in source
        and "connection=connection" in source
        and "create_engine" not in source
        and "engine_from_config" not in source
        and "sqlalchemy.url" not in source
        and "psycopg" not in source
    )


def _runtime_imports_absent(repo_root: Path) -> bool:
    needle = "production_identity_storage_pis_003_sd_pg_001_connection_evidence"
    protected = [
        "apps/api/src/ithildin_api/app.py",
        "apps/api/src/ithildin_api/config.py",
        "apps/api/src/ithildin_api/sandbox_descriptors.py",
        "apps/api/src/ithildin_api/storage.py",
        "apps/node/src/ithildin_node/client.py",
    ]
    return all(needle not in _read_text(repo_root / path) for path in protected)


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read_text(repo_root / "Makefile")
    readme = _read_text(repo_root / "README.md")
    guardrails = _read_text(repo_root / "scripts/release_guardrails.py")
    docs_site = _read_text(repo_root / "scripts/build_docs_site.py")
    index = _read_text(repo_root / "docs/codex/review-docs-index.md")
    return bool(
        f"{TARGET}:" in makefile
        and f"release-check: {TARGET}" in makefile
        and f"make {TARGET}" in readme
        and DOC_REL in review_docs.REVIEW_DOCS
        and DOC_REL in docs_site
        and TARGET in guardrails
        and "Connection Evidence Implementation Record" in index
    )


def _candidate_paths(repo_root: Path) -> set[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", BASELINE_COMMIT],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.returncode != 0 or untracked.returncode != 0:
        return set()
    return {
        line.strip()
        for line in (tracked.stdout + "\n" + untracked.stdout).splitlines()
        if line.strip()
    }


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"PIS-003 connection implementation contract cannot be loaded: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 connection implementation contract must be an object"]
    return payload, []


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        manifests = payload.get("manifests")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return -1
    return len(manifests) if isinstance(manifests, list) else -1


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


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


def _git_one(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


if __name__ == "__main__":
    raise SystemExit(main())
