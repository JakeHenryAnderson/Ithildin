"""Validate the bounded PIS-003 environment-evidence collection authority candidate."""

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
    production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_gate_check,
    review_docs,
)

parent_gate = (
    production_identity_storage_pis_003_sd_pg_001_environment_evidence_collection_gate_check
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "environment-evidence-collection-authority-record.md"
)
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "environment-evidence-collection-authority.json"
)
DOC_SHA256 = "615319d9d9b8b1fb9a3569fa97bf0c9b7bf28438229e0e88674328c0714e0649"
CONTRACT_SHA256 = "fa6068fda80ec1e065e96b7518c6fa62705eb8dad7ce6cc826fabb30caa76db1"
TARGET = (
    "production-identity-storage-pis-003-sd-pg-001-"
    "environment-evidence-collection-authority-check"
)
AUTHORITY_RECORD_ID = (
    "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-"
    "ENVIRONMENT-EVIDENCE-COLLECTION-AUTHORITY"
)
PARENT_GATE_ID = (
    "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-"
    "ENVIRONMENT-EVIDENCE-COLLECTION-GATE"
)
BASELINE_COMMIT = "31c5653f04b1c7d20d2573cabfed2d0c677d6d4e"
REVIEWED_AUTHORITY_COMMIT = "35e3148b6573729958196ca962e36f1156c7ae25"

EXPECTED_REVIEWED_PATH_HASHES = {
    "Makefile": "73aa48c4265a073fcb7ba36b2683e710ea600a2f58fac9cff8caf014c47e019d",
    "README.md": "2b4304b9b8e9eb49005b8a802405188b5b508255cc7b88b8dcf0c01d2cd39067",
    "docs/codex/post-rc-decision-register.md": (
        "ca9031e5c6753186cd119a5ce8a45a8c642b672abbe06a87f515a4e3fc4fa0dc"
    ),
    DOC_REL: "92497e4b9815f3c65be677e6bca30e9007c4529ec5f78c202d9a31258307548f",
    CONTRACT_REL: "fa7d21680acd02a317ee7f45c3a17c586de7ab54fc1198b4d7f171d82ac694d7",
    "docs/codex/review-docs-index.md": (
        "bd151ef658f36938a9e97a9193474c4eb6c9c74d878d93fe160f5977c4e8d359"
    ),
    "scripts/build_docs_site.py": (
        "b8f77289eae2c327100c1d383e3b24af25de7feec27e5a251d3b7bfac728c476"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_evidence_collection_authority_check.py"
    ): "49cc8dbbaff290d76b62e7b8026509ac76c063855f8cf591d7dd264114a7161e",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_evidence_collection_gate_check.py"
    ): "98e021a52fe7668977ea6092cc07773abe231cabac20260239e67c75f71a090e",
    "scripts/release_guardrails.py": (
        "1e92599ec8f2ea27b24bac31f54551819c3abc8a7a8eb7c63ed328349ec8a2f5"
    ),
    "scripts/review_docs.py": "196b231d942a0a9ac1e98a5be72e8a1e89fc5589f68e145949bc361f79d76ed6",
    "tests/test_release_readiness.py": (
        "8e88e2f076de6e9014520d0868de3054a7ac3e66afd52723df9bf7fe5e43ee6f"
    ),
}
EXPECTED_REVIEW_FINDINGS = {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "open": 0,
}
EXPECTED_VALIDATION_EVIDENCE = {
    "focused_environment_collection_tests": 19,
    "focused_authority_review_tests": 9,
    "docs_site_tests": 3,
    "full_release_python_tests": 1760,
    "full_release_ui_tests": 59,
    "strict_mypy_source_files": 132,
    "packet_redaction_files_scanned": 622,
    "packet_redaction_findings": 0,
    "full_release_check_passed": True,
    "artifact_freshness_check_passed": True,
    "agent_workflow_check_passed": True,
    "exact_review_findings_zero": True,
    "tool_count_unchanged": True,
    "sol_ultra_used": False,
}

EXPECTED_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/post-rc-decision-register.md",
    DOC_REL,
    CONTRACT_REL,
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_evidence_collection_authority_check.py"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_evidence_collection_gate_check.py"
    ),
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
        "environment-evidence-collection-gate.json"
    ): "d59a15288b7f183877ab9fe292a3949f8f31cb3da175586de0a2cce20cf751e8",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-evidence-collection-gate.md"
    ): "6ec53068768dab031533dd11067dd065531149f0c0799b86f9a566e7cf8fdf8f",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-execution-gate.json"
    ): "65161e4d66fe34625813091859ec2adf979ed9c958ea3572727a6742cf89a07b",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-execution-gate.md"
    ): "dd834a15025e6f859f8dfee1992883241cea584257b5abbde96dbeb390a3945a",
    "pyproject.toml": "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627",
    "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py": (
        "7137d469e7cf2713249de7f1a7b69e0311c8ec7873de1a6ec866b3e801ffda07"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_evidence_collection_gate_check.py"
    ): "98e021a52fe7668977ea6092cc07773abe231cabac20260239e67c75f71a090e",
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "environment_execution_gate_check.py"
    ): "2f374f7719a932b2b40b9240f350986fcd2ea7bc4a6640152efdf75036c17467",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
}
EXPECTED_PARENT_HASHES = {
    "document_sha256": "6ec53068768dab031533dd11067dd065531149f0c0799b86f9a566e7cf8fdf8f",
    "contract_sha256": "d59a15288b7f183877ab9fe292a3949f8f31cb3da175586de0a2cce20cf751e8",
    "validator_sha256": "98e021a52fe7668977ea6092cc07773abe231cabac20260239e67c75f71a090e",
}
EXPECTED_COLLECTION_BINDING: dict[str, Any] = {
    "scope": "external_evidence_intake_preparation_only",
    "intake_root": "var/review-runs/pis-003-sd-pg-001-external-environment-evidence",
    "intake_root_created_now": False,
    "explicit_file_inputs_only": True,
    "target_label_pattern": "^[a-z0-9][a-z0-9._-]{2,63}$",
    "issuer_id_pattern": "^[a-z][a-z0-9._-]{2,63}$",
    "run_id_pattern": "^pis3run_[0-9a-f]{32}$",
    "sha256_pattern": "^sha256:[0-9a-f]{64}$",
    "hmac_sha256_pattern": "^hmac-sha256:[0-9a-f]{64}$",
    "trust_record_min_count": 1,
    "trust_record_max_count": 3,
    "preconnection_receipt_types": [
        "preconnection_rollback_receipt",
        "target_owner_quarantine_receipt",
    ],
    "canonical_json_required": True,
    "signature_verification_required": True,
    "receipt_freshness_required": True,
    "exact_candidate_run_target_source_binding_required": True,
    "complete_set_required": True,
    "dsn_and_32_byte_binding_key_external_custody_only": True,
    "secret_material_allowed_in_evidence": False,
    "private_signing_key_custody_allowed": False,
    "symlink_inputs_allowed": False,
    "writable_receipts_allowed": False,
    "repository_or_output_local_receipts_allowed": False,
    "final_discard_receipt_is_future_post_connection_evidence_only": True,
}
EXPECTED_PRE_REVIEW_AUTHORITY = {
    "external_target_selection_allowed": False,
    "external_environment_receipt_collection_allowed": False,
}
EXPECTED_POST_REVIEW_CEILING = {
    "external_target_selection_allowed": True,
    "external_environment_receipt_collection_allowed": True,
    "activation_candidate_preparation_allowed": False,
    "host_credential_inspection_allowed": False,
    "test_harness_execution_allowed": False,
    "driver_load_allowed": False,
    "external_dsn_consumption_allowed": False,
    "target_binding_key_consumption_allowed": False,
    "database_connections_allowed": False,
    "migration_execution_allowed": False,
    "postgres_service_allowed": False,
    "container_lifecycle_allowed": False,
    "runtime_postgres_allowed": False,
    "production_identity_allowed": False,
    "arbitrary_host_control_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
}
EXPECTED_AUTHORITY = {
    "environment_evidence_collection_authority_record_prepared": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": True,
    "external_target_selection_allowed": False,
    "external_environment_receipt_collection_allowed": False,
    "activation_candidate_preparation_allowed": False,
    "host_credential_inspection_allowed": False,
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
    "arbitrary_host_control_allowed": False,
    "new_power_classes_allowed": False,
    "public_security_product_positioning_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
    "uat_required_now": False,
}
NEXT_ACTION = (
    "prepare_separate_pis_003_sd_pg_001_"
    "environment_evidence_collection_authority_activation_candidate"
)
REQUIRED_PHRASES = [
    (
        "Status: environment-evidence-collection authority-record exact-candidate review "
        "complete with zero findings"
    ),
    f"`{AUTHORITY_RECORD_ID}`.",
    f"`{BASELINE_COMMIT}`.",
    f"`{REVIEWED_AUTHORITY_COMMIT}`.",
    "Current governed tool count: `24`.",
    f"make {TARGET}",
    CONTRACT_REL,
    "Prose cannot broaden",
    "No target is selected, provisioned, inspected, or recorded.",
    "No intake root is created.",
    "This candidate changes exactly twelve",
    "`exact_candidate_source_review_complete: true`",
    "`external_target_selection_allowed: false`",
    "`external_environment_receipt_collection_allowed: false`",
    "`activation_candidate_preparation_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`arbitrary_host_control_allowed: false`",
    "`uat_complete: false`",
    f"`{NEXT_ACTION}`",
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
        f"PIS-003 environment evidence collection authority document missing: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "authority_record_id",
        "parent_gate_id",
        "parent_review_record_commit",
        "authority_baseline_commit",
        "reviewed_candidate_commit",
        "authority_outcome",
        "review_disposition",
        "review_method",
        "reviewed_candidate_path_hashes",
        "review_findings",
        "validation_evidence",
        "tool_count",
        "authority_candidate_path_inventory",
        "protected_hashes",
        "parent_collection_gate_hashes",
        "collection_contract_binding",
        "pre_review_authority",
        "post_review_authority_ceiling",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 environment evidence collection authority keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "authority_record_id": AUTHORITY_RECORD_ID,
        "parent_gate_id": PARENT_GATE_ID,
        "parent_review_record_commit": BASELINE_COMMIT,
        "authority_baseline_commit": BASELINE_COMMIT,
        "reviewed_candidate_commit": REVIEWED_AUTHORITY_COMMIT,
        "authority_outcome": (
            "environment_evidence_collection_authority_record_exact_review_complete_"
            "all_live_authority_false"
        ),
        "review_disposition": (
            "cleared_for_separate_two_permission_activation_candidate_preparation_only"
        ),
        "review_method": "independent_read_only_gpt_5_6_sol_xhigh_no_ultra",
        "tool_count": 24,
        "next_required_action": NEXT_ACTION,
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(
                f"PIS-003 environment evidence collection authority field {key} is not exact"
            )
    exact_objects = {
        "authority_candidate_path_inventory": sorted(EXPECTED_PATHS),
        "reviewed_candidate_path_hashes": EXPECTED_REVIEWED_PATH_HASHES,
        "review_findings": EXPECTED_REVIEW_FINDINGS,
        "validation_evidence": EXPECTED_VALIDATION_EVIDENCE,
        "protected_hashes": EXPECTED_PROTECTED_HASHES,
        "parent_collection_gate_hashes": EXPECTED_PARENT_HASHES,
        "collection_contract_binding": EXPECTED_COLLECTION_BINDING,
        "pre_review_authority": EXPECTED_PRE_REVIEW_AUTHORITY,
        "post_review_authority_ceiling": EXPECTED_POST_REVIEW_CEILING,
        "authority": EXPECTED_AUTHORITY,
    }
    for key, expected in exact_objects.items():
        if contract.get(key) != expected:
            failures.append(
                f"PIS-003 environment evidence collection authority {key} is not exact"
            )
    for key in ("pre_review_authority", "post_review_authority_ceiling", "authority"):
        value = contract.get(key)
        if not isinstance(value, dict) or any(type(item) is not bool for item in value.values()):
            failures.append(
                f"PIS-003 environment evidence collection authority {key} types are not closed"
            )
    findings = contract.get("review_findings")
    if not isinstance(findings, dict) or any(type(item) is not int for item in findings.values()):
        failures.append(
            "PIS-003 environment evidence collection authority review_findings types are not closed"
        )
    evidence = contract.get("validation_evidence")
    if not isinstance(evidence, dict) or any(
        type(item) not in {int, bool} for item in evidence.values()
    ):
        failures.append(
            "PIS-003 environment evidence collection authority "
            "validation_evidence types are not closed"
        )
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 environment evidence collection authority document is not UTF-8")
    failures.extend(validate_document(doc_text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append(
            "PIS-003 environment evidence collection authority document digest mismatch"
        )
    if contract_hash != CONTRACT_SHA256:
        failures.append(
            "PIS-003 environment evidence collection authority contract digest mismatch"
        )

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    reviewed_authority_exists = _commit_exists(repo_root, REVIEWED_AUTHORITY_COMMIT)
    reviewed_authority_is_ancestor = _is_ancestor(
        repo_root, REVIEWED_AUTHORITY_COMMIT, "HEAD"
    )
    if not baseline_exists or not baseline_is_ancestor:
        failures.append("PIS-003 environment evidence collection authority baseline is invalid")
    if not reviewed_authority_exists or not reviewed_authority_is_ancestor:
        failures.append("PIS-003 reviewed environment evidence collection authority is invalid")

    reviewed_candidate_path_hashes_match = all(
        _sha256_at_commit(repo_root, REVIEWED_AUTHORITY_COMMIT, path) == digest
        for path, digest in EXPECTED_REVIEWED_PATH_HASHES.items()
    )
    if not reviewed_candidate_path_hashes_match:
        failures.append(
            "PIS-003 reviewed environment evidence collection authority path hashes changed"
        )

    candidate_paths = _candidate_paths(repo_root)
    candidate_inventory_exact = candidate_paths == EXPECTED_PATHS
    if not candidate_inventory_exact:
        failures.append("PIS-003 environment evidence collection authority inventory is not exact")

    protected_hashes_match = all(
        _sha256(repo_root / path) == digest for path, digest in EXPECTED_PROTECTED_HASHES.items()
    )
    if not protected_hashes_match:
        failures.append(
            "PIS-003 environment evidence collection authority protected hashes changed"
        )

    parent_report = parent_gate.build_report(repo_root)
    parent_gate_valid = bool(
        parent_report.get("valid")
        and parent_report.get("gate_id") == PARENT_GATE_ID
        and parent_report.get("review_record_commit") == BASELINE_COMMIT
        and parent_report.get("review_record_commit_exists") is True
        and parent_report.get("review_record_commit_is_ancestor") is True
        and parent_report.get("reviewed_candidate_path_hashes_match") is True
        and parent_report.get("exact_candidate_source_review_complete") is True
        and parent_report.get("external_target_selection_allowed") is False
        and parent_report.get("external_environment_receipt_collection_allowed") is False
        and parent_report.get("activation_candidate_preparation_allowed") is False
        and parent_report.get("database_connections_allowed") is False
        and parent_report.get("migration_execution_allowed") is False
        and parent_report.get("runtime_postgres_allowed") is False
    )
    if not parent_gate_valid:
        failures.append("PIS-003 reviewed collection-gate prerequisite is invalid")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append("PIS-003 environment evidence collection authority tool count changed")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 environment evidence collection authority wiring is incomplete")

    valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "authority_document": DOC_REL,
        "authority_record_id": (
            contract.get("authority_record_id") if valid else "invalid"
        ),
        "authority_outcome": contract.get("authority_outcome") if valid else "invalid",
        "authority_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "reviewed_candidate_commit": REVIEWED_AUTHORITY_COMMIT,
        "reviewed_candidate_commit_exists": reviewed_authority_exists,
        "reviewed_candidate_commit_is_ancestor": reviewed_authority_is_ancestor,
        "reviewed_candidate_path_hashes_match": reviewed_candidate_path_hashes_match,
        "candidate_commit": _git_one(repo_root, "rev-parse", "HEAD"),
        "candidate_path_count": len(candidate_paths),
        "candidate_inventory_exact": candidate_inventory_exact,
        "authority_document_hash_matches": doc_hash == DOC_SHA256,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "protected_hashes_match": protected_hashes_match,
        "parent_gate_valid": parent_gate_valid,
        "target_selected": False,
        "receipt_collection_started": False,
        "intake_root_created": False,
        "psycopg_driver_loaded": "psycopg" in sys.modules,
        "database_connection_attempted": False,
        "online_migration_executed": False,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": contract.get("next_required_action") if valid else "invalid_gate",
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "authority_document",
        "authority_record_id",
        "authority_outcome",
        "authority_baseline_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "reviewed_candidate_commit",
        "reviewed_candidate_commit_exists",
        "reviewed_candidate_commit_is_ancestor",
        "reviewed_candidate_path_hashes_match",
        "candidate_commit",
        "candidate_path_count",
        "candidate_inventory_exact",
        "authority_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "parent_gate_valid",
        "target_selected",
        "receipt_collection_started",
        "intake_root_created",
        "psycopg_driver_loaded",
        "database_connection_attempted",
        "online_migration_executed",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 environment evidence collection authority check"]
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
        and "Environment Evidence Collection Authority Record" in index
        and "Current PIS-003 environment evidence collection authority record" in register
        and "review complete at `e33cca9` with zero findings" in register
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"PIS-003 environment evidence collection authority cannot be loaded: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 environment evidence collection authority must be an object"]
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


def _sha256_at_commit(repo_root: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else ""


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
