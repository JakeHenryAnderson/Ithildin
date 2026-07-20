"""Validate the PIS-001 threat-model and dependency-decision artifact."""

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
CONTRACT_REL = "docs/codex/production-identity-storage-pis-001-decision.json"
TARGET = "production-identity-storage-pis-001-decision-check"
BASELINE_COMMIT = "aa4b296f7b096b6ad0129bdf442a91c45d3d876f"
BASELINE_HASHES = {
    "apps/ui/package-lock.json": (
        "71d6ca3398895b16cfae18b46e53cbdb5d5183c3b001ec6b4d8af8fe555a7322"
    ),
    "apps/ui/package.json": (
        "e5d7c04d104ed8f95eed199615b2078a665267801899fec2ee212c3118dcb06a"
    ),
    "deploy/Dockerfile.api": (
        "f95fe4b7439173f90500deed6ee5e2c130fbb65a80a06bb6b88cc87389887e41"
    ),
    "deploy/Dockerfile.node": (
        "3666412ebf94abd532f99fc4b991ac4bfd31dd8ab71444e42959a7b09ddab9ec"
    ),
    "deploy/Dockerfile.ui": (
        "f5fa657b70ba4dc24a8414c7cb9f4b87b4419db392e8e239c5a5225eda54e950"
    ),
    "deploy/hermes-poc/Dockerfile": (
        "c7be5fae79c638c588a9b64207cddc25fe36d0b8c04b5cb6bbd608b89e8f2f8a"
    ),
    "pyproject.toml": "d7f72600511d9a3fbb1777b388dafc58d7ffc5886d0e5d40a95cbd4debc2063d",
    "uv.lock": "431403895950d714cf060923e5e98c77ffb6f927e696ba86e4ac99d005fca2c5",
    "tool-manifests.lock.json": (
        "3834a18a5b8169dd66b3d96d79d6e69d252ebae17a1a9453f93f8686db1edc77"
    ),
}

ALLOWED_CHANGED_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/batch-validation-strategy.md",
    "docs/codex/enterprise-active-route-clarity.md",
    "docs/codex/enterprise-current-checkpoint.md",
    "docs/codex/enterprise-external-review-queue.md",
    "docs/codex/enterprise-north-star-roadmap.md",
    "docs/codex/enterprise-operator-next-action.md",
    "docs/codex/enterprise-progress-model.md",
    "docs/codex/enterprise-readiness-gap-matrix.md",
    "docs/codex/enterprise-response-application-protocol.md",
    "docs/codex/enterprise-response-intake-quickstart.md",
    "docs/codex/enterprise-review-handoff-drill.md",
    "docs/codex/enterprise-roadmap-control-board.md",
    "docs/codex/enterprise-status-export.md",
    "docs/codex/ithildin-two-lane-development-control-board.md",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/production-identity-storage-pis-001-decision.json",
    "docs/codex/production-identity-storage-pis-001-internal-source-review.md",
    "docs/codex/production-identity-storage-pis-001-planning-gate.md",
    "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md",
    "docs/codex/review-docs-index.md",
    "docs/codex/technical-mvp-execution-board.md",
    "docs/codex/v1.0-progress-assessment.md",
    "scripts/build_docs_site.py",
    "scripts/enterprise_active_route_clarity.py",
    "scripts/enterprise_current_checkpoint.py",
    "scripts/enterprise_external_review_queue_check.py",
    "scripts/enterprise_north_star_roadmap.py",
    "scripts/enterprise_operator_next_action.py",
    "scripts/enterprise_progress_model.py",
    "scripts/enterprise_readiness_gap_matrix_check.py",
    "scripts/enterprise_response_application_protocol.py",
    "scripts/enterprise_response_intake_quickstart.py",
    "scripts/enterprise_review_handoff_drill.py",
    "scripts/enterprise_review_send_preflight.py",
    "scripts/enterprise_status_export.py",
    "scripts/production_identity_storage_pis_001_decision_check.py",
    "scripts/production_identity_storage_pis_001_internal_review_check.py",
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "scripts/status_now.py",
    "scripts/technical_mvp_execution_board.py",
    "scripts/technical_mvp_operator_trial_readiness.py",
    "scripts/technical_mvp_ticket_map.py",
    "scripts/v1_operator_trial_record.py",
    "scripts/v1_progress_assessment.py",
    "tests/test_release_readiness.py",
}

EXPECTED_AUTHORITY = {
    "pis_001_planning_artifact_recorded": True,
    "pis_002_entry_decision_required": True,
    "pis_002_implementation_allowed": False,
    "dependency_changes_allowed": False,
    "runtime_changes_allowed": False,
    "public_api_changes_allowed": False,
    "schema_changes_allowed": False,
    "database_migrations_allowed": False,
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

EXPECTED_DEPENDENCY_DECISIONS = {
    "authlib_client": ("recommended_deferred", "PIS-004"),
    "hand_rolled_oidc_pyjwt_httpx": ("rejected", "none"),
    "sqlalchemy_2_core": ("recommended_deferred", "PIS-002-entry-decision"),
    "psycopg_3": ("recommended_deferred", "PIS-003"),
    "alembic": ("recommended_deferred", "PIS-003"),
    "psycopg_pool": ("deferred", "post-PIS-003-load-evidence"),
    "asyncpg": ("rejected_for_phase_1", "new-architecture-decision"),
    "sqlalchemy_orm": ("rejected_for_authority_state", "new-architecture-decision"),
    "general_retry_framework": ("rejected", "new-architecture-decision"),
    "provider_sdks": ("deferred_unselected", "provider-specific-entry-decision"),
}

EXPECTED_THREAT_IDS = {
    "oidc_identity_confusion",
    "session_and_membership_abuse",
    "tenant_and_authority_spoofing",
    "node_identity_and_configuration_replay",
    "deployment_epoch_and_restore_rollback",
    "transaction_audit_and_outbox_ambiguity",
    "migration_backup_and_database_role_failure",
    "dependency_and_evidence_compromise",
}

EXPECTED_ACCEPTED_RISKS = {
    "AR-001": "accepted_deferred",
    "AR-002": "accepted_deferred",
    "AR-003": "accepted_deferred",
    "AR-009": "accepted_deferred",
    "AR-010": "accepted_deferred",
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

FORBIDDEN_AUTHORITY_PATTERNS = [
    re.compile(
        r"\bpis-?002\b.{0,48}\b(?:may|can)\b.{0,24}"
        r"\b(?:proceed|begin|start|implement)\b"
    ),
    re.compile(
        r"\bruntime implementation\b.{0,32}"
        r"\b(?:approved|authorized|allowed)\b"
    ),
    re.compile(
        r"\bdependencies?\b.{0,32}\b(?:may|can)\b.{0,16}"
        r"\b(?:be )?installed\b"
    ),
    re.compile(
        r"\b(?:production identity|runtime postgresql|enterprise rbac)\b.{0,32}"
        r"\b(?:approved|authorized|allowed|enabled)\b"
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT, require_clean=not args.allow_dirty)
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
    for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
        if pattern.search(lowered):
            failures.append(
                "PIS-001 decision contains forbidden authority pattern: "
                f"{pattern.pattern}"
            )
    return failures


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_top_keys = {
        "schema_version",
        "decision_id",
        "parent_decision",
        "decision_outcome",
        "planning_baseline_commit",
        "tool_count",
        "authority",
        "dependency_decisions",
        "threat_families",
        "accepted_risks",
    }
    if set(contract) != expected_top_keys:
        failures.append("PIS-001 contract top-level keys are not the closed schema")
    expected_scalars = {
        "schema_version": "1",
        "decision_id": "PRD-PROD-IAM-STORAGE-PIS-001",
        "parent_decision": "PRD-PROD-IAM-STORAGE-ARCH-001",
        "decision_outcome": "threat_model_frozen_dependency_recommendations_recorded",
        "planning_baseline_commit": BASELINE_COMMIT,
        "tool_count": 24,
    }
    for key, expected in expected_scalars.items():
        if contract.get(key) != expected:
            failures.append(f"PIS-001 contract field {key} does not match {expected!r}")
    authority = contract.get("authority")
    if (
        not isinstance(authority, dict)
        or set(authority) != set(EXPECTED_AUTHORITY)
        or any(type(authority.get(key)) is not bool for key in EXPECTED_AUTHORITY)
        or authority != EXPECTED_AUTHORITY
    ):
        failures.append("PIS-001 contract authority map is not the exact fail-closed map")

    dependencies = contract.get("dependency_decisions")
    if not isinstance(dependencies, dict) or set(dependencies) != set(
        EXPECTED_DEPENDENCY_DECISIONS
    ):
        failures.append("PIS-001 contract dependency keys are not the closed set")
    else:
        for name, (decision, later_gate) in EXPECTED_DEPENDENCY_DECISIONS.items():
            if dependencies.get(name) != {
                "decision": decision,
                "later_gate": later_gate,
            }:
                failures.append(f"PIS-001 dependency decision is invalid: {name}")

    threat_families = contract.get("threat_families")
    threat_ids: list[str] = []
    if not isinstance(threat_families, list):
        failures.append("PIS-001 contract threat_families must be a list")
    else:
        for item in threat_families:
            if not isinstance(item, dict) or set(item) != {
                "id",
                "owner",
                "safe_evidence",
                "recovery",
                "tests",
            }:
                failures.append("PIS-001 threat family does not use the closed row schema")
                continue
            threat_id = item.get("id")
            if not isinstance(threat_id, str):
                failures.append("PIS-001 threat family ID must be a string")
                continue
            threat_ids.append(threat_id)
            if not isinstance(item.get("owner"), str) or not item["owner"].strip():
                failures.append(f"PIS-001 threat family has no owner: {threat_id}")
            for field in ("safe_evidence", "recovery", "tests"):
                values = item.get(field)
                if (
                    not isinstance(values, list)
                    or not values
                    or any(not isinstance(value, str) or not value for value in values)
                ):
                    failures.append(
                        f"PIS-001 threat family has invalid {field}: {threat_id}"
                    )
        if len(threat_ids) != len(set(threat_ids)):
            failures.append("PIS-001 contract has duplicate threat family IDs")
        if set(threat_ids) != EXPECTED_THREAT_IDS:
            failures.append("PIS-001 contract threat family IDs are not the required set")

    if contract.get("accepted_risks") != EXPECTED_ACCEPTED_RISKS:
        failures.append("PIS-001 accepted-risk map is not the exact deferred set")
    return failures


def build_report(repo_root: Path, *, require_clean: bool = False) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    if not doc_path.exists():
        failures.append("PIS-001 threat-model and dependency decision is missing")
    failures.extend(validate_decision_text(text))

    contract, contract_failures = _load_contract(repo_root / CONTRACT_REL)
    contract_validation_failures = validate_contract(contract)
    failures.extend(contract_failures)
    failures.extend(contract_validation_failures)

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

    baseline_is_ancestor = _baseline_is_ancestor(repo_root)
    if not baseline_is_ancestor:
        failures.append("PIS-001 planning baseline is not an ancestor of current HEAD")
    committed_changed_paths = _changed_paths(repo_root) if baseline_is_ancestor else []
    working_tree_changed_paths = _working_tree_changed_paths(repo_root)
    changed_paths = sorted(set(committed_changed_paths) | set(working_tree_changed_paths))
    unexpected_changed_paths = sorted(set(changed_paths) - ALLOWED_CHANGED_PATHS)
    if unexpected_changed_paths:
        failures.append(
            "PIS-001 candidate changed paths outside the planning allowlist: "
            + ", ".join(unexpected_changed_paths)
        )
    candidate_tree_clean = not bool(_git(repo_root, "status", "--short"))
    if require_clean and not candidate_tree_clean:
        failures.append("PIS-001 exact-candidate check requires a clean working tree")

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
    if CONTRACT_REL not in text or CONTRACT_REL not in readme:
        failures.append("PIS-001 machine-readable contract pointer is incomplete")

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
        "baseline_is_ancestor": baseline_is_ancestor,
        "candidate_tree_clean": candidate_tree_clean,
        "candidate_scope_valid": not unexpected_changed_paths,
        "changed_paths": changed_paths,
        "working_tree_changed_paths": working_tree_changed_paths,
        "contract_valid": not contract_failures and not contract_validation_failures,
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
        "baseline_is_ancestor",
        "candidate_tree_clean",
        "candidate_scope_valid",
        "contract_valid",
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


def _baseline_is_ancestor(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0


def _changed_paths(repo_root: Path) -> list[str]:
    output = _git(repo_root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD")
    return sorted(line for line in output.splitlines() if line)


def _working_tree_changed_paths(repo_root: Path) -> list[str]:
    paths: set[str] = set()
    for arguments in [
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ]:
        output = _git(repo_root, *arguments)
        paths.update(line for line in output.splitlines() if line)
    return sorted(paths)


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key, value in pairs:
            if key in document:
                raise ValueError(f"duplicate JSON member: {key}")
            document[key] = value
        return document

    try:
        document = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"PIS-001 machine-readable contract is invalid: {exc}")
        return {}, failures
    if not isinstance(document, dict):
        failures.append("PIS-001 machine-readable contract must be an object")
        return {}, failures
    return document, failures


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
