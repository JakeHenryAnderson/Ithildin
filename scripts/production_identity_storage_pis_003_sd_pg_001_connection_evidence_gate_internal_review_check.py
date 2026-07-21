"""Validate the exact-candidate PIS-003 connection-evidence gate review."""

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
    production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate-internal-source-review.md"
)
DOC_TITLE = (
    "Production Identity And Storage PIS-003 SD-PG-001 Connection Evidence Gate "
    "Internal Source Review"
)
DOC_SHA256 = "8c6da7eae92006445e358f51617b31ad2649270f4d91be2ae34886db93cd99cc"
CONTRACT_REL = (
    "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate-review-authority.json"
)
CONTRACT_SHA256 = "6701c3de1d49ed48edf188f232e7e7f419fa0f9f16ddf0968408b474dc84bec0"
TARGET = (
    "production-identity-storage-pis-003-sd-pg-001-"
    "connection-evidence-gate-internal-review-check"
)
BASELINE_COMMIT = "bf26418b5f27b1fcd08552758e4387867b5eafe0"
SUPERSEDED_COMMIT = "08937f3f83321d64bd6b1604d9af8012b8d9f5aa"
REVIEWED_COMMIT = "86b2074493410019914b8190e1cc9e079c0ce929"

REVIEWED_PATH_HASHES = {
    "Makefile": "569b475aaa60b6b01293664bbab1c14bf92a2c9abb8d5113717008385c25e642",
    "README.md": "c788a76f5fa9376068bff93998f9533a5e3ea2b60f2cfa2490a2c09b45fbccb4",
    "docs/codex/post-rc-decision-register.md": (
        "037d20ff9e8761577480bc2f3c88505f2bb8d6a4c8e797bed0a1f51f5cf96af6"
    ),
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-gate.json"
    ): "502367304bb9fd7272a9201219ae03d5eb5b28c021f79f69ecc63ef6dcfd0f17",
    (
        "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "connection-evidence-gate.md"
    ): "43a40e958eb5c12768adbf825eed38e3952b8b73a6959c7ea983e2546c8540b5",
    "docs/codex/review-docs-index.md": (
        "21e797ff2fcbb0ed94f2953f694c72970c8d1119d4b4ea8c8579cf1d734ab7e4"
    ),
    "scripts/build_docs_site.py": (
        "5a1b793bedc70628ff3e543787a47cafb4eb0fe4f406f13e9618abebb30e7e07"
    ),
    (
        "scripts/production_identity_storage_pis_003_sd_pg_001_"
        "connection_evidence_gate_check.py"
    ): "063218e920850a7ebae1a91fb529a9dc8a80b33726d0d923a8b59c5bf48a2744",
    "scripts/release_guardrails.py": (
        "33f5befff86639f0fce2652a63c288ed395900afd3831b53dfb9bf9efc9871cc"
    ),
    "scripts/review_docs.py": (
        "ef10b173f840c9ad893d46800b8036678264a3713d69bd4893357864214c1c09"
    ),
    "tests/test_release_readiness.py": (
        "8bf0136b1819ec4f5ee308f6ab5910979ca5828f6cd9941e618369b9be4d334e"
    ),
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
    "pis_003_sd_pg_001_connection_evidence_gate_recorded": True,
    "connection_evidence_candidate_selected": True,
    "offline_candidate_review_prerequisite_satisfied": True,
    "exact_candidate_source_review_required": True,
    "exact_candidate_source_review_complete": True,
    "connection_evidence_implementation_allowed": True,
    "environment_receipt_implementation_allowed": True,
    "test_harness_implementation_allowed": True,
    "synthetic_snapshot_reader_implementation_allowed": True,
    "online_alembic_caller_connection_implementation_allowed": True,
    "failure_evidence_implementation_allowed": True,
    "execution_preflight_implementation_allowed": True,
    "psycopg_plain_sync_use_allowed": False,
    "external_dsn_consumption_allowed": False,
    "test_harness_execution_allowed": False,
    "isolated_test_connection_allowed": False,
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
    "connection_execution_authority_required": True,
}

REQUIRED_PHRASES = [
    (
        "Status: `PIS-003-SD-PG-001` connection-evidence gate exact-candidate source "
        "review complete; no"
    ),
    (
        "Review ID: `PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-"
        "CONNECTION-EVIDENCE-GATE-REVIEW`."
    ),
    "Review disposition: `cleared_for_connection_evidence_implementation_only`.",
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    f"Superseded NO-GO commit: `{SUPERSEDED_COMMIT}`.",
    f"Gate baseline commit: `{BASELINE_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "Current governed tool count: `24`.",
    "`exact_candidate_source_review_complete: true`",
    "`connection_evidence_implementation_allowed: true`",
    "`test_harness_execution_allowed: false`",
    "`database_connections_allowed: false`",
    "`migration_execution_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`production_identity_allowed: false`",
    "`release_allowed: false`",
    "`uat_complete: false`",
    "The next allowed action is `implement_pis_003_sd_pg_001_connection_evidence_candidate`.",
    CONTRACT_REL,
    "Prose cannot broaden the closed contract.",
    f"make {TARGET}",
]


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


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_keys = {
        "schema_version",
        "review_id",
        "parent_gate",
        "gate_baseline_commit",
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
        failures.append("PIS-003 connection gate review contract keys are not closed")
    expected_scalars = {
        "schema_version": "1",
        "review_id": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE-REVIEW"
        ),
        "parent_gate": (
            "PRD-PROD-IAM-STORAGE-PIS-003-SD-PG-001-CONNECTION-EVIDENCE-GATE"
        ),
        "gate_baseline_commit": BASELINE_COMMIT,
        "superseded_candidate_commit": SUPERSEDED_COMMIT,
        "reviewed_commit": REVIEWED_COMMIT,
        "review_document_sha256": DOC_SHA256,
        "review_disposition": "cleared_for_connection_evidence_implementation_only",
        "review_method": "independent_read_only_gpt_5_6_sol_xhigh_no_ultra",
        "next_required_action": "implement_pis_003_sd_pg_001_connection_evidence_candidate",
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-003 connection gate review field {key} is not exact")
    if contract.get("reviewed_path_hashes") != REVIEWED_PATH_HASHES:
        failures.append("PIS-003 connection gate reviewed path hashes are not exact")
    findings = contract.get("findings")
    if (
        findings != EXPECTED_FINDINGS
        or not isinstance(findings, dict)
        or any(type(value) is not int for value in findings.values())
    ):
        failures.append("PIS-003 connection gate review findings are not exact integers")
    if contract.get("closed_superseded_reviews") != EXPECTED_SUPERSEDED_REVIEWS:
        failures.append("PIS-003 connection gate superseded review record is not exact")
    authority = contract.get("authority")
    if (
        authority != EXPECTED_AUTHORITY
        or not isinstance(authority, dict)
        or any(type(value) is not bool for value in authority.values())
    ):
        failures.append("PIS-003 connection gate review authority is not exact")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_bytes = _read_bytes(repo_root / DOC_REL)
    contract_bytes = _read_bytes(repo_root / CONTRACT_REL)
    try:
        doc_text = doc_bytes.decode("utf-8")
    except UnicodeDecodeError:
        doc_text = ""
        failures.append("PIS-003 connection gate review document is not UTF-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in doc_text:
            failures.append(f"PIS-003 connection gate review document missing: {phrase}")
    doc_hash = hashlib.sha256(doc_bytes).hexdigest()
    contract_hash = hashlib.sha256(contract_bytes).hexdigest()
    if doc_hash != DOC_SHA256:
        failures.append("PIS-003 connection gate review document digest does not match")
    if contract_hash != CONTRACT_SHA256:
        failures.append("PIS-003 connection gate review contract digest does not match")

    contract, load_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_failures = validate_contract(contract)
    failures.extend(load_failures)
    failures.extend(contract_failures)

    candidate_exists = _commit_exists(repo_root, REVIEWED_COMMIT)
    candidate_is_ancestor = _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD")
    baseline_is_ancestor = _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT)
    superseded_is_parent = _commit_parent(repo_root, REVIEWED_COMMIT) == SUPERSEDED_COMMIT
    if not candidate_exists:
        failures.append("PIS-003 reviewed connection gate candidate is unavailable")
    if not candidate_is_ancestor:
        failures.append("PIS-003 reviewed connection gate candidate is not an ancestor of HEAD")
    if not baseline_is_ancestor:
        failures.append("PIS-003 connection gate baseline is not an ancestor of candidate")
    if not superseded_is_parent:
        failures.append("PIS-003 repaired connection gate parent is not the superseded candidate")

    candidate_paths = set(
        _git_lines(
            repo_root,
            "diff",
            "--name-only",
            f"{BASELINE_COMMIT}..{REVIEWED_COMMIT}",
        )
    )
    candidate_inventory_exact = candidate_paths == set(REVIEWED_PATH_HASHES)
    if not candidate_inventory_exact:
        failures.append("PIS-003 reviewed connection gate candidate inventory is not exact")
    path_hashes_match = all(
        _hash_at_commit(repo_root, REVIEWED_COMMIT, path) == expected
        for path, expected in REVIEWED_PATH_HASHES.items()
    )
    if not path_hashes_match:
        failures.append("PIS-003 reviewed connection gate candidate hashes do not match")

    gate_report = (
        production_identity_storage_pis_003_sd_pg_001_connection_evidence_gate_check.build_report(
            repo_root
        )
    )
    gate_valid = bool(
        gate_report.get("valid")
        and gate_report.get("candidate_commit") == REVIEWED_COMMIT
        and gate_report.get("candidate_inventory_exact")
        and gate_report.get("protected_hashes_match")
        and gate_report.get("tool_count") == 24
        and gate_report.get("database_connections_allowed") is False
        and gate_report.get("test_harness_execution_allowed") is False
    )
    if not gate_valid:
        failures.append("PIS-003 reviewed connection gate prerequisite is invalid")

    wiring_valid = _wiring_valid(repo_root)
    if not wiring_valid:
        failures.append("PIS-003 connection gate review wiring is incomplete")
    valid = not failures
    raw_authority = contract.get("authority")
    authority: dict[str, Any] = raw_authority if isinstance(raw_authority, dict) else {}

    def allowed(name: str) -> bool:
        return bool(valid and authority.get(name) is True)

    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "review_document": DOC_REL,
        "review_id": contract.get("review_id") if valid else "invalid",
        "review_disposition": contract.get("review_disposition") if valid else "invalid",
        "gate_baseline_commit": BASELINE_COMMIT,
        "superseded_candidate_commit": SUPERSEDED_COMMIT,
        "reviewed_commit": REVIEWED_COMMIT,
        "candidate_exists": candidate_exists,
        "candidate_is_ancestor": candidate_is_ancestor,
        "baseline_is_ancestor": baseline_is_ancestor,
        "superseded_is_parent": superseded_is_parent,
        "candidate_path_count": len(candidate_paths),
        "candidate_inventory_exact": candidate_inventory_exact,
        "reviewed_path_hashes_match": path_hashes_match,
        "review_document_hash_matches": doc_hash == DOC_SHA256,
        "review_contract_hash_matches": contract_hash == CONTRACT_SHA256,
        "contract_valid": not load_failures and not contract_failures,
        "gate_prerequisite_valid": gate_valid,
        "findings": contract.get("findings") if valid else {},
        "tool_count": gate_report.get("tool_count", -1),
        "wiring_valid": wiring_valid,
        **{name: allowed(name) for name in EXPECTED_AUTHORITY},
        "next_required_action": contract.get("next_required_action") if valid else "invalid_review",
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "review_document",
        "review_id",
        "review_disposition",
        "gate_baseline_commit",
        "superseded_candidate_commit",
        "reviewed_commit",
        "candidate_exists",
        "candidate_is_ancestor",
        "baseline_is_ancestor",
        "superseded_is_parent",
        "candidate_path_count",
        "candidate_inventory_exact",
        "reviewed_path_hashes_match",
        "review_document_hash_matches",
        "review_contract_hash_matches",
        "contract_valid",
        "gate_prerequisite_valid",
        "findings",
        "tool_count",
        "wiring_valid",
        *EXPECTED_AUTHORITY,
        "next_required_action",
    ]
    lines = ["Ithildin PIS-003 SD-PG-001 connection-evidence gate review check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _wiring_valid(repo_root: Path) -> bool:
    makefile = _read_text(repo_root / "Makefile")
    readme = _read_text(repo_root / "README.md")
    guardrails = _read_text(repo_root / "scripts/release_guardrails.py")
    docs_site = _read_text(repo_root / "scripts/build_docs_site.py")
    index = _read_text(repo_root / "docs/codex/review-docs-index.md")
    return bool(
        f"{TARGET}:" in makefile
        and f"release-check: {TARGET}" in makefile
        and f"make {TARGET}" in readme
        and DOC_REL in review_docs.REVIEW_DOCS
        and DOC_REL in docs_site
        and TARGET in guardrails
        and DOC_TITLE in index
    )


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, [f"PIS-003 connection gate review contract cannot be loaded: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["PIS-003 connection gate review contract must be an object"]
    return payload, []


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _hash_at_commit(repo_root: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else ""


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _commit_parent(repo_root: Path, commit: str) -> str:
    lines = _git_lines(repo_root, "rev-list", "--parents", "-n", "1", commit)
    if not lines:
        return ""
    parts = lines[0].split()
    return parts[1] if len(parts) == 2 else ""


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        check=False,
        capture_output=True,
    ).returncode == 0


def _git_lines(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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


if __name__ == "__main__":
    raise SystemExit(main())
