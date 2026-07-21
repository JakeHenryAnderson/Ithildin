"""Validate the exact PIS-002 sandbox-descriptor repository implementation candidate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ithildin_api.sandbox_descriptors as sandbox_descriptors_module
from ithildin_api.sandbox_descriptors import (
    SandboxDescriptorRepository,
    SandboxDescriptorStore,
)

from scripts import production_identity_storage_pis_002_entry_decision_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "production-identity-storage-pis-002-sandbox-descriptor-repository-implementation.md"
)
DOC_TITLE = (
    "Production Identity And Storage PIS-002 Sandbox Descriptor Repository Implementation"
)
TARGET = "production-identity-storage-pis-002-sandbox-descriptor-repository-check"
BASELINE_COMMIT = "934ebaa4ccd5d03032e269473198e7c94755c13c"

IMPLEMENTATION_PATHS = frozenset(
    cast(
        list[str],
        production_identity_storage_pis_002_entry_decision_check.EXPECTED_SLICE[
            "allowed_code_paths"
        ],
    )
)
EVIDENCE_PATHS = frozenset(
    {
        "Makefile",
        "README.md",
        "docs/codex/post-rc-decision-register.md",
        DOC_REL,
        "docs/codex/review-docs-index.md",
        "scripts/build_docs_site.py",
        "scripts/production_identity_storage_pis_001_decision_check.py",
        "scripts/production_identity_storage_pis_001_internal_review_check.py",
        "scripts/production_identity_storage_pis_002_sandbox_descriptor_repository_check.py",
        "scripts/release_guardrails.py",
        "scripts/review_docs.py",
        "tests/test_release_readiness.py",
    }
)
EXPECTED_CHANGED_PATHS = IMPLEMENTATION_PATHS | EVIDENCE_PATHS

PROTECTED_HASHES = {
    key: value
    for key, value in (
        production_identity_storage_pis_002_entry_decision_check.EXPECTED_BASELINE_HASHES.items()
    )
    if key in {"pyproject.toml", "uv.lock", "tool-manifests.lock.json"}
}

REPOSITORY_METHODS = {
    "initialize",
    "create",
    "list",
    "get",
    "authority_record",
    "status",
}
EXPECTED_REPOSITORY_TESTS = {
    "test_sqlite_repository_preserves_record_bytes_hash_and_authority",
    "test_sqlite_repository_reads_and_extends_an_entry_baseline_database",
    "test_repository_audit_metadata_is_minimized_and_exact",
}
EXPECTED_API_TESTS = {
    "test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
    "test_sandbox_descriptor_remains_committed_after_audit_failure",
}

REQUIRED_DOC_PHRASES = [
    "Status: implemented bounded `PIS-002-SD-001` candidate",
    "Implementation baseline commit: `934ebaa4ccd5d03032e269473198e7c94755c13c`.",
    "Current governed tool count: `24`.",
    "make production-identity-storage-pis-002-sandbox-descriptor-repository-check",
    "`SandboxDescriptorRepository` protocol",
    "`SandboxDescriptorStore` remains the only runtime implementation",
    "audit_failure_ordering_parity",
    "revert_interface_and_adapter_commit_without_schema_or_data_conversion",
    "review_pis_002_sd_001_exact_candidate",
    "PIS-003 and any second PIS-002 aggregate remain blocked",
]

EXPECTED_COLUMNS = [
    ("descriptor_id", "TEXT", 0, 1),
    ("status", "TEXT", 1, 0),
    ("created_at", "TEXT", 1, 0),
    ("updated_at", "TEXT", 1, 0),
    ("payload_hash", "TEXT", 1, 0),
    ("payload_json", "TEXT", 1, 0),
]
EXPECTED_INDEXES = [
    ("idx_sandbox_descriptors_created_at", 0, "c"),
    ("sqlite_autoindex_sandbox_descriptors_1", 1, "pk"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT, require_clean=not args.allow_dirty)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, *, require_clean: bool = True) -> dict[str, Any]:
    failures: list[str] = []
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")

    if not (repo_root / DOC_REL).exists():
        failures.append("PIS-002 sandbox descriptor repository implementation doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"PIS-002 repository implementation doc missing phrase: {phrase}")

    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_is_ancestor:
        failures.append("PIS-002 implementation baseline is not an ancestor of current HEAD")
    committed_paths = _changed_paths(repo_root) if baseline_is_ancestor else []
    worktree_paths = _working_tree_changed_paths(repo_root)
    rename_records = _rename_records(repo_root) if baseline_is_ancestor else []
    scope_failures = validate_candidate_scope(
        committed_paths=committed_paths,
        worktree_paths=worktree_paths,
        rename_records=rename_records,
        require_clean=require_clean,
    )
    failures.extend(scope_failures)

    repository_source = _read(
        repo_root / "apps/api/src/ithildin_api/sandbox_descriptors.py"
    )
    structure = validate_repository_structure(repository_source)
    failures.extend(structure["failures"])

    app_source = _read(repo_root / "apps/api/src/ithildin_api/app.py")
    trusted_host_source = _read(
        repo_root / "apps/api/src/ithildin_api/trusted_host_promotions.py"
    )
    consumer_typing_valid, consumer_failures = validate_consumer_typing(
        app_source, trusted_host_source
    )
    failures.extend(consumer_failures)

    runtime_protocol_present = bool(
        getattr(SandboxDescriptorRepository, "_is_protocol", False)
    )
    runtime_implementations = _runtime_repository_implementations()
    runtime_sqlite_adapter_only = runtime_implementations == ["SandboxDescriptorStore"]
    if not runtime_protocol_present:
        failures.append("SandboxDescriptorRepository is not a runtime-recognized Protocol")
    if not runtime_sqlite_adapter_only:
        failures.append(
            "runtime sandbox descriptor module exposes an unexpected repository implementation"
        )

    repository_protocol_present = bool(
        structure["repository_protocol_present"] and runtime_protocol_present
    )
    sqlite_adapter_only = bool(
        structure["sqlite_adapter_only"] and runtime_sqlite_adapter_only
    )

    test_contract_valid, test_failures = validate_test_contracts(
        _read(repo_root / "tests/test_sandbox_descriptor_repository.py"),
        _read(repo_root / "tests/test_api_service.py"),
    )
    failures.extend(test_failures)

    protected_hashes_match, protected_failures = _validate_protected_hashes(
        repo_root, PROTECTED_HASHES
    )
    failures.extend(protected_failures)

    schema_valid, schema_failures = _validate_sqlite_schema()
    failures.extend(schema_failures)

    parent = production_identity_storage_pis_002_entry_decision_check.build_report(repo_root)
    failures.extend(f"PIS-002 entry decision: {failure}" for failure in parent["failures"])

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-002 repository governed tool count is {tool_count}, expected 24")

    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-002 repository check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require the PIS-002 repository check")
    if f"make {TARGET}" not in readme or DOC_REL not in readme:
        failures.append("README PIS-002 repository implementation wiring is incomplete")
    if DOC_REL not in docs_site:
        failures.append("PIS-002 repository implementation is missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-002 repository implementation is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing the PIS-002 repository implementation")

    candidate_commit = _git(repo_root, "rev-parse", "HEAD")
    candidate_tree_clean = not worktree_paths
    candidate_scope_valid = not scope_failures
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "implementation_doc": DOC_REL,
        "implementation_slice": "PIS-002-SD-001",
        "implementation_baseline_commit": BASELINE_COMMIT,
        "candidate_commit": candidate_commit,
        "candidate_tree_clean": candidate_tree_clean,
        "candidate_scope_valid": candidate_scope_valid,
        "selected_aggregate": "sandbox_descriptors",
        "repository_protocol_present": repository_protocol_present,
        "consumer_protocol_typing_valid": consumer_typing_valid,
        "sqlite_adapter_only": sqlite_adapter_only,
        "runtime_repository_implementations": runtime_implementations,
        "repository_test_contract_valid": test_contract_valid,
        "sqlite_schema_valid": schema_valid,
        "protected_hashes_match": protected_hashes_match,
        "tool_count": tool_count,
        "runtime_behavior_changes_allowed": False,
        "dependency_changes_allowed": False,
        "schema_changes_allowed": False,
        "audit_ordering_changes_allowed": False,
        "additional_aggregate_implementation_allowed": False,
        "runtime_postgres_allowed": False,
        "production_identity_allowed": False,
        "new_power_classes_allowed": False,
        "source_review_complete": False,
        "uat_required_now": False,
        "next_required_action": "review_pis_002_sd_001_exact_candidate",
    }


def validate_candidate_scope(
    *,
    committed_paths: list[str],
    worktree_paths: list[str],
    rename_records: list[str],
    require_clean: bool,
) -> list[str]:
    failures: list[str] = []
    if set(committed_paths) != EXPECTED_CHANGED_PATHS:
        missing = sorted(EXPECTED_CHANGED_PATHS - set(committed_paths))
        unexpected = sorted(set(committed_paths) - EXPECTED_CHANGED_PATHS)
        failures.append(
            "PIS-002 implementation changed-path inventory is not exact"
            f"; missing={missing}; unexpected={unexpected}"
        )
    if rename_records:
        failures.append(
            "PIS-002 implementation candidate contains rename/copy records: "
            + ", ".join(rename_records)
        )
    if require_clean and worktree_paths:
        failures.append(
            "PIS-002 exact-candidate check requires a clean working tree; changed="
            + ", ".join(worktree_paths)
        )
    return failures


def validate_repository_structure(source: str) -> dict[str, Any]:
    failures: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {
            "repository_protocol_present": False,
            "sqlite_adapter_only": False,
            "repository_implementations": [],
            "failures": ["sandbox descriptor repository source is not valid Python"],
        }

    classes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    protocol = classes.get("SandboxDescriptorRepository")
    protocol_methods = _class_methods(protocol) if protocol is not None else set()
    protocol_bases = {
        _qualified_name(base) for base in protocol.bases
    } if protocol is not None else set()
    repository_protocol_present = bool(
        protocol is not None
        and "Protocol" in protocol_bases
        and protocol_methods == REPOSITORY_METHODS
    )
    if not repository_protocol_present:
        failures.append(
            "SandboxDescriptorRepository must be a real Protocol with the exact repository methods"
        )

    implementations = sorted(
        name
        for name, node in classes.items()
        if name != "SandboxDescriptorRepository"
        and REPOSITORY_METHODS <= _class_methods(node)
    )
    sqlite_adapter_only = implementations == ["SandboxDescriptorStore"]
    if not sqlite_adapter_only:
        failures.append(
            "sandbox descriptor source must expose SandboxDescriptorStore as its sole repository "
            f"implementation; found={implementations}"
        )
    return {
        "repository_protocol_present": repository_protocol_present,
        "sqlite_adapter_only": sqlite_adapter_only,
        "repository_implementations": implementations,
        "failures": failures,
    }


def validate_consumer_typing(
    app_source: str, trusted_host_source: str
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        app_tree = ast.parse(app_source)
        trusted_tree = ast.parse(trusted_host_source)
    except SyntaxError:
        return False, ["sandbox descriptor consumer source is not valid Python"]

    construction_valid = any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "sandbox_descriptor_store"
        and _qualified_name(node.annotation) == "SandboxDescriptorRepository"
        and isinstance(node.value, ast.Call)
        and _qualified_name(node.value.func) == "SandboxDescriptorStore"
        for node in ast.walk(app_tree)
    )
    service_annotation_valid = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "__init__"
        and any(
            argument.arg == "descriptor_store"
            and argument.annotation is not None
            and _qualified_name(argument.annotation) == "SandboxDescriptorRepository"
            for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        )
        for node in ast.walk(trusted_tree)
    )
    if not construction_valid:
        failures.append(
            "application must type the constructed SandboxDescriptorStore through the repository"
        )
    if not service_annotation_valid:
        failures.append(
            "trusted-host promotion must type descriptor_store through the repository"
        )
    return construction_valid and service_annotation_valid, failures


def validate_test_contracts(
    repository_test_source: str, api_test_source: str
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        repository_tree = ast.parse(repository_test_source)
        api_tree = ast.parse(api_test_source)
    except SyntaxError:
        return False, ["PIS-002 focused test source is not valid Python"]
    repository_tests = {
        node.name
        for node in ast.walk(repository_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    api_tests = {
        node.name
        for node in ast.walk(api_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing_repository = sorted(EXPECTED_REPOSITORY_TESTS - repository_tests)
    missing_api = sorted(EXPECTED_API_TESTS - api_tests)
    if missing_repository:
        failures.append(f"PIS-002 repository parity tests are missing: {missing_repository}")
    if missing_api:
        failures.append(f"PIS-002 API parity tests are missing: {missing_api}")
    return not failures, failures


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "implementation_doc",
        "implementation_slice",
        "implementation_baseline_commit",
        "candidate_commit",
        "candidate_tree_clean",
        "candidate_scope_valid",
        "selected_aggregate",
        "repository_protocol_present",
        "consumer_protocol_typing_valid",
        "sqlite_adapter_only",
        "runtime_repository_implementations",
        "repository_test_contract_valid",
        "sqlite_schema_valid",
        "protected_hashes_match",
        "tool_count",
        "runtime_behavior_changes_allowed",
        "dependency_changes_allowed",
        "schema_changes_allowed",
        "audit_ordering_changes_allowed",
        "additional_aggregate_implementation_allowed",
        "runtime_postgres_allowed",
        "production_identity_allowed",
        "new_power_classes_allowed",
        "source_review_complete",
        "uat_required_now",
        "next_required_action",
    ]
    lines = ["Ithildin PIS-002 sandbox descriptor repository implementation check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _runtime_repository_implementations() -> list[str]:
    implementations: list[str] = []
    for name, value in vars(sandbox_descriptors_module).items():
        if (
            name != "SandboxDescriptorRepository"
            and inspect.isclass(value)
            and value.__module__ == sandbox_descriptors_module.__name__
            and all(callable(getattr(value, method, None)) for method in REPOSITORY_METHODS)
        ):
            implementations.append(name)
    return sorted(implementations)


def _class_methods(node: ast.ClassDef | None) -> set[str]:
    if node is None:
        return set()
    return {
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Subscript):
        return _qualified_name(node.value)
    return ""


def _validate_protected_hashes(
    repo_root: Path, expected_hashes: dict[str, str]
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for relative_path, expected_hash in expected_hashes.items():
        path = repo_root / relative_path
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual_hash != expected_hash:
            failures.append(f"protected entry-baseline file changed: {relative_path}")
    return not failures, failures


def _validate_sqlite_schema() -> tuple[bool, list[str]]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "ithildin.db"
        SandboxDescriptorStore(db_path).initialize()
        with sqlite3.connect(db_path) as connection:
            columns = [
                (str(row[1]), str(row[2]), int(row[3]), int(row[5]))
                for row in connection.execute(
                    "PRAGMA table_info(sandbox_descriptors)"
                ).fetchall()
            ]
            indexes = [
                (str(row[1]), int(row[2]), str(row[3]))
                for row in connection.execute(
                    "PRAGMA index_list(sandbox_descriptors)"
                ).fetchall()
            ]
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
    if columns != EXPECTED_COLUMNS:
        failures.append("sandbox_descriptors columns differ from the entry-baseline shape")
    if indexes != EXPECTED_INDEXES:
        failures.append("sandbox_descriptors indexes differ from the entry-baseline shape")
    if tables != [("sandbox_descriptors",)]:
        failures.append("sandbox descriptor adapter created an unexpected table")
    return not failures, failures


def _changed_paths(repo_root: Path) -> list[str]:
    output = _git(
        repo_root,
        "diff",
        "--no-renames",
        "--name-only",
        f"{BASELINE_COMMIT}..HEAD",
    )
    return sorted(line for line in output.splitlines() if line)


def _working_tree_changed_paths(repo_root: Path) -> list[str]:
    paths: set[str] = set()
    for arguments in [
        ("diff", "--no-renames", "--name-only"),
        ("diff", "--cached", "--no-renames", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ]:
        output = _git(repo_root, *arguments)
        paths.update(line for line in output.splitlines() if line)
    return sorted(paths)


def _rename_records(repo_root: Path) -> list[str]:
    output = _git(
        repo_root,
        "diff",
        "--name-status",
        "--find-renames",
        f"{BASELINE_COMMIT}..HEAD",
    )
    return sorted(
        line for line in output.splitlines() if line.startswith(("R", "C"))
    )


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).returncode == 0


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    manifests = payload.get("manifests") if isinstance(payload, dict) else None
    return len(manifests) if isinstance(manifests, list) else 0


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())
