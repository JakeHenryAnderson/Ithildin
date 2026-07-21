"""Validate the bounded offline PIS-003 SD-PG-001 implementation candidate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_pis_003_sd_pg_001_implementation_gate_check,
    production_identity_storage_pis_003_sd_pg_001_implementation_gate_internal_review_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-record.md"
DOC_TITLE = "Production Identity And Storage PIS-003 SD-PG-001 Offline Implementation Record"
DOC_SHA256 = "d798e0f8c8ac39623534194f0a6c9a8737f4867e333535817d4d66bb9f269ff8"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-authority.json"
)
CONTRACT_SHA256 = "0cee5b95a31e6b215b8481e03aacc85b9d9a797fc362d218e4070b49bd2fd888"
TARGET = "production-identity-storage-pis-003-sd-pg-001-implementation-check"
BASELINE_COMMIT = "21cc758e2dd438c10f852574528f3ea971825b55"

EXPECTED_PATHS = [
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

EXPECTED_ARTIFACT_HASHES = {
    "apps/api/src/ithildin_api/storage_import.py": (
        "e1a29c0f994e7bfe1a7b7b0677bba881fd703c5f360ae12877de40b6e1c30ab9"
    ),
    "apps/api/src/ithildin_api/storage_schema.py": (
        "5e1e087f532e40b725a00ed87475a3d52093dbea33e2b5eacb8540ebadad62c4"
    ),
    "db/alembic/alembic.ini": (
        "ff49463eb16e95c6e8a67c57f305cc6787a5bd09f888d35ffac7b7a13a519a5f"
    ),
    "db/alembic/env.py": (
        "38ba3adbc686bceefbe50904761f073c50c204de7bd2b6ffa780f5ac93fe3c23"
    ),
    "db/alembic/script.py.mako": (
        "39f642cd27bc28f704e0a219da647ed744e1b9f70647914232c7c6e9b3196533"
    ),
    "db/alembic/versions/0001_sandbox_descriptors.py": (
        "40daefdf8882de79bd6ac68f19b0733c32877f19540c8bab1cb784534c93178e"
    ),
    "pyproject.toml": "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627",
    "tests/test_storage_schema_import.py": (
        "15ac644d9d578e0e06eae33736445574a3c1d909dd3e328cc574590d98f947fb"
    ),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
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
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

EXPECTED_AUTHORITY = {
    "pis_003_sd_pg_001_offline_implementation_recorded": True,
    "pis_003_sd_pg_001_offline_candidate_complete": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": False,
    "dependency_lock_delta_implemented": True,
    "offline_schema_implemented": True,
    "offline_migration_implemented": True,
    "validated_importer_implemented": True,
    "refusing_test_harness_contract_implemented": True,
    "psycopg_plain_sync_dependency_installed": True,
    "psycopg_plain_sync_use_allowed": False,
    "test_harness_execution_allowed": False,
    "isolated_test_connection_allowed": False,
    "database_connections_allowed": False,
    "migration_execution_allowed": False,
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
    "connection_evidence_gate_preparation_allowed": False,
    "connection_evidence_gate_required": True,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
    "uat_required_now": False,
}

EXPECTED_DEPENDENCY_CONTRACT = {
    "dependency_group": "pis3",
    "default_enabled": False,
    "direct_requirements": ["SQLAlchemy==2.0.51", "alembic==1.18.5", "psycopg==3.3.4"],
    "added_package_count": 7,
    "changed_existing_packages": [],
    "removed_packages": [],
    "driver_loaded_or_used": False,
}

EXPECTED_SCHEMA_CONTRACT = {
    "aggregate": "sandbox_descriptors",
    "application_table_count": 1,
    "column_count": 6,
    "check_constraint_count": 5,
    "application_index_count": 1,
    "revision": "0001_sandbox_descriptors",
    "head_count": 1,
    "json_type": "postgresql_jsonb",
    "timestamps": "timezone_aware_utc",
    "online_mode_allowed": False,
    "downgrade_allowed": False,
}

EXPECTED_IMPORT_CONTRACT = {
    "source_validation_before_connection": True,
    "source_field_count": 6,
    "canonical_json_required": True,
    "current_descriptor_payload_contract_required": True,
    "strict_canonical_utc_required": True,
    "duplicate_json_keys_rejected": True,
    "duplicate_descriptor_ids_rejected": True,
    "caller_owned_connection_only": True,
    "postgresql_dialect_required": True,
    "outer_transaction_required": True,
    "nested_transaction_allowed": False,
    "empty_target_required": True,
    "stable_order_key": "descriptor_id",
    "importer_commit_or_rollback_allowed": False,
    "transparent_retry_allowed": False,
    "in_place_repair_allowed": False,
    "receipt_contains_dsn_or_credentials": False,
}

EXPECTED_HARNESS_CONTRACT = {
    "path": "tests/test_storage_schema_import.py",
    "external_dsn_parameter_declared": True,
    "pool_class": "sqlalchemy.pool.NullPool",
    "create_engine_present": False,
    "execution_disposition": "always_raise_connection_evidence_gate_required",
    "invoked": False,
    "connection_attempted": False,
    "migration_executed_online": False,
}

EXPECTED_ROLLBACK = {
    "disposition": "revert_exact_candidate_and_discard_isolated_target_before_activation",
    "receipt_contract_implemented": True,
    "exact_candidate_commit_required": True,
    "safe_target_label_required": True,
    "bound_before_connection_required": True,
    "live_receipt_materialized": False,
    "live_receipt_reason": "no_target_or_connection_authorized",
    "source_sqlite_modified": False,
    "activation_allowed": False,
}

REQUIRED_PHRASES = [
    (
        "Status: bounded offline `PIS-003-SD-PG-001` implementation candidate complete; "
        "exact-candidate source review pending."
    ),
    "Implementation ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION`.",
    f"Implementation baseline commit: `{BASELINE_COMMIT}`.",
    ("`offline_implementation_complete_connection_evidence_gate_pending_exact_source_review`."),
    "Current governed tool count: `24`.",
    "`pis_003_sd_pg_001_offline_implementation_recorded: true`",
    "`pis_003_sd_pg_001_offline_candidate_complete: true`",
    "`exact_candidate_source_review_complete: false`",
    "`psycopg_plain_sync_use_allowed: false`",
    "`test_harness_execution_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`connection_evidence_gate_required: true`",
    "The next required action is `review_pis_003_sd_pg_001_offline_candidate_exact_commit`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    f"make {TARGET}",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def validate_document(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [
        f"PIS-003 offline implementation record is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "implementation_id",
        "parent_gate_review",
        "implementation_baseline_commit",
        "implementation_outcome",
        "tool_count",
        "implementation_document_sha256",
        "implementation_path_inventory",
        "implementation_artifact_hashes",
        "dependency_contract",
        "schema_contract",
        "import_contract",
        "test_harness_contract",
        "rollback",
        "protected_hashes",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 offline implementation contract keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "implementation_id": ("PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION"),
        "parent_gate_review": ("PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE-REVIEW"),
        "implementation_baseline_commit": BASELINE_COMMIT,
        "implementation_outcome": (
            "offline_implementation_complete_connection_evidence_gate_pending_exact_source_review"
        ),
        "tool_count": 24,
        "implementation_document_sha256": DOC_SHA256,
        "next_required_action": "review_pis_003_sd_pg_001_offline_candidate_exact_commit",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 offline implementation field {key} is not {expected!r}")
    if type(contract.get("tool_count")) is not int:
        failures.append("PIS-003 offline implementation tool_count must be an exact integer")
    exact_objects = {
        "implementation_path_inventory": EXPECTED_PATHS,
        "implementation_artifact_hashes": EXPECTED_ARTIFACT_HASHES,
        "dependency_contract": EXPECTED_DEPENDENCY_CONTRACT,
        "schema_contract": EXPECTED_SCHEMA_CONTRACT,
        "import_contract": EXPECTED_IMPORT_CONTRACT,
        "test_harness_contract": EXPECTED_HARNESS_CONTRACT,
        "rollback": EXPECTED_ROLLBACK,
        "protected_hashes": EXPECTED_PROTECTED_HASHES,
    }
    for key, expected in exact_objects.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 offline implementation {key} is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 offline implementation authority is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 offline implementation record is not UTF-8")
    failures.extend(validate_document(doc_text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 offline implementation record does not match its closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 offline implementation contract does not match its closed digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_exists:
        failures.append("PIS-003 offline implementation baseline is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 offline implementation baseline is not an ancestor of HEAD")

    candidate_paths = _candidate_paths(repo_root)
    candidate_inventory_exact = candidate_paths == set(EXPECTED_PATHS)
    if not candidate_inventory_exact:
        failures.append("PIS-003 offline implementation path inventory is not exact")

    artifact_hashes_match = True
    for path, expected_hash in EXPECTED_ARTIFACT_HASHES.items():
        if hashlib.sha256(_read_bytes(repo_root / path)).hexdigest() != expected_hash:
            artifact_hashes_match = False
            failures.append(f"PIS-003 offline implementation artifact hash mismatch: {path}")

    protected_hashes_match = True
    for path, expected_hash in EXPECTED_PROTECTED_HASHES.items():
        if hashlib.sha256(_read_bytes(repo_root / path)).hexdigest() != expected_hash:
            protected_hashes_match = False
            failures.append(f"PIS-003 offline implementation protected hash mismatch: {path}")

    dependency_contract_valid = _dependency_contract_valid(repo_root)
    if not dependency_contract_valid:
        failures.append("PIS-003 offline dependency group or lock transition is not exact")

    gate_review_validator = (
        production_identity_storage_pis_003_sd_pg_001_implementation_gate_internal_review_check
    )
    gate_review = gate_review_validator.build_report(repo_root)
    gate_review_valid = bool(
        gate_review.get("valid")
        and gate_review.get("review_disposition") == "cleared_for_offline_implementation_only"
        and gate_review.get("pis_003_sd_pg_001_implementation_allowed")
        and gate_review.get("dependency_changes_allowed")
        and not gate_review.get("database_connections_allowed")
        and not gate_review.get("migration_execution_allowed")
    )
    if not gate_review_valid:
        failures.append("PIS-003 gate review does not authorize the offline implementation")

    gate = production_identity_storage_pis_003_sd_pg_001_implementation_gate_check.build_report(
        repo_root
    )
    gate_transition_valid = bool(
        gate.get("valid")
        and gate.get("dependency_transition_state") == "post_review_implementation"
    )
    if not gate_transition_valid:
        failures.append("PIS-003 exact reviewed dependency transition is not valid")

    schema_valid, offline_sql_deterministic, alembic_head_count = _schema_evidence(repo_root)
    if not schema_valid:
        failures.append("PIS-003 offline schema contract is not exact")
    if not offline_sql_deterministic:
        failures.append("PIS-003 offline PostgreSQL SQL is not deterministic")
    if alembic_head_count != 1:
        failures.append(f"PIS-003 Alembic head count is {alembic_head_count}, expected 1")

    source_boundaries_valid, harness_refuses_execution = _source_boundaries(repo_root)
    if not source_boundaries_valid:
        failures.append("PIS-003 importer or runtime source boundary is invalid")
    if not harness_refuses_execution:
        failures.append("PIS-003 test harness contract does not fail closed")
    driver_loaded = "psycopg" in sys.modules
    if driver_loaded:
        failures.append("PIS-003 offline validation loaded the Psycopg driver")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-003 offline implementation tool count is {tool_count}, expected 24")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 offline implementation wiring is incomplete")

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
        "implementation_document_sha256": doc_hash,
        "implementation_document_hash_matches": doc_hash == DOC_SHA256,
        "authority_contract": CONTRACT_REL,
        "authority_contract_sha256": contract_hash,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "implementation_id": contract.get("implementation_id") if valid else "invalid",
        "implementation_outcome": contract.get("implementation_outcome") if valid else "invalid",
        "implementation_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_inventory_exact": candidate_inventory_exact,
        "candidate_path_count": len(candidate_paths),
        "artifact_hashes_match": artifact_hashes_match,
        "protected_hashes_match": protected_hashes_match,
        "dependency_contract_valid": dependency_contract_valid,
        "gate_review_valid": gate_review_valid,
        "gate_transition_valid": gate_transition_valid,
        "schema_valid": schema_valid,
        "offline_sql_deterministic": offline_sql_deterministic,
        "alembic_head_count": alembic_head_count,
        "source_boundaries_valid": source_boundaries_valid,
        "harness_refuses_execution": harness_refuses_execution,
        "psycopg_driver_loaded": driver_loaded,
        "database_connection_attempted": False,
        "online_migration_executed": False,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (contract.get("next_required_action") if valid else "invalid_gate"),
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
        "implementation_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "candidate_inventory_exact",
        "candidate_path_count",
        "artifact_hashes_match",
        "protected_hashes_match",
        "dependency_contract_valid",
        "gate_review_valid",
        "gate_transition_valid",
        "schema_valid",
        "offline_sql_deterministic",
        "alembic_head_count",
        "source_boundaries_valid",
        "harness_refuses_execution",
        "psycopg_driver_loaded",
        "database_connection_attempted",
        "online_migration_executed",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 offline implementation check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _dependency_contract_valid(repo_root: Path) -> bool:
    try:
        pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return False
    groups = pyproject.get("dependency-groups")
    return bool(
        isinstance(groups, dict)
        and groups.get("pis3")
        == [
            "SQLAlchemy==2.0.51",
            "alembic==1.18.5",
            "psycopg==3.3.4",
        ]
        and hashlib.sha256(_read_bytes(repo_root / "pyproject.toml")).hexdigest()
        == EXPECTED_ARTIFACT_HASHES["pyproject.toml"]
        and hashlib.sha256(_read_bytes(repo_root / "uv.lock")).hexdigest()
        == EXPECTED_ARTIFACT_HASHES["uv.lock"]
    )


def _schema_evidence(repo_root: Path) -> tuple[bool, bool, int]:
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from ithildin_api import storage_schema
        from sqlalchemy import CheckConstraint

        table = storage_schema.sandbox_descriptors
        constraints = [item for item in table.constraints if isinstance(item, CheckConstraint)]
        schema_valid = bool(
            list(storage_schema.metadata.tables) == ["sandbox_descriptors"]
            and list(table.c.keys())
            == [
                "descriptor_id",
                "status",
                "created_at",
                "updated_at",
                "payload_hash",
                "payload_json",
            ]
            and len(constraints) == 5
            and len(table.indexes) == 1
            and next(iter(table.indexes)).name == "idx_sandbox_descriptors_created_at"
        )
        direct_first = storage_schema.render_postgresql_schema_sql()
        direct_second = storage_schema.render_postgresql_schema_sql()
        output_one = io.StringIO()
        config_one = Config(
            str(repo_root / "db/alembic/alembic.ini"),
            stdout=io.StringIO(),
            output_buffer=output_one,
        )
        heads = ScriptDirectory.from_config(config_one).get_heads()
        command.upgrade(config_one, "head", sql=True)
        output_two = io.StringIO()
        config_two = Config(
            str(repo_root / "db/alembic/alembic.ini"),
            stdout=io.StringIO(),
            output_buffer=output_two,
        )
        command.upgrade(config_two, "head", sql=True)
        deterministic = bool(
            direct_first == direct_second
            and output_one.getvalue() == output_two.getvalue()
            and "payload_json JSONB NOT NULL" in output_one.getvalue()
        )
        return schema_valid, deterministic, len(heads)
    except (ImportError, RuntimeError, ValueError):
        return False, False, -1


def _source_boundaries(repo_root: Path) -> tuple[bool, bool]:
    importer_path = repo_root / "apps/api/src/ithildin_api/storage_import.py"
    test_path = repo_root / "tests/test_storage_schema_import.py"
    env_path = repo_root / "db/alembic/env.py"
    try:
        importer_text = importer_path.read_text(encoding="utf-8")
        importer_tree = ast.parse(importer_text)
        test_text = test_path.read_text(encoding="utf-8")
        test_tree = ast.parse(test_text)
        env_text = env_path.read_text(encoding="utf-8")
        ast.parse(env_text)
    except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
        return False, False

    import_names = {
        alias.name
        for node in ast.walk(importer_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(importer_tree) if isinstance(node, ast.ImportFrom)}
    forbidden_import = any(
        name == "psycopg"
        or name.startswith("psycopg.")
        or "sqlalchemy.orm" in name
        or "sqlalchemy.ext.asyncio" in name
        for name in import_names
    )
    importer_function = _function(importer_tree, "import_validated_descriptor_snapshot")
    importer_attrs = (
        {node.attr for node in ast.walk(importer_function) if isinstance(node, ast.Attribute)}
        if importer_function is not None
        else {"missing"}
    )
    forbidden_calls = {
        "begin",
        "begin_nested",
        "commit",
        "rollback",
        "connect",
        "dispose",
    }
    protected_clean = all(
        "storage_schema" not in _read(repo_root / path)
        and "storage_import" not in _read(repo_root / path)
        for path in (
            "apps/api/src/ithildin_api/app.py",
            "apps/api/src/ithildin_api/config.py",
            "apps/api/src/ithildin_api/sandbox_descriptors.py",
            "apps/api/src/ithildin_api/storage.py",
        )
    )
    source_valid = bool(
        not forbidden_import
        and not forbidden_calls.intersection(importer_attrs)
        and "create_engine" not in importer_text
        and "create_engine" not in env_text
        and "engine_from_config" not in env_text
        and "psycopg" not in env_text
        and protected_clean
    )

    harness = _function(test_tree, "_deferred_isolated_harness_contract")
    harness_refuses = False
    if harness is not None:
        parameter_names = [argument.arg for argument in harness.args.kwonlyargs]
        call_names = {
            node.func.id
            for node in ast.walk(harness)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        harness_refuses = bool(
            parameter_names == ["external_dsn", "rollback_receipt", "pool_class"]
            and "create_engine" not in call_names
            and any(isinstance(node, ast.Raise) for node in ast.walk(harness))
        )
    return source_valid, harness_refuses


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    return next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name),
        None,
    )


def _candidate_paths(repo_root: Path) -> set[str]:
    committed = set(_git_lines(repo_root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD"))
    status = _git_lines(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    working: set[str] = set()
    for line in status:
        path = line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", maxsplit=1)[1]
        working.add(path)
    return committed | working


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
            "Current PIS-003 SD-PG-001 offline implementation" in register,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 offline implementation contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 offline implementation contract has {exc}"]
        return {}, ["PIS-003 offline implementation contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 offline implementation contract must be a JSON object"]
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


def _git_lines(repo_root: Path, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments], cwd=repo_root, check=False, capture_output=True, text=True
    )
    return [line for line in result.stdout.splitlines() if line]


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
