"""Validate the durable Command Center closure-review candidate history."""

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

from scripts.review_candidate_packet_validation import immutable_packet_valid

ROOT = Path(__file__).resolve().parents[1]
TARGET = "command-center-closure-review-history-check"

CANDIDATE_COMMIT = "af593edddbca1b9a429a104d0894546708fac277"
DISPOSITION_COMMIT = "4be6f330bf22a27ac7ba580f0f3d22bff9684ae5"
SOURCE_REVIEW_COMMIT = "4edc9a6c963c357269d8e78df14f2e3a363f8664"
DISPOSITION_REL = (
    "docs/codex/command-center-sol-ultra-closure-review-dispatch-record.md"
)
SOURCE_REVIEW_REL = (
    "docs/codex/"
    "command-center-sol-ultra-closure-review-dispatch-record-internal-source-review.md"
)
PACKET_REL = (
    "var/review-packets/v0.2/"
    "ithildin-v0.2-review-packet-af593edddbca"
)
PACKET_RELEASE_CHECK_REL = f"{PACKET_REL}/release-check.txt"
PACKET_RELEASE_CHECK_SHA256 = (
    "c30d6646695bf8f1e861cbe7813134747e8d36c9f70f2d9ae83188854ae63926"
)
PACKET_RELEASE_CHECK_BYTES = 289_384
DISPOSITION_BLOB_SHA256 = (
    "0724ede668357fca1d8cf4ffb8d088689e7ea809d6132d64e4313dbfc5c34369"
)
SOURCE_REVIEW_BLOB_SHA256 = (
    "e8d0f5718f9c61dcd3f17bb91509b27a85ce114c920b22e9a4da255b5181bb69"
)

EXPECTED_DISPOSITION_PATHS = {
    DISPOSITION_REL,
    "tests/test_release_readiness.py",
}
EXPECTED_SOURCE_REVIEW_PATHS = {
    SOURCE_REVIEW_REL,
    "tests/test_release_readiness.py",
}
EXPECTED_RECORD_REVIEW_FINDINGS = {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "open": 0,
}
AUTHORITY = {
    "sol_ultra_user_approval_obtained": False,
    "closure_review_dispatch_allowed": False,
    "closure_findings_dispositioned": False,
    "ready_for_cc_pilot_107_uat": False,
    "human_uat_allowed": False,
    "runtime_changes_allowed": False,
    "runner_authority_allowed": False,
    "model_provider_authority_allowed": False,
    "arbitrary_host_control_allowed": False,
    "credential_consumption_allowed": False,
    "database_connections_allowed": False,
    "migration_execution_allowed": False,
    "service_or_container_lifecycle_allowed": False,
    "production_identity_allowed": False,
    "runtime_postgres_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "compliance_claims_allowed": False,
    "new_power_classes_allowed": False,
}


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

    for key, value in AUTHORITY.items():
        if value is not False:
            failures.append(f"historical review authority must remain false: {key}")

    for label, commit in [
        ("candidate", CANDIDATE_COMMIT),
        ("disposition", DISPOSITION_COMMIT),
        ("source review", SOURCE_REVIEW_COMMIT),
    ]:
        if not _commit_exists(repo_root, commit):
            failures.append(f"{label} commit is missing: {commit}")
        elif not _is_ancestor(repo_root, commit):
            failures.append(f"{label} commit is not an ancestor of HEAD: {commit}")

    if _parent(repo_root, DISPOSITION_COMMIT) != CANDIDATE_COMMIT:
        failures.append("disposition commit is not the direct child of the reviewed candidate")
    if _parent(repo_root, SOURCE_REVIEW_COMMIT) != DISPOSITION_COMMIT:
        failures.append("source-review record is not the direct child of the disposition commit")
    if _changed_paths(repo_root, DISPOSITION_COMMIT) != EXPECTED_DISPOSITION_PATHS:
        failures.append("disposition commit path inventory drifted")
    if _changed_paths(repo_root, SOURCE_REVIEW_COMMIT) != EXPECTED_SOURCE_REVIEW_PATHS:
        failures.append("source-review commit path inventory drifted")

    disposition = _blob(repo_root, DISPOSITION_COMMIT, DISPOSITION_REL)
    source_review = _blob(repo_root, SOURCE_REVIEW_COMMIT, SOURCE_REVIEW_REL)
    if _sha256(disposition) != DISPOSITION_BLOB_SHA256:
        failures.append("historical disposition record blob digest drifted")
    if _sha256(source_review) != SOURCE_REVIEW_BLOB_SHA256:
        failures.append("historical source-review record blob digest drifted")
    if _file_sha256(repo_root / DISPOSITION_REL) != DISPOSITION_BLOB_SHA256:
        failures.append("current disposition record differs from its reviewed historical blob")
    if _file_sha256(repo_root / SOURCE_REVIEW_REL) != SOURCE_REVIEW_BLOB_SHA256:
        failures.append("current source-review record differs from its recorded historical blob")

    for phrase in [
        CANDIDATE_COMMIT,
        PACKET_RELEASE_CHECK_REL,
        PACKET_RELEASE_CHECK_SHA256,
        "`closure_review_dispatch_allowed`",
        "`human_uat_allowed`",
        "Sol Ultra user approval has not been obtained",
        "The packet is now a valid reviewer locator",
    ]:
        if phrase not in disposition:
            failures.append(f"historical disposition record is missing phrase: {phrase}")
    for phrase in [
        "approved_as_durable_packet_ready_non_dispatch_record_only",
        DISPOSITION_COMMIT,
        CANDIDATE_COMMIT,
        "Critical findings: `0`",
        "High findings: `0`",
        "Medium findings: `0`",
        "Low findings: `0`",
        "Open findings: `0`",
        "Sol Ultra was not used",
        "grants no Sol Ultra authority",
    ]:
        if phrase not in source_review:
            failures.append(f"historical source-review record is missing phrase: {phrase}")

    candidate_manifest_paths = {
        path
        for path in _tree_paths(repo_root, CANDIDATE_COMMIT, "tool-manifests")
        if path.endswith((".yaml", ".yml"))
    }
    if len(candidate_manifest_paths) != 24:
        failures.append("reviewed candidate tool-manifest count is not 24")
    candidate_lock = _json_blob(repo_root, CANDIDATE_COMMIT, "tool-manifests.lock.json")
    locked_manifests = candidate_lock.get("manifests")
    if not isinstance(locked_manifests, list) or len(locked_manifests) != 24:
        failures.append("reviewed candidate manifest-lock count is not 24")
    else:
        locked_paths = {
            record.get("path")
            for record in locked_manifests
            if isinstance(record, dict)
        }
        if locked_paths != candidate_manifest_paths:
            failures.append("reviewed candidate manifest lock/path inventory drifted")

    packet_path = repo_root / PACKET_REL
    packet_locally_present = packet_path.is_dir()
    packet_locally_valid = packet_locally_present and immutable_packet_valid(
        packet_path,
        CANDIDATE_COMMIT,
    )
    if packet_locally_present and not packet_locally_valid:
        failures.append("historical review packet is locally present but invalid")
    if packet_locally_valid:
        release_check_path = packet_path / "release-check.txt"
        if release_check_path.stat().st_size != PACKET_RELEASE_CHECK_BYTES:
            failures.append("historical packet release-check byte count drifted")
        if _file_sha256(release_check_path) != PACKET_RELEASE_CHECK_SHA256:
            failures.append("historical packet release-check digest drifted")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "record_status": "durable_packet_ready_non_dispatch_only",
        "candidate_commit": CANDIDATE_COMMIT,
        "disposition_commit": DISPOSITION_COMMIT,
        "source_review_commit": SOURCE_REVIEW_COMMIT,
        "packet_relative_path": PACKET_REL,
        "packet_release_check_relative_path": PACKET_RELEASE_CHECK_REL,
        "packet_release_check_sha256": PACKET_RELEASE_CHECK_SHA256,
        "packet_release_check_bytes": PACKET_RELEASE_CHECK_BYTES,
        "packet_evidence_recorded": True,
        "packet_locally_present": packet_locally_present,
        "packet_locally_valid": packet_locally_valid,
        "record_review_method": "independent_read_only_gpt_5_6_sol_xhigh",
        "record_review_findings": EXPECTED_RECORD_REVIEW_FINDINGS,
        "tool_count": 24,
        **AUTHORITY,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Command Center closure-review history check",
        f"valid: {str(report['valid']).lower()}",
        f"record_status: {report['record_status']}",
        f"candidate_commit: {report['candidate_commit']}",
        f"disposition_commit: {report['disposition_commit']}",
        f"source_review_commit: {report['source_review_commit']}",
        f"packet_relative_path: {report['packet_relative_path']}",
        f"packet_release_check_relative_path: {report['packet_release_check_relative_path']}",
        f"packet_release_check_sha256: {report['packet_release_check_sha256']}",
        f"packet_release_check_bytes: {report['packet_release_check_bytes']}",
        f"packet_evidence_recorded: {str(report['packet_evidence_recorded']).lower()}",
        f"packet_locally_present: {str(report['packet_locally_present']).lower()}",
        f"packet_locally_valid: {str(report['packet_locally_valid']).lower()}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in AUTHORITY.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def _commit_exists(repo_root: Path, commit: str) -> bool:
    return _git(repo_root, ["cat-file", "-e", f"{commit}^{{commit}}"]).returncode == 0


def _is_ancestor(repo_root: Path, commit: str) -> bool:
    return _git(repo_root, ["merge-base", "--is-ancestor", commit, "HEAD"]).returncode == 0


def _parent(repo_root: Path, commit: str) -> str:
    result = _git(repo_root, ["rev-parse", f"{commit}^"])
    return result.stdout.strip() if result.returncode == 0 else ""


def _changed_paths(repo_root: Path, commit: str) -> set[str]:
    result = _git(
        repo_root,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", commit],
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _blob(repo_root: Path, commit: str, relative_path: str) -> str:
    result = _git(repo_root, ["show", f"{commit}:{relative_path}"])
    return result.stdout if result.returncode == 0 else ""


def _json_blob(repo_root: Path, commit: str, relative_path: str) -> dict[str, Any]:
    try:
        payload = json.loads(_blob(repo_root, commit, relative_path))
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _tree_paths(repo_root: Path, commit: str, relative_path: str) -> set[str]:
    result = _git(repo_root, ["ls-tree", "-r", "--name-only", commit, relative_path])
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
