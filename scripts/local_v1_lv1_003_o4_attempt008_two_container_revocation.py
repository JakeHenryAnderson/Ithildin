"""Observe the exact stopped API/UI pair and revoke the retained Attempt 008 Node."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Protocol, cast

from ithildin_api.nodes import (
    NodeConflictError,
    NodeNotFoundError,
    NodeStore,
)
from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import AuditEventType, JsonObject, JsonValue

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as identity,
)
from scripts import (
    local_v1_lv1_003_o4_attempt008_port_release as port_release,
)
from scripts import (
    local_v1_lv1_003_o4_attempt008_quarantine_revocation as predecessor,
)

ROOT = Path(__file__).resolve().parents[1]
PARENT_COMMIT = "cbf304512965fbd10df6b72b78777750ac4cc6d5"
PARENT_TREE = "654193cf9456433bcafc6da7c5dc6d2d076af54e"
RECOVERY_ID = "LV1-003-O4-ATTEMPT-008-TWO-CONTAINER-REVOCATION-001"
REVIEW_TAG = "ithildin/lv1-003-o4-attempt008-two-container-revocation-reviewed"
RECEIPT_DIRECTORY = "attempt-008-two-container-revocation-001"
CONSUMED_RECEIPT = "consumed.json"
JOURNAL_DIRECTORY = "journal"
DISPOSITION_RECEIPT = "disposition.json"
PROJECT = predecessor.PROJECT
GIT_EXECUTABLE = "/usr/bin/git"

AUTHORIZATION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-two-container-revocation-authorization.json"
)
AUTHORIZATION_MD = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-two-container-revocation-authorization.md"
)
PREDECESSOR_CLOSURE_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-quarantine-revocation-attempt-001-disposition.json"
)
PREDECESSOR_CLOSURE_MD = PREDECESSOR_CLOSURE_JSON.with_suffix(".md")
SCRIPT_PATH = Path("scripts/local_v1_lv1_003_o4_attempt008_two_container_revocation.py")
TEST_PATH = Path("tests/test_local_v1_lv1_003_o4_attempt008_two_container_revocation.py")
CHECK_TARGET = "local-v1-lv1-003-o4-attempt008-two-container-revocation-check"
RUN_TARGET = "local-v1-lv1-003-o4-attempt008-two-container-revocation-run"
CANDIDATE_PATH_ALLOWLIST = sorted(
    [
        "Makefile",
        "README.md",
        AUTHORIZATION_JSON.as_posix(),
        AUTHORIZATION_MD.as_posix(),
        PREDECESSOR_CLOSURE_JSON.as_posix(),
        PREDECESSOR_CLOSURE_MD.as_posix(),
        SCRIPT_PATH.as_posix(),
        TEST_PATH.as_posix(),
    ]
)

PREDECESSOR_RECEIPT_COMPONENTS = (
    "var",
    "local-v1-lv1-003-o4-reconciliation-receipts",
    predecessor.RECOVERY_RECEIPT_DIRECTORY,
)
PREDECESSOR_CONSUMED_SIZE = 494
PREDECESSOR_CONSUMED_SHA256 = (
    "sha256:b1873a883817b7171e1483ec84fde65c14f6a65df5fb36ea59da756a3197110a"
)
PREDECESSOR_IDENTITY_JOURNAL_SIZE = 806
PREDECESSOR_IDENTITY_JOURNAL_SHA256 = (
    "sha256:9db067d2261b53404280c9487c0fe704b6d79796144e383e7f8c64e991adf1a7"
)

EXPECTED_CONTAINERS: Final[dict[str, tuple[str, str]]] = {
    "ithildin-api": (
        "0bc38e9961ef6d190f5cc3d67b1c047077c2e143b541ee402032a06ecb292b85",
        "sha256:20edad55b1bc2a67f6aa02c164122cdfc54ef139c4628e9ed9043936b9114242",
    ),
    "ithildin-ui": (
        "5bc1d0a6d75db49d7501a8d1bdccc5ffe60d09ab54110d0a6eef6a99ca734d63",
        "sha256:c3f77a6d09fad1df44dbd2506a2b92ba437bb3d2fead2d43040019b2ff69a27c",
    ),
}
JOURNAL_EVENTS: Final[tuple[str, ...]] = (
    "predecessor-failed-operation-bound",
    "identity-receipts-validated",
    "exact-two-container-preinspection",
    "storage-aliases-bound",
    "storage-preflight-complete",
    "revocation-plan",
    "node-revocation-observed-pending",
    "audit-event-observed-complete",
    "node-evidence-observed-complete",
    "exact-two-container-postinspection",
    "disposition-intent",
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_EVENT_ID = re.compile(r"^evt_[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^req_[0-9a-f]{32}$")
MAX_DOCKER_OUTPUT_BYTES = predecessor.MAX_DOCKER_OUTPUT_BYTES


class RecoveryError(RuntimeError):
    """Stable, non-reflective successor recovery error."""

    def __init__(self, code: str) -> None:
        if re.fullmatch(r"[a-z0-9_]{3,96}", code) is None:
            raise ValueError("unsafe recovery error code")
        super().__init__(code)
        self.code = code


def _git(repo_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        (GIT_EXECUTABLE, *arguments),
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    if result.returncode != 0:
        raise RecoveryError("candidate_identity_invalid")
    return result.stdout.strip()


def _read_json(path: Path) -> JsonObject:
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=predecessor._closed_object,  # noqa: SLF001
        )
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
        predecessor.RecoveryError,
    ) as exc:
        raise RecoveryError("tracked_record_invalid") from exc
    if not isinstance(raw, dict):
        raise RecoveryError("tracked_record_invalid")
    return raw


def _expected_authorization() -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": ("local_v1_lv1_003_o4_attempt008_two_container_revocation_authorization"),
        "record_status": "AUTHORIZED_UNCONSUMED_EXACT_RESUMABLE_ONE_SHOT",
        "recovery_id": RECOVERY_ID,
        "parent_commit": PARENT_COMMIT,
        "parent_tree": PARENT_TREE,
        "candidate_path_count": 8,
        "review_tag": REVIEW_TAG,
        "target_project": PROJECT,
        "required_project_services": ["ithildin-api", "ithildin-ui"],
        "ithildin_node_project_observation": (
            "not_observed_in_exact_project_query_at_preinspection"
        ),
        "hermes_project_observation": ("not_observed_in_exact_project_query_at_preinspection"),
        "container_stop_authorized": False,
        "docker_mutation_authorized": False,
        "single_active_invocation_required": True,
        "attempt_budget": 1,
        "retry_authorized": False,
        "same_operation_resume_authorized": True,
        "static_validation_reads_runtime": False,
        "raw_node_id_tracked_or_printed": False,
        "audit_lifecycle_repair_authorized": False,
        "old_receipt_mutation_authorized": False,
        "uv_lock_deletion_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "generic_container_absence_claimed": False,
        "generic_process_absence_claimed": False,
        "host_wide_storage_exclusivity_claimed": False,
        "tool_count": 24,
        "release_allowed": False,
        "uat_complete": False,
    }


def _expected_predecessor_closure() -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": (
            "local_v1_lv1_003_o4_attempt008_quarantine_revocation_attempt_001_disposition"
        ),
        "record_status": "CONSUMED_FAILED_CLOSED",
        "recovery_id": predecessor.RECOVERY_ID,
        "execution_candidate_commit": PARENT_COMMIT,
        "execution_candidate_tree": PARENT_TREE,
        "review_tag": predecessor.REVIEW_TAG,
        "invocations": [
            {
                "sequence": 1,
                "result": "docker_trust_boundary_invalid",
                "last_durable_stage": "identity-receipts-validated",
                "docker_command_executed": False,
                "storage_mutation_executed": False,
            },
            {
                "sequence": 2,
                "result": "project_container_set_invalid",
                "last_durable_stage": "identity-receipts-validated",
                "exact_project_query_executed": True,
                "docker_mutation_executed": False,
                "storage_mutation_executed": False,
            },
        ],
        "receipt_binding": {
            "consumed_size": PREDECESSOR_CONSUMED_SIZE,
            "consumed_sha256": PREDECESSOR_CONSUMED_SHA256,
            "identity_journal_size": PREDECESSOR_IDENTITY_JOURNAL_SIZE,
            "identity_journal_sha256": PREDECESSOR_IDENTITY_JOURNAL_SHA256,
            "project_preinspection_absent": True,
            "database_alias_absent": True,
            "audit_alias_absent": True,
            "disposition_absent": True,
            "uv_lock_preserved_outside_authority": True,
        },
        "bounded_diagnostic": {
            "exact_project_container_count": 2,
            "services": {
                "ithildin-api": {
                    "reviewed_identity_match": True,
                    "running": False,
                    "status": "exited",
                },
                "ithildin-ui": {
                    "reviewed_identity_match": True,
                    "running": False,
                    "status": "exited",
                },
            },
            "ithildin_node": ("not_observed_in_exact_project_query_at_preinspection"),
            "hermes": ("not_observed_in_exact_project_query_at_preinspection"),
            "generic_container_absence_claimed": False,
            "generic_process_absence_claimed": False,
        },
        "attempt_budget": 0,
        "retry_authorized": False,
        "same_operation_resume_authorized": False,
        "old_tag_move_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "tool_count": 24,
        "release_allowed": False,
        "uat_complete": False,
    }


def validate_tracked_records(repo_root: Path) -> None:
    if _read_json(repo_root / AUTHORIZATION_JSON) != _expected_authorization():
        raise RecoveryError("authorization_invalid")
    closure = _read_json(repo_root / PREDECESSOR_CLOSURE_JSON)
    if closure != _expected_predecessor_closure():
        raise RecoveryError("predecessor_closure_invalid")
    for path, tokens in (
        (
            AUTHORIZATION_MD,
            (
                RECOVERY_ID,
                REVIEW_TAG,
                "no Docker mutation",
                "not_observed_in_exact_project_query_at_preinspection",
                "count remains 24",
            ),
        ),
        (
            PREDECESSOR_CLOSURE_MD,
            (
                "CONSUMED_FAILED_CLOSED",
                PARENT_COMMIT,
                "No stop intent",
                "budget is zero",
            ),
        ),
    ):
        try:
            text = (repo_root / path).read_text(encoding="utf-8")
        except OSError as exc:
            raise RecoveryError("tracked_record_invalid") from exc
        if any(token not in text for token in tokens):
            raise RecoveryError("tracked_record_invalid")


def validate_static_candidate(repo_root: Path) -> tuple[str, str]:
    validate_tracked_records(repo_root)
    commit = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    if not _COMMIT.fullmatch(commit) or not _COMMIT.fullmatch(tree):
        raise RecoveryError("candidate_identity_invalid")
    if _git(repo_root, "status", "--porcelain=v1"):
        raise RecoveryError("candidate_worktree_not_clean")
    if _git(repo_root, "show", "-s", "--format=%P", commit).split() != [PARENT_COMMIT]:
        raise RecoveryError("candidate_parent_invalid")
    if _git(repo_root, "rev-parse", f"{PARENT_COMMIT}^{{tree}}") != PARENT_TREE:
        raise RecoveryError("candidate_parent_invalid")
    changed = sorted(
        line
        for line in _git(
            repo_root,
            "diff",
            "--name-only",
            f"{PARENT_COMMIT}..{commit}",
        ).splitlines()
        if line
    )
    if changed != CANDIDATE_PATH_ALLOWLIST:
        raise RecoveryError("candidate_scope_invalid")
    if len(list((repo_root / "tool-manifests").glob("*.yaml"))) != 24:
        raise RecoveryError("tool_count_invalid")
    return commit, tree


def validate_review_binding(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    try:
        tagged_commit = _git(repo_root, "rev-parse", f"refs/tags/{REVIEW_TAG}^{{commit}}")
        tagged_tree = _git(repo_root, "rev-parse", f"refs/tags/{REVIEW_TAG}^{{tree}}")
    except RecoveryError as exc:
        raise RecoveryError("review_binding_invalid") from exc
    if tagged_commit != candidate_commit or tagged_tree != candidate_tree:
        raise RecoveryError("review_binding_invalid")


def build_report(repo_root: Path = ROOT) -> JsonObject:
    failures: list[str] = []
    binding_failures: list[str] = []
    commit: str | None = None
    tree: str | None = None
    try:
        commit, tree = validate_static_candidate(repo_root)
    except RecoveryError as exc:
        failures.append(exc.code)
    static_valid = not failures
    if static_valid and commit is not None and tree is not None:
        try:
            validate_review_binding(
                repo_root,
                candidate_commit=commit,
                candidate_tree=tree,
            )
        except RecoveryError as exc:
            binding_failures.append(exc.code)
    binding_valid = not binding_failures
    execution_available = static_valid and binding_valid
    return {
        "recovery_id": RECOVERY_ID,
        "candidate_commit": commit,
        "candidate_tree": tree,
        "static_candidate_valid": static_valid,
        "review_binding_valid": binding_valid,
        "execution_available": execution_available,
        "attempt_budget": 1 if execution_available else 0,
        "static_failures": cast(list[JsonValue], failures),
        "review_binding_failures": cast(list[JsonValue], binding_failures),
        "docker_mutation_authorized": False,
        "container_stop_authorized": False,
        "retry_authorized": False,
        "same_operation_resume_authorized": True,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _validate_predecessor_receipts(repo_root: Path) -> None:
    consumed = predecessor._read_bound_leaf(  # noqa: SLF001
        repo_root,
        PREDECESSOR_RECEIPT_COMPONENTS,
        predecessor.CONSUMED_RECEIPT,
        expected_size=PREDECESSOR_CONSUMED_SIZE,
        expected_digest=PREDECESSOR_CONSUMED_SHA256,
    )
    identity_journal = predecessor._read_bound_leaf(  # noqa: SLF001
        repo_root,
        (*PREDECESSOR_RECEIPT_COMPONENTS, predecessor.JOURNAL_DIRECTORY),
        "0001-identity-receipts-validated.json",
        expected_size=PREDECESSOR_IDENTITY_JOURNAL_SIZE,
        expected_digest=PREDECESSOR_IDENTITY_JOURNAL_SHA256,
    )
    consumed_record = predecessor._closed_json(  # noqa: SLF001
        consumed,
        error_code="predecessor_receipt_invalid",
    )
    journal_record = predecessor._closed_json(  # noqa: SLF001
        identity_journal,
        error_code="predecessor_receipt_invalid",
    )
    if (
        consumed_record.get("recovery_id") != predecessor.RECOVERY_ID
        or consumed_record.get("candidate_commit") != PARENT_COMMIT
        or consumed_record.get("candidate_tree") != PARENT_TREE
        or consumed_record.get("attempt_budget") != 0
        or consumed_record.get("retry_authorized") is not False
        or journal_record.get("recovery_id") != predecessor.RECOVERY_ID
        or journal_record.get("sequence") != 1
        or journal_record.get("event") != "identity-receipts-validated"
        or not isinstance(journal_record.get("payload"), dict)
    ):
        raise RecoveryError("predecessor_receipt_invalid")
    descriptors: list[int] = []
    try:
        descriptors, _identities = predecessor._open_fixed_chain(  # noqa: SLF001
            repo_root,
            PREDECESSOR_RECEIPT_COMPONENTS,
        )
        root_fd = descriptors[-1]
        journal_fd = os.open(
            predecessor.JOURNAL_DIRECTORY,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=root_fd,
        )
        descriptors.append(journal_fd)
        forbidden_later_leaves = [
            (root_fd, predecessor.DISPOSITION_RECEIPT),
            (root_fd, predecessor.DATABASE_ALIAS),
            (root_fd, predecessor.AUDIT_ALIAS),
        ]
        forbidden_later_leaves.extend(
            (journal_fd, f"{sequence:04d}-{event}.json")
            for sequence, event in enumerate(
                predecessor.JOURNAL_EVENTS[1:],
                start=2,
            )
        )
        for directory_fd, name in forbidden_later_leaves:
            try:
                os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise RecoveryError("predecessor_receipt_invalid")
    except OSError as exc:
        raise RecoveryError("predecessor_receipt_invalid") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


@dataclass
class ReceiptSession:
    repo_root: Path
    receipt_fd: int
    held: list[int]
    candidate_commit: str
    candidate_tree: str

    @property
    def root_path(self) -> Path:
        return (
            self.repo_root / "var/local-v1-lv1-003-o4-reconciliation-receipts" / RECEIPT_DIRECTORY
        )

    def close(self) -> None:
        for descriptor in reversed(self.held):
            os.close(descriptor)
        self.held.clear()


def consume_or_resume(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> ReceiptSession:
    try:
        base_fd, held = identity._open_or_create_receipt_base(  # noqa: SLF001
            repo_root
        )
    except identity.ReconciliationError as exc:
        raise RecoveryError("receipt_invalid") from exc
    created = False
    try:
        try:
            os.mkdir(RECEIPT_DIRECTORY, 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
            created = True
        except FileExistsError:
            pass
        receipt_fd, _receipt_identity = identity._open_directory(  # noqa: SLF001
            base_fd,
            RECEIPT_DIRECTORY,
            private=True,
        )
        held.append(receipt_fd)
        held.append(predecessor._acquire_operation_lock(receipt_fd))  # noqa: SLF001
        expected: JsonObject = {
            "schema_version": "1",
            "record_type": "attempt008_two_container_revocation_consumption",
            "recovery_id": RECOVERY_ID,
            "candidate_commit": candidate_commit,
            "candidate_tree": candidate_tree,
            "consumed_before_live_access": True,
            "attempt_budget": 0,
            "retry_authorized": False,
            "same_operation_resume_authorized": True,
            "docker_mutation_authorized": False,
            "cleanup_authorized": False,
            "successor_o4_authorized": False,
            "release_allowed": False,
            "uat_complete": False,
        }
        if created:
            predecessor._write_exclusive(  # noqa: SLF001
                receipt_fd,
                CONSUMED_RECEIPT,
                expected,
            )
        elif (
            predecessor._read_private_json(  # noqa: SLF001
                receipt_fd, CONSUMED_RECEIPT
            )
            != expected
        ):
            raise RecoveryError("receipt_invalid")
        if (
            predecessor._read_private_json(  # noqa: SLF001
                receipt_fd, DISPOSITION_RECEIPT
            )
            is not None
        ):
            raise RecoveryError("operation_already_completed")
        return ReceiptSession(
            repo_root,
            receipt_fd,
            held,
            candidate_commit,
            candidate_tree,
        )
    except BaseException:
        for descriptor in reversed(held):
            os.close(descriptor)
        raise


class DurableJournal:
    def __init__(self, session: ReceiptSession) -> None:
        self._session = session
        try:
            try:
                os.mkdir(JOURNAL_DIRECTORY, 0o700, dir_fd=session.receipt_fd)
                os.fsync(session.receipt_fd)
            except FileExistsError:
                pass
            self._fd, _identity = identity._open_directory(  # noqa: SLF001
                session.receipt_fd,
                JOURNAL_DIRECTORY,
                private=True,
            )
        except (OSError, identity.ReconciliationError) as exc:
            raise RecoveryError("journal_invalid") from exc
        self._next_index = 0

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def _name(self, index: int) -> str:
        return f"{index + 1:04d}-{JOURNAL_EVENTS[index]}.json"

    def peek(self, event: str) -> JsonObject | None:
        if self._next_index >= len(JOURNAL_EVENTS) or JOURNAL_EVENTS[self._next_index] != event:
            raise RecoveryError("journal_sequence_invalid")
        index = self._next_index
        existing = predecessor._read_private_json(  # noqa: SLF001
            self._fd, self._name(index)
        )
        if existing is None:
            for future in range(index + 1, len(JOURNAL_EVENTS)):
                if (
                    predecessor._read_private_json(  # noqa: SLF001
                        self._fd, self._name(future)
                    )
                    is not None
                ):
                    raise RecoveryError("journal_sequence_invalid")
            return None
        if (
            set(existing)
            != {
                "schema_version",
                "record_type",
                "recovery_id",
                "sequence",
                "event",
                "payload",
            }
            or existing.get("schema_version") != "1"
            or existing.get("record_type") != "attempt008_two_container_revocation_journal"
            or existing.get("recovery_id") != RECOVERY_ID
            or existing.get("sequence") != index + 1
            or existing.get("event") != event
            or not isinstance(existing.get("payload"), dict)
        ):
            raise RecoveryError("journal_invalid")
        return cast(JsonObject, existing["payload"])

    def record(
        self,
        event: str,
        proposed_payload: JsonObject,
    ) -> tuple[JsonObject, bool]:
        index = self._next_index
        payload = self.peek(event)
        created = payload is None
        if payload is None:
            payload = proposed_payload
            predecessor._write_exclusive(  # noqa: SLF001
                self._fd,
                self._name(index),
                {
                    "schema_version": "1",
                    "record_type": ("attempt008_two_container_revocation_journal"),
                    "recovery_id": RECOVERY_ID,
                    "sequence": index + 1,
                    "event": event,
                    "payload": payload,
                },
            )
        self._next_index += 1
        return payload, created


@dataclass(frozen=True)
class ObservationPlan:
    docker_executable: str

    def query(self) -> tuple[str, ...]:
        return (
            self.docker_executable,
            "ps",
            "--all",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
        )

    def inspect(self, container_id: str) -> tuple[str, ...]:
        if container_id not in {value[0] for value in EXPECTED_CONTAINERS.values()}:
            raise RecoveryError("container_inspection_not_allowed")
        return (
            self.docker_executable,
            "container",
            "inspect",
            "--format",
            port_release.INSPECT_FORMAT,
            container_id,
        )


class ObservationExecutor:
    def __init__(
        self,
        environment: Mapping[str, str],
        plan: ObservationPlan,
        sealed: port_release.SealedDockerExecutable,
    ) -> None:
        if "PATH" in environment or sealed.path != plan.docker_executable:
            raise RecoveryError("docker_environment_not_isolated")
        self._environment = dict(environment)
        self._plan = plan
        self._sealed = sealed

    def _run(self, command: tuple[str, ...]) -> port_release.CommandResult:
        self._sealed.verify()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=20,
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RecoveryError("docker_command_unavailable") from exc
        self._sealed.verify()
        if len(completed.stdout) > MAX_DOCKER_OUTPUT_BYTES:
            raise RecoveryError("docker_output_invalid")
        try:
            output = completed.stdout.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise RecoveryError("docker_output_invalid") from exc
        return port_release.CommandResult(completed.returncode, output)

    def query(self) -> port_release.CommandResult:
        return self._run(self._plan.query())

    def inspect(self, container_id: str) -> port_release.CommandResult:
        return self._run(self._plan.inspect(container_id))


class ProjectObserver(Protocol):
    def query(self) -> port_release.CommandResult: ...

    def inspect(self, container_id: str) -> port_release.CommandResult: ...


class RecoveryJournal(Protocol):
    def peek(self, event: str) -> JsonObject | None: ...

    def record(
        self,
        event: str,
        proposed_payload: JsonObject,
    ) -> tuple[JsonObject, bool]: ...


def observe_exact_project(executor: ProjectObserver) -> JsonObject:
    query = executor.query()
    if query.returncode != 0:
        raise RecoveryError("project_container_query_failed")
    try:
        ids = port_release._parse_ids(query.stdout)  # noqa: SLF001
    except port_release.PortReleaseError as exc:
        raise RecoveryError("project_container_set_invalid") from exc
    expected_ids = {value[0] for value in EXPECTED_CONTAINERS.values()}
    if len(ids) != 2 or set(ids) != expected_ids:
        raise RecoveryError("project_container_set_invalid")
    observed: JsonObject = {}
    for container_id in ids:
        result = executor.inspect(container_id)
        if result.returncode != 0:
            raise RecoveryError("container_inspection_failed")
        try:
            projection = port_release._parse_projection(  # noqa: SLF001
                result.stdout,
                container_id,
                allow_cleared_ports=True,
            )
        except port_release.PortReleaseError as exc:
            raise RecoveryError("container_projection_invalid") from exc
        expected = EXPECTED_CONTAINERS.get(projection.service)
        if (
            expected is None
            or expected != (projection.container_id, projection.image_id)
            or projection.running
            or projection.status != "exited"
            or projection.ports != {}
            or projection.service in observed
        ):
            raise RecoveryError("container_projection_invalid")
        observed[projection.service] = predecessor._projection_record(  # noqa: SLF001
            projection
        )
    if set(observed) != set(EXPECTED_CONTAINERS):
        raise RecoveryError("project_container_set_invalid")
    return observed


def _deterministic_id(prefix: str, label: bytes) -> str:
    digest = hashlib.sha256(RECOVERY_ID.encode("ascii") + b"\x00" + label).hexdigest()
    return prefix + digest[:32]


def _execute_storage_transition(
    aliases: predecessor.StorageAliases,
    reconciled: predecessor.ReconciledIdentity,
    journal: RecoveryJournal,
    require_quiesced: Callable[[], None],
) -> JsonObject:
    require_quiesced()
    aliases.revalidate()
    database_before = aliases.database_bytes()
    audit_before = aliases.audit_bytes()
    store = NodeStore(aliases.database_path)
    writer = AuditWriter(aliases.database_path, aliases.audit_path)
    aliases_payload, _created = journal.record(
        "storage-aliases-bound",
        {
            "database_alias_bound": True,
            "audit_alias_bound": True,
            "source_paths_retained": True,
            "aliases_retained_for_same_operation_resume": True,
        },
    )
    if aliases_payload != {
        "database_alias_bound": True,
        "audit_alias_bound": True,
        "source_paths_retained": True,
        "aliases_retained_for_same_operation_resume": True,
    }:
        raise RecoveryError("journal_invalid")
    existing_preflight = journal.peek("storage-preflight-complete")
    if existing_preflight is None:
        if (
            len(database_before) != reconciled.database_size
            or predecessor._sha256(database_before)  # noqa: SLF001
            != reconciled.database_digest
        ):
            raise RecoveryError("database_snapshot_binding_changed")
        projected = identity.project_identity(database_before)
        if (
            projected.get("classification") != "identity_bound_active_quarantine_required"
            or projected.get("node_id") != reconciled.node_id
            or projected.get("node_identity_digest") != reconciled.identity_digest
        ):
            raise RecoveryError("database_identity_preflight_invalid")
        record = store.get(reconciled.node_id)
        predecessor._require_node_state(record, reconciled)  # noqa: SLF001
        if record.status != "enrolled" or record.evidence_status != "complete":
            raise RecoveryError("database_identity_preflight_invalid")
        preflight_payload: JsonObject = {
            "database_size": len(database_before),
            "database_sha256": predecessor._sha256(database_before),  # noqa: SLF001
            "audit_size": len(audit_before),
            "audit_sha256": predecessor._sha256(audit_before),  # noqa: SLF001
            "audit_posture": predecessor._audit_posture(writer),  # noqa: SLF001
            "identity_digest": reconciled.identity_digest,
        }
    else:
        preflight_payload = existing_preflight
    preflight, preflight_created = journal.record("storage-preflight-complete", preflight_payload)
    if (
        set(preflight)
        != {
            "database_size",
            "database_sha256",
            "audit_size",
            "audit_sha256",
            "audit_posture",
            "identity_digest",
        }
        or preflight.get("database_size") != reconciled.database_size
        or preflight.get("database_sha256") != reconciled.database_digest
        or type(preflight.get("audit_size")) is not int
        or cast(int, preflight["audit_size"]) < 0
        or not isinstance(preflight.get("audit_sha256"), str)
        or _SHA256.fullmatch(cast(str, preflight["audit_sha256"])) is None
        or preflight.get("identity_digest") != reconciled.identity_digest
        or not isinstance(preflight.get("audit_posture"), dict)
    ):
        raise RecoveryError("journal_invalid")
    predecessor._validate_audit_posture(  # noqa: SLF001
        preflight["audit_posture"]
    )
    if not preflight_created:
        predecessor._audit_posture(writer)  # noqa: SLF001
    proposed_plan: JsonObject = {
        "event_id": _deterministic_id("evt_", b"event"),
        "request_id": _deterministic_id("req_", b"request"),
        "revoked_at": datetime.now(UTC).isoformat(),
        "identity_digest": reconciled.identity_digest,
        "principal": "system:local-recovery",
    }
    plan, _created = journal.record("revocation-plan", proposed_plan)
    event_id = plan.get("event_id")
    request_id = plan.get("request_id")
    timestamp = predecessor._parse_aware_timestamp(  # noqa: SLF001
        plan.get("revoked_at")
    )
    if (
        set(plan)
        != {
            "event_id",
            "request_id",
            "revoked_at",
            "identity_digest",
            "principal",
        }
        or not isinstance(event_id, str)
        or _EVENT_ID.fullmatch(event_id) is None
        or event_id != _deterministic_id("evt_", b"event")
        or not isinstance(request_id, str)
        or _REQUEST_ID.fullmatch(request_id) is None
        or request_id != _deterministic_id("req_", b"request")
        or plan.get("identity_digest") != reconciled.identity_digest
        or plan.get("principal") != "system:local-recovery"
    ):
        raise RecoveryError("revocation_plan_invalid")
    record = store.get(reconciled.node_id)
    predecessor._require_node_state(record, reconciled)  # noqa: SLF001
    if (
        record.status == "enrolled"
        and record.evidence_status == "complete"
        and (
            predecessor._sha256(database_before)  # noqa: SLF001
            != preflight["database_sha256"]
            or predecessor._sha256(audit_before)  # noqa: SLF001
            != preflight["audit_sha256"]
        )
    ):
        raise RecoveryError("storage_resume_snapshot_changed")
    existing_event = predecessor._load_audit_event(  # noqa: SLF001
        aliases.database_path, event_id
    )
    if record.status == "enrolled" and record.evidence_status == "complete":
        if existing_event is not None:
            raise RecoveryError("revocation_state_ambiguous")
        require_quiesced()
        aliases.revalidate()
        try:
            record = store.revoke(reconciled.node_id, now=timestamp)
        except (NodeConflictError, NodeNotFoundError) as exc:
            raise RecoveryError("node_revocation_failed") from exc
        aliases.revalidate()
        require_quiesced()
    elif (
        record.status == "revoked"
        and record.evidence_status in {"pending", "complete"}
        and record.revoked_at == timestamp.isoformat()
        and record.updated_at == timestamp.isoformat()
    ):
        pass
    else:
        raise RecoveryError("revocation_state_ambiguous")
    expected_pending: JsonObject = {
        "identity_digest": reconciled.identity_digest,
        "status": "revoked",
        "pending_transition_observed": True,
        "revoked_at": timestamp.isoformat(),
    }
    pending, _created = journal.record(
        "node-revocation-observed-pending",
        expected_pending,
    )
    if pending != expected_pending:
        raise RecoveryError("journal_invalid")
    predecessor._audit_posture(writer)  # noqa: SLF001
    record = store.get(reconciled.node_id)
    expected_metadata = predecessor._expected_audit_metadata(  # noqa: SLF001
        record
    )
    existing_event = predecessor._load_audit_event(  # noqa: SLF001
        aliases.database_path, event_id
    )
    if existing_event is None:
        if record.status != "revoked" or record.evidence_status != "pending":
            raise RecoveryError("revocation_state_ambiguous")
        require_quiesced()
        aliases.revalidate()
        try:
            existing_event = writer.write_event(
                event_id=event_id,
                event_type=AuditEventType.NODE_REVOKED,
                request_id=request_id,
                principal={"id": "system:local-recovery", "roles": ["Admin"]},
                timestamp=timestamp,
                metadata=expected_metadata,
            )
        except AuditWriteError as exc:
            raise RecoveryError("audit_lifecycle_recovery_required") from exc
        aliases.revalidate()
        require_quiesced()
    predecessor._validate_audit_event(  # noqa: SLF001
        existing_event,
        event_id=event_id,
        request_id=request_id,
        timestamp=timestamp,
        expected_metadata=expected_metadata,
    )
    audit_posture = predecessor._audit_posture(writer)  # noqa: SLF001
    expected_audit_payload: JsonObject = {
        "event_id": event_id,
        "event_hash": existing_event.event_hash,
        "event_type": AuditEventType.NODE_REVOKED.value,
        "audit_posture": audit_posture,
    }
    audit_payload, _created = journal.record(
        "audit-event-observed-complete",
        expected_audit_payload,
    )
    if audit_payload != expected_audit_payload:
        raise RecoveryError("journal_invalid")
    record = store.get(reconciled.node_id)
    predecessor._require_node_state(record, reconciled)  # noqa: SLF001
    if record.status != "revoked":
        raise RecoveryError("revocation_state_ambiguous")
    if record.evidence_status == "pending":
        require_quiesced()
        aliases.revalidate()
        try:
            record = store.mark_node_evidence_complete(reconciled.node_id)
        except NodeConflictError as exc:
            raise RecoveryError("node_evidence_completion_failed") from exc
        aliases.revalidate()
        require_quiesced()
    if record.evidence_status != "complete":
        raise RecoveryError("node_evidence_completion_failed")
    expected_complete: JsonObject = {
        "identity_digest": reconciled.identity_digest,
        "status": "revoked",
        "evidence_status": "complete",
        "revoked_at": timestamp.isoformat(),
    }
    complete, _created = journal.record(
        "node-evidence-observed-complete",
        expected_complete,
    )
    if complete != expected_complete:
        raise RecoveryError("journal_invalid")
    require_quiesced()
    aliases.revalidate()
    database_after = aliases.database_bytes()
    projected_after = identity.project_identity(database_after)
    if (
        projected_after.get("classification") != "identity_bound_revoked"
        or projected_after.get("node_id") != reconciled.node_id
        or projected_after.get("node_identity_digest") != reconciled.identity_digest
    ):
        raise RecoveryError("revocation_postcondition_invalid")
    final_audit = predecessor._audit_posture(writer)  # noqa: SLF001
    return {
        "identity_digest": reconciled.identity_digest,
        "node_status": "revoked",
        "node_evidence_status": "complete",
        "revoked_at": timestamp.isoformat(),
        "audit_event_id": event_id,
        "audit_event_hash": existing_event.event_hash,
        "audit_posture": final_audit,
        "database_before_sha256": preflight["database_sha256"],
        "database_after_sha256": predecessor._sha256(database_after),  # noqa: SLF001
        "audit_before_sha256": preflight["audit_sha256"],
        "audit_after_sha256": predecessor._sha256(  # noqa: SLF001
            aliases.audit_bytes()
        ),
        "storage_aliases_retained": True,
        "cleanup_completed": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def execute_storage_transition(
    aliases: predecessor.StorageAliases,
    reconciled: predecessor.ReconciledIdentity,
    journal: RecoveryJournal,
    require_quiesced: Callable[[], None],
) -> JsonObject:
    try:
        return _execute_storage_transition(
            aliases,
            reconciled,
            journal,
            require_quiesced,
        )
    except predecessor.RecoveryError as exc:
        raise RecoveryError(exc.code) from None


def _finalize(
    session: ReceiptSession,
    journal: RecoveryJournal,
    *,
    postinspection: JsonObject,
    storage: JsonObject,
    require_quiesced: Callable[[], None],
) -> JsonObject:
    expected_observed: JsonObject = {
        "compose_project": PROJECT,
        "exact_two_stopped": True,
        "projections": postinspection,
        "ithildin_node": ("not_observed_in_exact_project_query_at_preinspection"),
        "hermes": "not_observed_in_exact_project_query_at_preinspection",
    }
    observed, _created = journal.record(
        "exact-two-container-postinspection",
        expected_observed,
    )
    if observed != expected_observed:
        raise RecoveryError("journal_invalid")
    disposition: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_two_container_revocation_disposition",
        "recovery_id": RECOVERY_ID,
        "candidate_commit": session.candidate_commit,
        "candidate_tree": session.candidate_tree,
        "status": "completed",
        "compose_project": PROJECT,
        "exact_two_container_projection": postinspection,
        "storage": storage,
        "docker_mutation_performed": False,
        "container_stop_performed": False,
        "generic_absence_claimed": False,
        "cleanup_completed": False,
        "retry_authorized": False,
        "same_operation_resume_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }
    intent, _created = journal.record("disposition-intent", disposition)
    if intent != disposition:
        raise RecoveryError("journal_invalid")
    require_quiesced()
    try:
        predecessor._write_exclusive(  # noqa: SLF001
            session.receipt_fd,
            DISPOSITION_RECEIPT,
            disposition,
        )
    except FileExistsError as exc:
        raise RecoveryError("operation_already_completed") from exc
    return disposition


def run_live(
    repo_root: Path = ROOT,
    *,
    environment: Mapping[str, str] | None = None,
) -> JsonObject:
    report = build_report(repo_root)
    if (
        report["static_candidate_valid"] is not True
        or report["review_binding_valid"] is not True
        or report["execution_available"] is not True
    ):
        raise RecoveryError("two_container_revocation_not_authorized")
    session = consume_or_resume(
        repo_root,
        candidate_commit=cast(str, report["candidate_commit"]),
        candidate_tree=cast(str, report["candidate_tree"]),
    )
    journal: DurableJournal | None = None
    aliases: predecessor.StorageAliases | None = None
    try:
        journal = DurableJournal(session)
        source_environment = os.environ if environment is None else environment
        predecessor._reject_ambient_authority(source_environment)  # noqa: SLF001
        _validate_predecessor_receipts(repo_root)
        expected_bound: JsonObject = {
            "candidate_commit": PARENT_COMMIT,
            "candidate_tree": PARENT_TREE,
            "consumed_sha256": PREDECESSOR_CONSUMED_SHA256,
            "identity_journal_sha256": (PREDECESSOR_IDENTITY_JOURNAL_SHA256),
            "later_operation_stages_absent": True,
            "old_receipts_preserved": True,
        }
        bound, _created = journal.record(
            "predecessor-failed-operation-bound",
            expected_bound,
        )
        if bound != expected_bound:
            raise RecoveryError("journal_invalid")
        reconciled = predecessor.read_reconciled_identity(repo_root)
        expected_identity: JsonObject = {
            "reconciliation_commit": predecessor.RECONCILIATION_COMMIT,
            "reconciliation_tree": predecessor.RECONCILIATION_TREE,
            "identity_digest": reconciled.identity_digest,
            "database_size": reconciled.database_size,
            "database_sha256": reconciled.database_digest,
            "classification": ("identity_bound_active_quarantine_required"),
        }
        identity_payload, _created = journal.record(
            "identity-receipts-validated",
            expected_identity,
        )
        if identity_payload != expected_identity:
            raise RecoveryError("journal_invalid")
        try:
            docker_host = port_release._local_docker_socket()  # noqa: SLF001
            with port_release.SealedDockerExecutable.create() as sealed:
                plan = ObservationPlan(sealed.path)
                with tempfile.TemporaryDirectory(
                    prefix="ithildin-attempt008-two-container-",
                    dir=session.root_path,
                ) as temporary:
                    config = port_release._empty_docker_config(  # noqa: SLF001
                        Path(temporary) / "docker-config"
                    )
                    executor = ObservationExecutor(
                        {
                            "DOCKER_HOST": docker_host,
                            "DOCKER_CONFIG": str(config),
                        },
                        plan,
                        sealed,
                    )
                    initial = observe_exact_project(executor)
                    expected_preinspection: JsonObject = {
                        "compose_project": PROJECT,
                        "exact_two_stopped": True,
                        "projections": initial,
                        "ithildin_node": ("not_observed_in_exact_project_query_at_preinspection"),
                        "hermes": ("not_observed_in_exact_project_query_at_preinspection"),
                    }
                    recorded, _created = journal.record(
                        "exact-two-container-preinspection",
                        expected_preinspection,
                    )
                    if recorded != expected_preinspection:
                        raise RecoveryError("journal_invalid")

                    def require_quiesced() -> None:
                        if observe_exact_project(executor) != initial:
                            raise RecoveryError("project_projection_changed")

                    aliases = predecessor.StorageAliases.bind(cast(Any, session))
                    storage = execute_storage_transition(
                        aliases,
                        reconciled,
                        journal,
                        require_quiesced,
                    )
                    postinspection = observe_exact_project(executor)
                    if postinspection != initial:
                        raise RecoveryError("project_projection_changed")
                    disposition = _finalize(
                        session,
                        journal,
                        postinspection=postinspection,
                        storage=storage,
                        require_quiesced=require_quiesced,
                    )
        except port_release.PortReleaseError as exc:
            raise RecoveryError("docker_trust_boundary_invalid") from exc
        return {
            "recovery_id": RECOVERY_ID,
            "status": disposition["status"],
            "identity_digest": reconciled.identity_digest,
            "node_status": "revoked",
            "node_evidence_status": "complete",
            "docker_mutation_performed": False,
            "cleanup_completed": False,
            "successor_o4_authorized": False,
            "release_allowed": False,
            "uat_complete": False,
        }
    except RecoveryError:
        raise
    except predecessor.RecoveryError as exc:
        raise RecoveryError(exc.code) from None
    except (
        AuditWriteError,
        identity.ReconciliationError,
        OSError,
        sqlite3.Error,
    ):
        raise RecoveryError("two_container_revocation_recovery_required") from None
    except KeyboardInterrupt:
        raise
    except Exception:
        raise RecoveryError("two_container_revocation_unexpected_failure") from None
    finally:
        if aliases is not None:
            aliases.close()
        if journal is not None:
            journal.close()
        session.close()


def main(arguments: Iterable[str] | None = None) -> int:
    effective = list(sys.argv[1:] if arguments is None else arguments)
    if effective:
        print("attempt008_two_container_revocation_error: arguments_not_allowed")
        return 2
    try:
        result = run_live()
    except RecoveryError as exc:
        print(f"attempt008_two_container_revocation_error: {exc.code}")
        return 1
    except KeyboardInterrupt:
        print("attempt008_two_container_revocation_error: interrupted")
        return 1
    except Exception:
        print("attempt008_two_container_revocation_error: unexpected_failure")
        return 1
    print(f"attempt008_two_container_revocation_status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
