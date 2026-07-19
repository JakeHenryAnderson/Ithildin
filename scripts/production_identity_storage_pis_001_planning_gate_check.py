"""Validate the bounded production identity/storage PIS-001 planning gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    production_identity_storage_architecture_decision_record_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/production-identity-storage-pis-001-planning-gate.md"
DOC_NAME = "production-identity-storage-pis-001-planning-gate.md"
DOC_TITLE = "Production Identity And Storage PIS-001 Planning Gate"
TARGET = "production-identity-storage-pis-001-planning-gate-check"
OUTPUT_REL = (
    "docs/codex/"
    "production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
)

REQUIRED_PHRASES = [
    "Status: ready for bounded `PIS-001` planning execution.",
    "Work package: `PIS-001`.",
    "Parent decision: `PRD-PROD-IAM-STORAGE-ARCH-001`.",
    "Parent decision status: `approved_for_pis_001_planning_only`.",
    "Current governed tool count: `24`.",
    "Current selected runtime capability: `not selected`.",
    "Current `ERG-006` status: `planning_only`.",
    "Current `ERG-007` status: `planning_only`.",
    OUTPUT_REL,
    "Allowed Work",
    "Forbidden Work",
    "Threat-Model Minimums",
    "Dependency-Decision Minimums",
    "Exact Contract Freeze",
    "Done Criteria",
    "Stop Conditions",
    "PIS-002 remains blocked behind a separate entry decision",
    f"make {TARGET}",
    "does not prove that PIS-001 is complete",
]

REQUIRED_BOUNDARIES = [
    "adding, removing, upgrading, importing, or executing a new dependency",
    "pyproject.toml",
    "uv.lock",
    "public APIs",
    "MCP tools",
    "schemas",
    "migrations",
    "production credentials",
    "production identity",
    "enterprise RBAC",
    "remote admin",
    "PostgreSQL",
    "backup/restore",
    "retention",
    "KMS/HSM/CA",
    "24-tool manifest",
    "shell",
    "Docker socket",
    "Kubernetes",
    "browser automation",
    "arbitrary HTTP",
    "broad filesystem writes",
    "sandbox orchestration",
    "SIEM runtime delivery",
    "hosted telemetry",
    "public security-product claims",
    "UAT acceptance",
]

FORBIDDEN_PHRASES = [
    "status: pis-001 is complete",
    "pis-002 is approved",
    "dependency changes are allowed",
    "production identity is allowed",
    "runtime postgresql is allowed",
    "database migrations are allowed",
    "runtime work is authorized",
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


def validate_gate_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    for phrase in REQUIRED_PHRASES:
        if " ".join(phrase.split()) not in normalized:
            failures.append(f"PIS-001 planning gate is missing phrase: {phrase}")
    for phrase in REQUIRED_BOUNDARIES:
        if phrase not in text:
            failures.append(f"PIS-001 planning gate is missing boundary: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"PIS-001 planning gate contains forbidden phrase: {phrase}")
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc_path = repo_root / DOC_REL
    text = _read(doc_path)
    if not doc_path.exists():
        failures.append("PIS-001 planning gate doc is missing")
    failures.extend(validate_gate_text(text))

    parent = production_identity_storage_architecture_decision_record_check.build_report(
        repo_root
    )
    failures.extend(f"parent decision: {failure}" for failure in parent["failures"])
    if parent.get("decision_status") != "approved_for_pis_001_planning_only":
        failures.append("parent decision does not permit PIS-001 planning")
    if parent.get("dependency_changes_allowed") is not False:
        failures.append("parent decision permits dependency changes")
    if parent.get("pis_002_planning_allowed") is not False:
        failures.append("parent decision permits PIS-002 planning")

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
                / "docs/codex/production-identity-storage-architecture-decision-record.md"
            ),
            "architecture decision record",
        ),
        (_read(repo_root / "docs/codex/post-rc-decision-register.md"), "decision register"),
        (_read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md"), "gap matrix"),
    ]
    for linked_text, label in linked_sources:
        if DOC_NAME not in linked_text and DOC_REL not in linked_text:
            failures.append(f"{label} is missing PIS-001 planning-gate pointer")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-001 planning gate is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing PIS-001 planning gate title")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-001 planning gate check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require PIS-001 planning gate check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing PIS-001 planning gate command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "planning_gate_doc": DOC_REL,
        "required_output": OUTPUT_REL,
        "work_package": "PIS-001",
        "parent_decision": "PRD-PROD-IAM-STORAGE-ARCH-001",
        "status": "ready_for_bounded_planning_execution",
        "tool_count": 24,
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "pis_001_planning_allowed": True,
        "pis_001_complete": False,
        "dependency_changes_allowed": False,
        "pis_002_allowed": False,
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "database_migrations_allowed": False,
        "new_power_classes_allowed": False,
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = ["Ithildin production identity/storage PIS-001 planning gate check"]
    for key in [
        "valid",
        "planning_gate_doc",
        "required_output",
        "work_package",
        "parent_decision",
        "status",
        "tool_count",
        "erg_006_status",
        "erg_007_status",
        "pis_001_planning_allowed",
        "pis_001_complete",
        "dependency_changes_allowed",
        "pis_002_allowed",
        "runtime_changes_allowed",
        "production_identity_allowed",
        "runtime_postgres_allowed",
        "database_migrations_allowed",
        "new_power_classes_allowed",
        "uat_required_now",
    ]:
        value = report[key]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{key}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
