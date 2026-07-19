"""Validate the planning-only ERG-006/ERG-007 architecture decision record."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_architecture_check,
    production_identity_storage_disposition_closure_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-architecture-decision-record.md"
DOC_NAME = "production-identity-storage-architecture-decision-record.md"
DOC_TITLE = "Production Identity And Storage Architecture Decision Record"
TARGET = "production-identity-storage-architecture-decision-record-check"
REVIEWED_COMMIT = "88f8e53cc54e599df25da6b14d465a5fb06848d7"
REVIEWED_PACKET_HASH = (
    "sha256:bdcac6f8cbb1c5a3cec40730eccdf2cb6a3a2d1f9c0ab2a588e3f1afaf378c57"
)
FINDING_IDS = [f"EXT-PROD-IAM-STORAGE-{index:03d}" for index in range(1, 6)]

REQUIRED_PHRASES = [
    "Status: committed planning-only architecture decision for `ERG-006` and `ERG-007`.",
    "Decision ID: `PRD-PROD-IAM-STORAGE-ARCH-001`.",
    "Decision record status: `approved_for_pis_001_planning_only`.",
    "Current governed tool count: `24`.",
    "Current selected runtime capability: `not selected`.",
    "Recorded `ERG-006` status: `planning_only`.",
    "Recorded `ERG-007` status: `planning_only`.",
    REVIEWED_COMMIT,
    REVIEWED_PACKET_HASH,
    "continue_architecture_planning",
    "ready_for_architecture_decision_record",
    "Accepted Architecture Direction",
    "Allowed `PIS-001` Scope",
    "Explicitly Forbidden Scope",
    "Required `PIS-001` Evidence",
    "Stop Conditions",
    "approved_for_pis_001_planning_only",
    "ERG-006/ERG-007 architecture review recorded -> PIS-001 planning gate",
    "Passing `PIS-001` will not itself authorize `PIS-002`",
    f"make {TARGET}",
    "Release gates must continue to pass with no live normalized response present.",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "dependency additions",
    "runtime implementation",
    "production IAM",
    "enterprise RBAC",
    "tenant/team authorization runtime behavior",
    "remote administration",
    "remote MCP",
    "runtime PostgreSQL",
    "schema creation",
    "migrations",
    "backup/restore runtime behavior",
    "retention enforcement",
    "production credentials",
    "Node transport expansion",
    "shell",
    "Docker",
    "Kubernetes",
    "browser automation",
    "arbitrary HTTP",
    "broad filesystem writes",
    "sandbox orchestration",
    "SIEM adapter runtime behavior",
    "hosted telemetry",
    "compliance automation",
    "custody-grade audit",
    "public/security-product positioning",
    "release",
    "UAT acceptance",
    "new governed tool or power class",
]

FORBIDDEN_PHRASES = [
    "dependency changes are approved",
    "production identity is approved",
    "enterprise rbac is approved",
    "runtime postgresql is approved",
    "database migrations are approved",
    "remote administration is approved",
    "runtime implementation is approved",
    "pis-002 is approved",
    "new governed powers are approved",
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
    lowered = text.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"decision record is missing phrase: {phrase}")
    for phrase in REQUIRED_BLOCKED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"decision record is missing blocked boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"decision record contains forbidden phrase: {phrase}")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    if not doc_path.exists():
        failures.append("production identity/storage architecture decision record is missing")
    failures.extend(validate_decision_text(text))

    source_review = _read(
        repo_root / "docs/codex/production-identity-storage-source-review.md"
    )
    normalized_source_review = " ".join(source_review.split())
    for marker in [
        REVIEWED_COMMIT,
        REVIEWED_PACKET_HASH,
        "continue_architecture_planning",
        "ready_for_architecture_decision_record",
        "all five findings as `fixed`",
        "no new critical, high, or medium finding",
    ]:
        if marker not in normalized_source_review:
            failures.append(f"source-review record is missing exact evidence: {marker}")

    for finding_id in FINDING_IDS:
        finding_matches = sorted(
            (repo_root / "docs/codex/findings").glob(f"{finding_id.lower()}-*.md")
        )
        if len(finding_matches) != 1:
            failures.append(f"expected one finding record for {finding_id}")
            continue
        finding_text = _read(finding_matches[0])
        if "- Disposition: fixed" not in finding_text:
            failures.append(f"finding is not fixed: {finding_id}")

    if not _commit_exists(repo_root, REVIEWED_COMMIT):
        failures.append("reviewed remediation commit is not available in repository history")

    architecture = production_identity_storage_architecture_check.build_report(repo_root)
    closure = production_identity_storage_disposition_closure_check.build_report(repo_root)
    failures.extend(f"architecture: {failure}" for failure in architecture["failures"])
    failures.extend(f"closure: {failure}" for failure in closure["failures"])
    if architecture.get("tool_count") != 24:
        failures.append("architecture tool count is not 24")
    if architecture.get("erg_006_status") != "planning_only":
        failures.append("ERG-006 architecture status is not planning_only")
    if architecture.get("erg_007_status") != "planning_only":
        failures.append("ERG-007 architecture status is not planning_only")
    if closure.get("normalized_response_present") is not False:
        failures.append("live normalized response must be absent after disposition recording")
    if closure.get("closure_ready") is not False:
        failures.append("ordinary closure gate must fail closed without a live response")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    linked_sources = [
        (readme, "README"),
        (docs_site, "docs site"),
        (review_index, "review-docs index"),
        (_read(repo_root / "docs/codex/post-rc-decision-register.md"), "decision register"),
        (_read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md"), "gap matrix"),
        (
            _read(repo_root / "docs/codex/production-identity-storage-architecture.md"),
            "architecture",
        ),
    ]
    for linked_text, label in linked_sources:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{label} is missing architecture decision record pointer")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("architecture decision record is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing architecture decision record title")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if TARGET not in release_check_body and f"release-check: {TARGET}" not in makefile:
        failures.append("architecture decision record check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require architecture decision record check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing architecture decision record command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_doc": DOC_REL,
        "decision_id": "PRD-PROD-IAM-STORAGE-ARCH-001",
        "decision_status": "approved_for_pis_001_planning_only",
        "reviewed_commit": REVIEWED_COMMIT,
        "reviewed_packet_hash": REVIEWED_PACKET_HASH,
        "finding_count": len(FINDING_IDS),
        "tool_count": 24,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "pis_001_planning_allowed": True,
        "dependency_changes_allowed": False,
        "pis_002_planning_allowed": False,
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
        "decision_record_doc",
        "decision_id",
        "decision_status",
        "reviewed_commit",
        "reviewed_packet_hash",
        "finding_count",
        "tool_count",
        "erg_006_status",
        "erg_007_status",
        "pis_001_planning_allowed",
        "dependency_changes_allowed",
        "pis_002_planning_allowed",
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
    lines = ["Ithildin production identity/storage architecture decision record check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


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
