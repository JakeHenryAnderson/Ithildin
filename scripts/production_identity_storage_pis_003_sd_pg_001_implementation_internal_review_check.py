"""Validate the exact-candidate PIS-003 SD-PG-001 offline implementation review."""

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

from scripts import (
    production_identity_storage_pis_003_sd_pg_001_implementation_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "implementation-internal-source-review.md"
)
REVIEW_DOC_TITLE = (
    "Production Identity And Storage PIS-003 SD-PG-001 Offline Implementation "
    "Internal Source Review"
)
REVIEW_DOC_SHA256 = "aec09c328470b4352b097e89c3d8f3068745a4fc72c0daa284040c8c113918af"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "implementation-review-authority.json"
)
CONTRACT_SHA256 = "e5d573a28272fc25046fa3c7c7810d03770fde485fb5aa5ad4d7860d5d668602"
TARGET = "production-identity-storage-pis-003-sd-pg-001-implementation-internal-review-check"
BASELINE_COMMIT = "21cc758e2dd438c10f852574528f3ea971825b55"
SUPERSEDED_COMMIT = "26ead3f95f7f72fb8c3047c68a0ecce9586743d6"
REVIEWED_COMMIT = "ba60478ede66abce519e134981fcabcb3f68482f"

REVIEWED_PATH_HASHES = {
    "Makefile": "61694e55759923a18a422a64f1fead5c43a66549152de07469b0f097250b6c9d",
    "README.md": "6f637928394402b14da17ff0468b2dc70678a2bb746bf407376a7dfba9b0e6e9",
    "apps/api/src/ithildin_api/storage_import.py": (
        "854ac31a7c23c4f3c680daa0bc3f16507cacb5003fc61d7632e16b7c36cfb65d"
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
    "docs/codex/post-rc-decision-register.md": (
        "aa28b5019a9725e394a79b49d3ed4f2b60bb3cda4d275f1994ddd05389f976af"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "implementation-authority.json"
    ): "f4dc1e5d4ca8cf589ffb9ddfbd20aae4c4c0e94216fc41668179d0db10c6bb3d",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "implementation-record.md"
    ): "38b2f3425feb8b080caced5121e17f0f648d6d68893915c70366815c06faa945",
    "docs/codex/review-docs-index.md": (
        "e6248e0cb3bf2e7d25fc4b7575e4768b27023e731f60bf4618336225e5657812"
    ),
    "pyproject.toml": "8f260ab9cc8508cbe856258e86bc7960a7ee073156fe4c2981e0f6854e381627",
    "scripts/build_docs_site.py": (
        "aba6249dee1458cd39a3d0ff83151cc4304c9a61e9b6d0547cb4f7f0aaae863c"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_implementation_check.py"
    ): "6db5fca5a502b0f3f9f39296c6f79cd0b502cf30075586c6d55b95d6e5bf5bfa",
    "scripts/release_guardrails.py": (
        "b571410f1022a6ee85078f6f4770a9c8d46a0bb89e28fde9c172ebe1b16e182b"
    ),
    "scripts/review_docs.py": (
        "a606dc18a774daba3e0861476756345154fe30c6f3b1927f8f33fcf0e216cc74"
    ),
    "tests/test_release_readiness.py": (
        "3336e3681811c031eb536bdc6c1ab62487da2c146111be1eac424a1b2e263180"
    ),
    "tests/test_storage_schema_import.py": (
        "a1e6eaec5b119411e9f42cc07915e5c3733fb5278b109e413a8737fedebf5277"
    ),
    "uv.lock": "a0ea98764d069193226a9debe837f37655ee707cb17dcdf6731b922883a4dafb",
}

EXPECTED_FINDINGS = {"critical": 0, "high": 0, "medium": 0, "low": 0, "open": 0}
EXPECTED_SUPERSEDED_REVIEWS = [
    {
        "candidate_commit": SUPERSEDED_COMMIT,
        "finding_count": 1,
        "maximum_severity": "medium",
    }
]
EXPECTED_AUTHORITY = {
    "pis_003_sd_pg_001_offline_implementation_recorded": True,
    "pis_003_sd_pg_001_offline_candidate_complete": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": True,
    "dependency_lock_delta_implemented": True,
    "offline_schema_implemented": True,
    "offline_migration_implemented": True,
    "validated_importer_implemented": True,
    "refusing_test_harness_contract_implemented": True,
    "psycopg_plain_sync_dependency_installed": True,
    "connection_evidence_gate_preparation_allowed": True,
    "connection_evidence_gate_required": True,
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
    "release_allowed": False,
    "production_promotion_allowed": False,
    "uat_complete": False,
    "uat_required_now": False,
}

REQUIRED_PHRASES = [
    (
        "Status: `PIS-003-SD-PG-001` offline implementation exact-candidate source review "
        "complete; no open findings."
    ),
    "Review ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION-REVIEW`.",
    "Review disposition: `cleared_for_connection_evidence_gate_preparation_only`.",
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    f"Implementation baseline commit: `{BASELINE_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "Current governed tool count: `24`.",
    "`exact_candidate_source_review_complete: true`",
    "`connection_evidence_gate_preparation_allowed: true`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    (
        "The next allowed action is "
        "`prepare_pis_003_sd_pg_001_connection_evidence_gate`."
    ),
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


def validate_review_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [
        f"PIS-003 offline implementation review is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "review_id",
        "parent_implementation",
        "implementation_baseline_commit",
        "superseded_candidate_commit",
        "reviewed_commit",
        "review_document_sha256",
        "review_disposition",
        "review_method",
        "reviewed_path_hashes",
        "findings",
        "closed_superseded_reviews",
        "authority",
        "next_required_action",
    }
    if set(contract) != expected_keys:
        failures.append("PIS-003 offline implementation review contract keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "review_id": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION-REVIEW"
        ),
        "parent_implementation": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-OFFLINE-IMPLEMENTATION"
        ),
        "implementation_baseline_commit": BASELINE_COMMIT,
        "superseded_candidate_commit": SUPERSEDED_COMMIT,
        "reviewed_commit": REVIEWED_COMMIT,
        "review_document_sha256": REVIEW_DOC_SHA256,
        "review_disposition": "cleared_for_connection_evidence_gate_preparation_only",
        "review_method": "independent_read_only_gpt_5_6_sol_xhigh_no_ultra",
        "next_required_action": "prepare_pis_003_sd_pg_001_connection_evidence_gate",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 offline implementation review field {key} is not exact")
    if contract.get("reviewed_path_hashes") != REVIEWED_PATH_HASHES:
        failures.append("PIS-003 offline implementation review path/hash inventory is not exact")
    findings = contract.get("findings")
    if (
        findings != EXPECTED_FINDINGS
        or not isinstance(findings, dict)
        or any(type(value) is not int for value in findings.values())
    ):
        failures.append("PIS-003 offline implementation review findings are not exact integers")
    if contract.get("closed_superseded_reviews") != EXPECTED_SUPERSEDED_REVIEWS:
        failures.append("PIS-003 offline implementation superseded review history is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 offline implementation review authority is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    review_bytes = _read_bytes(repo_root / REVIEW_DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        review_text = review_bytes.decode("utf-8")
    except UnicodeDecodeError:
        review_text = ""
        failures.append("PIS-003 offline implementation review is not UTF-8")
    failures.extend(validate_review_text(review_text))
    review_hash = hashlib.sha256(review_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if review_hash != REVIEW_DOC_SHA256:
        failures.append("PIS-003 offline implementation review does not match its digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 offline implementation review contract digest is invalid")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    reviewed_exists = _commit_exists(repo_root, REVIEWED_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT)
    reviewed_is_ancestor = _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD")
    lineage_exact = bool(
        _git(repo_root, "rev-parse", f"{REVIEWED_COMMIT}^") == SUPERSEDED_COMMIT
        and _git(repo_root, "rev-parse", f"{SUPERSEDED_COMMIT}^") == BASELINE_COMMIT
    )
    if not reviewed_exists:
        failures.append("PIS-003 offline implementation reviewed commit is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 offline implementation review baseline ancestry is invalid")
    if not reviewed_is_ancestor:
        failures.append("PIS-003 offline implementation reviewed commit is not an ancestor of HEAD")
    if not lineage_exact:
        failures.append("PIS-003 offline implementation reviewed lineage is not exact")

    reviewed_paths = set(
        _git_lines(repo_root, "diff", "--name-only", f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}")
    )
    reviewed_inventory_exact = reviewed_paths == set(REVIEWED_PATH_HASHES)
    if not reviewed_inventory_exact:
        failures.append("PIS-003 offline implementation reviewed path inventory is not exact")
    reviewed_hashes_match = True
    for path, expected_hash in REVIEWED_PATH_HASHES.items():
        actual_hash = hashlib.sha256(_git_bytes(repo_root, REVIEWED_COMMIT, path)).hexdigest()
        if actual_hash != expected_hash:
            reviewed_hashes_match = False
            failures.append(f"PIS-003 offline implementation reviewed hash mismatch: {path}")

    implementation = production_identity_storage_pis_003_sd_pg_001_implementation_check
    historical_doc = _git_bytes(repo_root, REVIEWED_COMMIT, implementation.DOC_REL)
    historical_contract_bytes = _git_bytes(repo_root, REVIEWED_COMMIT, implementation.CONTRACT_REL)
    historical_contract = _load_json_bytes(historical_contract_bytes)
    reviewed_implementation_artifacts_valid = bool(
        hashlib.sha256(historical_doc).hexdigest() == implementation.DOC_SHA256
        and hashlib.sha256(historical_contract_bytes).hexdigest() == implementation.CONTRACT_SHA256
        and not implementation.validate_document(historical_doc.decode("utf-8"))
        and not implementation.validate_contract(historical_contract)
    )
    implementation_report = implementation.build_report(repo_root)
    implementation_check_valid = bool(
        implementation_report.get("valid")
        and implementation_report.get("candidate_commit") == REVIEWED_COMMIT
        and implementation_report.get("candidate_inventory_exact")
        and not implementation_report.get("database_connections_allowed")
        and not implementation_report.get("migration_execution_allowed")
    )
    if not reviewed_implementation_artifacts_valid:
        failures.append("PIS-003 reviewed historical implementation artifacts are invalid")
    if not implementation_check_valid:
        failures.append("PIS-003 offline implementation prerequisite is invalid")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(
            f"PIS-003 offline implementation review tool count is {tool_count}, expected 24"
        )
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 offline implementation review wiring is incomplete")

    valid = not failures
    authority = contract.get("authority")
    authority = authority if isinstance(authority, dict) else {}
    findings = contract.get("findings")
    findings = findings if isinstance(findings, dict) else {}

    def allowed(name: str) -> bool:
        return bool(valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "review_doc": REVIEW_DOC_REL,
        "review_document_sha256": review_hash,
        "review_document_hash_matches": review_hash == REVIEW_DOC_SHA256,
        "authority_contract": CONTRACT_REL,
        "authority_contract_sha256": contract_hash,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "review_disposition": contract.get("review_disposition") if valid else "invalid",
        "reviewed_commit": REVIEWED_COMMIT,
        "reviewed_commit_exists": reviewed_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "reviewed_commit_is_ancestor": reviewed_is_ancestor,
        "lineage_exact": lineage_exact,
        "reviewed_inventory_exact": reviewed_inventory_exact,
        "reviewed_path_count": len(reviewed_paths),
        "reviewed_hashes_match": reviewed_hashes_match,
        "reviewed_implementation_artifacts_valid": reviewed_implementation_artifacts_valid,
        "implementation_check_valid": implementation_check_valid,
        "critical_findings": findings.get("critical", -1) if valid else -1,
        "high_findings": findings.get("high", -1) if valid else -1,
        "medium_findings": findings.get("medium", -1) if valid else -1,
        "low_findings": findings.get("low", -1) if valid else -1,
        "open_findings": findings.get("open", -1) if valid else -1,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": contract.get("next_required_action") if valid else "invalid_gate",
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "review_doc",
        "review_disposition",
        "reviewed_commit",
        "reviewed_commit_exists",
        "baseline_is_ancestor",
        "reviewed_commit_is_ancestor",
        "lineage_exact",
        "review_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "reviewed_inventory_exact",
        "reviewed_path_count",
        "reviewed_hashes_match",
        "reviewed_implementation_artifacts_valid",
        "implementation_check_valid",
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
        "open_findings",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 offline implementation internal source review check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    return all(
        (
            f"{TARGET}:" in makefile,
            f"release-check: {TARGET}" in makefile,
            f"make {TARGET}" in readme,
            REVIEW_DOC_REL in readme,
            CONTRACT_REL in readme,
            REVIEW_DOC_REL in docs_site,
            REVIEW_DOC_TITLE in review_index,
            TARGET in release_guardrails,
            REVIEW_DOC_REL in review_docs.REVIEW_DOCS,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 offline implementation review contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 offline implementation review contract has {exc}"]
        return {}, ["PIS-003 offline implementation review contract is invalid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 offline implementation review contract must be a JSON object"]
    return payload, []


def _load_json_bytes(value: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(value.decode("utf-8"), object_pairs_hook=_closed_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _git(repo_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo_root, check=False, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_lines(repo_root: Path, *arguments: str) -> list[str]:
    return [line for line in _git(repo_root, *arguments).splitlines() if line]


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
