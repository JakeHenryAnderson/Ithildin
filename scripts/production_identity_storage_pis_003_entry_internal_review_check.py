"""Validate the exact-candidate PIS-003 entry-decision source review."""

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

from scripts import production_identity_storage_pis_003_entry_decision_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-entry-internal-source-review.md"
)
REVIEW_DOC_TITLE = "Production Identity And Storage PIS-003 Entry Internal Source Review"
REVIEW_DOC_SHA256 = "939082ddd7c247227889dc974cdab5957687a52e60920d12f969fb0a5145db6c"
CONTRACT_REL = "docs/codex/production-identity-storage-pis-003-entry-review-authority.json"
CONTRACT_SHA256 = "455f9f1cacbc0c91a2776cb0bd9bf6a58c70ae9b6be0e54325dce83227019379"
TARGET = "production-identity-storage-pis-003-entry-internal-review-check"
BASELINE_COMMIT = "159bf93b4b1e3975d7cab615ef51d2e951f9a80a"
REVIEWED_COMMIT = "fe870f2b96aafeed8419e611a57c64756cfda79f"

REVIEWED_PATH_HASHES = {
    "Makefile": "6f5e283db1afa9bd9a72f98cee168cd0a2e2181c8ab8deecf678a3baca0c7b5e",
    "README.md": "6405c57cfa127b40fc2240a917dfa0fa9a16918b71082aa2052c89561c508388",
    "docs/codex/post-rc-decision-register.md": (
        "2a12a37fe36e32c0d28744fd59e9012b911a0402da5934da6d8ec660dc4e4576"
    ),
    "docs/codex/production-identity-storage-pis-003-entry-decision-record.md": (
        "1af9d450dac5214995adf34a3dabfd877b0e98bd1f5085263eafe496edf299f8"
    ),
    "docs/codex/production-identity-storage-pis-003-entry-decision.json": (
        "41f413e1d9532019d91aa39daaec13bdcf679a761bc4d73f8d9575a229fd9269"
    ),
    "docs/codex/review-docs-index.md": (
        "fbde051f793b2fce8092e640b74b7ea32b99763b80fbb789faf9f1d7c60f7aea"
    ),
    "scripts/build_docs_site.py": (
        "a57e16fa4667567ff519e24e2a79f7cc509612daf83124ce2617d38d4249524c"
    ),
    "scripts/production_identity_storage_pis_003_entry_decision_check.py": (
        "d3e8d30d8279b862688345e21f7ea31d8106345d107bb218dc5544cb8c77405c"
    ),
    "scripts/release_guardrails.py": (
        "ee1f4538f98465da9a7fecd59b404475062c9208cd675ca8984a356818e8e70c"
    ),
    "scripts/review_docs.py": (
        "6065a48c32f6d46cd27678e5310d234c68cde58d19ada3c4a5529c30a76becc7"
    ),
    "tests/test_release_readiness.py": (
        "9995c8eec0d0ec4d0fc8ae0996c9fb613841cebc59ad236c208efe6214f90dd1"
    ),
}

EXPECTED_FINDINGS = {"critical": 0, "high": 0, "medium": 0, "low": 0, "open": 0}

EXPECTED_AUTHORITY = {
    "pis_003_entry_source_review_complete": True,
    "pis_003_entry_decision_cleared": True,
    "pis_003_sd_pg_001_implementation_gate_preparation_allowed": True,
    "pis_003_sd_pg_001_implementation_allowed": False,
    "dependency_changes_allowed": False,
    "sqlalchemy_use_allowed": False,
    "alembic_use_allowed": False,
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

EXPECTED_SUPERSEDED_REVIEWS = [
    {
        "candidate_commit": "1f1670a7e7d729ddfc986b4e8f72a96847a0c543",
        "finding_count": 2,
        "maximum_severity": "medium",
    },
    {
        "candidate_commit": "bdb6b2cb46927cf7fbf0bbbdb7290b6739676a38",
        "finding_count": 1,
        "maximum_severity": "medium",
    },
]

REQUIRED_PHRASES = [
    "Status: `PIS-003` entry-decision exact-candidate source review complete; no open findings.",
    "Review ID: `PRD-PROD-IAM-STORAGE-PIS-003-ENTRY-REVIEW`.",
    (
        "Review disposition: "
        "`cleared_for_separate_pis_003_sd_pg_001_implementation_gate_preparation_only`."
    ),
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    f"Entry baseline commit: `{BASELINE_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "Current governed tool count: `24`.",
    "`pis_003_entry_source_review_complete: true`",
    "`pis_003_entry_decision_cleared: true`",
    "`pis_003_sd_pg_001_implementation_gate_preparation_allowed: true`",
    "`pis_003_sd_pg_001_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`database_connections_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`uat_required_now: false`",
    "The next allowed action is `prepare_pis_003_sd_pg_001_implementation_gate`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    f"make {TARGET}",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(
        r"\bpis-003(?:-sd-pg-001)? implementation "
        r"(?:is|has been) (?:approved|authorized)\b"
    ),
    re.compile(r"\bdependencies? may now be (?:added|changed|installed)\b"),
    re.compile(r"\bpostgres(?:ql)? may now (?:connect|run|serve|start)\b"),
    re.compile(r"\b(?:release|production promotion|uat) (?:is|has been) (?:approved|complete)\b"),
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
    lowered = normalized.lower()
    failures = [
        f"PIS-003 entry review is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]
    failures.extend(
        f"PIS-003 entry review contains forbidden authority pattern: {pattern.pattern}"
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS
        if pattern.search(lowered)
    )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "review_id",
        "parent_decision",
        "implementation_slice",
        "entry_baseline_commit",
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
        failures.append("PIS-003 entry review contract top-level keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "review_id": "PRD-PROD-IAM-STORAGE-PIS-003-ENTRY-REVIEW",
        "parent_decision": "PRD-PROD-IAM-STORAGE-PIS-003-ENTRY",
        "implementation_slice": "PIS-003-SD-PG-001",
        "entry_baseline_commit": BASELINE_COMMIT,
        "reviewed_commit": REVIEWED_COMMIT,
        "review_document_sha256": REVIEW_DOC_SHA256,
        "review_disposition": (
            "cleared_for_separate_pis_003_sd_pg_001_implementation_gate_preparation_only"
        ),
        "review_method": "independent_read_only_gpt_5_6_sol_xhigh_no_ultra",
        "next_required_action": "prepare_pis_003_sd_pg_001_implementation_gate",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 entry review field {key} is not {expected!r}")
    if contract.get("reviewed_path_hashes") != REVIEWED_PATH_HASHES:
        failures.append("PIS-003 entry review path/hash inventory is not exact")
    findings = contract.get("findings")
    if (
        findings != EXPECTED_FINDINGS
        or not isinstance(findings, dict)
        or any(type(value) is not int for value in findings.values())
    ):
        failures.append("PIS-003 entry review finding counts are not exact integers")
    if contract.get("closed_superseded_reviews") != EXPECTED_SUPERSEDED_REVIEWS:
        failures.append("PIS-003 superseded review history is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 entry review authority is not the exact closed Boolean map")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    review_bytes = _read_bytes(repo_root / REVIEW_DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        review_text = review_bytes.decode("utf-8")
    except UnicodeDecodeError:
        review_text = ""
        failures.append("PIS-003 entry internal review is not UTF-8")
    failures.extend(validate_review_text(review_text))
    review_hash = hashlib.sha256(review_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if review_hash != REVIEW_DOC_SHA256:
        failures.append("PIS-003 entry review bytes do not match the closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 entry review authority bytes do not match the closed digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    reviewed_exists = _commit_exists(repo_root, REVIEWED_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT)
    reviewed_is_ancestor = _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD")
    if not reviewed_exists:
        failures.append("PIS-003 reviewed candidate commit is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 reviewed candidate does not descend from entry baseline")
    if not reviewed_is_ancestor:
        failures.append("PIS-003 reviewed candidate is not an ancestor of HEAD")

    reviewed_paths = set(
        _git_lines(
            repo_root,
            "diff",
            "--name-only",
            f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}",
        )
    )
    reviewed_inventory_exact = reviewed_paths == set(REVIEWED_PATH_HASHES)
    if not reviewed_inventory_exact:
        failures.append("PIS-003 reviewed candidate path inventory is not exact")
    reviewed_hashes_match = True
    for path, expected_hash in REVIEWED_PATH_HASHES.items():
        reviewed_hash = hashlib.sha256(
            _git_bytes(repo_root, REVIEWED_COMMIT, path)
        ).hexdigest()
        if reviewed_hash != expected_hash:
            reviewed_hashes_match = False
            failures.append(f"PIS-003 reviewed candidate hash mismatch: {path}")

    entry = production_identity_storage_pis_003_entry_decision_check.build_report(repo_root)
    entry_valid = bool(
        entry["valid"]
        and entry["pis_003_entry_decision_recorded"]
        and entry["pis_003_sd_pg_001_selected"]
        and entry["implementation_gate_required"]
        and not entry["pis_003_sd_pg_001_implementation_allowed"]
        and not entry["dependency_changes_allowed"]
        and not entry["database_connections_allowed"]
        and not entry["runtime_postgres_allowed"]
    )
    if not entry_valid:
        failures.append("PIS-003 reviewed entry decision is not valid")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-003 entry review governed tool count is {tool_count}, expected 24")
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 entry internal review wiring is incomplete")

    gate_valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}
    raw_findings = contract.get("findings")
    findings: dict[str, Any] = raw_findings if isinstance(raw_findings, dict) else {}

    def allowed(name: str) -> bool:
        return bool(gate_valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": gate_valid,
        "failures": failures,
        "review_doc": REVIEW_DOC_REL,
        "review_document_sha256": review_hash,
        "review_document_hash_matches": review_hash == REVIEW_DOC_SHA256,
        "authority_contract": CONTRACT_REL,
        "authority_contract_sha256": contract_hash,
        "authority_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "reviewed_commit": REVIEWED_COMMIT,
        "reviewed_commit_exists": reviewed_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "reviewed_commit_is_ancestor": reviewed_is_ancestor,
        "reviewed_inventory_exact": reviewed_inventory_exact,
        "reviewed_path_count": len(reviewed_paths),
        "reviewed_hashes_match": reviewed_hashes_match,
        "entry_decision_valid": entry_valid,
        "critical_findings": findings.get("critical", -1) if gate_valid else -1,
        "high_findings": findings.get("high", -1) if gate_valid else -1,
        "medium_findings": findings.get("medium", -1) if gate_valid else -1,
        "low_findings": findings.get("low", -1) if gate_valid else -1,
        "open_findings": findings.get("open", -1) if gate_valid else -1,
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
        "review_doc",
        "reviewed_commit",
        "reviewed_commit_exists",
        "baseline_is_ancestor",
        "reviewed_commit_is_ancestor",
        "review_document_hash_matches",
        "authority_contract_hash_matches",
        "contract_valid",
        "reviewed_inventory_exact",
        "reviewed_path_count",
        "reviewed_hashes_match",
        "entry_decision_valid",
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
    lines = ["Ithildin PIS-003 entry-decision internal source review check"]
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
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
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
            "Current PIS-003 entry-decision review" in register,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 entry review authority contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 entry review authority has {exc}"]
        return {}, ["PIS-003 entry review authority is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 entry review authority must be a JSON object"]
    return payload, []


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _git_lines(repo_root: Path, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments], cwd=repo_root, check=False, capture_output=True, text=True
    )
    return [line for line in result.stdout.splitlines() if line]


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
