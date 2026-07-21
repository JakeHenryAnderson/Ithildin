"""Validate the bounded PIS-002 continuation decision."""

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
    production_identity_storage_pis_002_sandbox_descriptor_repository_internal_review_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/production-identity-storage-pis-002-continuation-decision-record.md"
)
DOC_TITLE = "Production Identity And Storage PIS-002 Continuation Decision Record"
CONTRACT_REL = "docs/codex/production-identity-storage-pis-002-continuation-decision.json"
TARGET = "production-identity-storage-pis-002-continuation-decision-check"
BASELINE_COMMIT = "308735a670a6bfbe3032de7658366539fe9a3686"
REVIEWED_IMPLEMENTATION_COMMIT = "887de154aeb4c047325eed2372c83deda1fda251"
DOCUMENT_SHA256 = "8d985f6518944a0c7629a05fe050a59502d8a03a02f06b073cfb10d45a7e9bc1"

DIRECT_SQLITE_MODULES = [
    "apps/api/src/ithildin_api/agent_runs.py",
    "apps/api/src/ithildin_api/approvals.py",
    "apps/api/src/ithildin_api/database_migration_backup.py",
    "apps/api/src/ithildin_api/mission_reports.py",
    "apps/api/src/ithildin_api/missions.py",
    "apps/api/src/ithildin_api/node_configuration.py",
    "apps/api/src/ithildin_api/node_configuration_trust.py",
    "apps/api/src/ithildin_api/nodes.py",
    "apps/api/src/ithildin_api/patches.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
    "apps/api/src/ithildin_api/trusted_host_promotions.py",
    "packages/audit-core/src/ithildin_audit_core/writer.py",
]

UNRESOLVED_BOUNDARIES = [
    "portable_transaction_handle",
    "cross_store_atomicity_and_recovery",
    "audit_ordering_and_canonical_outbox",
    "sqlite_rowid_and_json_dialect_dependencies",
    "postgresql_schema_and_constraint_parity",
    "offline_migration_and_isolated_import",
    "ambiguous_commit_and_connection_loss",
    "dependency_packaging_license_and_provenance",
]

EXPECTED_AUTHORITY = {
    "pis_002_sd_001_source_review_complete": True,
    "pis_002_dependency_free_interface_phase_complete": True,
    "additional_pis_002_aggregate_implementation_allowed": False,
    "pis_003_entry_decision_preparation_allowed": True,
    "pis_003_implementation_allowed": False,
    "dependency_evaluation_allowed": True,
    "dependency_changes_allowed": False,
    "sqlalchemy_allowed": False,
    "psycopg_allowed": False,
    "alembic_allowed": False,
    "public_api_changes_allowed": False,
    "schema_changes_allowed": False,
    "database_migrations_allowed": False,
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

EXPECTED_CONTRACT = {
    "schema_version": "1",
    "decision_id": "PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION",
    "parent_decision": "PRD-PROD-IAM-STORAGE-PIS-002-ENTRY",
    "decision_baseline_commit": BASELINE_COMMIT,
    "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
    "completed_slice": "PIS-002-SD-001",
    "decision_document_sha256": DOCUMENT_SHA256,
    "decision_outcome": (
        "close_dependency_free_pis_002_after_one_proven_seam_"
        "prepare_pis_003_entry_decision_only"
    ),
    "direct_sqlite_modules": DIRECT_SQLITE_MODULES,
    "unresolved_boundaries": UNRESOLVED_BOUNDARIES,
    "authority": EXPECTED_AUTHORITY,
    "next_required_action": "prepare_pis_003_entry_decision_record",
}

EXPECTED_CHANGED_PATHS = {
    "Makefile",
    "README.md",
    DOC_REL,
    CONTRACT_REL,
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    "scripts/production_identity_storage_pis_002_continuation_decision_check.py",
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
}

PROTECTED_HASHES = {
    "apps/api/src/ithildin_api/app.py": (
        "2cd6cb4304165de300b4418c73308d7cd15d9c5ac36c2869ada1b7f7d28fc0d4"
    ),
    "apps/api/src/ithildin_api/sandbox_descriptors.py": (
        "30aa57adffe7b981cf5f5a92786b33ae0da5ea1c611cd0806cb780ec6d603bec"
    ),
    "apps/api/src/ithildin_api/trusted_host_promotions.py": (
        "4090817b1c95114e75edd6b3f8908e734fa19c8db07f42c1a830831d1f458759"
    ),
    (
        "docs/codex/production-identity-storage-pis-002-"
        "sandbox-descriptor-repository-implementation.md"
    ): "9afda1144c0743675bf1db52aadce456a99dcde142139f89b5eed2754521cefb",
    (
        "docs/codex/production-identity-storage-pis-002-"
        "sandbox-descriptor-repository-internal-source-review.md"
    ): "9896aab3a4727747e3ee59e98123dc59093e34c248a4ce27cd1e2a9d7a5a46d6",
    (
        "docs/codex/production-identity-storage-pis-002-"
        "sandbox-descriptor-repository-review-authority.json"
    ): "0b5544685b681861be64327c4ac381d01db6618bb99e6ce0557a1ac864322648",
    (
        "scripts/production_identity_storage_pis_002_"
        "sandbox_descriptor_repository_check.py"
    ): "2461a58f98f3333a1cfbd7033581cfe397ccd05422113bb12bac314c7de0ba26",
    (
        "scripts/production_identity_storage_pis_002_"
        "sandbox_descriptor_repository_internal_review_check.py"
    ): "fb9c4d28abb2708a8ab4f0f349bab240d34581168d1f55cd408b47211fe7e25c",
    "pyproject.toml": "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d",
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

REQUIRED_PHRASES = [
    (
        "Status: committed PIS-002 continuation decision after the cleared "
        "`PIS-002-SD-001` exact candidate."
    ),
    "Decision ID: `PRD-PROD-IAM-STORAGE-PIS-002-CONTINUATION`.",
    f"Decision baseline commit: `{BASELINE_COMMIT}`.",
    f"Reviewed implementation commit: `{REVIEWED_IMPLEMENTATION_COMMIT}`.",
    (
        "Decision outcome: `close_dependency_free_pis_002_after_one_proven_seam_"
        "prepare_pis_003_entry_decision_only`."
    ),
    "Current governed tool count: `24`.",
    "The current runtime has `13` direct-SQLite modules",
    "No second PIS-002 aggregate is selected. No runtime candidate follows this decision.",
    "The next required action is `prepare_pis_003_entry_decision_record`.",
    "PIS-003 entry-decision preparation may evaluate",
    "Prose cannot broaden the closed contract.",
    "`additional_pis_002_aggregate_implementation_allowed: false`",
    "`pis_003_entry_decision_preparation_allowed: true`",
    "`pis_003_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`sqlalchemy_allowed: false`",
    "`psycopg_allowed: false`",
    "`alembic_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`new_power_classes_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`uat_required_now: false`",
    f"make {TARGET}",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    authority = contract.get("authority")
    if isinstance(authority, dict) and any(
        type(value) is not bool for value in authority.values()
    ):
        failures.append("PIS-002 continuation authority values must be exact Booleans")
    if not _closed_equal(contract, EXPECTED_CONTRACT):
        failures.append("PIS-002 continuation contract is not the exact closed contract")
    return failures


def validate_decision_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [
        f"PIS-002 continuation decision is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    document_bytes = _read_bytes(repo_root / DOC_REL)
    try:
        document_text = document_bytes.decode("utf-8")
    except UnicodeDecodeError:
        document_text = ""
        failures.append("PIS-002 continuation decision is not UTF-8")
    if not document_bytes:
        failures.append("PIS-002 continuation decision is missing")
    failures.extend(validate_decision_text(document_text))
    document_sha256 = hashlib.sha256(document_bytes).hexdigest()
    document_hash_matches = document_sha256 == DOCUMENT_SHA256
    if not document_hash_matches:
        failures.append("PIS-002 continuation decision bytes do not match the reviewed digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)
    contract_valid = not load_failures and not contract_failures
    authority = contract.get("authority") if contract_valid else {}
    if not isinstance(authority, dict):
        authority = {}

    baseline_exists = _commit_exists(repo_root, BASELINE_COMMIT)
    if not baseline_exists:
        failures.append("PIS-002 continuation baseline commit is unavailable")
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_is_ancestor:
        failures.append("PIS-002 continuation baseline is not an ancestor of HEAD")
    candidate_commit = _decision_candidate_commit(repo_root)
    candidate_paths = _candidate_paths(repo_root, candidate_commit)
    candidate_scope_exact = candidate_paths == EXPECTED_CHANGED_PATHS
    if not candidate_scope_exact:
        failures.append("PIS-002 continuation candidate path inventory is not exact")
    if candidate_commit:
        candidate_parent = _git(repo_root, "rev-parse", f"{candidate_commit}^")
        candidate_parent_exact = candidate_parent == BASELINE_COMMIT
    else:
        candidate_parent_exact = _git(repo_root, "rev-parse", "HEAD") == BASELINE_COMMIT
    if not candidate_parent_exact:
        failures.append("PIS-002 continuation candidate parent is not the exact baseline")

    protected_hashes_match = True
    for path, expected_hash in PROTECTED_HASHES.items():
        baseline_bytes = _git_bytes(repo_root, BASELINE_COMMIT, path)
        current_path = repo_root / path
        if (
            hashlib.sha256(baseline_bytes).hexdigest() != expected_hash
            or not current_path.is_file()
            or hashlib.sha256(current_path.read_bytes()).hexdigest() != expected_hash
        ):
            protected_hashes_match = False
            failures.append(f"PIS-002 continuation protected artifact changed: {path}")

    source_review = (
        production_identity_storage_pis_002_sandbox_descriptor_repository_internal_review_check.build_report(
            repo_root
        )
    )
    source_review_valid = bool(
        source_review["valid"]
        and source_review["pis_002_sd_001_source_review_complete"]
        and source_review["pis_002_sd_001_cleared"]
        and source_review["critical_findings"] == 0
        and source_review["high_findings"] == 0
        and source_review["open_findings"] == 0
    )
    if not source_review_valid:
        failures.append("PIS-002 continuation prerequisite source review is not valid")

    direct_sqlite_modules = _direct_sqlite_modules(repo_root)
    direct_sqlite_inventory_exact = direct_sqlite_modules == DIRECT_SQLITE_MODULES
    if not direct_sqlite_inventory_exact:
        failures.append("PIS-002 continuation direct-SQLite module inventory is not exact")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    wiring_valid = all(
        (
            f"{TARGET}:" in makefile,
            f"release-check: {TARGET}" in makefile,
            f"make {TARGET}" in readme,
            DOC_REL in readme,
            DOC_REL in docs_site,
            DOC_TITLE in review_index,
            TARGET in release_guardrails,
            DOC_REL in review_docs.REVIEW_DOCS,
            "Current PIS-002 continuation decision" in register,
        )
    )
    if not wiring_valid:
        failures.append("PIS-002 continuation decision wiring is incomplete")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-002 continuation governed tool count is {tool_count}, expected 24")

    gate_valid = not failures

    def allowed(name: str) -> bool:
        return bool(gate_valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": gate_valid,
        "failures": failures,
        "decision_doc": DOC_REL,
        "decision_document_sha256": document_sha256,
        "decision_document_hash_matches": document_hash_matches,
        "authority_contract": CONTRACT_REL,
        "contract_valid": contract_valid,
        "decision_outcome": contract.get("decision_outcome") if gate_valid else "invalid",
        "baseline_commit": BASELINE_COMMIT,
        "baseline_exists": baseline_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_commit": candidate_commit or "working_tree",
        "candidate_parent_exact": candidate_parent_exact,
        "candidate_scope_exact": candidate_scope_exact,
        "candidate_path_count": len(candidate_paths),
        "protected_hashes_match": protected_hashes_match,
        "source_review_valid": source_review_valid,
        "direct_sqlite_module_count": len(direct_sqlite_modules),
        "direct_sqlite_inventory_exact": direct_sqlite_inventory_exact,
        "wiring_valid": wiring_valid,
        "tool_count": tool_count,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (
            contract.get("next_required_action") if gate_valid else "invalid_gate"
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [key for key in report if key != "failures"]
    lines = ["Ithildin PIS-002 continuation decision check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-002 continuation contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-002 continuation contract has {exc}"]
        return {}, ["PIS-002 continuation contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-002 continuation contract must be a JSON object"]
    return payload, []


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _closed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _closed_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _closed_equal(left, right)
            for left, right in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def _decision_candidate_commit(repo_root: Path) -> str | None:
    commits = _git(
        repo_root,
        "log",
        "--diff-filter=A",
        "--format=%H",
        "--",
        DOC_REL,
    ).splitlines()
    return commits[0] if commits else None


def _candidate_paths(repo_root: Path, candidate_commit: str | None = None) -> set[str]:
    if candidate_commit:
        return set(
            _git(
                repo_root,
                "diff",
                "--name-only",
                f"{BASELINE_COMMIT}..{candidate_commit}",
            ).splitlines()
        ) - {""}
    committed = set(
        _git(repo_root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD").splitlines()
    )
    dirty: set[str] = set()
    status = _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    for line in status.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        dirty.add(path)
    return (committed | dirty) - {""}


def _direct_sqlite_modules(repo_root: Path) -> list[str]:
    roots = [repo_root / "apps/api/src", repo_root / "packages/audit-core/src"]
    modules: list[str] = []
    pattern = re.compile(r"^(?:import sqlite3|from sqlite3\b)", re.MULTILINE)
    for root in roots:
        for path in root.rglob("*.py"):
            if pattern.search(path.read_text(encoding="utf-8")):
                modules.append(path.relative_to(repo_root).as_posix())
    return sorted(modules)


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).returncode == 0


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).returncode == 0


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.rstrip("\n")


def _git_bytes(repo_root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    manifests = payload.get("manifests") if isinstance(payload, dict) else None
    return len(manifests) if isinstance(manifests, list) else 0


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


if __name__ == "__main__":
    raise SystemExit(main())
