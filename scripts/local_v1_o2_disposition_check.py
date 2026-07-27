"""Validate the current Local-v1 O2 disposition and its private report binding."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

from scripts import local_v1_real_agent_rehearsal as real_agent
from scripts import local_v1_real_agent_rehearsal_check as real_agent_check

ROOT = Path(__file__).resolve().parents[1]
DISPOSITION_REL = Path("docs/codex/local-v1-lv1-007-o2-disposition.json")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_EVIDENCE_PATHS = (
    "docs/codex/local-v1-lv1-007-real-agent.md",
    "scripts/local_v1_real_agent_rehearsal.py",
    "tests/test_local_v1_real_agent_rehearsal.py",
)
EXPECTED_QUALIFICATION_PATHS = (
    "Makefile",
    "docs/codex/local-v1-completion-contract.md",
    "docs/codex/local-v1-lv1-007-o2-disposition.json",
    "docs/codex/local-v1-lv1-007-o2-disposition.md",
    "scripts/local_v1_contract_check.py",
    "scripts/local_v1_o2_disposition_check.py",
    "tests/test_local_v1_contract.py",
    "tests/test_local_v1_golden_path.py",
    "tests/test_local_v1_o2_disposition_check.py",
    "tests/test_release_readiness.py",
)
REQUIRED_OBSERVATIONS = (
    *real_agent.REQUIRED_GATEWAY_OBSERVATIONS,
    "exact_runtime_cleanup_complete",
    "gateway_truth_authoritative",
)

JsonObject = dict[str, Any]


def main() -> int:
    report = build_report(ROOT)
    print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> JsonObject:
    failures: list[str] = []
    disposition = _read_disposition(repo_root, failures)
    candidate, binding = validate_disposition_contract(disposition, failures)
    evidence_commit = candidate.get("commit")
    current_commit = _git(repo_root, "rev-parse", "HEAD", failures=failures)

    candidate_identity_valid = False
    candidate_runtime_parity = False
    if _is_commit(evidence_commit):
        observed_tree = _git(
            repo_root,
            "rev-parse",
            f"{evidence_commit}^{{tree}}",
            failures=failures,
        )
        observed_parent = _git(
            repo_root,
            "rev-parse",
            f"{evidence_commit}^",
            failures=failures,
        )
        candidate_identity_valid = (
            observed_tree == candidate.get("tree")
            and observed_parent == candidate.get("parent")
        )
        if not candidate_identity_valid:
            failures.append("O2 evidence candidate identity does not match Git")
        ancestor = _git_success(
            repo_root,
            "merge-base",
            "--is-ancestor",
            str(evidence_commit),
            str(current_commit),
        )
        changed_paths = tuple(
            _git(
                repo_root,
                "diff",
                "--name-only",
                str(evidence_commit),
                str(current_commit),
                failures=failures,
            ).splitlines()
        )
        candidate_runtime_parity = (
            ancestor and changed_paths == EXPECTED_QUALIFICATION_PATHS
        )
        if not candidate_runtime_parity:
            failures.append(
                "current candidate is not the exact O2 qualification-only descendant"
            )
    else:
        failures.append("O2 evidence candidate commit is invalid")

    if _git(repo_root, "status", "--porcelain=v1", failures=failures):
        failures.append("O2 disposition check requires a clean checkout")

    report_digest_bound = False
    report_valid = False
    report_path = select_bound_private_report(repo_root, binding, failures)
    if report_path is not None and _is_commit(evidence_commit):
        checker_failures = real_agent_check.validate_report(
            report_path,
            expected_candidate=str(evidence_commit),
        )
        if checker_failures:
            failures.extend(
                f"private O2 report: {failure}" for failure in checker_failures
            )
        else:
            report_valid = True
        report_digest_bound = validate_private_report_binding(
            report_path,
            binding,
            failures,
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "evidence_candidate": evidence_commit,
        "current_candidate": current_commit,
        "candidate_identity_valid": candidate_identity_valid,
        "candidate_runtime_parity": candidate_runtime_parity,
        "private_report_valid": report_valid,
        "report_digest_bound": report_digest_bound,
        "tool_count": disposition.get("tool_count"),
        "authority_all_false": _authority_all_false(disposition),
    }


def validate_disposition_contract(
    disposition: JsonObject,
    failures: list[str],
) -> tuple[JsonObject, JsonObject]:
    _require_exact_keys(
        disposition,
        {
            "schema_version",
            "record_type",
            "record_status",
            "evidence_candidate",
            "private_evidence_binding",
            "observations",
            "review",
            "validation",
            "authority",
            "closure",
            "tool_count",
        },
        "O2 disposition",
        failures,
    )
    if disposition.get("schema_version") != "1":
        failures.append("O2 disposition schema version is invalid")
    if disposition.get("record_type") != "local_v1_lv1_007_o2_disposition":
        failures.append("O2 disposition record type is invalid")
    if (
        disposition.get("record_status")
        != "O2_COMPLETE_O8_CANDIDATE_WORK_IN_PROGRESS_NO_RELEASE_OR_UAT_AUTHORITY"
    ):
        failures.append("O2 disposition status is invalid")
    if disposition.get("tool_count") != 24:
        failures.append("O2 disposition tool count is not 24")

    candidate = _mapping(disposition.get("evidence_candidate"))
    _require_exact_keys(
        candidate,
        {"commit", "tree", "parent", "recovery_base", "paths"},
        "O2 evidence candidate",
        failures,
    )
    if tuple(candidate.get("paths", ())) != EXPECTED_EVIDENCE_PATHS:
        failures.append("O2 disposition evidence path inventory drifted")
    for field in ("commit", "tree", "parent", "recovery_base"):
        if not _is_commit(candidate.get(field)):
            failures.append(f"O2 disposition candidate {field} is invalid")

    binding = _mapping(disposition.get("private_evidence_binding"))
    _require_exact_keys(
        binding,
        {
            "report_sha256",
            "report_mode",
            "report_size_bytes",
            "raw_run_identity_recorded",
            "raw_request_or_approval_identity_recorded",
            "private_runtime_artifacts_retained",
            "checker_result",
        },
        "O2 private evidence binding",
        failures,
    )
    if not DIGEST.fullmatch(str(binding.get("report_sha256", ""))):
        failures.append("O2 private report digest is invalid")
    if binding.get("report_mode") != "0600":
        failures.append("O2 private report mode is invalid")
    if (
        type(binding.get("report_size_bytes")) is not int
        or binding["report_size_bytes"] <= 0
    ):
        failures.append("O2 private report size is invalid")
    for field in (
        "raw_run_identity_recorded",
        "raw_request_or_approval_identity_recorded",
        "private_runtime_artifacts_retained",
    ):
        if binding.get(field) is not False:
            failures.append(f"O2 private evidence boundary is invalid: {field}")
    if binding.get("checker_result") != "valid":
        failures.append("O2 candidate-bound checker result is invalid")

    observations = _mapping(disposition.get("observations"))
    _require_exact_keys(
        observations,
        {
            "allowed_read_completed",
            "out_of_scope_read_denied_before_execution",
            "approval_required_observed",
            "approval_v2_pending_storage_observed",
            "approval_request_not_executed",
            "fixed_stdio_identity_observed",
            "audit_chain_valid",
            "audit_event_count",
            "approval_count",
            "runner_turn_exit_zero",
            "runner_process_exit_zero",
            "exact_runtime_cleanup_complete",
            "gateway_truth_authoritative",
            "runner_state_authority",
            "model_provider_state_authority",
        },
        "O2 observations",
        failures,
    )
    if any(observations.get(name) is not True for name in REQUIRED_OBSERVATIONS):
        failures.append("O2 required observation is missing")
    if observations.get("approval_count") != 1:
        failures.append("O2 approval count is not exactly one")
    if observations.get("audit_event_count") != 7:
        failures.append("O2 audit event count is not exactly seven")
    if observations.get("runner_turn_exit_zero") != {
        "allowed-read": True,
        "denied-read": True,
        "approval-write": True,
    }:
        failures.append("O2 runner turn observations are invalid")
    if observations.get("runner_process_exit_zero") is not True:
        failures.append("O2 runner process observation is invalid")
    if (
        observations.get("runner_state_authority") != "process_exit_observed_only"
        or observations.get("model_provider_state_authority")
        != "dependency_observed_only"
    ):
        failures.append("O2 truth-source boundary is invalid")

    review = _mapping(disposition.get("review"))
    _require_exact_keys(
        review,
        {
            "model_tier",
            "xhigh_used",
            "initial_candidate",
            "initial_disposition",
            "initial_findings",
            "final_candidate",
            "final_disposition",
            "final_findings",
        },
        "O2 review",
        failures,
    )
    if (
        review.get("model_tier") != "sol_high"
        or review.get("xhigh_used") is not False
        or not _is_commit(review.get("initial_candidate"))
        or review.get("initial_disposition") != "NO_GO"
        or review.get("initial_findings")
        != {"critical": 0, "high": 0, "medium": 1, "low": 0}
        or review.get("final_candidate") != candidate.get("commit")
        or review.get("final_disposition") != "GO"
        or review.get("final_findings")
        != {"critical": 0, "high": 0, "medium": 0, "low": 0}
    ):
        failures.append("O2 final review binding is invalid")

    validation = _mapping(disposition.get("validation"))
    _require_exact_keys(
        validation,
        {
            "focused_rehearsal_tests_passed",
            "ruff",
            "strict_mypy",
            "approval_semantics_tests",
            "candidate_bound_report_check",
            "local_v1_contract_check",
            "docs_site_tests",
            "agent_workflow_check",
        },
        "O2 validation",
        failures,
    )
    if validation != {
        "focused_rehearsal_tests_passed": 33,
        "ruff": "passed",
        "strict_mypy": "passed",
        "approval_semantics_tests": "passed",
        "candidate_bound_report_check": "passed",
        "local_v1_contract_check": "passed",
        "docs_site_tests": "passed",
        "agent_workflow_check": "passed",
    }:
        failures.append("O2 validation record is invalid")

    authority = _mapping(disposition.get("authority"))
    _require_exact_keys(
        authority,
        {
            "arbitrary_host_control_authorized",
            "docker_socket_mounted",
            "new_api_authorized",
            "new_governed_power_authorized",
            "new_governed_tool",
            "production_authorized",
            "promotion_allowed",
            "release_allowed",
            "uat_complete",
        },
        "O2 authority",
        failures,
    )
    closure = _mapping(disposition.get("closure"))
    _require_exact_keys(
        closure,
        {"o2_complete", "o8_status", "lv1_007_status", "active_next_action"},
        "O2 closure",
        failures,
    )
    if closure != {
        "o2_complete": True,
        "o8_status": "in_progress",
        "lv1_007_status": "in_progress",
        "active_next_action": "LV1-007",
    }:
        failures.append("O2 closure state is invalid")
    if not _authority_all_false(disposition):
        failures.append("O2 authority is not entirely false")
    return candidate, binding


def select_bound_private_report(
    repo_root: Path,
    binding: JsonObject,
    failures: list[str],
) -> Path | None:
    base = repo_root / "var/local-v1-real-agent"
    try:
        base_entry = os.lstat(base)
    except OSError:
        failures.append("O2 private evidence base is unavailable")
        return None
    if (
        not stat.S_ISDIR(base_entry.st_mode)
        or stat.S_ISLNK(base_entry.st_mode)
        or base_entry.st_uid != os.getuid()
        or stat.S_IMODE(base_entry.st_mode) & 0o022
    ):
        failures.append("O2 private evidence base is invalid")
        return None
    try:
        with os.scandir(base) as entries:
            run_entries = list(entries)
    except OSError:
        failures.append("O2 private evidence inventory is unavailable")
        return None
    if not run_entries:
        failures.append("O2 private evidence inventory is empty")
        return None
    matching_reports: list[Path] = []
    for entry in run_entries:
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError:
            failures.append("O2 private evidence run metadata is unavailable")
            return None
        if (
            entry.is_symlink()
            or not entry.is_dir(follow_symlinks=False)
            or not real_agent.RUN_ID.fullmatch(entry.name)
            or entry_stat.st_uid != os.getuid()
            or stat.S_IMODE(entry_stat.st_mode) != 0o700
        ):
            failures.append("O2 private evidence inventory contains an unsafe run")
            return None
        try:
            confined = real_agent.confined_run_root(Path(entry.path))
        except (OSError, ValueError):
            failures.append("O2 private evidence run is not confined")
            return None
        report_path = confined / real_agent.REPORT_NAME
        try:
            os.lstat(report_path)
        except FileNotFoundError:
            continue
        except OSError:
            failures.append("O2 private report metadata is unavailable")
            return None
        safe, matches = _inspect_private_report(report_path, binding)
        if not safe:
            failures.append("O2 private evidence inventory contains an unsafe report")
            return None
        if matches:
            matching_reports.append(report_path)
    if len(matching_reports) != 1:
        failures.append("O2 private report binding does not select exactly one report")
        return None
    return matching_reports[0]


def validate_private_report_binding(
    report_path: Path,
    binding: JsonObject,
    failures: list[str],
) -> bool:
    safe, matches = _inspect_private_report(report_path, binding)
    if not safe or not matches:
        failures.append("O2 private report does not match its digest-safe binding")
    return safe and matches


def _inspect_private_report(
    report_path: Path,
    binding: JsonObject,
) -> tuple[bool, bool]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(report_path, os.O_RDONLY | nofollow)
    except OSError:
        return False, False
    try:
        before = os.fstat(descriptor)
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 131072)
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    digest = f"sha256:{hashlib.sha256(payload).hexdigest()}"
    safe = (
        stat.S_ISREG(before.st_mode)
        and before.st_uid == os.getuid()
        and stat.S_IMODE(before.st_mode) == 0o600
        and (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        == (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
    )
    matches = (
        safe
        and before.st_size == binding.get("report_size_bytes")
        and digest == binding.get("report_sha256")
    )
    return safe, matches


def render_report(report: JsonObject) -> str:
    lines = [
        "Ithildin Local-v1 O2 disposition check",
        f"valid: {str(report['valid']).lower()}",
        f"evidence_candidate: {report['evidence_candidate']}",
        f"current_candidate: {report['current_candidate']}",
        f"candidate_identity_valid: {str(report['candidate_identity_valid']).lower()}",
        f"candidate_runtime_parity: {str(report['candidate_runtime_parity']).lower()}",
        f"private_report_valid: {str(report['private_report_valid']).lower()}",
        f"report_digest_bound: {str(report['report_digest_bound']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"authority_all_false: {str(report['authority_all_false']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read_disposition(repo_root: Path, failures: list[str]) -> JsonObject:
    path = repo_root / DISPOSITION_REL
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, ValueError):
        failures.append("O2 disposition is unreadable")
        return {}
    if not isinstance(payload, dict):
        failures.append("O2 disposition is not an object")
        return {}
    return payload


def _authority_all_false(disposition: JsonObject) -> bool:
    authority = _mapping(disposition.get("authority"))
    return bool(authority) and all(value is False for value in authority.values())


def _mapping(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _require_exact_keys(
    value: JsonObject,
    expected: set[str],
    label: str,
    failures: list[str],
) -> None:
    if set(value) != expected:
        failures.append(f"{label} keys are invalid")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> JsonObject:
    value: JsonObject = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _is_commit(value: Any) -> bool:
    return isinstance(value, str) and COMMIT.fullmatch(value) is not None


def _git(
    repo_root: Path,
    *arguments: str,
    failures: list[str],
) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"Git command failed: {' '.join(arguments)}")
        return ""
    return result.stdout.strip()


def _git_success(repo_root: Path, *arguments: str) -> bool:
    return (
        subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
