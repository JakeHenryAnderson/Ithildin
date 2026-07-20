"""Validate the PIS-001 threat-model and dependency-decision artifact."""

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
    production_identity_storage_architecture_check,
    production_identity_storage_architecture_decision_record_check,
    production_identity_storage_pis_001_planning_gate_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
)
DOC_NAME = "production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
DOC_TITLE = "Production Identity And Storage PIS-001 Threat Model And Dependency Decision"
TARGET = "production-identity-storage-pis-001-decision-check"
BASELINE_COMMIT = "aa4b296f7b096b6ad0129bdf442a91c45d3d876f"
BASELINE_HASHES = {
    "pyproject.toml": "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d",
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

REQUIRED_PHRASES = [
    "Status: `PIS-001` planning artifact recorded; `PIS-002` entry decision required.",
    "Decision ID: `PRD-PROD-IAM-STORAGE-PIS-001`.",
    "Parent decision: `PRD-PROD-IAM-STORAGE-ARCH-001`.",
    "Decision outcome: `threat_model_frozen_dependency_recommendations_recorded`.",
    "Current governed tool count: `24`.",
    "Current selected runtime capability: `not selected`.",
    "Current `ERG-006` status: `planning_only`.",
    "Current `ERG-007` status: `planning_only`.",
    BASELINE_COMMIT,
    "Phase 1 Security Objective",
    "Security Invariants",
    "Assets And Data Classes",
    "Actors And Assumptions",
    "Trust Boundaries And Entry Points",
    "Authority Transitions",
    "Abuse-Case And Control Matrix",
    "Threat Evidence, Recovery, And Residual Ownership",
    "Required Fail-Closed Behavior",
    "Current Dependency Inventory",
    "Candidate Dependency Decisions",
    "Exact Identity And Storage Contract Freeze",
    "Negative, Interruption, Restart, And Partition Plan",
    "Rollback And Recovery Rules",
    "Unresolved External Decisions And Accepted-Risk Impact",
    "PIS-002 Entry Decision",
    "Explicit Non-Goals And Claims",
    "Primary Sources Checked",
    "PIS-001 is evidence-complete only after focused checks",
    f"make {TARGET}",
]

REQUIRED_SECURITY_MARKERS = [
    "exact issuer",
    "subject remap",
    "caller-role",
    "membership drift",
    "session fixation",
    "CSRF",
    "cross-workspace",
    "disabled-principal",
    "Node key cloning",
    "stale configuration",
    "split brain",
    "ambiguous transaction",
    "partial/incorrect migration",
    "audit-head race",
    "outbox loss",
    "stale restore",
    "backup/WAL theft",
    "dependency compromise",
    "sensitive evidence leakage",
    "response mix-up",
    "redirect URI",
    "outbound destination allowlist",
    "`aud`, `azp`",
    "JWK rollover",
    "Threat family | Minimum safe evidence | Recovery or fencing action | Residual risk owner",
    "IdP/discovery/JWK endpoint",
    "Session-digest key",
    "Trustworthy time",
    "PostgreSQL or transaction outcome",
    "KMS/CA/signing service",
    "External watermark/fence",
]

REQUIRED_DEPENDENCY_DECISIONS = [
    "Authlib client integration — recommended, deferred to a PIS-004 dependency gate",
    "Hand-rolled OIDC using transitive PyJWT plus HTTPX — rejected",
    "SQLAlchemy 2.0 Core — recommended, deferred to the PIS-002 entry decision",
    "Psycopg 3 — recommended, deferred to a PIS-003 dependency gate",
    "Alembic — recommended, deferred to a PIS-003 dependency gate",
    "Psycopg pool, asyncpg, ORM usage, and retry frameworks",
    "Provider SDKs and infrastructure products — deferred and unselected",
    "`recommended_deferred`",
    "`rejected`",
    "`rejected_for_phase_1`",
    "`rejected_for_authority_state`",
    "`AR-001`",
    "`AR-002`",
    "`AR-003`",
    "`AR-009`",
    "`AR-010`",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "does not add or authorize a dependency",
    "public API",
    "schema",
    "migration",
    "OIDC integration",
    "production identity",
    "enterprise RBAC",
    "remote administration",
    "runtime PostgreSQL",
    "backup/restore behavior",
    "retention enforcement",
    "runtime code",
    "new governed tool",
    "production promotion",
    "UAT acceptance",
    "`PIS-002` remains `no_go_pending_separate_entry_decision`.",
    "does not authorize PIS-002 implementation",
]

FORBIDDEN_PHRASES = [
    "dependency installation is authorized",
    "pis-002 implementation is authorized",
    "production identity is authorized",
    "runtime postgresql is authorized",
    "database migrations are authorized",
    "enterprise rbac is authorized",
    "remote administration is authorized",
    "new governed powers are authorized",
    "uat is complete",
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


def validate_decision_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    for phrase in REQUIRED_PHRASES:
        if " ".join(phrase.split()) not in normalized:
            failures.append(f"PIS-001 decision is missing phrase: {phrase}")
    for phrase in REQUIRED_SECURITY_MARKERS:
        if phrase.lower() not in lowered:
            failures.append(f"PIS-001 decision is missing security marker: {phrase}")
    for phrase in REQUIRED_DEPENDENCY_DECISIONS:
        if phrase not in text:
            failures.append(f"PIS-001 decision is missing dependency decision: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase.lower() not in lowered:
            failures.append(f"PIS-001 decision is missing blocked boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"PIS-001 decision contains forbidden authority phrase: {phrase}")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    if not doc_path.exists():
        failures.append("PIS-001 threat-model and dependency decision is missing")
    failures.extend(validate_decision_text(text))

    actual_hashes: dict[str, str] = {}
    for relative_path, expected_hash in BASELINE_HASHES.items():
        path = repo_root / relative_path
        if not path.exists():
            failures.append(f"PIS-001 protected baseline file is missing: {relative_path}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        actual_hashes[relative_path] = actual_hash
        if actual_hash != expected_hash:
            failures.append(
                f"PIS-001 protected baseline changed without a separate entry decision: "
                f"{relative_path}"
            )

    if not _commit_exists(repo_root, BASELINE_COMMIT):
        failures.append("PIS-001 planning baseline commit is unavailable in repository history")

    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append(f"PIS-001 governed tool count is {tool_count}, expected 24")

    planning_gate = production_identity_storage_pis_001_planning_gate_check.build_report(repo_root)
    architecture_decision = (
        production_identity_storage_architecture_decision_record_check.build_report(repo_root)
    )
    architecture = production_identity_storage_architecture_check.build_report(repo_root)
    for label, report in [
        ("planning gate", planning_gate),
        ("architecture decision", architecture_decision),
        ("architecture", architecture),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report["failures"])

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    linked_sources = [
        (readme, "README"),
        (docs_site, "docs site"),
        (review_index, "review-docs index"),
        (
            _read(
                repo_root
                / "docs/codex/production-identity-storage-pis-001-planning-gate.md"
            ),
            "PIS-001 planning gate",
        ),
        (_read(repo_root / "docs/codex/post-rc-decision-register.md"), "decision register"),
        (_read(repo_root / "docs/codex/batch-validation-strategy.md"), "batch strategy"),
    ]
    for linked_text, label in linked_sources:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{label} is missing PIS-001 decision pointer")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-001 decision is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing PIS-001 decision title")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-001 decision check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require PIS-001 decision check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing PIS-001 decision command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_doc": DOC_REL,
        "decision_id": "PRD-PROD-IAM-STORAGE-PIS-001",
        "decision_outcome": "threat_model_frozen_dependency_recommendations_recorded",
        "planning_baseline_commit": BASELINE_COMMIT,
        "baseline_hashes_match": all(
            actual_hashes.get(path) == expected
            for path, expected in BASELINE_HASHES.items()
        ),
        "tool_count": tool_count,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "pis_001_planning_artifact_recorded": True,
        "pis_002_entry_decision_required": True,
        "pis_002_implementation_allowed": False,
        "dependency_changes_allowed": False,
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "remote_admin_allowed": False,
        "runtime_postgres_allowed": False,
        "database_migrations_allowed": False,
        "backup_restore_runtime_allowed": False,
        "retention_enforcement_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "decision_doc",
        "decision_id",
        "decision_outcome",
        "planning_baseline_commit",
        "baseline_hashes_match",
        "tool_count",
        "erg_006_status",
        "erg_007_status",
        "pis_001_planning_artifact_recorded",
        "pis_002_entry_decision_required",
        "pis_002_implementation_allowed",
        "dependency_changes_allowed",
        "runtime_changes_allowed",
        "production_identity_allowed",
        "enterprise_rbac_allowed",
        "remote_admin_allowed",
        "runtime_postgres_allowed",
        "database_migrations_allowed",
        "backup_restore_runtime_allowed",
        "retention_enforcement_allowed",
        "new_power_classes_allowed",
        "public_security_product_positioning_allowed",
        "uat_required_now",
    ]
    lines = ["Ithildin production identity/storage PIS-001 decision check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _tool_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return -1
    manifests = payload.get("manifests")
    return len(manifests) if isinstance(manifests, list) else -1


def _commit_exists(repo_root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
