"""Validate the bounded PIS-002 repository-interface entry decision."""

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

from scripts import production_identity_storage_pis_001_internal_review_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-002-entry-decision-record.md"
DOC_NAME = "production-identity-storage-pis-002-entry-decision-record.md"
DOC_TITLE = "Production Identity And Storage PIS-002 Entry Decision Record"
CONTRACT_REL = "docs/codex/production-identity-storage-pis-002-entry-decision.json"
TARGET = "production-identity-storage-pis-002-entry-decision-check"
BASELINE_COMMIT = "1f3945b116be9c68c282d0b8f191f39fb9787006"

EXPECTED_AGGREGATE = {
    "aggregate_id": "sandbox_descriptors",
    "store_symbol": "ithildin_api.sandbox_descriptors.SandboxDescriptorStore",
    "table_names": ["sandbox_descriptors"],
    "public_routes": [
        "POST /sandbox-descriptors",
        "GET /sandbox-descriptors",
        "GET /sandbox-descriptors/{descriptor_id}",
    ],
    "authority_consumers": [
        "TrustedHostPromotionService.create_proposal",
        "TrustedHostPromotionService._authority_snapshot",
    ],
    "current_audit_ordering": "descriptor_commit_then_audit_write",
    "schema_changes_allowed": False,
}

EXPECTED_SLICE = {
    "slice_id": "PIS-002-SD-001",
    "repository_protocol_allowed": True,
    "sqlite_adapter_required": True,
    "general_transaction_manager_allowed": False,
    "sqlalchemy_decision": "deferred_until_first_aggregate_exact_candidate_review",
    "allowed_code_paths": [
        "apps/api/src/ithildin_api/sandbox_descriptors.py",
        "apps/api/src/ithildin_api/app.py",
        "apps/api/src/ithildin_api/trusted_host_promotions.py",
        "tests/test_sandbox_descriptor_repository.py",
        "tests/test_api_service.py",
    ],
    "required_evidence": [
        "repository_contract_parity",
        "persisted_record_parity",
        "public_route_parity",
        "audit_failure_ordering_parity",
        "audit_event_metadata_parity",
        "trusted_host_authority_parity",
        "restart_and_existing_database_parity",
        "dependency_and_schema_invariance",
        "rollback_without_data_migration",
    ],
    "rollback": "revert_interface_and_adapter_commit_without_schema_or_data_conversion",
}

EXPECTED_AUTHORITY = {
    "pis_002_entry_decision_recorded": True,
    "pis_002_bounded_implementation_allowed": True,
    "additional_aggregate_implementation_allowed": False,
    "runtime_behavior_changes_allowed": False,
    "dependency_changes_allowed": False,
    "sqlalchemy_allowed": False,
    "public_api_changes_allowed": False,
    "schema_changes_allowed": False,
    "database_migrations_allowed": False,
    "audit_ordering_changes_allowed": False,
    "production_identity_allowed": False,
    "enterprise_rbac_allowed": False,
    "remote_admin_allowed": False,
    "runtime_postgres_allowed": False,
    "backup_restore_runtime_allowed": False,
    "retention_enforcement_allowed": False,
    "new_power_classes_allowed": False,
    "public_security_product_positioning_allowed": False,
    "uat_required_now": False,
}

EXPECTED_RESIDUALS = {
    "descriptor_can_remain_committed_after_audit_failure": (
        "accepted_preserved_current_behavior"
    ),
    "created_at_desc_has_no_secondary_tiebreaker": (
        "accepted_preserved_current_behavior"
    ),
    "sqlite_is_only_supported_runtime_backend": "required",
}

EXPECTED_BASELINE_HASHES = {
    "apps/api/src/ithildin_api/sandbox_descriptors.py": (
        "9f9fd1b121f6672c86beb3605e3230e26f95f00f742b02c931763de7f26527fc"
    ),
    "apps/api/src/ithildin_api/app.py": (
        "9c1c52d071c8e2dc62150a08ed6de65d364d914a432bbbf5cd34d93157858cb4"
    ),
    "apps/api/src/ithildin_api/trusted_host_promotions.py": (
        "33b14e27df14dc5a22d53d01aa97177b90d7f9642dac383d5f744541bdbad190"
    ),
    "tests/test_api_service.py": (
        "2fcc0c53ab3bbf8ec449a0ee49743f517bb3208c5639c2f0c7362d1bc54c5f07"
    ),
    "pyproject.toml": (
        "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d"
    ),
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

REQUIRED_PHRASES = [
    (
        "Status: committed `PIS-002` entry decision for one bounded dependency-free "
        "repository-interface implementation slice."
    ),
    "Decision ID: `PRD-PROD-IAM-STORAGE-PIS-002-ENTRY`.",
    "Parent decision: `PRD-PROD-IAM-STORAGE-PIS-001`.",
    (
        "Decision outcome: "
        "`approved_for_bounded_dependency_free_repository_interface_implementation`."
    ),
    "Implementation slice: `PIS-002-SD-001`.",
    f"Entry baseline commit: `{BASELINE_COMMIT}`.",
    "Current governed tool count: `24`.",
    "Current `ERG-006` status: `planning_only`.",
    "Current `ERG-007` status: `planning_only`.",
    "The selected aggregate is `sandbox_descriptors`.",
    "Current audit ordering: `descriptor_commit_then_audit_write`.",
    "audit failure can leave the descriptor committed while the request fails",
    "Interface work begins without a dependency change.",
    "SQLAlchemy 2.0 Core remains `recommended_deferred`",
    "Rollback is `revert_interface_and_adapter_commit_without_schema_or_data_conversion`.",
    "`pis_002_bounded_implementation_allowed: true` for `PIS-002-SD-001` only",
    "`additional_aggregate_implementation_allowed: false`",
    "`runtime_behavior_changes_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`sqlalchemy_allowed: false`",
    "`schema_changes_allowed: false`",
    "`audit_ordering_changes_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`new_power_classes_allowed: false`",
    "`uat_required_now: false`",
    "implement_pis_002_sandbox_descriptor_repository_boundary",
    f"make {TARGET}",
]

FORBIDDEN_PHRASES = [
    "sqlalchemy is approved",
    "dependency changes are approved",
    "public api changes are approved",
    "schema changes are approved",
    "audit ordering changes are approved",
    "runtime postgresql is approved",
    "production identity is approved",
    "enterprise rbac is approved",
    "additional aggregates are approved",
    "uat is complete",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(
        r"\bdependencies?\b.{0,40}\b(?:may|can)\b.{0,32}"
        r"\b(?:be )?(?:added|changed|installed|introduced|updated)\b"
    ),
    re.compile(
        r"\bsqlalchemy\b.{0,40}\b(?:may|can)\b.{0,32}"
        r"\b(?:be )?(?:added|installed|introduced|used)\b"
    ),
    re.compile(
        r"\b(?:may|can)\b.{0,32}\b(?:add|install|introduce|use)\b"
        r".{0,16}\bsqlalchemy\b"
    ),
    re.compile(
        r"\b(?:public api|schema|migration|audit ordering|audit commit ordering)\b"
        r".{0,40}\b(?:may|can)\b.{0,32}"
        r"\b(?:be )?(?:altered|changed|introduced|reordered|started)\b"
    ),
    re.compile(
        r"\b(?:may|can)\b.{0,32}\b(?:alter|change|introduce|start)\b"
        r".{0,32}\b(?:public api|schema|migration)\b"
    ),
    re.compile(
        r"\b(?:additional|another|second)\b.{0,20}\baggregate\b.{0,40}"
        r"\b(?:may|can)\b.{0,32}\b(?:be )?(?:added|implemented|migrated|started)\b"
    ),
    re.compile(
        r"\b(?:approvals?|missions?|nodes?|patches?|audit events?)\b.{0,40}"
        r"\b(?:may|can)\b.{0,32}\b(?:be )?"
        r"(?:changed|extracted|implemented|migrated|refactored)\b"
    ),
    re.compile(
        r"\b(?:may|can)\b.{0,32}\b(?:change|extract|implement|migrate|refactor)\b"
        r".{0,32}\b(?:approvals?|missions?|nodes?|patches?|audit events?)\b"
    ),
    re.compile(
        r"\b(?:runtime postgresql|production identity|enterprise rbac|remote admin)\b"
        r".{0,40}\b(?:may|can)\b.{0,32}"
        r"\b(?:be )?(?:added|enabled|implemented|introduced|started|used)\b"
    ),
    re.compile(
        r"\b(?:descriptor and audit commits|audit and descriptor commits)\b.{0,40}"
        r"\b(?:may|can)\b.{0,32}\b(?:be )?(?:changed|reordered)\b"
    ),
    re.compile(
        r"\b(?:may|can)\b.{0,32}\b(?:change|reorder)\b.{0,32}"
        r"\b(?:descriptor and audit commits|audit and descriptor commits|audit ordering)\b"
    ),
    re.compile(
        r"\b(?:new governed powers?|new governed tool powers?|new power classes?)\b"
        r".{0,40}\b(?:may|can)\b.{0,32}"
        r"\b(?:be )?(?:added|enabled|introduced|used)\b"
    ),
]


def validate_decision_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    for phrase in REQUIRED_PHRASES:
        if " ".join(phrase.split()) not in normalized:
            failures.append(f"PIS-002 entry decision is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"PIS-002 entry decision contains forbidden phrase: {phrase}")
    for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
        if pattern.search(lowered):
            failures.append(
                "PIS-002 entry decision contains forbidden authority pattern: "
                f"{pattern.pattern}"
            )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "decision_id",
        "parent_decision",
        "decision_outcome",
        "entry_baseline_commit",
        "tool_count",
        "selected_aggregate",
        "implementation_slice",
        "baseline_hashes",
        "authority",
        "preserved_residuals",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-002 entry contract top-level keys are not the closed schema")
    expected_scalars = {
        "schema_version": "1",
        "decision_id": "PRD-PROD-IAM-STORAGE-PIS-002-ENTRY",
        "parent_decision": "PRD-PROD-IAM-STORAGE-PIS-001",
        "decision_outcome": (
            "approved_for_bounded_dependency_free_repository_interface_implementation"
        ),
        "entry_baseline_commit": BASELINE_COMMIT,
        "tool_count": 24,
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-002 entry contract field {key} is not {expected!r}")
    if type(contract.get("tool_count")) is not int:
        failures.append("PIS-002 entry contract tool_count must be an exact integer")
    if not _closed_equal(contract.get("selected_aggregate"), EXPECTED_AGGREGATE):
        failures.append(
            "PIS-002 entry selected aggregate is not the closed sandbox descriptor seam"
        )
    if not _closed_equal(contract.get("implementation_slice"), EXPECTED_SLICE):
        failures.append("PIS-002 entry implementation slice is not the closed bounded slice")
    authority = contract.get("authority")
    if (
        not isinstance(authority, dict)
        or set(authority) != set(EXPECTED_AUTHORITY)
        or any(type(authority.get(key)) is not bool for key in EXPECTED_AUTHORITY)
        or authority != EXPECTED_AUTHORITY
    ):
        failures.append("PIS-002 entry authority map is not the exact closed map")
    if not _closed_equal(contract.get("preserved_residuals"), EXPECTED_RESIDUALS):
        failures.append("PIS-002 entry preserved residuals are not the exact closed set")
    if not _closed_equal(contract.get("baseline_hashes"), EXPECTED_BASELINE_HASHES):
        failures.append("PIS-002 entry baseline hashes are not the exact closed snapshot")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    if not doc_path.exists():
        failures.append("PIS-002 entry decision record is missing")
    failures.extend(validate_decision_text(text))

    contract, contract_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_validation_failures = validate_contract(contract)
    failures.extend(contract_failures)
    failures.extend(contract_validation_failures)

    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, "HEAD")
    if not baseline_is_ancestor:
        failures.append("PIS-002 entry baseline commit is not an ancestor of current HEAD")

    baseline_hashes_match = True
    for relative_path, expected_hash in EXPECTED_BASELINE_HASHES.items():
        baseline_bytes = _git_show(repo_root, BASELINE_COMMIT, relative_path)
        if baseline_bytes is None:
            baseline_hashes_match = False
            failures.append(f"PIS-002 entry baseline path is unavailable: {relative_path}")
            continue
        if hashlib.sha256(baseline_bytes).hexdigest() != expected_hash:
            baseline_hashes_match = False
            failures.append(f"PIS-002 entry baseline hash is invalid: {relative_path}")

    pis_001_review = production_identity_storage_pis_001_internal_review_check.build_report(
        repo_root
    )
    failures.extend(f"PIS-001 review: {failure}" for failure in pis_001_review["failures"])
    if pis_001_review.get("open_findings") != 0:
        failures.append("PIS-001 exact-candidate review has open findings")
    if pis_001_review.get("pis_002_entry_decision_record_preparation_allowed") is not True:
        failures.append("PIS-001 review does not permit the PIS-002 entry decision")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-002 entry governed tool count is {tool_count}, expected 24")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    for linked_text, label in [
        (readme, "README"),
        (docs_site, "docs site"),
        (review_index, "review-docs index"),
        (decision_register, "post-RC decision register"),
    ]:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{label} is missing the PIS-002 entry decision pointer")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-002 entry decision is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing the PIS-002 entry decision title")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-002 entry decision check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require the PIS-002 entry decision check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the PIS-002 entry decision command")
    if CONTRACT_REL not in text or CONTRACT_REL not in readme:
        failures.append("PIS-002 machine-readable contract pointer is incomplete")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_doc": DOC_REL,
        "decision_id": "PRD-PROD-IAM-STORAGE-PIS-002-ENTRY",
        "decision_outcome": (
            "approved_for_bounded_dependency_free_repository_interface_implementation"
        ),
        "entry_baseline_commit": BASELINE_COMMIT,
        "baseline_is_ancestor": baseline_is_ancestor,
        "baseline_hashes_match": baseline_hashes_match,
        "contract_valid": not contract_failures and not contract_validation_failures,
        "tool_count": tool_count,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "selected_aggregate": "sandbox_descriptors",
        "implementation_slice": "PIS-002-SD-001",
        "pis_002_bounded_implementation_allowed": True,
        "additional_aggregate_implementation_allowed": False,
        "runtime_behavior_changes_allowed": False,
        "dependency_changes_allowed": False,
        "sqlalchemy_allowed": False,
        "schema_changes_allowed": False,
        "database_migrations_allowed": False,
        "audit_ordering_changes_allowed": False,
        "runtime_postgres_allowed": False,
        "production_identity_allowed": False,
        "new_power_classes_allowed": False,
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "decision_doc",
        "decision_id",
        "decision_outcome",
        "entry_baseline_commit",
        "baseline_is_ancestor",
        "baseline_hashes_match",
        "contract_valid",
        "tool_count",
        "erg_006_status",
        "erg_007_status",
        "selected_aggregate",
        "implementation_slice",
        "pis_002_bounded_implementation_allowed",
        "additional_aggregate_implementation_allowed",
        "runtime_behavior_changes_allowed",
        "dependency_changes_allowed",
        "sqlalchemy_allowed",
        "schema_changes_allowed",
        "database_migrations_allowed",
        "audit_ordering_changes_allowed",
        "runtime_postgres_allowed",
        "production_identity_allowed",
        "new_power_classes_allowed",
        "uat_required_now",
    ]
    lines = ["Ithildin production identity/storage PIS-002 entry decision check"]
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
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_closed_object,
        )
    except FileNotFoundError:
        return {}, ["PIS-002 entry contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-002 entry contract has {exc}"]
        return {}, ["PIS-002 entry contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-002 entry contract must be a JSON object"]
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
            _closed_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def _git_show(repo_root: Path, commit: str, relative_path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


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


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return -1
    manifests = payload.get("manifests")
    return len(manifests) if isinstance(manifests, list) else -1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


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


if __name__ == "__main__":
    raise SystemExit(main())
