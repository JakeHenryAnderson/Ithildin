"""Validate the exact-candidate PIS-002 sandbox repository source-review disposition."""

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
    production_identity_storage_pis_002_sandbox_descriptor_repository_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOC_REL = (
    "docs/codex/"
    "production-identity-storage-pis-002-sandbox-descriptor-repository-internal-source-review.md"
)
REVIEW_DOC_TITLE = (
    "Production Identity And Storage PIS-002 Sandbox Descriptor Repository Internal Source Review"
)
CONTRACT_REL = (
    "docs/codex/"
    "production-identity-storage-pis-002-sandbox-descriptor-repository-review-authority.json"
)
TARGET = (
    "production-identity-storage-pis-002-sandbox-descriptor-repository-internal-review-check"
)
BASELINE_COMMIT = "934ebaa4ccd5d03032e269473198e7c94755c13c"
REVIEWED_COMMIT = "887de154aeb4c047325eed2372c83deda1fda251"
REVIEW_DOCUMENT_SHA256 = "9896aab3a4727747e3ee59e98123dc59093e34c248a4ce27cd1e2a9d7a5a46d6"

EXPECTED_CONTRACT = {
    "schema_version": "1",
    "review_id": "PRD-PROD-IAM-STORAGE-PIS-002-SD-001-REVIEW",
    "parent_decision": "PRD-PROD-IAM-STORAGE-PIS-002-ENTRY",
    "implementation_slice": "PIS-002-SD-001",
    "implementation_baseline_commit": BASELINE_COMMIT,
    "reviewed_commit": REVIEWED_COMMIT,
    "review_document_sha256": REVIEW_DOCUMENT_SHA256,
    "review_disposition": "cleared_bounded_sandbox_descriptor_repository_interface_only",
    "findings": {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "open": 0,
    },
    "authority": {
        "pis_002_sd_001_source_review_complete": True,
        "pis_002_sd_001_cleared": True,
        "pis_002_continuation_decision_preparation_allowed": True,
        "additional_aggregate_implementation_allowed": False,
        "pis_003_entry_decision_preparation_allowed": False,
        "pis_003_implementation_allowed": False,
        "dependency_changes_allowed": False,
        "sqlalchemy_allowed": False,
        "schema_changes_allowed": False,
        "database_migrations_allowed": False,
        "audit_ordering_changes_allowed": False,
        "runtime_postgres_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "release_allowed": False,
        "production_promotion_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "uat_complete": False,
        "uat_required_now": False,
    },
    "next_required_action": "prepare_pis_002_continuation_decision_record",
}

REVIEWED_HASHES = {
    "Makefile": "1a64fdb0230a6278a6031bed2515d0ab62b2a59852a05e124b47c2f7f9982abb",
    "README.md": "6c8ba56857877f79b31fa061d5e82f2141f3705ef4e80e34b1e3af53d88f49cc",
    "apps/api/src/ithildin_api/app.py": (
        "2cd6cb4304165de300b4418c73308d7cd15d9c5ac36c2869ada1b7f7d28fc0d4"
    ),
    "apps/api/src/ithildin_api/sandbox_descriptors.py": (
        "30aa57adffe7b981cf5f5a92786b33ae0da5ea1c611cd0806cb780ec6d603bec"
    ),
    "apps/api/src/ithildin_api/trusted_host_promotions.py": (
        "4090817b1c95114e75edd6b3f8908e734fa19c8db07f42c1a830831d1f458759"
    ),
    "docs/codex/post-rc-decision-register.md": (
        "e454e95542d6005682b9cea823e237ba3da10499546bd34e8d368f07f1749d7c"
    ),
    (
        "docs/codex/"
        "production-identity-storage-pis-002-sandbox-descriptor-repository-implementation.md"
    ): (
        "9afda1144c0743675bf1db52aadce456a99dcde142139f89b5eed2754521cefb"
    ),
    "docs/codex/review-docs-index.md": (
        "da1202dba3c40d81e97c16ddd62d31af97410182f449b5824f01b6d62510dccd"
    ),
    "scripts/build_docs_site.py": (
        "28b851f09219edbcba3d9d5a87f29bfce0810759b062f2a17c3bc99c7c938e58"
    ),
    "scripts/production_identity_storage_pis_001_decision_check.py": (
        "121857df58daced57e20543b07e891a91896d1a7eae65786a319b70510bbebe8"
    ),
    "scripts/production_identity_storage_pis_001_internal_review_check.py": (
        "c753f825d95bd78fc9858b98343ffbe571e40f8b2ae4e2e8f6740d32d296f82c"
    ),
    "scripts/production_identity_storage_pis_002_sandbox_descriptor_repository_check.py": (
        "1aa81163d26557cf085b947ef565e1a58aeb78fdc09e5252a768374f4258cb13"
    ),
    "scripts/release_guardrails.py": (
        "4da7c1c4510a78cc9c164df7585dab80e3bd2ae5d7455d6f1515276c65ba58ec"
    ),
    "scripts/review_docs.py": (
        "cf0ef901265b94bdbd719eaef20ba40089220c40619efb5885c39772324cf4e2"
    ),
    "tests/test_api_service.py": (
        "4027041f223d0495e0942f775879e20dec3764c6fe09939c8c17c0db97bccef0"
    ),
    "tests/test_release_readiness.py": (
        "de77d50fcefbf7a40cff02953181c9765862ea7ba880c1f219159b9f5e247090"
    ),
    "tests/test_sandbox_descriptor_repository.py": (
        "182cdc6ce204299d4aebadec5aa710c03a619ebd4d04dd30bc796b9f8c28ecd8"
    ),
}

CURRENT_STABLE_PATHS = {
    "apps/api/src/ithildin_api/app.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/trusted_host_promotions.py",
    "docs/codex/production-identity-storage-pis-002-sandbox-descriptor-repository-implementation.md",
    "scripts/production_identity_storage_pis_001_decision_check.py",
    "scripts/production_identity_storage_pis_001_internal_review_check.py",
    "tests/test_api_service.py",
    "tests/test_sandbox_descriptor_repository.py",
}
CURRENT_SCOPED_SUCCESSOR_HASHES = {
    "scripts/production_identity_storage_pis_002_sandbox_descriptor_repository_check.py": (
        "2461a58f98f3333a1cfbd7033581cfe397ccd05422113bb12bac314c7de0ba26"
    )
}

REQUIRED_PHRASES = [
    "Status: `PIS-002-SD-001` exact-candidate internal source review complete; no open findings.",
    "Review disposition: `cleared_bounded_sandbox_descriptor_repository_interface_only`.",
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "`pis_002_sd_001_source_review_complete: true`",
    "`additional_aggregate_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`new_power_classes_allowed: false`",
    "`uat_required_now: false`",
    "The next allowed action is `prepare_pis_002_continuation_decision_record`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
]

FORBIDDEN_PHRASES = [
    "second aggregate implementation is approved",
    "pis-003 implementation is approved",
    "postgresql runtime is approved",
    "production identity is approved",
    "uat is complete",
]

_POSITIVE_GRANT = (
    r"(?:may|can|could|will|shall)\s+(?:now\s+)?(?:"
    r"proceed(?:\s+to)?(?:\s+implementation)?|"
    r"be\s+(?:implemented|added|enabled|changed|installed|introduced|used|started|"
    r"authorized|approved|completed|released)|"
    r"(?:be\s+)?(?:authorized|approved|enabled|allowed|completed|released))"
    r"|(?:is|are|has\s+been|have\s+been)\s+(?:now\s+)?"
    r"(?:authorized|approved|enabled|allowed|complete|completed|passed|released)"
    r"|has\s+passed"
)
_AUTHORITY_SUBJECTS = [
    r"(?:a\s+)?(?:second|additional|another)\s+(?:persisted\s+)?aggregate",
    r"pis[- ]?003",
    r"(?:dependencies|dependency\s+changes?|packages?|sqlalchemy)",
    r"(?:database\s+)?(?:schema|migrations?)",
    r"(?:audit|descriptor)(?:\s+commit)?\s+ordering",
    r"(?:runtime\s+postgres(?:ql)?|postgresql\s+runtime)",
    r"(?:production\s+identity|enterprise\s+rbac)",
    r"(?:release|production\s+promotion)",
    r"(?:uat|user\s+acceptance\s+testing|acceptance)",
    r"(?:new\s+power\s+classes?|new\s+governed\s+tools?)",
]
FORBIDDEN_AUTHORITY_PATTERNS = [
    pattern
    for subject in _AUTHORITY_SUBJECTS
    for pattern in (
        re.compile(rf"\b(?:{subject})\b.{{0,56}}\b(?:{_POSITIVE_GRANT})\b"),
        re.compile(
            rf"\b(?:implementation|changes?|installation|enablement|authorization|approval|"
            rf"permission|completion)\b.{{0,40}}\b(?:{_POSITIVE_GRANT})\b.{{0,56}}"
            rf"\b(?:{subject})\b"
        ),
        re.compile(
            rf"\b(?:authorization|approval|permission)\s+(?:is|has\s+been)\s+granted"
            rf".{{0,56}}\b(?:{subject})\b"
        ),
    )
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def validate_review_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    for phrase in REQUIRED_PHRASES:
        if " ".join(phrase.split()) not in normalized:
            failures.append(f"PIS-002 repository review is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(
                f"PIS-002 repository review contains forbidden authority phrase: {phrase}"
            )
    for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
        if pattern.search(lowered):
            failures.append(
                "PIS-002 repository review contains forbidden authority pattern: "
                f"{pattern.pattern}"
            )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    authority = contract.get("authority")
    if isinstance(authority, dict) and any(
        type(value) is not bool for value in authority.values()
    ):
        failures.append(
            "PIS-002 repository review authority values must be exact Booleans"
        )
    findings = contract.get("findings")
    if isinstance(findings, dict) and any(
        type(value) is not int for value in findings.values()
    ):
        failures.append(
            "PIS-002 repository review finding counts must be exact integers"
        )
    if not _closed_equal(contract, EXPECTED_CONTRACT):
        failures.append(
            "PIS-002 repository review authority contract is not the exact closed contract"
        )
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    review_bytes = _read_bytes(repo_root / REVIEW_DOC_REL)
    try:
        review_text = review_bytes.decode("utf-8")
    except UnicodeDecodeError:
        review_text = ""
        failures.append("PIS-002 sandbox repository internal source review is not UTF-8")
    if not review_bytes:
        failures.append("PIS-002 sandbox repository internal source review is missing")
    failures.extend(validate_review_text(review_text))
    review_document_sha256 = hashlib.sha256(review_bytes).hexdigest()
    review_document_hash_matches = review_document_sha256 == REVIEW_DOCUMENT_SHA256
    if not review_document_hash_matches:
        failures.append(
            "PIS-002 sandbox repository internal source review bytes do not match the "
            "reviewed digest"
        )

    contract, contract_load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_validation_failures = validate_contract(contract)
    failures.extend(contract_load_failures)
    failures.extend(contract_validation_failures)
    contract_valid = not contract_load_failures and not contract_validation_failures
    authority = contract.get("authority") if contract_valid else {}
    findings = contract.get("findings") if contract_valid else {}
    if not isinstance(authority, dict):
        authority = {}
    if not isinstance(findings, dict):
        findings = {}

    reviewed_commit_exists = _commit_exists(repo_root, REVIEWED_COMMIT)
    if not reviewed_commit_exists:
        failures.append("PIS-002 reviewed candidate commit is unavailable")
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT)
    if not baseline_is_ancestor:
        failures.append("PIS-002 reviewed candidate does not descend from its baseline")
    candidate_is_ancestor = _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD")
    if not candidate_is_ancestor:
        failures.append("PIS-002 reviewed candidate is not an ancestor of current HEAD")
    candidate_parent = _git(repo_root, "rev-parse", f"{REVIEWED_COMMIT}^")
    if candidate_parent != BASELINE_COMMIT:
        failures.append("PIS-002 reviewed candidate is not the immediate baseline child")

    reviewed_paths = set(
        _git(
            repo_root,
            "diff",
            "--no-renames",
            "--name-only",
            f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}",
        ).splitlines()
    )
    reviewed_paths.discard("")
    expected_paths = set(
        production_identity_storage_pis_002_sandbox_descriptor_repository_check.EXPECTED_CHANGED_PATHS
    )
    reviewed_inventory_exact = reviewed_paths == expected_paths == set(REVIEWED_HASHES)
    if not reviewed_inventory_exact:
        failures.append("PIS-002 reviewed candidate path inventory is not exact")

    rename_records = _git(
        repo_root,
        "diff",
        "--name-status",
        "--find-renames",
        f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}",
    ).splitlines()
    if any(line.startswith(("R", "C")) for line in rename_records):
        failures.append("PIS-002 reviewed candidate contains a rename or copy record")

    reviewed_hashes_match = True
    for path, expected_hash in REVIEWED_HASHES.items():
        reviewed_bytes = _git_bytes(repo_root, REVIEWED_COMMIT, path)
        if hashlib.sha256(reviewed_bytes).hexdigest() != expected_hash:
            reviewed_hashes_match = False
            failures.append(f"PIS-002 reviewed hash does not match: {path}")

    current_stable_artifacts_match = reviewed_hashes_match

    implementation = (
        production_identity_storage_pis_002_sandbox_descriptor_repository_check.build_report(
            repo_root, require_clean=False
        )
    )
    failures.extend(f"PIS-002 implementation: {item}" for item in implementation["failures"])

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    if REVIEW_DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-002 internal review is missing from review docs")
    if REVIEW_DOC_REL not in docs_site:
        failures.append("PIS-002 internal review is missing from docs site")
    if REVIEW_DOC_TITLE not in review_index:
        failures.append("review-docs index is missing the PIS-002 internal review")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-002 internal review check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require the PIS-002 internal review check")
    if (
        f"make {TARGET}" not in readme
        or REVIEW_DOC_REL not in readme
        or CONTRACT_REL not in readme
    ):
        failures.append("README PIS-002 internal review wiring is incomplete")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-002 reviewed governed tool count is {tool_count}, expected 24")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "review_doc": REVIEW_DOC_REL,
        "review_document_sha256": review_document_sha256,
        "review_document_hash_matches": review_document_hash_matches,
        "authority_contract": CONTRACT_REL,
        "contract_valid": contract_valid,
        "review_disposition": (
            contract.get("review_disposition") if contract_valid else "invalid"
        ),
        "reviewed_commit": contract.get("reviewed_commit") if contract_valid else None,
        "reviewed_commit_exists": reviewed_commit_exists,
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_is_ancestor": candidate_is_ancestor,
        "candidate_parent_exact": candidate_parent == BASELINE_COMMIT,
        "reviewed_inventory_exact": reviewed_inventory_exact,
        "reviewed_hashes_match": reviewed_hashes_match,
        "current_stable_artifacts_match": current_stable_artifacts_match,
        "implementation_check_valid": implementation["valid"],
        "critical_findings": findings.get("critical") if contract_valid else None,
        "high_findings": findings.get("high") if contract_valid else None,
        "medium_findings": findings.get("medium") if contract_valid else None,
        "low_findings": findings.get("low") if contract_valid else None,
        "open_findings": findings.get("open") if contract_valid else None,
        "tool_count": tool_count,
        "pis_002_sd_001_source_review_complete": bool(
            contract_valid and authority.get("pis_002_sd_001_source_review_complete") is True
        ),
        "pis_002_sd_001_cleared": bool(
            contract_valid and authority.get("pis_002_sd_001_cleared") is True
        ),
        "pis_002_continuation_decision_preparation_allowed": bool(
            contract_valid
            and authority.get("pis_002_continuation_decision_preparation_allowed") is True
        ),
        "additional_aggregate_implementation_allowed": bool(
            contract_valid
            and authority.get("additional_aggregate_implementation_allowed") is True
        ),
        "pis_003_entry_decision_preparation_allowed": bool(
            contract_valid
            and authority.get("pis_003_entry_decision_preparation_allowed") is True
        ),
        "pis_003_implementation_allowed": bool(
            contract_valid and authority.get("pis_003_implementation_allowed") is True
        ),
        "dependency_changes_allowed": bool(
            contract_valid and authority.get("dependency_changes_allowed") is True
        ),
        "sqlalchemy_allowed": bool(
            contract_valid and authority.get("sqlalchemy_allowed") is True
        ),
        "schema_changes_allowed": bool(
            contract_valid and authority.get("schema_changes_allowed") is True
        ),
        "database_migrations_allowed": bool(
            contract_valid and authority.get("database_migrations_allowed") is True
        ),
        "audit_ordering_changes_allowed": bool(
            contract_valid and authority.get("audit_ordering_changes_allowed") is True
        ),
        "runtime_postgres_allowed": bool(
            contract_valid and authority.get("runtime_postgres_allowed") is True
        ),
        "production_identity_allowed": bool(
            contract_valid and authority.get("production_identity_allowed") is True
        ),
        "enterprise_rbac_allowed": bool(
            contract_valid and authority.get("enterprise_rbac_allowed") is True
        ),
        "release_allowed": bool(
            contract_valid and authority.get("release_allowed") is True
        ),
        "production_promotion_allowed": bool(
            contract_valid and authority.get("production_promotion_allowed") is True
        ),
        "new_power_classes_allowed": bool(
            contract_valid and authority.get("new_power_classes_allowed") is True
        ),
        "public_security_product_positioning_allowed": bool(
            contract_valid
            and authority.get("public_security_product_positioning_allowed") is True
        ),
        "uat_complete": bool(contract_valid and authority.get("uat_complete") is True),
        "uat_required_now": bool(
            contract_valid and authority.get("uat_required_now") is True
        ),
        "next_required_action": (
            contract.get("next_required_action") if contract_valid else "invalid_contract"
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "review_doc",
        "review_document_sha256",
        "review_document_hash_matches",
        "authority_contract",
        "contract_valid",
        "review_disposition",
        "reviewed_commit",
        "reviewed_commit_exists",
        "baseline_is_ancestor",
        "candidate_is_ancestor",
        "candidate_parent_exact",
        "reviewed_inventory_exact",
        "reviewed_hashes_match",
        "current_stable_artifacts_match",
        "implementation_check_valid",
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
        "open_findings",
        "tool_count",
        "pis_002_sd_001_source_review_complete",
        "pis_002_sd_001_cleared",
        "pis_002_continuation_decision_preparation_allowed",
        "additional_aggregate_implementation_allowed",
        "pis_003_entry_decision_preparation_allowed",
        "pis_003_implementation_allowed",
        "dependency_changes_allowed",
        "sqlalchemy_allowed",
        "schema_changes_allowed",
        "database_migrations_allowed",
        "audit_ordering_changes_allowed",
        "runtime_postgres_allowed",
        "production_identity_allowed",
        "enterprise_rbac_allowed",
        "release_allowed",
        "production_promotion_allowed",
        "new_power_classes_allowed",
        "public_security_product_positioning_allowed",
        "uat_complete",
        "uat_required_now",
        "next_required_action",
    ]
    lines = ["Ithildin PIS-002 sandbox repository internal source-review check"]
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
        return {}, ["PIS-002 repository review authority contract is missing"]
    except (json.JSONDecodeError, ValueError) as exc:
        if str(exc).startswith("duplicate JSON member:"):
            return {}, [f"PIS-002 repository review authority contract has {exc}"]
        return {}, ["PIS-002 repository review authority contract is not valid JSON"]
    if not isinstance(payload, dict):
        return {}, ["PIS-002 repository review authority contract must be a JSON object"]
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


def _git_bytes(repo_root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


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
