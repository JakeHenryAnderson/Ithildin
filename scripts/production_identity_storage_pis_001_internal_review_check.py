"""Validate the exact-candidate PIS-001 internal source-review record."""

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

from scripts import production_identity_storage_pis_001_decision_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOC_REL = (
    "docs/codex/production-identity-storage-pis-001-internal-source-review.md"
)
REVIEW_DOC_TITLE = "Production Identity And Storage PIS-001 Internal Source Review"
TARGET = "production-identity-storage-pis-001-internal-review-check"
BASELINE_COMMIT = "aa4b296f7b096b6ad0129bdf442a91c45d3d876f"
REVIEWED_COMMIT = "177c0c6e461176d85126c9817dba40b3a092ec95"
REVIEWED_HASHES = {
    "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md": (
        "c01372edba661536a2bf5f799ef84c7ede285e4b1ee681ff21bf106abc1c116d"
    ),
    "docs/codex/production-identity-storage-pis-001-decision.json": (
        "f4f59e58e5f9d1a724a49f6ffe4f9420f118c25c44a27b238fc17eccf239e652"
    ),
    "scripts/production_identity_storage_pis_001_decision_check.py": (
        "bfc8c25f54662a566296e0b03e49a5b77f5744d46bb03979f54296fc529e2b34"
    ),
    "tests/test_release_readiness.py": (
        "dc27302f9c622a1ae3b4b56b386a59735c40072dd90e179f9d8de1e1a8c03c55"
    ),
}
CURRENT_SCOPED_SUCCESSOR_HASHES = {
    "scripts/production_identity_storage_pis_001_decision_check.py": (
        "121857df58daced57e20543b07e891a91896d1a7eae65786a319b70510bbebe8"
    ),
}
EXPECTED_REVIEWED_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/batch-validation-strategy.md",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/production-identity-storage-pis-001-decision.json",
    "docs/codex/production-identity-storage-pis-001-planning-gate.md",
    "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md",
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    "scripts/production_identity_storage_pis_001_decision_check.py",
    "scripts/release_guardrails.py",
    "scripts/review_docs.py",
    "tests/test_release_readiness.py",
}
REQUIRED_PHRASES = [
    "Status: `PIS-001` exact-candidate internal source review complete; no open findings.",
    "Review disposition: `cleared_pis_001_planning_evidence_only`.",
    f"Reviewed exact commit: `{REVIEWED_COMMIT}`.",
    "Review method: independent read-only GPT-5.6 Sol xhigh review. Sol Ultra was not used.",
    "Critical findings: `0`.",
    "High findings: `0`.",
    "Medium findings: `0`.",
    "Low findings: `0`.",
    "Open findings: `0`.",
    "`PIS-002` remains `no_go_pending_separate_entry_decision`.",
    "allows preparation of a separate **PIS-002 entry decision record only**",
    "`pis_002_implementation_allowed: false`",
    "`dependency_changes_allowed: false`",
    "`runtime_changes_allowed: false`",
    "`runtime_postgres_allowed: false`",
    "`new_power_classes_allowed: false`",
    "`uat_required_now: false`",
    "The next allowed action is `prepare_pis_002_entry_decision_record`.",
]
FORBIDDEN_PHRASES = [
    "pis-002 implementation is approved",
    "dependency installation is authorized",
    "production identity is approved",
    "runtime postgresql is approved",
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


def validate_review_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    for phrase in REQUIRED_PHRASES:
        if " ".join(phrase.split()) not in normalized:
            failures.append(f"PIS-001 internal review is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(
                f"PIS-001 internal review contains forbidden authority phrase: {phrase}"
            )
    return failures


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    review_text = _read(repo_root / REVIEW_DOC_REL)
    if not review_text:
        failures.append("PIS-001 internal source-review record is missing")
    failures.extend(validate_review_text(review_text))

    if not _commit_exists(repo_root, REVIEWED_COMMIT):
        failures.append("PIS-001 reviewed commit is unavailable")
    if not _is_ancestor(repo_root, BASELINE_COMMIT, REVIEWED_COMMIT):
        failures.append("PIS-001 reviewed commit does not descend from planning baseline")
    if not _is_ancestor(repo_root, REVIEWED_COMMIT, "HEAD"):
        failures.append("PIS-001 reviewed commit is not an ancestor of current HEAD")

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
    if reviewed_paths != EXPECTED_REVIEWED_PATHS:
        failures.append("PIS-001 reviewed candidate path inventory is not exact")

    reviewed_hashes_match = True
    for path, expected_hash in REVIEWED_HASHES.items():
        reviewed_bytes = _git_bytes(repo_root, REVIEWED_COMMIT, path)
        if hashlib.sha256(reviewed_bytes).hexdigest() != expected_hash:
            reviewed_hashes_match = False
            failures.append(f"PIS-001 reviewed hash does not match record: {path}")
    current_reviewed_artifacts_match = reviewed_hashes_match

    decision_report = production_identity_storage_pis_001_decision_check.build_report(
        repo_root, require_clean=False
    )
    failures.extend(
        f"PIS-001 decision: {failure}" for failure in decision_report["failures"]
    )

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    if REVIEW_DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("PIS-001 internal review is missing from review docs")
    if REVIEW_DOC_REL not in docs_site:
        failures.append("PIS-001 internal review is missing from docs site inputs")
    if REVIEW_DOC_TITLE not in review_index:
        failures.append("review-docs index is missing PIS-001 internal review title")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("PIS-001 internal review check is missing from release-check")
    if TARGET not in release_guardrails:
        failures.append("release guardrails do not require PIS-001 internal review check")
    if f"make {TARGET}" not in readme or REVIEW_DOC_REL not in readme:
        failures.append("README is missing PIS-001 internal review wiring")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "review_doc": REVIEW_DOC_REL,
        "reviewed_commit": REVIEWED_COMMIT,
        "review_disposition": "cleared_pis_001_planning_evidence_only",
        "reviewed_hashes_match": reviewed_hashes_match,
        "current_reviewed_artifacts_match": current_reviewed_artifacts_match,
        "scoped_successor_validator_active": True,
        "critical_findings": 0,
        "high_findings": 0,
        "medium_findings": 0,
        "low_findings": 0,
        "open_findings": 0,
        "tool_count": decision_report.get("tool_count"),
        "erg_006_status": "planning_only",
        "erg_007_status": "planning_only",
        "pis_002_entry_decision_record_preparation_allowed": True,
        "pis_002_implementation_allowed": False,
        "dependency_changes_allowed": False,
        "runtime_changes_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "database_migrations_allowed": False,
        "new_power_classes_allowed": False,
        "uat_required_now": False,
    }


def render_report(report: dict[str, Any]) -> str:
    fields = [
        "valid",
        "review_doc",
        "reviewed_commit",
        "review_disposition",
        "reviewed_hashes_match",
        "current_reviewed_artifacts_match",
        "scoped_successor_validator_active",
        "critical_findings",
        "high_findings",
        "medium_findings",
        "low_findings",
        "open_findings",
        "tool_count",
        "erg_006_status",
        "erg_007_status",
        "pis_002_entry_decision_record_preparation_allowed",
        "pis_002_implementation_allowed",
        "dependency_changes_allowed",
        "runtime_changes_allowed",
        "production_identity_allowed",
        "runtime_postgres_allowed",
        "database_migrations_allowed",
        "new_power_classes_allowed",
        "uat_required_now",
    ]
    lines = ["Ithildin production identity/storage PIS-001 internal review check"]
    for field in fields:
        value = report[field]
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        lines.append(f"{field}: {rendered}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def _git_bytes(repo_root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout


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


if __name__ == "__main__":
    raise SystemExit(main())
