"""Exact-project quarantine and offline audited revocation for Attempt 008.

The preparation path reads only Git and tracked authorization artifacts.  The
live path is a consumed, resumable recovery operation over one exact Compose
project, two exact reconciliation receipts, one SQLite database, and its
canonical JSONL audit mirror.  It never starts a service, reads credentials,
or grants successor mission authority.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast

from ithildin_api.nodes import (
    NodeConflictError,
    NodeNotFoundError,
    NodeRecord,
    NodeStore,
    node_audit_metadata,
)
from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import AuditEvent, AuditEventType, JsonObject, JsonValue, canonical_json

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as identity,
)
from scripts import local_v1_lv1_003_o4_attempt008_port_release as port_release

ROOT = Path(__file__).resolve().parents[1]
PARENT_COMMIT = "66c85f8af3e2db11fd8556a9cbbf33ed826e991b"
PARENT_TREE = "d2ef30bac1c2ac8ddb58db400b31ff98c6b785e4"
RECONCILIATION_COMMIT = PARENT_COMMIT
RECONCILIATION_TREE = PARENT_TREE
RECOVERY_ID = "LV1-003-O4-ATTEMPT-008-QUARANTINE-REVOCATION-001"
REVIEW_TAG = "ithildin/lv1-003-o4-attempt008-quarantine-revocation-reviewed"
RUN_ID = identity.RUN_ID
PROJECT = identity.PROJECT
WORKSPACE_ID = identity.WORKSPACE_ID
DISPLAY_NAME = identity.DISPLAY_NAME
EXPECTED_DESCRIPTOR_DIGEST = identity.EXPECTED_DESCRIPTOR_DIGEST
GIT_EXECUTABLE = "/usr/bin/git"

AUTHORIZATION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-quarantine-revocation-authorization.json"
)
AUTHORIZATION_MD = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-quarantine-revocation-authorization.md"
)
SCRIPT_PATH = Path("scripts/local_v1_lv1_003_o4_attempt008_quarantine_revocation.py")
TEST_PATH = Path("tests/test_local_v1_lv1_003_o4_attempt008_quarantine_revocation.py")
CHECK_TARGET = "local-v1-lv1-003-o4-attempt008-quarantine-revocation-check"
RUN_TARGET = "local-v1-lv1-003-o4-attempt008-quarantine-revocation-run"
CANDIDATE_PATH_ALLOWLIST = sorted(
    [
        "Makefile",
        "README.md",
        AUTHORIZATION_JSON.as_posix(),
        AUTHORIZATION_MD.as_posix(),
        SCRIPT_PATH.as_posix(),
        TEST_PATH.as_posix(),
    ]
)

HISTORICAL_RECEIPT_COMPONENTS = (
    "var",
    "local-v1-lv1-003-o4-reconciliation-receipts",
    "attempt-008-node-identity-reconciliation-001",
)
HISTORICAL_CONSUMED = "consumed.json"
HISTORICAL_RESULT = "result.json"
HISTORICAL_CONSUMED_SIZE = 504
HISTORICAL_CONSUMED_SHA256 = (
    "sha256:ecaae7ace8fcdbfee2d27cfcc993d3faf7fefb1a00b5a27add96107a35ed42b8"
)
HISTORICAL_RESULT_SIZE = 1_196
HISTORICAL_RESULT_SHA256 = "sha256:0629fd7f90ff9625d16dfde3b1c4bb4534ec89eb56430f7456273162a4849bd9"

RECOVERY_RECEIPT_DIRECTORY = "attempt-008-quarantine-revocation-001"
CONSUMED_RECEIPT = "consumed.json"
JOURNAL_DIRECTORY = "journal"
DISPOSITION_RECEIPT = "disposition.json"
ACTIVE_LOCK = "active.lock"
DATABASE_ALIAS = "attempt008-revocation.sqlite3"
AUDIT_ALIAS = "attempt008-audit.jsonl"

RUNTIME_VAR_COMPONENTS = (
    "var",
    "local-v1-lv1-003-o4-runtime",
    RUN_ID,
    "var",
)
DATABASE_DIRECTORY = "db"
DATABASE_NAME = "ithildin.sqlite3"
AUDIT_DIRECTORY = "logs"
AUDIT_NAME = "audit.jsonl"
DATABASE_SIDECARS = tuple(f"{DATABASE_NAME}{suffix}" for suffix in ("-journal", "-wal", "-shm"))
ALIAS_SIDECARS = tuple(f"{DATABASE_ALIAS}{suffix}" for suffix in ("-journal", "-wal", "-shm"))

SERVICES: Final[tuple[str, ...]] = (
    "ithildin-api",
    "ithildin-ui",
    "ithildin-node",
    "hermes",
)
MAX_RECEIPT_BYTES = 16_384
MAX_DATABASE_BYTES = identity.MAX_DATABASE_BYTES
MAX_AUDIT_BYTES = 64 * 1024 * 1024
MAX_DOCKER_OUTPUT_BYTES = port_release.MAX_DOCKER_OUTPUT_BYTES

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_NODE_ID = re.compile(r"^node_[0-9a-f]{32}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_EVENT_ID = re.compile(r"^evt_[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^req_[0-9a-f]{32}$")
_OPEN_FILE_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_OPEN_RW_FLAGS = (
    os.O_RDWR
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)

JOURNAL_EVENTS: Final[tuple[str, ...]] = (
    "identity-receipts-validated",
    "project-preinspection",
    "ithildin-api-stop-intent",
    "ithildin-api-stop-result",
    "ithildin-ui-stop-intent",
    "ithildin-ui-stop-result",
    "ithildin-node-stop-intent",
    "ithildin-node-stop-result",
    "hermes-stop-intent",
    "hermes-stop-result",
    "project-quiesced",
    "storage-aliases-bound",
    "storage-preflight-complete",
    "revocation-plan",
    "node-revocation-observed-pending",
    "audit-event-observed-complete",
    "node-evidence-observed-complete",
    "project-postinspection",
    "disposition-intent",
)

AUTHORITY_TRUE = {
    "exact_tracked_artifact_validation",
    "reviewed_candidate_git_ref_binding",
    "exact_reconciliation_receipt_validation",
    "exact_project_container_inspection",
    "exact_project_service_stop",
    "descriptor_bound_storage_aliases",
    "single_node_offline_revocation",
    "single_node_revocation_audit",
    "owner_only_recovery_receipts",
    "single_active_invocation_lock",
    "same_operation_resume",
}
AUTHORITY_FALSE = {
    "api_access",
    "arbitrary_sql",
    "ambient_credential_access",
    "compose_use",
    "container_deletion",
    "container_exec",
    "container_restart",
    "container_start",
    "database_migration",
    "database_repair",
    "evidence_deletion",
    "generic_docker_query",
    "generic_process_control",
    "generic_process_discovery",
    "image_deletion",
    "network_access",
    "network_deletion",
    "port_access",
    "project_down",
    "provider_access",
    "release",
    "runtime_cleanup",
    "successor_o4_attempt",
    "uat",
    "volume_deletion",
}


class RecoveryError(RuntimeError):
    """Stable, non-reflective recovery refusal."""

    def __init__(self, code: str) -> None:
        if re.fullmatch(r"[a-z0-9_]{3,96}", code) is None:
            raise ValueError("unsafe recovery error code")
        super().__init__(code)
        self.code = code


def _sha256(content: bytes | bytearray) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _git(repo_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        (GIT_EXECUTABLE, *arguments),
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
        },
    )
    if result.returncode != 0:
        raise RecoveryError("candidate_identity_invalid")
    return result.stdout.strip()


def candidate_identity(repo_root: Path) -> tuple[str, str]:
    commit = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    if not _COMMIT.fullmatch(commit) or not _COMMIT.fullmatch(tree):
        raise RecoveryError("candidate_identity_invalid")
    return commit, tree


def _expected_authorization() -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": ("local_v1_lv1_003_o4_attempt008_quarantine_revocation_authorization"),
        "record_status": "AUTHORIZED_UNCONSUMED_EXACT_RESUMABLE_ONE_SHOT",
        "recovery_id": RECOVERY_ID,
        "parent_commit": PARENT_COMMIT,
        "parent_tree": PARENT_TREE,
        "candidate_path_allowlist": cast(list[JsonValue], CANDIDATE_PATH_ALLOWLIST),
        "review_binding": {
            "git_tag": REVIEW_TAG,
            "required_for_live_execution": True,
            "tag_move_authorized": False,
        },
        "target": {
            "run_id": RUN_ID,
            "compose_project": PROJECT,
            "reconciliation_commit": RECONCILIATION_COMMIT,
            "reconciliation_tree": RECONCILIATION_TREE,
            "consumed_receipt_size": HISTORICAL_CONSUMED_SIZE,
            "consumed_receipt_sha256": HISTORICAL_CONSUMED_SHA256,
            "result_receipt_size": HISTORICAL_RESULT_SIZE,
            "result_receipt_sha256": HISTORICAL_RESULT_SHA256,
            "services": cast(list[JsonValue], list(SERVICES)),
            "database_path": (
                f"var/local-v1-lv1-003-o4-runtime/{RUN_ID}/var/{DATABASE_DIRECTORY}/{DATABASE_NAME}"
            ),
            "audit_path": (
                f"var/local-v1-lv1-003-o4-runtime/{RUN_ID}/var/{AUDIT_DIRECTORY}/{AUDIT_NAME}"
            ),
        },
        "attempt_budget": 1,
        "consumed": False,
        "retry_authorized": False,
        "same_operation_resume_authorized": True,
        "single_active_invocation_required": True,
        "static_validation_reads_runtime": False,
        "raw_node_id_tracked_or_printed": False,
        "audit_lifecycle_repair_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "authority_true": cast(list[JsonValue], sorted(AUTHORITY_TRUE)),
        "authority_false": cast(list[JsonValue], sorted(AUTHORITY_FALSE)),
        "tool_count": 24,
        "release_allowed": False,
        "uat_complete": False,
    }


def validate_authorization(repo_root: Path) -> None:
    try:
        observed = json.loads((repo_root / AUTHORIZATION_JSON).read_text(encoding="utf-8"))
        document = (repo_root / AUTHORIZATION_MD).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError("authorization_invalid") from exc
    if observed != _expected_authorization():
        raise RecoveryError("authorization_invalid")
    for required in (
        RECOVERY_ID,
        PARENT_COMMIT,
        PARENT_TREE,
        "exact six-path allowlist",
        "same-operation resume",
        REVIEW_TAG,
        "single active invocation",
        "does not authorize audit-lifecycle repair",
        "does not authorize cleanup",
        "does not authorize Attempt 010",
        "release remains false",
        "UAT remains false",
    ):
        if required not in document:
            raise RecoveryError("authorization_invalid")


def validate_static_candidate(repo_root: Path) -> tuple[str, str]:
    validate_authorization(repo_root)
    commit, tree = candidate_identity(repo_root)
    if _git(repo_root, "status", "--porcelain=v1"):
        raise RecoveryError("candidate_worktree_not_clean")
    parents = _git(repo_root, "show", "-s", "--format=%P", commit).split()
    if parents != [PARENT_COMMIT]:
        raise RecoveryError("candidate_parent_invalid")
    if _git(repo_root, "rev-parse", f"{PARENT_COMMIT}^{{tree}}") != PARENT_TREE:
        raise RecoveryError("candidate_parent_invalid")
    changed = sorted(
        value
        for value in _git(
            repo_root,
            "diff",
            "--name-only",
            f"{PARENT_COMMIT}..{commit}",
        ).splitlines()
        if value
    )
    if changed != CANDIDATE_PATH_ALLOWLIST:
        raise RecoveryError("candidate_scope_invalid")
    manifests = sorted((repo_root / "tool-manifests").glob("*.yaml"))
    if len(manifests) != 24:
        raise RecoveryError("tool_count_invalid")
    return commit, tree


def validate_review_binding(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    try:
        reviewed_commit = _git(
            repo_root,
            "rev-parse",
            f"refs/tags/{REVIEW_TAG}^{{commit}}",
        )
        reviewed_tree = _git(
            repo_root,
            "rev-parse",
            f"refs/tags/{REVIEW_TAG}^{{tree}}",
        )
    except RecoveryError as exc:
        raise RecoveryError("review_binding_invalid") from exc
    if reviewed_commit != candidate_commit or reviewed_tree != candidate_tree:
        raise RecoveryError("review_binding_invalid")


def build_report(repo_root: Path = ROOT) -> JsonObject:
    failures: list[str] = []
    review_binding_failures: list[str] = []
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
            review_binding_failures.append(exc.code)
    review_binding_valid = not review_binding_failures
    execution_available = static_valid and review_binding_valid
    return {
        "recovery_id": RECOVERY_ID,
        "candidate_commit": commit,
        "candidate_tree": tree,
        "static_candidate_valid": static_valid,
        "review_binding_tag": REVIEW_TAG,
        "review_binding_valid": review_binding_valid,
        "static_validation_reads_runtime": False,
        "attempt_budget": 1 if execution_available else 0,
        "tracked_consumed": False,
        "live_exclusive_consumption_or_resume_required": True,
        "execution_available": execution_available,
        "static_failures": cast(list[JsonValue], failures),
        "review_binding_failures": cast(list[JsonValue], review_binding_failures),
        "retry_authorized": False,
        "same_operation_resume_authorized": True,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _closed_json(content: bytes, *, error_code: str) -> JsonObject:
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_closed_object,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise RecoveryError(error_code) from exc
    if not isinstance(value, dict):
        raise RecoveryError(error_code)
    return cast(JsonObject, value)


def _open_fixed_chain(
    repo_root: Path,
    components: tuple[str, ...],
) -> tuple[list[int], list[identity.FileIdentity]]:
    descriptors: list[int] = []
    identities: list[identity.FileIdentity] = []
    try:
        root = os.open(repo_root, identity._OPEN_DIRECTORY_FLAGS)  # noqa: SLF001
        descriptors.append(root)
        identities.append(identity.FileIdentity.from_stat(os.fstat(root)))
        current = root
        for index, component in enumerate(components):
            next_fd, file_identity = identity._open_directory(  # noqa: SLF001
                current,
                component,
                private=index > 0,
            )
            descriptors.append(next_fd)
            identities.append(file_identity)
            current = next_fd
        return descriptors, identities
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _revalidate_fixed_chain(
    repo_root: Path,
    components: tuple[str, ...],
    descriptors: list[int],
    identities: list[identity.FileIdentity],
) -> None:
    if len(descriptors) != len(components) + 1 or len(identities) != len(descriptors):
        raise RecoveryError("storage_identity_changed")
    try:
        root_lexical = identity.FileIdentity.from_stat(os.stat(repo_root, follow_symlinks=False))
        if (
            root_lexical != identities[0]
            or identity.FileIdentity.from_stat(os.fstat(descriptors[0])) != identities[0]
        ):
            raise RecoveryError("storage_identity_changed")
        for index, component in enumerate(components, start=1):
            lexical = identity.FileIdentity.from_stat(
                os.stat(
                    component,
                    dir_fd=descriptors[index - 1],
                    follow_symlinks=False,
                )
            )
            opened = identity.FileIdentity.from_stat(os.fstat(descriptors[index]))
            if lexical != identities[index] or opened != identities[index]:
                raise RecoveryError("storage_identity_changed")
    except OSError as exc:
        raise RecoveryError("storage_identity_changed") from exc


def _read_bound_leaf(
    repo_root: Path,
    components: tuple[str, ...],
    name: str,
    *,
    expected_size: int,
    expected_digest: str,
    maximum: int = MAX_RECEIPT_BYTES,
) -> bytes:
    descriptors, identities = _open_fixed_chain(repo_root, components)
    leaf = -1
    try:
        directory_fd = descriptors[-1]
        leaf = os.open(name, _OPEN_FILE_FLAGS, dir_fd=directory_fd)
        before = identity.FileIdentity.from_stat(os.fstat(leaf))
        if (
            not stat.S_ISREG(before.mode)
            or before.uid != os.geteuid()
            or stat.S_IMODE(before.mode) != 0o600
            or before.links != 1
            or before.size != expected_size
            or before.size <= 0
            or before.size > maximum
        ):
            raise RecoveryError("reconciliation_receipt_invalid")
        data = bytearray()
        while len(data) <= maximum:
            block = os.read(leaf, min(65_536, maximum + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = identity.FileIdentity.from_stat(os.fstat(leaf))
        lexical = identity.FileIdentity.from_stat(
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        )
        _revalidate_fixed_chain(
            repo_root,
            components,
            descriptors,
            identities,
        )
        if (
            before != after
            or before != lexical
            or len(data) != expected_size
            or _sha256(data) != expected_digest
        ):
            raise RecoveryError("reconciliation_receipt_invalid")
        return bytes(data)
    except (OSError, identity.ReconciliationError, RecoveryError) as exc:
        raise RecoveryError("reconciliation_receipt_invalid") from exc
    finally:
        if leaf >= 0:
            os.close(leaf)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


@dataclass(frozen=True)
class ReconciledIdentity:
    node_id: str
    principal_id: str
    identity_digest: str
    database_size: int
    database_digest: str


@dataclass(frozen=True)
class StaticFileIdentity:
    device: int
    inode: int
    file_type: int
    permissions: int
    uid: int
    gid: int

    @classmethod
    def from_stat(cls, details: os.stat_result) -> StaticFileIdentity:
        return cls(
            device=details.st_dev,
            inode=details.st_ino,
            file_type=stat.S_IFMT(details.st_mode),
            permissions=stat.S_IMODE(details.st_mode),
            uid=details.st_uid,
            gid=details.st_gid,
        )


def validate_reconciliation_documents(
    consumed: JsonObject,
    result: JsonObject,
) -> ReconciledIdentity:
    consumed_expected = {
        "schema_version",
        "record_type",
        "reconciliation_id",
        "candidate_commit",
        "candidate_tree",
        "run_id",
        "compose_project",
        "consumed_before_database_open",
        "attempt_budget",
        "retry_authorized",
        "release_allowed",
        "uat_complete",
    }
    result_expected = {
        "schema_version",
        "record_type",
        "reconciliation_id",
        "candidate_commit",
        "candidate_tree",
        "database_snapshot_size",
        "database_snapshot_sha256",
        "database_source_unchanged",
        "database_sidecars_absent",
        "classification",
        "node_id",
        "node_identity_digest",
        "principal_id",
        "workspace_id",
        "display_name",
        "descriptor_digest",
        "status",
        "evidence_status",
        "enrolled_at",
        "revoked_at",
        "quarantine_confirmed",
        "revocation_authorized",
        "cleanup_authorized",
        "successor_o4_authorized",
        "release_allowed",
        "uat_complete",
    }
    node_id = result.get("node_id")
    principal_id = result.get("principal_id")
    identity_digest = result.get("node_identity_digest")
    database_size = result.get("database_snapshot_size")
    database_digest = result.get("database_snapshot_sha256")
    if (
        set(consumed) != consumed_expected
        or consumed.get("schema_version") != "1"
        or consumed.get("record_type") != "attempt008_node_identity_reconciliation_consumption"
        or consumed.get("reconciliation_id") != identity.RECONCILIATION_ID
        or consumed.get("candidate_commit") != RECONCILIATION_COMMIT
        or consumed.get("candidate_tree") != RECONCILIATION_TREE
        or consumed.get("run_id") != RUN_ID
        or consumed.get("compose_project") != PROJECT
        or consumed.get("consumed_before_database_open") is not True
        or consumed.get("attempt_budget") != 0
        or consumed.get("retry_authorized") is not False
        or consumed.get("release_allowed") is not False
        or consumed.get("uat_complete") is not False
        or set(result) != result_expected
        or result.get("schema_version") != "1"
        or result.get("record_type") != "attempt008_node_identity_reconciliation_result"
        or result.get("reconciliation_id") != identity.RECONCILIATION_ID
        or result.get("candidate_commit") != RECONCILIATION_COMMIT
        or result.get("candidate_tree") != RECONCILIATION_TREE
        or result.get("database_source_unchanged") is not True
        or result.get("database_sidecars_absent") is not True
        or result.get("classification") != "identity_bound_active_quarantine_required"
        or not isinstance(node_id, str)
        or _NODE_ID.fullmatch(node_id) is None
        or principal_id != f"agent:node.{node_id}"
        or not isinstance(identity_digest, str)
        or _DIGEST.fullmatch(identity_digest) is None
        or identity_digest
        != _sha256(b"ITHILDIN-ATTEMPT008-NODE-ID-V1\x00" + node_id.encode("ascii"))
        or type(database_size) is not int
        or not 1 <= database_size <= MAX_DATABASE_BYTES
        or not isinstance(database_digest, str)
        or _DIGEST.fullmatch(database_digest) is None
        or result.get("workspace_id") != WORKSPACE_ID
        or result.get("display_name") != DISPLAY_NAME
        or result.get("descriptor_digest") != EXPECTED_DESCRIPTOR_DIGEST
        or result.get("status") != "enrolled"
        or result.get("evidence_status") != "complete"
        or result.get("revoked_at") is not None
        or result.get("quarantine_confirmed") is not False
        or result.get("revocation_authorized") is not False
        or result.get("cleanup_authorized") is not False
        or result.get("successor_o4_authorized") is not False
        or result.get("release_allowed") is not False
        or result.get("uat_complete") is not False
    ):
        raise RecoveryError("reconciliation_receipt_invalid")
    return ReconciledIdentity(
        node_id=node_id,
        principal_id=principal_id,
        identity_digest=identity_digest,
        database_size=database_size,
        database_digest=database_digest,
    )


def read_reconciled_identity(repo_root: Path) -> ReconciledIdentity:
    consumed = _closed_json(
        _read_bound_leaf(
            repo_root,
            HISTORICAL_RECEIPT_COMPONENTS,
            HISTORICAL_CONSUMED,
            expected_size=HISTORICAL_CONSUMED_SIZE,
            expected_digest=HISTORICAL_CONSUMED_SHA256,
        ),
        error_code="reconciliation_receipt_invalid",
    )
    result = _closed_json(
        _read_bound_leaf(
            repo_root,
            HISTORICAL_RECEIPT_COMPONENTS,
            HISTORICAL_RESULT,
            expected_size=HISTORICAL_RESULT_SIZE,
            expected_digest=HISTORICAL_RESULT_SHA256,
        ),
        error_code="reconciliation_receipt_invalid",
    )
    return validate_reconciliation_documents(consumed, result)


def _write_exclusive(directory_fd: int, name: str, record: JsonObject) -> None:
    content = (canonical_json(record) + "\n").encode()
    if len(content) > MAX_RECEIPT_BYTES:
        raise RecoveryError("receipt_write_failed")
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory_fd,
        )
        offset = 0
        while offset < len(content):
            written = os.write(descriptor, content[offset:])
            if written <= 0:
                raise RecoveryError("receipt_write_failed")
            offset += written
        os.fsync(descriptor)
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_size != len(content)
        ):
            raise RecoveryError("receipt_write_failed")
        os.fsync(directory_fd)
    except FileExistsError:
        raise
    except (OSError, RecoveryError) as exc:
        raise RecoveryError("receipt_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_private_json(
    directory_fd: int,
    name: str,
    *,
    maximum: int = MAX_RECEIPT_BYTES,
) -> JsonObject | None:
    descriptor = -1
    try:
        descriptor = os.open(name, _OPEN_FILE_FLAGS, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RecoveryError("receipt_invalid") from exc
    try:
        before = identity.FileIdentity.from_stat(os.fstat(descriptor))
        if (
            not stat.S_ISREG(before.mode)
            or stat.S_IMODE(before.mode) != 0o600
            or before.uid != os.geteuid()
            or before.links != 1
            or before.size <= 0
            or before.size > maximum
        ):
            raise RecoveryError("receipt_invalid")
        content = bytearray()
        while len(content) <= maximum:
            block = os.read(descriptor, min(65_536, maximum + 1 - len(content)))
            if not block:
                break
            content.extend(block)
        after = identity.FileIdentity.from_stat(os.fstat(descriptor))
        lexical = identity.FileIdentity.from_stat(
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        )
        if (
            before != after
            or before != lexical
            or len(content) != before.size
            or len(content) > maximum
        ):
            raise RecoveryError("receipt_invalid")
        return _closed_json(bytes(content), error_code="receipt_invalid")
    except OSError as exc:
        raise RecoveryError("receipt_invalid") from exc
    finally:
        os.close(descriptor)


@dataclass
class ReceiptSession:
    repo_root: Path
    receipt_fd: int
    held: list[int]
    candidate_commit: str
    candidate_tree: str

    def close(self) -> None:
        for descriptor in reversed(self.held):
            os.close(descriptor)
        self.held.clear()

    @property
    def root_path(self) -> Path:
        return (
            self.repo_root
            / "var/local-v1-lv1-003-o4-reconciliation-receipts"
            / RECOVERY_RECEIPT_DIRECTORY
        )


def _acquire_operation_lock(receipt_fd: int) -> int:
    lock_fd = -1
    try:
        lock_fd = os.open(
            ACTIVE_LOCK,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=receipt_fd,
        )
        opened = os.fstat(lock_fd)
        lexical = os.stat(
            ACTIVE_LOCK,
            dir_fd=receipt_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_uid != os.geteuid()
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (lexical.st_dev, lexical.st_ino)
        ):
            raise RecoveryError("operation_lock_invalid")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RecoveryError("operation_already_active") from exc
        os.fsync(lock_fd)
        os.fsync(receipt_fd)
        return lock_fd
    except RecoveryError:
        if lock_fd >= 0:
            os.close(lock_fd)
        raise
    except OSError as exc:
        if lock_fd >= 0:
            os.close(lock_fd)
        raise RecoveryError("operation_lock_invalid") from exc


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
            os.mkdir(RECOVERY_RECEIPT_DIRECTORY, 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
            created = True
        except FileExistsError:
            pass
        receipt_fd, _receipt_identity = identity._open_directory(  # noqa: SLF001
            base_fd,
            RECOVERY_RECEIPT_DIRECTORY,
            private=True,
        )
        held.append(receipt_fd)
        lock_fd = _acquire_operation_lock(receipt_fd)
        held.append(lock_fd)
        expected: JsonObject = {
            "schema_version": "1",
            "record_type": "attempt008_quarantine_revocation_consumption",
            "recovery_id": RECOVERY_ID,
            "candidate_commit": candidate_commit,
            "candidate_tree": candidate_tree,
            "consumed_before_live_access": True,
            "attempt_budget": 0,
            "retry_authorized": False,
            "same_operation_resume_authorized": True,
            "cleanup_authorized": False,
            "successor_o4_authorized": False,
            "release_allowed": False,
            "uat_complete": False,
        }
        if created:
            _write_exclusive(receipt_fd, CONSUMED_RECEIPT, expected)
        elif _read_private_json(receipt_fd, CONSUMED_RECEIPT) != expected:
            raise RecoveryError("receipt_invalid")
        if _read_private_json(receipt_fd, DISPOSITION_RECEIPT) is not None:
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
            self._fd, _journal_identity = identity._open_directory(  # noqa: SLF001
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
        existing = _read_private_json(self._fd, self._name(index))
        if existing is None:
            for future in range(index + 1, len(JOURNAL_EVENTS)):
                if _read_private_json(self._fd, self._name(future)) is not None:
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
            or existing.get("record_type") != "attempt008_quarantine_revocation_journal"
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
        name = self._name(index)
        payload = self.peek(event)
        created = payload is None
        if payload is None:
            document: JsonObject = {
                "schema_version": "1",
                "record_type": "attempt008_quarantine_revocation_journal",
                "recovery_id": RECOVERY_ID,
                "sequence": index + 1,
                "event": event,
                "payload": proposed_payload,
            }
            _write_exclusive(self._fd, name, document)
            payload = proposed_payload
        self._next_index += 1
        return payload, created


@dataclass(frozen=True)
class QuarantinePlan:
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
        if re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
            raise RecoveryError("container_id_invalid")
        return (
            self.docker_executable,
            "container",
            "inspect",
            "--format",
            port_release.INSPECT_FORMAT,
            container_id,
        )

    def stop(self, service: str, container_id: str) -> tuple[str, ...]:
        if service not in SERVICES or re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
            raise RecoveryError("container_stop_not_allowed")
        return (
            self.docker_executable,
            "container",
            "stop",
            "--time",
            "10",
            container_id,
        )


class DockerExecutor:
    def __init__(
        self,
        environment: Mapping[str, str],
        plan: QuarantinePlan,
        sealed: port_release.SealedDockerExecutable,
    ) -> None:
        if "PATH" in environment or sealed.path != plan.docker_executable:
            raise RecoveryError("docker_environment_not_isolated")
        self._environment = dict(environment)
        self._plan = plan
        self._sealed = sealed
        self._known_ids: set[str] = set()
        self._stopped_ids: set[str] = set()

    def bind_ids(self, values: set[str]) -> None:
        if (
            self._known_ids
            or len(values) != 4
            or any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in values)
        ):
            raise RecoveryError("container_set_invalid")
        self._known_ids = set(values)

    def _run(
        self,
        command: tuple[str, ...],
        *,
        mutation: bool,
    ) -> port_release.CommandResult:
        self._sealed.verify()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL if mutation else subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=30 if mutation else 20,
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RecoveryError("docker_command_unavailable") from exc
        self._sealed.verify()
        raw = b"" if mutation else completed.stdout
        if len(raw) > MAX_DOCKER_OUTPUT_BYTES:
            raise RecoveryError("docker_output_invalid")
        try:
            output = raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise RecoveryError("docker_output_invalid") from exc
        return port_release.CommandResult(completed.returncode, output)

    def query(self) -> port_release.CommandResult:
        return self._run(self._plan.query(), mutation=False)

    def inspect(self, container_id: str) -> port_release.CommandResult:
        if container_id not in self._known_ids:
            raise RecoveryError("container_inspection_not_allowed")
        return self._run(self._plan.inspect(container_id), mutation=False)

    def stop(self, service: str, container_id: str) -> port_release.CommandResult:
        if container_id not in self._known_ids or container_id in self._stopped_ids:
            raise RecoveryError("container_stop_not_allowed")
        self._stopped_ids.add(container_id)
        return self._run(self._plan.stop(service, container_id), mutation=True)


def _projection_record(
    projection: port_release.ContainerProjection,
) -> JsonObject:
    return port_release._projection_record(projection)  # noqa: SLF001


def _inspect_project(
    executor: DockerExecutor,
) -> dict[str, port_release.ContainerProjection]:
    query = executor.query()
    if query.returncode != 0:
        raise RecoveryError("project_container_query_failed")
    try:
        ids = port_release._parse_ids(query.stdout)  # noqa: SLF001
    except port_release.PortReleaseError as exc:
        raise RecoveryError("project_container_set_invalid") from exc
    if len(ids) != 4:
        raise RecoveryError("project_container_set_invalid")
    if not executor._known_ids:  # noqa: SLF001
        executor.bind_ids(set(ids))
    elif set(ids) != executor._known_ids:  # noqa: SLF001
        raise RecoveryError("project_container_set_changed")
    observed: dict[str, port_release.ContainerProjection] = {}
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
        if projection.service in observed:
            raise RecoveryError("duplicate_project_service")
        observed[projection.service] = projection
    if set(observed) != set(SERVICES):
        raise RecoveryError("project_container_set_invalid")
    return observed


def _records(
    projections: Mapping[str, port_release.ContainerProjection],
) -> JsonObject:
    return {service: _projection_record(projections[service]) for service in SERVICES}


def _record_identity(record: object) -> tuple[str, str, str]:
    if not isinstance(record, dict):
        raise RecoveryError("journal_invalid")
    container_id = record.get("container_id")
    image_id = record.get("image_id")
    service = record.get("service")
    if (
        not isinstance(container_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", container_id) is None
        or not isinstance(image_id, str)
        or not isinstance(service, str)
        or service not in SERVICES
    ):
        raise RecoveryError("journal_invalid")
    return container_id, image_id, service


def _validate_projection_record(
    record: object,
    *,
    require_stopped: bool | None = None,
) -> JsonObject:
    if not isinstance(record, dict) or set(record) != {
        "container_id",
        "image_id",
        "service",
        "running",
        "status",
        "ports",
    }:
        raise RecoveryError("journal_invalid")
    container_id, image_id, service = _record_identity(record)
    running = record.get("running")
    status_value = record.get("status")
    ports = record.get("ports")
    contract = port_release.SERVICES[service]
    expected_ports: JsonObject = {}
    if contract.container_port is not None:
        expected_ports = {
            contract.container_port: [
                {
                    "HostIp": "127.0.0.1",
                    "HostPort": cast(str, contract.host_port),
                }
            ]
        }
    if (
        type(running) is not bool
        or not isinstance(status_value, str)
        or status_value not in {"running", "exited", "created", "dead"}
        or (running is True and status_value != "running")
        or (running is False and status_value == "running")
        or not isinstance(ports, dict)
        or image_id != contract.image_id
        or (
            ports != expected_ports
            and not (
                running is False and service in {"ithildin-api", "ithildin-ui"} and ports == {}
            )
        )
        or (require_stopped is True and running is not False)
        or (require_stopped is False and running is not True)
        or re.fullmatch(r"[0-9a-f]{64}", container_id) is None
    ):
        raise RecoveryError("journal_invalid")
    return record


def _require_same_project_identity(
    recorded: JsonObject,
    observed: Mapping[str, port_release.ContainerProjection],
) -> None:
    if set(recorded) != set(SERVICES):
        raise RecoveryError("journal_invalid")
    for service in SERVICES:
        projection = _validate_projection_record(recorded[service])
        if _record_identity(projection) != (
            observed[service].container_id,
            observed[service].image_id,
            service,
        ):
            raise RecoveryError("project_container_set_changed")


def quiesce_project(
    executor: DockerExecutor,
    journal: DurableJournal,
) -> JsonObject:
    initial = _inspect_project(executor)
    pre_payload, pre_created = journal.record(
        "project-preinspection",
        {
            "compose_project": PROJECT,
            "projections": _records(initial),
        },
    )
    recorded = pre_payload.get("projections")
    if (
        set(pre_payload) != {"compose_project", "projections"}
        or pre_payload.get("compose_project") != PROJECT
        or not isinstance(recorded, dict)
    ):
        raise RecoveryError("journal_invalid")
    _require_same_project_identity(recorded, initial)
    if not pre_created:
        initial = _inspect_project(executor)
        _require_same_project_identity(recorded, initial)

    for service in SERVICES:
        expected_record = recorded[service]
        container_id, image_id, _service = _record_identity(expected_record)
        intent_payload, _intent_created = journal.record(
            f"{service}-stop-intent",
            {
                "service": service,
                "container_id": container_id,
                "image_id": image_id,
                "action": "stop_if_running",
                "result_at_record_time": "unknown",
            },
        )
        if intent_payload != {
            "service": service,
            "container_id": container_id,
            "image_id": image_id,
            "action": "stop_if_running",
            "result_at_record_time": "unknown",
        }:
            raise RecoveryError("journal_invalid")
        existing_result = journal.peek(f"{service}-stop-result")
        current = _inspect_project(executor)[service]
        if _record_identity(_projection_record(current)) != (
            container_id,
            image_id,
            service,
        ):
            raise RecoveryError("project_container_set_changed")
        proposed_result: JsonObject
        if existing_result is not None:
            proposed_result = existing_result
        elif current.running:
            stopped = executor.stop(service, container_id)
            if stopped.returncode != 0 or stopped.stdout:
                raise RecoveryError("container_stop_failed")
            current = _inspect_project(executor)[service]
            if current.running:
                raise RecoveryError("container_stop_not_observed")
            proposed_result = {
                "service": service,
                "container_id": container_id,
                "status": "stopped_observed",
                "stop_issued": True,
                "post_observation": _projection_record(current),
            }
        else:
            proposed_result = {
                "service": service,
                "container_id": container_id,
                "status": "already_stopped_observed",
                "stop_issued": False,
                "post_observation": _projection_record(current),
            }
        result_payload, result_created = journal.record(
            f"{service}-stop-result",
            proposed_result,
        )
        if (
            set(result_payload)
            != {
                "service",
                "container_id",
                "status",
                "stop_issued",
                "post_observation",
            }
            or result_payload.get("service") != service
            or result_payload.get("container_id") != container_id
            or result_payload.get("status") not in {"stopped_observed", "already_stopped_observed"}
            or type(result_payload.get("stop_issued")) is not bool
            or not isinstance(result_payload.get("post_observation"), dict)
        ):
            raise RecoveryError("journal_invalid")
        if (
            result_payload.get("stop_issued") is True
            and result_payload.get("status") != "stopped_observed"
        ) or (
            result_payload.get("stop_issued") is False
            and result_payload.get("status") != "already_stopped_observed"
        ):
            raise RecoveryError("journal_invalid")
        now = current if result_created else _inspect_project(executor)[service]
        post_observation = _validate_projection_record(
            result_payload["post_observation"],
            require_stopped=True,
        )
        if (
            now.running
            or post_observation != _projection_record(now)
            or _record_identity(post_observation) != (container_id, image_id, service)
        ):
            raise RecoveryError("project_restarted_after_quiescence")

    final = _inspect_project(executor)
    _require_same_project_identity(recorded, final)
    if any(projection.running for projection in final.values()):
        raise RecoveryError("project_not_quiesced")
    payload, _created = journal.record(
        "project-quiesced",
        {
            "compose_project": PROJECT,
            "all_four_stopped": True,
            "projections": _records(final),
        },
    )
    if (
        set(payload) != {"compose_project", "all_four_stopped", "projections"}
        or payload.get("compose_project") != PROJECT
        or payload.get("all_four_stopped") is not True
        or not isinstance(payload.get("projections"), dict)
        or payload.get("projections") != _records(final)
    ):
        raise RecoveryError("journal_invalid")
    _require_same_project_identity(
        cast(JsonObject, payload["projections"]),
        final,
    )
    return recorded


def require_project_still_quiesced(
    executor: DockerExecutor,
    recorded: JsonObject,
) -> JsonObject:
    observed = _inspect_project(executor)
    _require_same_project_identity(recorded, observed)
    if any(projection.running for projection in observed.values()):
        raise RecoveryError("project_restarted_after_quiescence")
    return _records(observed)


@dataclass
class StorageAliases:
    repo_root: Path
    receipt_fd: int
    receipt_path: Path
    descriptors: list[int]
    identities: list[identity.FileIdentity]
    runtime_var_fd: int
    database_directory_fd: int
    audit_directory_fd: int
    database_directory_identity: identity.FileIdentity
    audit_directory_identity: identity.FileIdentity
    database_fd: int
    audit_fd: int
    database_identity: StaticFileIdentity
    audit_identity: StaticFileIdentity

    @property
    def database_path(self) -> Path:
        return self.receipt_path / DATABASE_ALIAS

    @property
    def audit_path(self) -> Path:
        return self.receipt_path / AUDIT_ALIAS

    @classmethod
    def bind(cls, session: ReceiptSession) -> StorageAliases:
        descriptors, identities = _open_fixed_chain(
            session.repo_root,
            RUNTIME_VAR_COMPONENTS,
        )
        database_directory_fd = -1
        audit_directory_fd = -1
        database_fd = -1
        audit_fd = -1
        try:
            runtime_var_fd = descriptors[-1]
            database_directory_fd, database_directory_identity = identity._open_directory(  # noqa: SLF001
                runtime_var_fd,
                DATABASE_DIRECTORY,
                private=True,
            )
            audit_directory_fd, audit_directory_identity = identity._open_directory(  # noqa: SLF001
                runtime_var_fd,
                AUDIT_DIRECTORY,
                private=True,
            )
            database_fd = os.open(
                DATABASE_NAME,
                _OPEN_RW_FLAGS,
                dir_fd=database_directory_fd,
            )
            audit_fd = os.open(
                AUDIT_NAME,
                _OPEN_RW_FLAGS,
                dir_fd=audit_directory_fd,
            )
            database_stat = os.fstat(database_fd)
            audit_stat = os.fstat(audit_fd)
            for details, maximum in (
                (database_stat, MAX_DATABASE_BYTES),
                (audit_stat, MAX_AUDIT_BYTES),
            ):
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_uid != os.geteuid()
                    or stat.S_IMODE(details.st_mode) & 0o022
                    or details.st_size < 0
                    or details.st_size > maximum
                    or details.st_nlink not in {1, 2}
                ):
                    raise RecoveryError("storage_identity_invalid")
            if database_stat.st_size <= 0:
                raise RecoveryError("storage_identity_invalid")
            cls._bind_alias(
                source_directory_fd=database_directory_fd,
                source_name=DATABASE_NAME,
                source_stat=database_stat,
                destination_directory_fd=session.receipt_fd,
                destination_name=DATABASE_ALIAS,
            )
            cls._bind_alias(
                source_directory_fd=audit_directory_fd,
                source_name=AUDIT_NAME,
                source_stat=audit_stat,
                destination_directory_fd=session.receipt_fd,
                destination_name=AUDIT_ALIAS,
            )
            return cls(
                session.repo_root,
                session.receipt_fd,
                session.root_path,
                descriptors,
                identities,
                runtime_var_fd,
                database_directory_fd,
                audit_directory_fd,
                database_directory_identity,
                audit_directory_identity,
                database_fd,
                audit_fd,
                StaticFileIdentity.from_stat(database_stat),
                StaticFileIdentity.from_stat(audit_stat),
            )
        except BaseException:
            for descriptor in (
                database_fd,
                audit_fd,
                database_directory_fd,
                audit_directory_fd,
            ):
                if descriptor >= 0:
                    os.close(descriptor)
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise

    @staticmethod
    def _bind_alias(
        *,
        source_directory_fd: int,
        source_name: str,
        source_stat: os.stat_result,
        destination_directory_fd: int,
        destination_name: str,
    ) -> None:
        try:
            os.link(
                source_name,
                destination_name,
                src_dir_fd=source_directory_fd,
                dst_dir_fd=destination_directory_fd,
                follow_symlinks=False,
            )
            os.fsync(source_directory_fd)
            os.fsync(destination_directory_fd)
        except FileExistsError:
            pass
        except OSError as exc:
            raise RecoveryError("storage_alias_binding_failed") from exc
        try:
            source_after = os.stat(
                source_name,
                dir_fd=source_directory_fd,
                follow_symlinks=False,
            )
            alias = os.stat(
                destination_name,
                dir_fd=destination_directory_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise RecoveryError("storage_alias_binding_failed") from exc
        if (
            (source_after.st_dev, source_after.st_ino) != (source_stat.st_dev, source_stat.st_ino)
            or (alias.st_dev, alias.st_ino) != (source_stat.st_dev, source_stat.st_ino)
            or source_after.st_nlink != 2
            or alias.st_nlink != 2
            or not stat.S_ISREG(alias.st_mode)
        ):
            raise RecoveryError("storage_alias_binding_failed")

    def close(self) -> None:
        for descriptor in (
            self.database_fd,
            self.audit_fd,
            self.database_directory_fd,
            self.audit_directory_fd,
        ):
            if descriptor >= 0:
                os.close(descriptor)
        for descriptor in reversed(self.descriptors):
            os.close(descriptor)
        self.descriptors.clear()

    def _require_sidecars_absent(self) -> None:
        for directory_fd, names in (
            (self.database_directory_fd, DATABASE_SIDECARS),
            (self.receipt_fd, ALIAS_SIDECARS),
        ):
            for name in names:
                try:
                    os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    raise RecoveryError("storage_sidecar_invalid") from exc
                raise RecoveryError("storage_sidecar_invalid")

    def revalidate(self) -> None:
        try:
            database_source = os.stat(
                DATABASE_NAME,
                dir_fd=self.database_directory_fd,
                follow_symlinks=False,
            )
            audit_source = os.stat(
                AUDIT_NAME,
                dir_fd=self.audit_directory_fd,
                follow_symlinks=False,
            )
            database_alias = os.stat(
                DATABASE_ALIAS,
                dir_fd=self.receipt_fd,
                follow_symlinks=False,
            )
            audit_alias = os.stat(
                AUDIT_ALIAS,
                dir_fd=self.receipt_fd,
                follow_symlinks=False,
            )
            _revalidate_fixed_chain(
                self.repo_root,
                RUNTIME_VAR_COMPONENTS,
                self.descriptors,
                self.identities,
            )
            database_directory_lexical = identity.FileIdentity.from_stat(
                os.stat(
                    DATABASE_DIRECTORY,
                    dir_fd=self.runtime_var_fd,
                    follow_symlinks=False,
                )
            )
            database_directory_open = identity.FileIdentity.from_stat(
                os.fstat(self.database_directory_fd)
            )
            audit_directory_lexical = identity.FileIdentity.from_stat(
                os.stat(
                    AUDIT_DIRECTORY,
                    dir_fd=self.runtime_var_fd,
                    follow_symlinks=False,
                )
            )
            audit_directory_open = identity.FileIdentity.from_stat(
                os.fstat(self.audit_directory_fd)
            )
            database_open = os.fstat(self.database_fd)
            audit_open = os.fstat(self.audit_fd)
        except (OSError, identity.ReconciliationError) as exc:
            raise RecoveryError("storage_identity_changed") from exc
        if (
            database_directory_lexical != self.database_directory_identity
            or database_directory_open != self.database_directory_identity
            or audit_directory_lexical != self.audit_directory_identity
            or audit_directory_open != self.audit_directory_identity
            or StaticFileIdentity.from_stat(database_source) != self.database_identity
            or StaticFileIdentity.from_stat(database_alias) != self.database_identity
            or StaticFileIdentity.from_stat(database_open) != self.database_identity
            or StaticFileIdentity.from_stat(audit_source) != self.audit_identity
            or StaticFileIdentity.from_stat(audit_alias) != self.audit_identity
            or StaticFileIdentity.from_stat(audit_open) != self.audit_identity
            or database_source.st_nlink != 2
            or database_alias.st_nlink != 2
            or audit_source.st_nlink != 2
            or audit_alias.st_nlink != 2
            or database_source.st_size <= 0
            or database_source.st_size > MAX_DATABASE_BYTES
            or audit_source.st_size < 0
            or audit_source.st_size > MAX_AUDIT_BYTES
        ):
            raise RecoveryError("storage_identity_changed")
        self._require_sidecars_absent()

    @staticmethod
    def _read_descriptor(
        descriptor: int,
        *,
        maximum: int,
    ) -> bytes:
        os.lseek(descriptor, 0, os.SEEK_SET)
        data = bytearray()
        while len(data) <= maximum:
            block = os.read(
                descriptor,
                min(1024 * 1024, maximum + 1 - len(data)),
            )
            if not block:
                break
            data.extend(block)
        if len(data) > maximum:
            raise RecoveryError("storage_size_invalid")
        return bytes(data)

    def database_bytes(self) -> bytes:
        self.revalidate()
        content = self._read_descriptor(
            self.database_fd,
            maximum=MAX_DATABASE_BYTES,
        )
        if not content.startswith(b"SQLite format 3\x00"):
            raise RecoveryError("storage_database_invalid")
        self.revalidate()
        return content

    def audit_bytes(self) -> bytes:
        self.revalidate()
        content = self._read_descriptor(
            self.audit_fd,
            maximum=MAX_AUDIT_BYTES,
        )
        self.revalidate()
        return content


def _audit_posture(writer: AuditWriter) -> JsonObject:
    try:
        verification = writer.verify_chain()
        exact_match = writer.exact_jsonl_match()
    except AuditWriteError as exc:
        raise RecoveryError("audit_lifecycle_recovery_required") from exc
    if not verification.valid or not exact_match:
        raise RecoveryError("audit_lifecycle_recovery_required")
    return {
        "event_count": verification.event_count,
        "head_hash": verification.head_hash,
        "chain_valid": True,
        "sqlite_jsonl_exact_match": True,
    }


def _validate_audit_posture(value: object) -> JsonObject:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "event_count",
            "head_hash",
            "chain_valid",
            "sqlite_jsonl_exact_match",
        }
        or type(value.get("event_count")) is not int
        or cast(int, value["event_count"]) < 0
        or not isinstance(value.get("head_hash"), str)
        or _DIGEST.fullmatch(cast(str, value["head_hash"])) is None
        or value.get("chain_valid") is not True
        or value.get("sqlite_jsonl_exact_match") is not True
    ):
        raise RecoveryError("journal_invalid")
    return value


def _deterministic_id(prefix: str, label: bytes) -> str:
    return (
        prefix + hashlib.sha256(b"ITHILDIN-ATTEMPT008-REVOCATION-V1\x00" + label).hexdigest()[:32]
    )


def _parse_aware_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise RecoveryError("revocation_plan_invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RecoveryError("revocation_plan_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RecoveryError("revocation_plan_invalid")
    return parsed


def _expected_audit_metadata(record: NodeRecord) -> JsonObject:
    metadata = node_audit_metadata(record)
    metadata["status"] = "revoked"
    metadata["evidence_status"] = "pending"
    return metadata


def _load_audit_event(
    database_path: Path,
    event_id: str,
) -> AuditEvent | None:
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT payload_json FROM audit_events WHERE event_id = ?",
                (event_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise RecoveryError("audit_event_invalid") from exc
    if not rows:
        return None
    if len(rows) != 1:
        raise RecoveryError("audit_event_invalid")
    try:
        return AuditEvent.model_validate(json.loads(str(rows[0][0])))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RecoveryError("audit_event_invalid") from exc


def _validate_audit_event(
    event: AuditEvent,
    *,
    event_id: str,
    request_id: str,
    timestamp: datetime,
    expected_metadata: JsonObject,
) -> None:
    if (
        event.event_id != event_id
        or event.request_id != request_id
        or event.timestamp != timestamp
        or event.event_type != AuditEventType.NODE_REVOKED
        or event.principal != {"id": "system:local-recovery", "roles": ["Admin"]}
        or event.metadata != expected_metadata
        or event.tool_name is not None
        or event.resource is not None
        or event.decision is not None
        or event.policy_version is not None
        or event.matched_rules
        or event.input_hash is not None
    ):
        raise RecoveryError("audit_event_invalid")


def _require_node_state(
    record: NodeRecord,
    reconciled: ReconciledIdentity,
) -> None:
    if (
        record.node_id != reconciled.node_id
        or record.principal_id != reconciled.principal_id
        or record.workspace_id != WORKSPACE_ID
        or record.display_name != DISPLAY_NAME
        or record.descriptor_hash != EXPECTED_DESCRIPTOR_DIGEST
    ):
        raise RecoveryError("node_identity_changed")


def execute_storage_transition(
    aliases: StorageAliases,
    reconciled: ReconciledIdentity,
    journal: DurableJournal,
    require_quiesced: Callable[[], None],
) -> JsonObject:
    require_quiesced()
    aliases.revalidate()
    database_before = aliases.database_bytes()
    audit_before = aliases.audit_bytes()
    store = NodeStore(aliases.database_path)
    writer = AuditWriter(aliases.database_path, aliases.audit_path)

    aliases_payload, _aliases_created = journal.record(
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
            or _sha256(database_before) != reconciled.database_digest
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
        _require_node_state(record, reconciled)
        if record.status != "enrolled" or record.evidence_status != "complete":
            raise RecoveryError("database_identity_preflight_invalid")
        audit_preflight = _audit_posture(writer)
        preflight_payload: JsonObject = {
            "database_size": len(database_before),
            "database_sha256": _sha256(database_before),
            "audit_size": len(audit_before),
            "audit_sha256": _sha256(audit_before),
            "audit_posture": audit_preflight,
            "identity_digest": reconciled.identity_digest,
        }
    else:
        preflight_payload = existing_preflight

    preflight, preflight_created = journal.record(
        "storage-preflight-complete",
        preflight_payload,
    )
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
        or not isinstance(preflight.get("audit_size"), int)
        or cast(int, preflight["audit_size"]) < 0
        or not isinstance(preflight.get("audit_sha256"), str)
        or _DIGEST.fullmatch(cast(str, preflight["audit_sha256"])) is None
        or not isinstance(preflight.get("audit_posture"), dict)
        or preflight.get("identity_digest") != reconciled.identity_digest
    ):
        raise RecoveryError("journal_invalid")
    _validate_audit_posture(preflight["audit_posture"])
    if not preflight_created:
        _audit_posture(writer)

    proposed_plan: JsonObject = {
        "event_id": _deterministic_id("evt_", b"event"),
        "request_id": _deterministic_id("req_", b"request"),
        "revoked_at": datetime.now(UTC).isoformat(),
        "identity_digest": reconciled.identity_digest,
        "principal": "system:local-recovery",
    }
    plan, _plan_created = journal.record("revocation-plan", proposed_plan)
    event_id = plan.get("event_id")
    request_id = plan.get("request_id")
    timestamp = _parse_aware_timestamp(plan.get("revoked_at"))
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
    _require_node_state(record, reconciled)
    existing_event = _load_audit_event(aliases.database_path, event_id)
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
    pending_payload, _pending_created = journal.record(
        "node-revocation-observed-pending",
        {
            "identity_digest": reconciled.identity_digest,
            "status": "revoked",
            "pending_transition_observed": True,
            "revoked_at": timestamp.isoformat(),
        },
    )
    if pending_payload != {
        "identity_digest": reconciled.identity_digest,
        "status": "revoked",
        "pending_transition_observed": True,
        "revoked_at": timestamp.isoformat(),
    }:
        raise RecoveryError("journal_invalid")

    _audit_posture(writer)
    record = store.get(reconciled.node_id)
    expected_metadata = _expected_audit_metadata(record)
    existing_event = _load_audit_event(aliases.database_path, event_id)
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
                principal={
                    "id": "system:local-recovery",
                    "roles": ["Admin"],
                },
                timestamp=timestamp,
                metadata=expected_metadata,
            )
        except AuditWriteError as exc:
            raise RecoveryError("audit_lifecycle_recovery_required") from exc
        aliases.revalidate()
        require_quiesced()
    _validate_audit_event(
        existing_event,
        event_id=event_id,
        request_id=request_id,
        timestamp=timestamp,
        expected_metadata=expected_metadata,
    )
    audit_posture = _audit_posture(writer)
    audit_payload, _audit_created = journal.record(
        "audit-event-observed-complete",
        {
            "event_id": event_id,
            "event_hash": existing_event.event_hash,
            "event_type": AuditEventType.NODE_REVOKED.value,
            "audit_posture": audit_posture,
        },
    )
    if (
        set(audit_payload) != {"event_id", "event_hash", "event_type", "audit_posture"}
        or audit_payload.get("event_id") != event_id
        or audit_payload.get("event_hash") != existing_event.event_hash
        or audit_payload.get("event_type") != AuditEventType.NODE_REVOKED.value
        or not isinstance(audit_payload.get("audit_posture"), dict)
    ):
        raise RecoveryError("journal_invalid")
    _validate_audit_posture(audit_payload["audit_posture"])

    record = store.get(reconciled.node_id)
    _require_node_state(record, reconciled)
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
    complete_payload, _complete_created = journal.record(
        "node-evidence-observed-complete",
        {
            "identity_digest": reconciled.identity_digest,
            "status": "revoked",
            "evidence_status": "complete",
            "revoked_at": timestamp.isoformat(),
        },
    )
    if complete_payload != {
        "identity_digest": reconciled.identity_digest,
        "status": "revoked",
        "evidence_status": "complete",
        "revoked_at": timestamp.isoformat(),
    }:
        raise RecoveryError("journal_invalid")

    require_quiesced()
    aliases.revalidate()
    database_after = aliases.database_bytes()
    audit_after = aliases.audit_bytes()
    projected_after = identity.project_identity(database_after)
    if (
        projected_after.get("classification") != "identity_bound_revoked"
        or projected_after.get("node_id") != reconciled.node_id
        or projected_after.get("node_identity_digest") != reconciled.identity_digest
    ):
        raise RecoveryError("revocation_postcondition_invalid")
    final_audit = _audit_posture(writer)
    return {
        "identity_digest": reconciled.identity_digest,
        "node_status": "revoked",
        "node_evidence_status": "complete",
        "revoked_at": timestamp.isoformat(),
        "audit_event_id": event_id,
        "audit_event_hash": existing_event.event_hash,
        "audit_posture": final_audit,
        "database_before_sha256": preflight["database_sha256"],
        "database_after_sha256": _sha256(database_after),
        "audit_before_sha256": preflight["audit_sha256"],
        "audit_after_sha256": _sha256(audit_after),
        "storage_aliases_retained": True,
        "cleanup_completed": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _finalize(
    session: ReceiptSession,
    journal: DurableJournal,
    *,
    project_postinspection: JsonObject,
    storage: JsonObject,
) -> JsonObject:
    post_payload, _post_created = journal.record(
        "project-postinspection",
        {
            "compose_project": PROJECT,
            "all_four_stopped": True,
            "projections": project_postinspection,
        },
    )
    if (
        post_payload.get("compose_project") != PROJECT
        or post_payload.get("all_four_stopped") is not True
        or post_payload.get("projections") != project_postinspection
    ):
        raise RecoveryError("journal_invalid")
    disposition: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_quarantine_revocation_disposition",
        "recovery_id": RECOVERY_ID,
        "candidate_commit": session.candidate_commit,
        "candidate_tree": session.candidate_tree,
        "status": "completed",
        "compose_project": PROJECT,
        "exact_project_quiesced_point_in_time": True,
        "storage": storage,
        "container_start_authorized": False,
        "container_deletion_authorized": False,
        "cleanup_completed": False,
        "retry_authorized": False,
        "same_operation_resume_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }
    intent_payload, _intent_created = journal.record(
        "disposition-intent",
        disposition,
    )
    if intent_payload != disposition:
        raise RecoveryError("journal_invalid")
    try:
        _write_exclusive(
            session.receipt_fd,
            DISPOSITION_RECEIPT,
            disposition,
        )
    except FileExistsError as exc:
        raise RecoveryError("operation_already_completed") from exc
    return disposition


def _reject_ambient_authority(environment: Mapping[str, str]) -> None:
    try:
        port_release._reject_authority_environment(environment)  # noqa: SLF001
    except port_release.PortReleaseError as exc:
        raise RecoveryError("ambient_authority_environment_rejected") from exc


def run_live(
    repo_root: Path = ROOT,
    *,
    environment: Mapping[str, str] | None = None,
) -> JsonObject:
    report = build_report(repo_root)
    if report["static_candidate_valid"] is not True or report["execution_available"] is not True:
        raise RecoveryError("quarantine_revocation_not_authorized")
    commit = cast(str, report["candidate_commit"])
    tree = cast(str, report["candidate_tree"])
    session = consume_or_resume(
        repo_root,
        candidate_commit=commit,
        candidate_tree=tree,
    )
    journal: DurableJournal | None = None
    aliases: StorageAliases | None = None
    try:
        journal = DurableJournal(session)
        source_environment = os.environ if environment is None else environment
        _reject_ambient_authority(source_environment)
        reconciled = read_reconciled_identity(repo_root)
        identity_payload, _identity_created = journal.record(
            "identity-receipts-validated",
            {
                "reconciliation_commit": RECONCILIATION_COMMIT,
                "reconciliation_tree": RECONCILIATION_TREE,
                "consumed_receipt_sha256": HISTORICAL_CONSUMED_SHA256,
                "result_receipt_sha256": HISTORICAL_RESULT_SHA256,
                "identity_digest": reconciled.identity_digest,
                "database_size": reconciled.database_size,
                "database_sha256": reconciled.database_digest,
                "classification": "identity_bound_active_quarantine_required",
            },
        )
        if identity_payload.get("identity_digest") != reconciled.identity_digest:
            raise RecoveryError("journal_invalid")

        try:
            docker_host = port_release._local_docker_socket()  # noqa: SLF001
            with port_release.SealedDockerExecutable.create() as sealed:
                plan = QuarantinePlan(sealed.path)
                with tempfile.TemporaryDirectory(
                    prefix="ithildin-attempt008-quarantine-revocation-"
                ) as temporary:
                    config = port_release._empty_docker_config(  # noqa: SLF001
                        Path(temporary) / "docker-config"
                    )
                    executor = DockerExecutor(
                        {
                            "DOCKER_HOST": docker_host,
                            "DOCKER_CONFIG": str(config),
                        },
                        plan,
                        sealed,
                    )
                    recorded_project = quiesce_project(executor, journal)
                    require_project_still_quiesced(executor, recorded_project)
                    aliases = StorageAliases.bind(session)

                    def require_storage_quiescence() -> None:
                        require_project_still_quiesced(
                            executor,
                            recorded_project,
                        )

                    storage = execute_storage_transition(
                        aliases,
                        reconciled,
                        journal,
                        require_storage_quiescence,
                    )
                    postinspection = require_project_still_quiesced(
                        executor,
                        recorded_project,
                    )
                    disposition = _finalize(
                        session,
                        journal,
                        project_postinspection=postinspection,
                        storage=storage,
                    )
        except port_release.PortReleaseError as exc:
            raise RecoveryError("docker_trust_boundary_invalid") from exc
        return {
            "recovery_id": RECOVERY_ID,
            "status": disposition["status"],
            "identity_digest": reconciled.identity_digest,
            "exact_project_quiesced_point_in_time": True,
            "node_status": "revoked",
            "node_evidence_status": "complete",
            "cleanup_completed": False,
            "successor_o4_authorized": False,
            "release_allowed": False,
            "uat_complete": False,
        }
    except RecoveryError:
        raise
    except (AuditWriteError, identity.ReconciliationError, OSError, sqlite3.Error):
        raise RecoveryError("quarantine_revocation_recovery_required") from None
    except KeyboardInterrupt:
        raise
    except Exception:
        raise RecoveryError("quarantine_revocation_unexpected_failure") from None
    finally:
        if aliases is not None:
            aliases.close()
        if journal is not None:
            journal.close()
        session.close()


def main(arguments: Iterable[str] | None = None) -> int:
    effective = list(sys.argv[1:] if arguments is None else arguments)
    if effective:
        print("attempt008_quarantine_revocation_error: arguments_not_allowed")
        return 2
    try:
        result = run_live()
    except RecoveryError as exc:
        print(f"attempt008_quarantine_revocation_error: {exc.code}")
        return 1
    except KeyboardInterrupt:
        print("attempt008_quarantine_revocation_error: interrupted")
        return 1
    except Exception:
        print("attempt008_quarantine_revocation_error: unexpected_failure")
        return 1
    print(f"attempt008_quarantine_revocation_status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
