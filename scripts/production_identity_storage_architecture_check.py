"""Validate the production identity and storage architecture packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/production-identity-storage-architecture.md"

REQUIRED_PHRASES = [
    "Status: design-only architecture packet for `ERG-006` and `ERG-007`.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "`ERG-006`: production identity and multi-user authorization.",
    "`ERG-007`: durable runtime storage and retention.",
    "local principal labels, not enterprise authentication",
    "SQLite runtime storage, not runtime Postgres",
    "Future Identity Architecture Questions",
    "Future Storage Architecture Questions",
    "Disaster-Recovery Candidate Contract",
    "replace a lost Node; do not restore its private",
    "Stale-Restore And Split-Brain Rule",
    "monotonic recovery watermark held outside the restored database",
    "Required Recovery Proof",
    "Evidence Contract",
    "Required Before Implementation",
    "external architecture review",
    "The current decision is `planning_only`.",
    "Runtime implementation remains blocked",
    "make production-identity-storage-architecture-check",
]

REQUIRED_SAFE_EVIDENCE_PHRASES = [
    "authenticated subject label and Ithildin principal ID",
    "tenant/team/workspace labels",
    "storage backend label and schema version",
    "migration state",
    "backup/restore status labels",
    "retention-policy label",
    "safe error labels for identity or storage failures",
    "retired Node credential replay",
    "reconciliation_failed",
    "fenced",
]

FORBIDDEN_PHRASES = [
    "production IAM is implemented",
    "enterprise RBAC is implemented",
    "runtime Postgres is enabled",
    "remote admin use is approved",
    "custody-grade audit is implemented",
    "compliance automation is approved",
    "public security product approved",
    "hosted control plane is implemented",
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


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    runway = (repo_root / "docs/codex/enterprise-readiness-runway.md").read_text(
        encoding="utf-8"
    )
    gap_matrix = (repo_root / "docs/codex/enterprise-readiness-gap-matrix.md").read_text(
        encoding="utf-8"
    )
    decision_register = (repo_root / "docs/codex/post-rc-decision-register.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    if not doc_path.exists():
        failures.append("production identity/storage architecture doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(
                    "production identity/storage architecture doc is missing phrase: "
                    f"{phrase}"
                )
        for phrase in REQUIRED_SAFE_EVIDENCE_PHRASES:
            if phrase not in text:
                failures.append(
                    "production identity/storage architecture doc is missing safe evidence "
                    f"phrase: {phrase}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    "production identity/storage architecture doc contains forbidden phrase: "
                    f"{phrase}"
                )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("production identity/storage architecture doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("production identity/storage architecture doc is missing from docs site")
    if "Production Identity And Storage Architecture" not in review_index:
        failures.append("review docs index is missing production identity/storage architecture")
    if "production-identity-storage-architecture-check:" not in makefile:
        failures.append("Make target is missing: production-identity-storage-architecture-check")
    if "production-identity-storage-architecture-check" not in release_check_body:
        failures.append(
            "production-identity-storage-architecture-check is missing from release-check"
        )
    if "make production-identity-storage-architecture-check" not in readme:
        failures.append("README is missing production identity/storage architecture command")
    if "production-identity-storage-architecture.md" not in readme:
        failures.append("README is missing production identity/storage architecture doc")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "production-identity-storage-architecture.md" not in container_text:
            failures.append(
                f"{container_name} is missing production identity/storage architecture pointer"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "architecture_doc": doc_rel,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "enterprise_rbac_allowed": False,
        "runtime_postgres_allowed": False,
        "remote_admin_allowed": False,
        "hosted_control_plane_allowed": False,
        "custody_grade_audit_allowed": False,
        "compliance_claims_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin production identity/storage architecture check",
        f"valid: {str(report['valid']).lower()}",
        f"architecture_doc: {report['architecture_doc']}",
        f"erg_006_status: {report['erg_006_status']}",
        f"erg_007_status: {report['erg_007_status']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"enterprise_rbac_allowed: {str(report['enterprise_rbac_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"remote_admin_allowed: {str(report['remote_admin_allowed']).lower()}",
        f"hosted_control_plane_allowed: {str(report['hosted_control_plane_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
