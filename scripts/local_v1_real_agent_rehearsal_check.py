"""Validate one explicitly selected Local-v1 real-agent report."""

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

from scripts import local_v1_real_agent_rehearsal as real_agent

ROOT = Path(__file__).resolve().parents[1]
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PRIVATE_ID = re.compile(r"\b(?:appr|req|run)_[0-9a-f]{16,}\b")
REQUIRED_OBSERVATIONS = {
    *real_agent.REQUIRED_GATEWAY_OBSERVATIONS,
    "exact_runtime_cleanup_complete",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-candidate", required=True)
    args = parser.parse_args()
    failures = validate_report(args.report, expected_candidate=args.expected_candidate)
    print("Ithildin Local-v1 real-agent rehearsal check")
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
        root = real_agent.confined_run_root(selected_report.parent)
    except (OSError, ValueError):
        return ["report_path_not_confined"]
    if selected_report != root / real_agent.REPORT_NAME:
        return ["report_filename_invalid"]
    try:
        text, entry, retained_names = _read_report_and_siblings_nofollow(root)
        if stat.S_IMODE(entry.st_mode) != 0o600:
            failures.append("report_not_private_regular_file")
        report = json.loads(text)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return failures + ["report_unreadable"]
    if not isinstance(report, dict):
        return failures + ["report_not_object"]
    if report.get("schema_version") != "ithildin.local-v1-real-agent.v1":
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
    if (
        type(observations.get("audit_event_count")) is not int
        or observations["audit_event_count"] <= 0
    ):
        failures.append("audit_event_count_invalid")
    if not isinstance(observations.get("runner_process_exit_zero"), bool):
        failures.append("runner_process_exit_observation_invalid")
    if observations.get("approval_count") != 1:
        failures.append("approval_count_invalid")
    topology = _mapping(report.get("topology"))
    if topology != {
        "candidate_source": "git_archive",
        "docker_socket_mounted": False,
        "ingress": "local_stdio_mcp",
        "model_provider": "local_ollama_dependency",
        "runner_lifecycle": "operator_managed",
        "synthetic_state_only": True,
    }:
        failures.append("topology_boundary_invalid")
    truth_sources = _mapping(report.get("truth_sources"))
    if truth_sources != {
        "gateway_policy_execution_approval_audit": "authoritative",
        "model_provider_state": "dependency_observed_only",
        "runner_state": "process_exit_observed_only",
    }:
        failures.append("truth_source_boundary_invalid")
    authority = _mapping(report.get("authority"))
    if set(authority) != set(real_agent.AUTHORITY) or any(authority.values()):
        failures.append("authority_not_false")
    if report.get("tool_count") != 24:
        failures.append("tool_count_invalid")
    if not isinstance(report.get("nonclaims"), list) or len(report["nonclaims"]) < 5:
        failures.append("nonclaims_incomplete")
    if sorted(retained_names) != [real_agent.REPORT_NAME]:
        failures.append("private_runtime_artifacts_retained")
    if datetime.fromtimestamp(entry.st_mtime, UTC) < datetime.now(UTC) - timedelta(days=7):
        failures.append("report_stale")
    serialized = json.dumps(report, sort_keys=True)
    lowered = serialized.lower()
    if (
        PRIVATE_ID.search(serialized)
        or "bearer " in lowered
        or "synthetic-test-token" in lowered
        or real_agent.FIXED_QUERY in serialized
    ):
        failures.append("report_contains_private_or_prompt_content")
    return failures


def _read_report_and_siblings_nofollow(
    root: Path,
) -> tuple[str, os.stat_result, list[str]]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    try:
        relative = root.relative_to(real_agent.ROOT)
    except ValueError as exc:
        raise ValueError("report root is outside the repository") from exc
    repository_descriptor = os.open(
        real_agent.ROOT,
        os.O_RDONLY | nofollow | directory,
    )
    root_descriptor = repository_descriptor
    try:
        for component in relative.parts:
            next_descriptor = os.open(
                component,
                os.O_RDONLY | nofollow | directory,
                dir_fd=root_descriptor,
            )
            if root_descriptor != repository_descriptor:
                os.close(root_descriptor)
            root_descriptor = next_descriptor
        report_descriptor = os.open(
            real_agent.REPORT_NAME,
            os.O_RDONLY | nofollow,
            dir_fd=root_descriptor,
        )
        try:
            entry = os.fstat(report_descriptor)
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError("report is not a regular file")
            with os.fdopen(os.dup(report_descriptor), encoding="utf-8") as stream:
                text = stream.read()
            return text, entry, os.listdir(root_descriptor)
        finally:
            os.close(report_descriptor)
    finally:
        if root_descriptor != repository_descriptor:
            os.close(root_descriptor)
        os.close(repository_descriptor)


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
