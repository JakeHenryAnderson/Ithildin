"""Validate the exact-candidate PIS-003 SD-PG-001 implementation-gate review."""

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
    production_identity_storage_pis_003_entry_internal_review_check,
    production_identity_storage_pis_003_sd_pg_001_implementation_gate_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "implementation-gate-internal-source-review.md"
)
REVIEW_DOC_TITLE = (
    "Production Identity And Storage PIS-003 SD-PG-001 Implementation Gate Internal Source Review"
)
REVIEW_DOC_SHA256 = "830ab095b8bd7a77d9017c828fa87404d772ad82146aa1e415fba671b2cc4dbd"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "implementation-gate-review-authority.json"
)
CONTRACT_SHA256 = "e58fc6c5ecf22ad4149b4f9fb6342b6b34b41a57102c6d113f36d60cead06b69"
TARGET = "production-identity-storage-pis-003-sd-pg-001-implementation-gate-internal-review-check"
BASELINE_COMMIT = "ebb656ac8e5b0f428641092135d7e99b5845fa85"
FAILED_COMMIT = "f0c5475e28ea37503b6bb4154711387c96584c92"
REVIEWED_COMMIT = "9f347fafac24f3f8bab002f30b46939846c985ab"

REVIEWED_PATH_HASHES = {
    "Makefile": "90a4f51c472493e66b76d1751699ca34e580149cba032b360be758812ba43d8c",
    "README.md": "daeabfae9dca163f0e1ea359e97db9838dad4a064726d47815afe95bad9851d8",
    "docs/codex/post-rc-decision-register.md": (
        "d6b78d33ac4bcf59a1aae291e5bc5e2cc5a8c80a6434ea0b5376420af3d09727"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-gate.json"
    ): "b670118ca53b6701a30bbb0b4692f15caf704267ebd468a7db3843d769e2e1fd",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-implementation-gate.md"
    ): "42bb379ab0afee8507555e971febecd55904f41695bec16d7ceb2e91112a51f7",
    "docs/codex/review-docs-index.md": (
        "dfe788304eea66a9b152fea6d2d88f1ca3a98abe77b5a4f28cbebb438c843422"
    ),
    "scripts/build_docs_site.py": (
        "f5cd9d0ecdf3088fafb94f1b66d552ed193d7de43d54140acf114151fadc7023"
    ),
    "scripts/production_identity_storage_pis_001_decision_check.py": (
        "0061fda48e6cf34f636a33af6de789f96223fe267743ba5c34e7e683eae2fade"
    ),
    "scripts/production_identity_storage_pis_001_internal_review_check.py": (
        "b55267fb3b41729ad04ebb3dadfd386c7e28eeed09e159c29ae432baaa194cef"
    ),
    "scripts/production_identity_storage_pis_002_continuation_decision_check.py": (
        "e263bcf92bec46c6b3c0b39d172a5e9c8e53cf88f65cd18d5da116720885f5d2"
    ),
    (
        "scripts/production_identity_storage_pis_002_sandbox_descriptor_repository_check.py"
    ): "ec5a987387772f47eb68b1e66dc11cded7b5ab7c9eafcd0d22cac1bdf0f9f16a",
    (
        "scripts/production_identity_storage_pis_002_"
        "sandbox_descriptor_repository_internal_review_check.py"
    ): "3cfb5cba464d644e7dba52491320a141e4d48046d759b4239ad47497eeb4c2e9",
    "scripts/production_identity_storage_pis_003_entry_decision_check.py": (
        "5eb9c13f0cf91e1bc4b09d5b55a19f89544e383b8a40e24feb156e0a1cfbcd0d"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_implementation_gate_check.py"
    ): "d2b5d073afc0e1e59c3cf815bd7b81d369ad893b2cd64b4b6553d3478e102a31",
    "scripts/release_guardrails.py": (
        "f6d4243bbf297a2145a2c9fc89404072d9342ab2b692ab88fb64ef6f07003a1d"
    ),
    "scripts/review_docs.py": ("5aaeab2f654deb398211395dc701e885f2509c7e6c90a457a30893ddcf34faae"),
    "tests/test_release_readiness.py": (
        "a04de3813c20b6eecd37e40d11a5ac87a05db17919e977970599b89aa22f2d44"
    ),
}

EXPECTED_FINDINGS = {"critical": 0, "high": 0, "medium": 0, "low": 0, "open": 0}
EXPECTED_AUTHORITY = (
    production_identity_storage_pis_003_sd_pg_001_implementation_gate_check
    .EXPECTED_POST_REVIEW_AUTHORITY_CEILING
)
EXPECTED_SUPERSEDED_REVIEWS = [
    {
        "candidate_commit": FAILED_COMMIT,
        "finding_count": 2,
        "maximum_severity": "medium",
    }
]

REQUIRED_PHRASES = [
    (
        "Status: `PIS-003-SD-PG-001` implementation-gate exact-candidate source review "
        "complete; no open findings."
    ),
    ("Review ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE-REVIEW`."),
    "Review disposition: `cleared_for_offline_implementation_only`.",
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    f"Gate baseline commit: `{BASELINE_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "Current governed tool count: `24`.",
    "`pis_003_sd_pg_001_implementation_allowed: true`",
    "`dependency_changes_allowed: true`",
    "`psycopg_plain_sync_dependency_allowed: true`",
    "`psycopg_plain_sync_use_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`postgres_service_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "`uat_required_now: false`",
    "The next allowed action is `implement_pis_003_sd_pg_001_offline_candidate`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    f"make {TARGET}",
]

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(r"\bpsycopg (?:driver )?(?:use|load|execution) (?:is|has been) authorized\b"),
    re.compile(r"\bexternal dsn (?:use|consumption) (?:is|has been) authorized\b"),
    re.compile(r"\bdatabase connections? (?:are|have been) authorized\b"),
    re.compile(r"\bmigration execution (?:is|has been) authorized\b"),
    re.compile(r"\bpostgres(?:ql)? service (?:is|has been) authorized\b"),
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
        f"PIS-003 implementation-gate review is missing phrase: {phrase}"
        for phrase in REQUIRED_PHRASES
        if " ".join(phrase.split()) not in normalized
    ]
    failures.extend(
        "PIS-003 implementation-gate review contains forbidden authority pattern: "
        f"{pattern.pattern}"
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS
        if pattern.search(lowered)
    )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "review_id",
        "parent_gate",
        "gate_baseline_commit",
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
        failures.append("PIS-003 implementation-gate review contract keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "review_id": ("PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE-REVIEW"),
        "parent_gate": "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-IMPLEMENTATION-GATE",
        "gate_baseline_commit": BASELINE_COMMIT,
        "reviewed_commit": REVIEWED_COMMIT,
        "review_document_sha256": REVIEW_DOC_SHA256,
        "review_disposition": "cleared_for_offline_implementation_only",
        "review_method": "independent_read_only_gpt_5_6_sol_xhigh_no_ultra",
        "next_required_action": "implement_pis_003_sd_pg_001_offline_candidate",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 implementation-gate review field {key} is not {expected!r}")
    if contract.get("reviewed_path_hashes") != REVIEWED_PATH_HASHES:
        failures.append("PIS-003 implementation-gate review path/hash inventory is not exact")
    findings = contract.get("findings")
    if (
        findings != EXPECTED_FINDINGS
        or not isinstance(findings, dict)
        or any(type(value) is not int for value in findings.values())
    ):
        failures.append("PIS-003 implementation-gate review findings are not exact integers")
    if contract.get("closed_superseded_reviews") != EXPECTED_SUPERSEDED_REVIEWS:
        failures.append("PIS-003 implementation-gate superseded review history is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 implementation-gate review authority is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    review_bytes = _read_bytes(repo_root / REVIEW_DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        review_text = review_bytes.decode("utf-8")
    except UnicodeDecodeError:
        review_text = ""
        failures.append("PIS-003 implementation-gate review is not UTF-8")
    failures.extend(validate_review_text(review_text))
    review_hash = hashlib.sha256(review_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if review_hash != REVIEW_DOC_SHA256:
        failures.append("PIS-003 implementation-gate review bytes do not match the closed digest")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 implementation-gate review contract bytes do not match the digest")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    reviewed_exists = _commit_exists(repo_root, REVIEWED_COMMIT)
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT)
    reviewed_is_ancestor = _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD")
    lineage_exact = (
        _git(repo_root, "rev-parse", f"{REVIEWED_COMMIT}^") == FAILED_COMMIT
        and _git(repo_root, "rev-parse", f"{FAILED_COMMIT}^") == BASELINE_COMMIT
    )
    if not reviewed_exists:
        failures.append("PIS-003 implementation-gate reviewed commit is unavailable")
    if not baseline_is_ancestor:
        failures.append("PIS-003 implementation-gate review baseline ancestry is invalid")
    if not reviewed_is_ancestor:
        failures.append("PIS-003 implementation-gate reviewed commit is not an ancestor of HEAD")
    if not lineage_exact:
        failures.append("PIS-003 implementation-gate reviewed lineage is not exact")

    reviewed_paths = set(
        _git_lines(repo_root, "diff", "--name-only", f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}")
    )
    reviewed_inventory_exact = reviewed_paths == set(REVIEWED_PATH_HASHES)
    if not reviewed_inventory_exact:
        failures.append("PIS-003 implementation-gate reviewed path inventory is not exact")
    reviewed_hashes_match = True
    for path, expected_hash in REVIEWED_PATH_HASHES.items():
        if (
            hashlib.sha256(_git_bytes(repo_root, REVIEWED_COMMIT, path)).hexdigest()
            != expected_hash
        ):
            reviewed_hashes_match = False
            failures.append(f"PIS-003 implementation-gate reviewed path hash mismatch: {path}")

    gate_validator = production_identity_storage_pis_003_sd_pg_001_implementation_gate_check
    reviewed_gate_doc = _git_bytes(repo_root, REVIEWED_COMMIT, gate_validator.DOC_REL)
    reviewed_gate_contract = _load_json_bytes(
        _git_bytes(repo_root, REVIEWED_COMMIT, gate_validator.CONTRACT_REL)
    )
    reviewed_gate_valid = bool(
        hashlib.sha256(reviewed_gate_doc).hexdigest() == gate_validator.DOC_SHA256
        and hashlib.sha256(
            _git_bytes(repo_root, REVIEWED_COMMIT, gate_validator.CONTRACT_REL)
        ).hexdigest()
        == gate_validator.CONTRACT_SHA256
        and not gate_validator.validate_gate_text(reviewed_gate_doc.decode("utf-8"))
        and not gate_validator.validate_contract(reviewed_gate_contract)
    )
    if not reviewed_gate_valid:
        failures.append("PIS-003 reviewed historical implementation gate is not valid")

    entry_review = production_identity_storage_pis_003_entry_internal_review_check.build_report(
        repo_root
    )
    entry_review_valid = bool(
        entry_review.get("valid")
        and entry_review.get("pis_003_entry_decision_cleared")
        and entry_review.get("pis_003_sd_pg_001_implementation_gate_preparation_allowed")
    )
    if not entry_review_valid:
        failures.append("PIS-003 entry review prerequisite is not valid")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(
            f"PIS-003 implementation-gate review tool count is {tool_count}, expected 24"
        )
    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 implementation-gate internal review wiring is incomplete")

    valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}
    raw_findings = contract.get("findings")
    findings: dict[str, Any] = raw_findings if isinstance(raw_findings, dict) else {}

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
        "review_disposition": (contract.get("review_disposition") if valid else "invalid"),
        "reviewed_commit": REVIEWED_COMMIT,
        "reviewed_commit_exists": reviewed_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "reviewed_commit_is_ancestor": reviewed_is_ancestor,
        "lineage_exact": lineage_exact,
        "reviewed_inventory_exact": reviewed_inventory_exact,
        "reviewed_path_count": len(reviewed_paths),
        "reviewed_hashes_match": reviewed_hashes_match,
        "reviewed_gate_valid": reviewed_gate_valid,
        "entry_review_valid": entry_review_valid,
        "critical_findings": findings.get("critical", -1) if valid else -1,
        "high_findings": findings.get("high", -1) if valid else -1,
        "medium_findings": findings.get("medium", -1) if valid else -1,
        "low_findings": findings.get("low", -1) if valid else -1,
        "open_findings": findings.get("open", -1) if valid else -1,
        "tool_count": tool_count,
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": (contract.get("next_required_action") if valid else "invalid_gate"),
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
        "reviewed_gate_valid",
        "entry_review_valid",
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
    lines = ["Ithildin PIS-003 SD-PG-001 implementation-gate internal source review check"]
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
            "Current PIS-003 SD-PG-001 implementation-gate review" in register,
        )
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except FileNotFoundError:
        return {}, ["PIS-003 implementation-gate review contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-003 implementation-gate review contract has {exc}"]
        return {}, ["PIS-003 implementation-gate review contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 implementation-gate review contract must be a JSON object"]
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
