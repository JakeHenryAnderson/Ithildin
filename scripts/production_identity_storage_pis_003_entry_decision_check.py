"""Validate the bounded PIS-003 schema/import entry-decision candidate."""

from __future__ import annotations

import argparse
import hashlib
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
    production_identity_storage_pis_002_continuation_decision_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-003-entry-decision-record.md"
DOC_NAME = "production-identity-storage-pis-003-entry-decision-record.md"
DOC_TITLE = "Production Identity And Storage PIS-003 Entry Decision Record"
DOC_SHA256 = "1af9d450dac5214995adf34a3dabfd877b0e98bd1f5085263eafe496edf299f8"
CONTRACT_REL = "docs/codex/production-identity-storage-pis-003-entry-decision.json"
CONTRACT_SHA256 = "00298c7217749d599a1413ee12c70c505ee212da4e181e82f194ca3e532ade3c"
TARGET = "production-identity-storage-pis-003-entry-decision-check"
BASELINE_COMMIT = "159bf93b4b1e3975d7cab615ef51d2e951f9a80a"

EXPECTED_DIRECT_REQUIREMENTS = [
    "SQLAlchemy==2.0.51",
    "alembic==1.18.5",
    "psycopg==3.3.4",
]

EXPECTED_AUTHORITY = {
    "pis_003_entry_decision_recorded": True,
    "pis_003_sd_pg_001_selected": True,
    "exact_candidate_source_review_required": True,
    "implementation_gate_required": True,
    "pis_003_sd_pg_001_implementation_allowed": False,
    "dependency_changes_allowed": False,
    "sqlalchemy_allowed": False,
    "alembic_allowed": False,
    "psycopg_use_allowed": False,
    "offline_schema_artifact_implementation_allowed": False,
    "offline_migration_artifact_implementation_allowed": False,
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
    "docs/codex/production-identity-storage-pis-002-continuation-decision-record.md": (
        "8d985f6518944a0c7629a05fe050a59502d8a03a02f06b073cfb10d45a7e9bc1"
    ),
    "docs/codex/production-identity-storage-pis-002-continuation-decision.json": (
        "4093a2abf4de79105d9e5b0a1ba71b6f33dcc99e4cf887ee44f9dec2f4188f71"
    ),
    (
        "docs/codex/production-identity-storage-pis-002-"
        "sandbox-descriptor-repository-internal-source-review.md"
    ): "9896aab3a4727747e3ee59e98123dc59093e34c248a4ce27cd1e2a9d7a5a46d6",
    (
        "docs/codex/production-identity-storage-pis-002-"
        "sandbox-descriptor-repository-review-authority.json"
    ): "0b5544685b681861be64327c4ac381d01db6618bb99e6ce0557a1ac864322648",
    "pyproject.toml": "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d",
    "scripts/production_identity_storage_pis_002_continuation_decision_check.py": (
        "773bc05bd3e0bb2980aac990efd5fff703e8800c6cc5a94c038cdc4b7fd295d6"
    ),
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
}

REQUIRED_PHRASES = [
    (
        "Status: committed `PIS-003` entry-decision candidate pending exact-candidate "
        "source review and a separate implementation gate."
    ),
    "Decision ID: `PRD-PROD-IAM-STORAGE-PIS-003-ENTRY`.",
    "Parent decision: `PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION`.",
    f"Entry baseline commit: `{BASELINE_COMMIT}`.",
    (
        "Decision outcome: "
        "`select_bounded_isolated_postgresql_schema_import_slice_pending_review_and_gate`."
    ),
    "Proposed implementation slice: `PIS-003-SD-PG-001`.",
    "Current governed tool count: `24`.",
    "Current `ERG-006` status: `planning_only`.",
    "Current `ERG-007` status: `planning_only`.",
    "Proposed tooling-group requirement: `SQLAlchemy==2.0.51`.",
    "Proposed tooling-group requirement: `alembic==1.18.5`.",
    "Proposed tooling-group requirement: `psycopg==3.3.4`.",
    "The selected flavor is the plain pure-Python package",
    "All three direct requirements belong in a non-default `pis3` dependency group.",
    "application services own the outer transaction boundary",
    "Connection loss during or after commit is `ambiguous_commit`",
    "No implementation may depend on physical row order.",
    "requires an empty PostgreSQL target",
    "`revert_pis_003_sd_pg_001_and_discard_isolated_target_before_activation`",
    "`pis_003_sd_pg_001_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`sqlalchemy_allowed: false`",
    "`alembic_allowed: false`",
    "`psycopg_use_allowed: false`",
    "`database_connections_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`new_power_classes_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`uat_required_now: false`",
    "The next required action is `review_pis_003_entry_decision_exact_candidate`.",
    f"make {TARGET}",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(
        r"\bpis-003(?:-sd-pg-001)? implementation "
        r"(?:is|has been) (?:approved|authorized)\b"
    ),
    re.compile(r"\bdependencies? may now be (?:added|changed|installed)\b"),
    re.compile(r"\b(?:sqlalchemy|alembic|psycopg) may now be (?:added|installed|used)\b"),
    re.compile(r"\bpostgres(?:ql)? may now (?:run|serve|start)\b"),
    re.compile(r"\b(?:release|production promotion|uat) (?:is|has been) (?:approved|complete)\b"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def validate_decision_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    failures = [
        f"PIS-003 entry decision is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]
    failures.extend(
        f"PIS-003 entry decision contains forbidden authority pattern: {pattern.pattern}"
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS
        if pattern.search(lowered)
    )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "decision_id",
        "parent_decision",
        "entry_baseline_commit",
        "decision_outcome",
        "tool_count",
        "dependency_decision",
        "transaction_contract",
        "proposed_slice",
        "protected_hashes",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 entry contract top-level keys are not the closed schema")
    expected_scalars = {
        "schema_version": "1",
        "decision_id": "PRD-PROD-IAM-STORAGE-PIS-003-ENTRY",
        "parent_decision": "PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION",
        "entry_baseline_commit": BASELINE_COMMIT,
        "decision_outcome": (
            "select_bounded_isolated_postgresql_schema_import_slice_"
            "pending_review_and_gate"
        ),
        "tool_count": 24,
        "next_required_action": "review_pis_003_entry_decision_exact_candidate",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 entry contract field {key} is not {expected!r}")
    if type(contract.get("tool_count")) is not int:
        failures.append("PIS-003 entry contract tool_count must be an exact integer")

    dependency = contract.get("dependency_decision")
    if not isinstance(dependency, dict):
        failures.append("PIS-003 dependency decision must be an object")
    else:
        if dependency.get("dependency_group") != "pis3":
            failures.append("PIS-003 dependencies are not confined to the non-default pis3 group")
        if dependency.get("dependency_group_default_enabled") is not False:
            failures.append("PIS-003 pis3 dependency group must remain non-default")
        if dependency.get("selected_direct_requirements") != EXPECTED_DIRECT_REQUIREMENTS:
            failures.append("PIS-003 direct dependency selection is not exact")
        if dependency.get("psycopg_package_flavor") != (
            "pure_python_system_libpq_psycopg_impl_python"
        ):
            failures.append("PIS-003 Psycopg package flavor is not the selected plain package")
        if dependency.get("forbidden_packages") != [
            "psycopg-c",
            "psycopg-binary",
            "psycopg-pool",
            "asyncpg",
        ]:
            failures.append("PIS-003 forbidden dependency package set is not exact")

    transaction = contract.get("transaction_contract")
    if not isinstance(transaction, dict):
        failures.append("PIS-003 transaction contract must be an object")
    else:
        expected_transaction_values = {
            "api_style": "synchronous_explicit_outer_transaction",
            "owner": "application_service",
            "repository_commit_or_rollback_allowed": False,
            "driver_objects_in_aggregate_protocols_allowed": False,
            "nested_authority_transactions_allowed": False,
            "savepoints_for_authority_mutations_allowed": False,
            "transparent_retries_allowed": False,
            "ambiguous_commit_disposition": (
                "reconciliation_required_never_replay_as_fresh_work"
            ),
            "physical_row_order_authoritative": False,
            "canonical_json_digest_owned_by_ithildin": True,
            "isolated_test_harness_input": "externally_supplied_dsn",
            "isolated_test_harness_engine": (
                "synchronous_sqlalchemy_engine_with_nullpool"
            ),
            "isolated_test_harness_owns_connection_and_outer_transaction": True,
            "importer_input": "caller_owned_sqlalchemy_connection",
            "importer_accepts_dsn": False,
            "importer_creates_engine_or_pool": False,
            "importer_commits_or_rolls_back": False,
            "alembic_input": "caller_owned_sqlalchemy_connection",
            "dsn_or_credentials_persisted_or_logged": False,
        }
        for key, expected in expected_transaction_values.items():
            if type(transaction.get(key)) is not type(expected) or transaction.get(key) != expected:
                failures.append(f"PIS-003 transaction contract field {key} is not exact")

    proposed_slice = contract.get("proposed_slice")
    if not isinstance(proposed_slice, dict):
        failures.append("PIS-003 proposed slice must be an object")
    else:
        if proposed_slice.get("slice_id") != "PIS-003-SD-PG-001":
            failures.append("PIS-003 proposed slice ID is not exact")
        if proposed_slice.get("selected_aggregate") != "sandbox_descriptors":
            failures.append("PIS-003 selected aggregate is not sandbox_descriptors")
        if proposed_slice.get("implementation_gate_required") is not True:
            failures.append("PIS-003 proposed slice does not require an implementation gate")
        if proposed_slice.get("rollback") != (
            "revert_pis_003_sd_pg_001_and_discard_isolated_target_before_activation"
        ):
            failures.append("PIS-003 proposed rollback is not exact")

    protected_hashes = contract.get("protected_hashes")
    if protected_hashes != EXPECTED_PROTECTED_HASHES:
        failures.append("PIS-003 protected hash contract is not exact")
    authority = contract.get("authority")
    if (
        not isinstance(authority, dict)
        or authority != EXPECTED_AUTHORITY
        or any(type(authority.get(key)) is not bool for key in EXPECTED_AUTHORITY)
    ):
        failures.append("PIS-003 entry authority map is not the exact closed Boolean map")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
        failures.append("PIS-003 entry decision is not UTF-8")
    failures.extend(validate_decision_text(text))
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 entry decision bytes do not match the closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 entry contract bytes do not match the closed digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    if not baseline_exists:
        failures.append("PIS-003 entry baseline commit is unavailable")
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_is_ancestor:
        failures.append("PIS-003 entry baseline is not an ancestor of HEAD")

    protected_hashes_match = True
    for relative_path, expected_hash in EXPECTED_PROTECTED_HASHES.items():
        baseline_bytes = _git_bytes(repo_root, BASELINE_COMMIT, relative_path)
        current_bytes = _read_bytes(repo_root / relative_path)
        if (
            hashlib.sha256(baseline_bytes).hexdigest() != expected_hash
            or hashlib.sha256(current_bytes).hexdigest() != expected_hash
        ):
            protected_hashes_match = False
            failures.append(f"PIS-003 protected artifact changed: {relative_path}")

    parent_report = (
        production_identity_storage_pis_002_continuation_decision_check.build_report(repo_root)
    )
    parent_valid = bool(
        parent_report["valid"]
        and parent_report["pis_003_entry_decision_preparation_allowed"]
        and not parent_report["pis_003_implementation_allowed"]
        and not parent_report["dependency_changes_allowed"]
    )
    if not parent_valid:
        failures.append("PIS-003 entry prerequisite continuation decision is not valid")

    dependencies_absent = _selected_dependencies_absent(repo_root)
    if not dependencies_absent:
        failures.append("PIS-003 selected dependencies changed before implementation authority")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-003 entry governed tool count is {tool_count}, expected 24")

    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 entry decision wiring is incomplete")

    gate_valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(gate_valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": gate_valid,
        "failures": failures,
        "decision_doc": DOC_REL,
        "decision_document_sha256": doc_hash,
        "decision_document_hash_matches": doc_hash == DOC_SHA256,
        "authority_contract": CONTRACT_REL,
        "authority_contract_sha256": contract_hash,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "decision_id": contract.get("decision_id") if gate_valid else "invalid",
        "decision_outcome": contract.get("decision_outcome") if gate_valid else "invalid",
        "entry_baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "protected_hashes_match": protected_hashes_match,
        "parent_continuation_valid": parent_valid,
        "selected_dependencies_absent": dependencies_absent,
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
        "decision_doc",
        "decision_id",
        "decision_outcome",
        "entry_baseline_commit",
        "baseline_exists",
        "baseline_is_ancestor",
        "decision_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "protected_hashes_match",
        "parent_continuation_valid",
        "selected_dependencies_absent",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin production identity/storage PIS-003 entry decision check"]
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
    project_blob = json.dumps(project).lower()
    lock_names = {
        str(package.get("name", "")).lower()
        for package in lock.get("package", [])
        if isinstance(package, dict)
    }
    selected = {"sqlalchemy", "alembic", "psycopg"}
    return all(name not in project_blob for name in selected) and lock_names.isdisjoint(selected)


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
            "Current PIS-003 entry-decision candidate" in register,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 entry contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 entry contract has {exc}"]
        return {}, ["PIS-003 entry contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 entry contract must be a JSON object"]
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
