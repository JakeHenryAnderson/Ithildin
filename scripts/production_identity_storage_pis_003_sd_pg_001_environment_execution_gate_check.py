"""Validate the bounded PIS-003 environment-execution gate candidate."""

from __future__ import annotations

import argparse
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
    production_identity_storage_pis_003_sd_pg_001_connection_evidence_implementation_check,
    review_docs,
)

implementation = (
    production_identity_storage_pis_003_sd_pg_001_connection_evidence_implementation_check
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-003-sd-pg-001-environment-execution-gate.md"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-environment-execution-gate.json"
)
DOC_SHA256 = "c0115deb144c23f1df5d758a37c588d64b40f7a7dc657ec7537473aec927c426"
CONTRACT_SHA256 = "31d72b46ab521efbb634d632ad83f5907dbdf0ecd852f1b223c84af4608d3923"
TARGET = "production-identity-storage-pis-003-sd-pg-001-environment-execution-gate-check"
GATE_ID = "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-ENVIRONMENT-EXECUTION-GATE"
BASELINE_COMMIT = "8da9ac630b191a36a2782e5febb45d739030cd48"
PARENT_REVIEW_RECORD_COMMIT = "8da9ac630b191a36a2782e5febb45d739030cd48"
REVIEWED_IMPLEMENTATION_COMMIT = "5d929d8e24e4f529cea08796e614fbf544d066bc"

EXPECTED_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/post-rc-decision-register.md",
    CONTRACT_REL,
    DOC_REL,
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "connection_evidence_implementation_check.py"
    ),
    ("scripts/production_identity_storage_pis_003_sd_pg_001_environment_execution_gate_check.py"),
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
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
    "db/alembic/env.py": "2508993adff958ef93efe5cd93b8b3c0f5f6fa57fb0fa6ea9b90861fc274a7e2",
    "db/alembic/versions/0001_sandbox_descriptors.py": (
        "40daefdf8882de79bd6ac68f19b0733c32877f19540c8bab1cb784534c93178e"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-implementation-authority.json"
    ): "5397b004a40c7f0dd46a5812a0f826b68a0d4960a338f5ea086d297a7361e5f8",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-implementation-record.md"
    ): "f6a9f9f680c2e8f2c9189d1a7f72f7456c8b07501d7e4d6965cc24965c37c22f",
    "pyproject.toml": "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627",
    "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py": (
        "7137d469e7cf2713249de7f1a7b69e0311c8ec7873de1a6ec866b3e801ffda07"
    ),
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
}
EXPECTED_GATE_ENVIRONMENT_EVIDENCE_STATE = {
    "target_selected": False,
    "target_label_recorded": False,
    "external_trust_record_present": False,
    "rollback_receipt_present": False,
    "target_owner_quarantine_receipt_present": False,
    "native_dependency_receipts_present": False,
    "tls_root_receipt_present": False,
    "sbom_and_license_receipt_present": False,
    "execution_manifest_present": False,
    "dsn_present_or_consumed": False,
    "target_binding_key_present_or_consumed": False,
    "driver_loaded": False,
    "database_connection_attempted": False,
    "online_migration_executed": False,
    "environment_execution_ready": False,
}
EXPECTED_EXTERNAL_EVIDENCE = [
    "dedicated_nonproduction_quarantined_empty_target_with_safe_label",
    "external_ed25519_trust_record_with_read_only_custody",
    "preconnection_rollback_receipt_bound_to_candidate_run_target_and_source",
    "target_owner_quarantine_receipt_with_dsn_hmac_and_attempt_budget",
    "exact_python_sqlalchemy_alembic_psycopg_libpq_and_libssl_identity_receipts",
    "tls_root_real_path_and_sha256_receipt",
    "python_and_native_dependency_sbom_and_license_receipt",
    "immutable_synthetic_sqlite_source_and_semantic_record_digests",
    "externally_custodied_dsn_and_32_byte_target_binding_key",
    "signed_execution_manifest_with_fifteen_minute_freshness_and_output_root",
    "named_external_discard_owner_available_for_post_connection_receipt",
]
EXPECTED_EXECUTION_CONTRACT = {
    "harness_location": (
        "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py"
    ),
    "harness_scope": "test_only_not_runtime_importable",
    "activation_change_requires_separate_commit": True,
    "activation_change_requires_exact_source_review": True,
    "activation_change_requires_complete_environment_receipts": True,
    "execution_authority_active_now": False,
    "cli_run_mode_present_now": False,
    "driver_import_after_preflight_only": True,
    "dsn_source": "ITHILDIN_PIS3_TEST_DSN_environment_only_after_activation_gate",
    "target_binding_key_source": (
        "ITHILDIN_PIS3_TARGET_BINDING_KEY_environment_only_after_activation_gate"
    ),
    "positive_run_count": 1,
    "positive_connection_attempt_budget": 2,
    "negative_connection_attempt_budget": 1,
    "transparent_retries_allowed": False,
    "commit_allowed": False,
    "outer_transaction_rollback_required": True,
    "post_rollback_absence_check_required": True,
    "final_discard_receipt_required": True,
    "source_digest_revalidation_required": True,
    "output_secret_scan_required": True,
    "runtime_imports_allowed": False,
    "repository_service_or_container_lifecycle_allowed": False,
    "database_or_role_creation_allowed": False,
    "target_activation_allowed": False,
    "runtime_postgres_allowed": False,
    "production_identity_allowed": False,
}
EXPECTED_POST_REVIEW_CEILING = {
    "external_target_selection_allowed": True,
    "external_environment_receipt_collection_allowed": True,
    "activation_candidate_preparation_allowed": True,
    "test_harness_execution_allowed": False,
    "driver_load_allowed": False,
    "external_dsn_consumption_allowed": False,
    "database_connections_allowed": False,
    "migration_execution_allowed": False,
    "postgres_service_allowed": False,
    "container_lifecycle_allowed": False,
    "runtime_postgres_allowed": False,
    "production_identity_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
}
EXPECTED_AUTHORITY = {
    "environment_execution_gate_prepared": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": False,
    "external_target_selection_allowed": False,
    "external_environment_receipt_collection_allowed": False,
    "activation_candidate_preparation_allowed": False,
    "test_harness_execution_allowed": False,
    "driver_load_allowed": False,
    "external_dsn_consumption_allowed": False,
    "target_binding_key_consumption_allowed": False,
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
}
REQUIRED_PHRASES = [
    "Status: environment-execution-gate candidate prepared",
    f"Gate ID: `{GATE_ID}`.",
    f"`{REVIEWED_IMPLEMENTATION_COMMIT}`.",
    f"Parent review-record commit: `{PARENT_REVIEW_RECORD_COMMIT}`.",
    "Current governed tool count: `24`.",
    f"make {TARGET}",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    "`EXECUTION_AUTHORITY_ACTIVE` remains `false`",
    "`environment_execution_ready` is `false`.",
    "Docker socket access",
    "one positive run with exactly two attempts",
    "each negative network scenario in a separate signed run with exactly one attempt",
    "`environment_execution_gate_prepared: true`",
    "`exact_candidate_source_review_complete: false`",
    "`test_harness_execution_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`uat_complete: false`",
    "`review_pis_003_sd_pg_001_environment_execution_gate_exact_candidate`",
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
        f"PIS-003 environment execution gate document missing: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "gate_id",
        "parent_implementation_id",
        "reviewed_connection_evidence_candidate_commit",
        "parent_review_record_commit",
        "gate_baseline_commit",
        "gate_outcome",
        "tool_count",
        "gate_candidate_path_inventory",
        "protected_hashes",
        "gate_environment_evidence_state",
        "required_external_environment_evidence",
        "execution_candidate_contract",
        "post_review_authority_ceiling",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 environment execution gate keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "gate_id": GATE_ID,
        "parent_implementation_id": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-IMPLEMENTATION"
        ),
        "reviewed_connection_evidence_candidate_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "parent_review_record_commit": PARENT_REVIEW_RECORD_COMMIT,
        "gate_baseline_commit": BASELINE_COMMIT,
        "gate_outcome": (
            "environment_execution_gate_prepared_external_environment_evidence_pending_exact_review"
        ),
        "tool_count": 24,
        "next_required_action": (
            "review_pis_003_sd_pg_001_environment_execution_gate_exact_candidate"
        ),
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 environment execution gate field {key} is not exact")
    exact_objects = {
        "gate_candidate_path_inventory": sorted(EXPECTED_PATHS),
        "protected_hashes": EXPECTED_PROTECTED_HASHES,
        "gate_environment_evidence_state": EXPECTED_GATE_ENVIRONMENT_EVIDENCE_STATE,
        "required_external_environment_evidence": EXPECTED_EXTERNAL_EVIDENCE,
        "execution_candidate_contract": EXPECTED_EXECUTION_CONTRACT,
        "post_review_authority_ceiling": EXPECTED_POST_REVIEW_CEILING,
        "authority": EXPECTED_AUTHORITY,
    }
    for key, expected in exact_objects.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 environment execution gate {key} is not exact")
    for key in ("gate_environment_evidence_state", "post_review_authority_ceiling", "authority"):
        value = contract.get(key)
        if not isinstance(value, dict) or any(type(item) is not bool for item in value.values()):
            failures.append(f"PIS-003 environment execution gate {key} types are not closed")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 environment execution gate document is not UTF-8")
    failures.extend(validate_document(doc_text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 environment execution gate document digest does not match")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 environment execution gate contract digest does not match")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    reviewed_implementation_exists = _commit_exists(repo_root, REVIEWED_IMPLEMENTATION_COMMIT)
    reviewed_implementation_is_ancestor = _is_ancestor(
        repo_root, REVIEWED_IMPLEMENTATION_COMMIT, "HEAD"
    )
    if not baseline_exists or not baseline_is_ancestor:
        failures.append("PIS-003 environment execution gate baseline is invalid")
    if not reviewed_implementation_exists or not reviewed_implementation_is_ancestor:
        failures.append("PIS-003 reviewed connection implementation ancestry is invalid")

    candidate_paths = _candidate_paths(repo_root)
    candidate_inventory_exact = candidate_paths == EXPECTED_PATHS
    if not candidate_inventory_exact:
        failures.append("PIS-003 environment execution gate candidate inventory is not exact")

    protected_hashes_match = all(
        _sha256(repo_root / path) == digest for path, digest in EXPECTED_PROTECTED_HASHES.items()
    )
    if not protected_hashes_match:
        failures.append("PIS-003 environment execution gate protected hashes changed")

    parent_report = implementation.build_report(repo_root)
    parent_implementation_valid = bool(
        parent_report.get("valid")
        and parent_report.get("reviewed_candidate_commit") == REVIEWED_IMPLEMENTATION_COMMIT
        and parent_report.get("review_record_commit") == PARENT_REVIEW_RECORD_COMMIT
        and parent_report.get("reviewed_candidate_path_hashes_match") is True
        and parent_report.get("exact_candidate_source_review_complete") is True
        and parent_report.get("database_connections_allowed") is False
        and parent_report.get("migration_execution_allowed") is False
    )
    if not parent_implementation_valid:
        failures.append("PIS-003 reviewed connection implementation prerequisite is invalid")

    harness_check = harness._render_check()
    harness_remains_dormant = bool(
        harness_check.get("valid") is True
        and harness_check.get("execution_authority_active") is False
        and harness_check.get("psycopg_imported") is False
        and harness_check.get("dsn_environment_read") is False
        and harness_check.get("engine_constructed") is False
        and harness_check.get("database_connection_attempted") is False
        and harness_check.get("migration_executed") is False
        and "psycopg" not in sys.modules
    )
    if not harness_remains_dormant:
        failures.append("PIS-003 connection harness is not dormant")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append("PIS-003 environment execution gate tool count changed")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 environment execution gate wiring is incomplete")

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
        "gate_id": contract.get("gate_id") if valid else "invalid",
        "gate_outcome": contract.get("gate_outcome") if valid else "invalid",
        "gate_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "reviewed_implementation_exists": reviewed_implementation_exists,
        "reviewed_implementation_is_ancestor": reviewed_implementation_is_ancestor,
        "candidate_commit": _git_one(repo_root, "rev-parse", "HEAD"),
        "candidate_path_count": len(candidate_paths),
        "candidate_inventory_exact": candidate_inventory_exact,
        "gate_document_hash_matches": doc_hash == DOC_SHA256,
        "gate_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "protected_hashes_match": protected_hashes_match,
        "parent_implementation_valid": parent_implementation_valid,
        "harness_remains_dormant": harness_remains_dormant,
        "environment_execution_ready": False,
        "psycopg_driver_loaded": "psycopg" in sys.modules,
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
        "gate_document",
        "gate_id",
        "gate_outcome",
        "gate_baseline_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "reviewed_implementation_commit",
        "reviewed_implementation_exists",
        "reviewed_implementation_is_ancestor",
        "candidate_commit",
        "candidate_path_count",
        "candidate_inventory_exact",
        "gate_document_hash_matches",
        "gate_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "parent_implementation_valid",
        "harness_remains_dormant",
        "environment_execution_ready",
        "psycopg_driver_loaded",
        "database_connection_attempted",
        "online_migration_executed",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 environment execution gate check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read_text(repo_root / "Makefile")
    readme = _read_text(repo_root / "README.md")
    guardrails = _read_text(repo_root / "scripts/release_guardrails.py")
    docs_site = _read_text(repo_root / "scripts/build_docs_site.py")
    index = _read_text(repo_root / "docs/codex/review-docs-index.md")
    register = _read_text(repo_root / "docs/codex/post-rc-decision-register.md")
    return bool(
        f"{TARGET}:" in makefile
        and f"release-check: {TARGET}" in makefile
        and f"make {TARGET}" in readme
        and DOC_REL in readme
        and CONTRACT_REL in readme
        and DOC_REL in review_docs.REVIEW_DOCS
        and DOC_REL in docs_site
        and TARGET in guardrails
        and "Environment Execution Gate" in index
        and "Current PIS-003 environment execution gate" in register
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"PIS-003 environment execution gate cannot be loaded: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 environment execution gate must be an object"]
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
