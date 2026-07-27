"""Validate one explicitly selected Local-v1 operations rehearsal report."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts import local_v1_operations_rehearsal as operations

ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_OBSERVATIONS = {
    "fresh_state_initialized",
    "gateway_health_verified",
    "command_center_http_verified",
    "clean_stop_before_backup",
    "backup_manifest_matched",
    "failed_update_failed_closed",
    "restore_manifest_matched",
    "restored_files_owner_only",
    "restored_stack_health_verified",
    "exact_project_cleanup_complete",
    "unique_images_removed",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    failures = validate_report(args.report, expected_candidate=args.expected_candidate)
    print("Ithildin Local-v1 operations rehearsal check")
    print(f"valid: {str(not failures).lower()}")
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


def validate_report(report_path: Path, *, expected_candidate: str) -> list[str]:
    failures: list[str] = []
    if not COMMIT.fullmatch(expected_candidate):
        return ["expected_candidate_invalid"]
    selected_report = Path(os.path.abspath(report_path))
    try:
        root = operations.confined_run_root(selected_report.parent)
    except (OSError, ValueError):
        return ["report_path_not_confined"]
    if selected_report != root / operations.REPORT_NAME:
        return ["report_filename_invalid"]
    try:
        text, entry = _read_report_nofollow(root)
        if stat.S_IMODE(entry.st_mode) != 0o600:
            failures.append("report_not_private_regular_file")
        report = json.loads(text)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return failures + ["report_unreadable"]
    if not isinstance(report, dict):
        return failures + ["report_not_object"]

    if report.get("schema_version") != "ithildin.local-v1-operations.v1":
        failures.append("schema_version_invalid")
    if report.get("result") != "passed":
        failures.append("result_not_passed")
    candidate = _mapping(report.get("candidate"))
    if candidate.get("commit") != expected_candidate:
        failures.append("candidate_mismatch")
    if candidate.get("tree") != _git_tree(expected_candidate):
        failures.append("candidate_tree_mismatch")
    if candidate.get("parent") != _git_parent(expected_candidate):
        failures.append("candidate_parent_mismatch")

    observations = _mapping(report.get("observations"))
    if any(observations.get(name) is not True for name in REQUIRED_OBSERVATIONS):
        failures.append("required_observation_missing")
    if observations.get("authenticated_tool_count") != 24:
        failures.append("observed_tool_count_invalid")
    backup = _mapping(report.get("backup"))
    if backup.get("private_artifacts_retained") is not False:
        failures.append("private_artifacts_retained")
    if not DIGEST.fullmatch(str(backup.get("manifest_digest", ""))):
        failures.append("backup_manifest_digest_invalid")
    topology = _mapping(report.get("topology"))
    if topology != {
        "docker_socket_mounted": False,
        "loopback_only": True,
        "model_provider_included": False,
        "optional_node_included": False,
    }:
        failures.append("topology_boundary_invalid")
    authority = _mapping(report.get("authority"))
    if set(authority) != set(operations.AUTHORITY) or any(authority.values()):
        failures.append("authority_not_false")
    if report.get("tool_count") != 24:
        failures.append("tool_count_invalid")
    if not isinstance(report.get("nonclaims"), list) or len(report["nonclaims"]) < 5:
        failures.append("nonclaims_incomplete")
    unexpected = sorted(
        path.name for path in root.iterdir() if path.name != operations.REPORT_NAME
    )
    if unexpected:
        failures.append("private_runtime_artifacts_retained")
    if datetime.fromtimestamp(entry.st_mtime, UTC) < datetime.now(UTC) - timedelta(days=7):
        failures.append("report_stale")
    serialized = json.dumps(report, sort_keys=True).lower()
    if "bearer " in serialized or "synthetic-test-token" in serialized:
        failures.append("report_contains_secret_marker")
    return failures


def _read_report_nofollow(root: Path) -> tuple[str, os.stat_result]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    root_descriptor = os.open(root, os.O_RDONLY | nofollow | directory)
    try:
        report_descriptor = os.open(
            operations.REPORT_NAME,
            os.O_RDONLY | nofollow,
            dir_fd=root_descriptor,
        )
        try:
            entry = os.fstat(report_descriptor)
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError("report is not a regular file")
            with os.fdopen(os.dup(report_descriptor), encoding="utf-8") as stream:
                return stream.read(), entry
        finally:
            os.close(report_descriptor)
    finally:
        os.close(root_descriptor)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _git_tree(commit: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_parent(commit: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{commit}^"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
