"""Exact, secret-safe Attempt 008 Node identity reconciliation.

The preparation/check path reads Git and tracked authorization only.  The live
path is a one-shot, descriptor-anchored read of one retained SQLite database.
It never connects to Docker, an API, a provider, or a credential-bearing file.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from ithildin_api.trusted_host_promotion_v2_migration import (
    DatabaseMigrationError,
    expected_pis004a_schema_fingerprint,
    expected_pis005a_schema_fingerprint,
    verify_pis004a_schema,
    verify_pis005a_schema,
)
from ithildin_schemas import JsonObject, JsonValue, canonical_json

ROOT = Path(__file__).resolve().parents[1]
PARENT_COMMIT = "457da3b4d245d38862f07c64a117aa69fc5874c7"
PARENT_TREE = "4656f76ad6769d96916bc5b6d8cbc74ca3b91d5a"
RECONCILIATION_ID = "LV1-003-O4-ATTEMPT-008-NODE-IDENTITY-RECONCILIATION-001"
RUN_ID = "20260726T001909Z-d801f37b"
PROJECT = "ithildin-local-v1-o4-d801f37b"
WORKSPACE_ID = "demo"
DISPLAY_NAME = "Local v1 O4 Node d801f37b"
EXPECTED_DESCRIPTOR_DIGEST = (
    "sha256:868d8b3d04bd35809d70b2611eb9b83192378e9844aaa5fa5354fc1b44f99a30"
)
EXPECTED_SCHEMA_VERSION = "4"
EXPECTED_MINIMUM_WRITER_VERSION = "4"
PIS004A_SCHEMA_VERSION = "6"
PIS004A_MINIMUM_WRITER_VERSION = "6"
PIS005A_SCHEMA_VERSION = "7"
PIS005A_MINIMUM_WRITER_VERSION = "7"
EXPECTED_PIS004A_SCHEMA_FINGERPRINT = (
    "sha256:ca52764e2c4544446f0a1379abc60ec6d74a9320222509974d1cb35c1c955114"
)
EXPECTED_PIS005A_SCHEMA_FINGERPRINT = (
    "sha256:5b804d92cd45385b5f21cd4a31b7c641ef35a6d5f4ea5ac0339ebdfebe67b9c5"
)
PIS005A_TABLES: Final[tuple[str, ...]] = (
    "node_workload_enrollment_digest_key_generations",
    "node_workload_deployments",
    "node_workload_enrollment_transactions",
    "node_workload_public_keys",
    "node_workload_identities",
    "node_workload_request_nonces",
)
MAX_DATABASE_BYTES = 128 * 1024 * 1024
GIT_EXECUTABLE = "/usr/bin/git"

AUTHORIZATION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-authorization.json"
)
AUTHORIZATION_MD = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-authorization.md"
)
SCRIPT_PATH = Path("scripts/local_v1_lv1_003_o4_attempt008_node_identity_reconciliation.py")
TEST_PATH = Path("tests/test_local_v1_lv1_003_o4_attempt008_node_identity_reconciliation.py")
CHECK_TARGET = "local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-check"
RUN_TARGET = "local-v1-lv1-003-o4-attempt008-node-identity-reconciliation-run"
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

RUNTIME_COMPONENTS = (
    "var",
    "local-v1-lv1-003-o4-runtime",
    RUN_ID,
    "var",
    "db",
)
DATABASE_NAME = "ithildin.sqlite3"
SIDECAR_NAMES = tuple(f"{DATABASE_NAME}{suffix}" for suffix in ("-journal", "-wal", "-shm"))
RECEIPT_BASE_COMPONENTS = (
    "var",
    "local-v1-lv1-003-o4-reconciliation-receipts",
)
RECEIPT_DIRECTORY = "attempt-008-node-identity-reconciliation-001"
CONSUMED_RECEIPT = "consumed.json"
RESULT_RECEIPT = "result.json"

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_NODE_ID = re.compile(r"^node_[0-9a-f]{32}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_OPEN_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_OPEN_FILE_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)

_EXPECTED_TABLE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "app_metadata": ("key", "value"),
    "node_enrollment_codes": (
        "code_id",
        "code_hash",
        "workspace_id",
        "display_name",
        "created_at",
        "expires_at",
        "consumed_at",
        "consumed_node_id",
        "evidence_status",
    ),
    "nodes": (
        "node_id",
        "principal_id",
        "workspace_id",
        "display_name",
        "status",
        "evidence_status",
        "public_key",
        "descriptor_hash",
        "descriptor_json",
        "enrolled_at",
        "updated_at",
        "last_seen_at",
        "revoked_at",
        "last_heartbeat_hash",
        "last_node_version",
        "last_configuration_digest",
        "last_mission_id",
        "desired_configuration_generation",
        "desired_configuration_digest",
        "acknowledged_configuration_generation",
        "acknowledged_configuration_digest",
        "acknowledged_configuration_signing_key_id",
        "acknowledged_active_configuration_signing_key_id",
        "configuration_acknowledged_at",
        "configuration_acknowledgment_status",
    ),
    "node_nonces": ("node_id", "nonce", "accepted_at"),
    "node_identity_key_rotations": (
        "rotation_id",
        "node_id",
        "principal_id",
        "workspace_id",
        "current_key_id",
        "current_public_key",
        "challenge_digest",
        "created_at",
        "expires_at",
        "status",
        "evidence_status",
        "next_public_key",
        "next_key_id",
        "activated_at",
    ),
    "node_configurations": (
        "configuration_id",
        "node_id",
        "generation",
        "configuration_digest",
        "bundle_json",
        "issued_at",
        "expires_at",
        "evidence_status",
        "assignment_kind",
        "rollback_source_generation",
    ),
    "node_configuration_trust_transitions": (
        "transition_id",
        "node_id",
        "transition_digest",
        "current_key_id",
        "next_key_id",
        "next_public_key",
        "bundle_json",
        "issued_at",
        "expires_at",
        "evidence_status",
        "acknowledgment_status",
        "acknowledgment_evidence_status",
        "acknowledged_at",
    ),
    "missions": (
        "mission_id",
        "requester_principal_id",
        "requester_identity_generation",
        "client_request_id",
        "admission_request_digest",
        "authority_snapshot_json",
        "authority_snapshot_hash",
        "target_node_id",
        "target_node_principal_id",
        "workspace_id",
        "configuration_generation",
        "configuration_digest",
        "policy_digest",
        "manifest_lock_digest",
        "mission_template_id",
        "template_registry_generation",
        "template_payload_digest",
        "envelope_digest",
        "requested_timeout_seconds",
        "lifecycle_state",
        "lifecycle_revision",
        "created_at",
        "updated_at",
        "admitted_at",
    ),
    "mission_audit_evidence_bindings": (
        "audit_event_id",
        "audit_event_hash",
        "owner_kind",
        "owner_id",
        "request_digest",
        "bound_at",
    ),
    "mission_transition_attempts": (
        "transition_id",
        "mission_id",
        "transition_kind",
        "prior_lifecycle_state",
        "prior_lifecycle_revision",
        "proposed_lifecycle_state",
        "proposed_lifecycle_revision",
        "request_digest",
        "safe_metadata_json",
        "evidence_status",
        "audit_event_id",
        "audit_event_hash",
        "failure_reason_code",
        "created_at",
        "finalized_at",
    ),
    "mission_claims": (
        "claim_id",
        "mission_id",
        "transition_id",
        "node_id",
        "node_identity_key_id",
        "envelope_digest",
        "authority_snapshot_json",
        "authority_snapshot_hash",
        "lifecycle_revision",
        "claim_status",
        "claimed_at",
        "expires_at",
    ),
    "mission_report_receipts": (
        "report_id",
        "mission_id",
        "claim_id",
        "node_id",
        "verified_node_identity_key_id",
        "envelope_digest",
        "expected_lifecycle_revision",
        "report_kind",
        "outcome_code",
        "reason_code",
        "artifact_digest",
        "request_digest",
        "receipt_posture_json",
        "receipt_disposition",
        "evidence_status",
        "audit_event_id",
        "audit_event_hash",
        "failure_reason_code",
        "received_at",
        "finalized_at",
    ),
    "mission_report_nonces": ("node_id", "nonce", "accepted_at"),
}

AUTHORITY_TRUE = {
    "exact_tracked_artifact_validation",
    "exact_descriptor_anchored_database_read",
    "bounded_in_memory_sqlite_projection",
    "owner_only_private_receipt_write",
}
AUTHORITY_FALSE = {
    "ambient_credential_access",
    "api_access",
    "audit_log_read",
    "compose_environment_read",
    "database_migration",
    "database_repair",
    "database_write",
    "docker_access",
    "filesystem_enumeration",
    "generic_filesystem_read",
    "network_access",
    "node_private_state_read",
    "process_access",
    "provider_access",
    "release",
    "revocation",
    "runtime_cleanup",
    "runtime_quarantine",
    "successor_o4_attempt",
    "uat",
}


class ReconciliationError(RuntimeError):
    """Fail-closed reconciliation error with a bounded outward code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    mode: int
    uid: int
    gid: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> FileIdentity:
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            uid=value.st_uid,
            gid=value.st_gid,
            links=value.st_nlink,
            size=value.st_size,
            modified_ns=value.st_mtime_ns,
            changed_ns=value.st_ctime_ns,
        )


def _git(repo_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        (GIT_EXECUTABLE, *arguments),
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise ReconciliationError("candidate_identity_invalid")
    return result.stdout.strip()


def candidate_identity(repo_root: Path) -> tuple[str, str]:
    commit = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    if not _COMMIT.fullmatch(commit) or not _COMMIT.fullmatch(tree):
        raise ReconciliationError("candidate_identity_invalid")
    return commit, tree


def _expected_authorization() -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": (
            "local_v1_lv1_003_o4_attempt008_node_identity_reconciliation_authorization"
        ),
        "record_status": "AUTHORIZED_UNCONSUMED_EXACT_ONE_SHOT",
        "reconciliation_id": RECONCILIATION_ID,
        "parent_commit": PARENT_COMMIT,
        "parent_tree": PARENT_TREE,
        "run_id": RUN_ID,
        "compose_project": PROJECT,
        "candidate_path_allowlist": cast(list[JsonValue], CANDIDATE_PATH_ALLOWLIST),
        "target": {
            "database_path": (f"var/local-v1-lv1-003-o4-runtime/{RUN_ID}/var/db/{DATABASE_NAME}"),
            "workspace_id": WORKSPACE_ID,
            "display_name": DISPLAY_NAME,
            "expected_descriptor_digest": EXPECTED_DESCRIPTOR_DIGEST,
            "schema_version": EXPECTED_SCHEMA_VERSION,
            "minimum_writer_version": EXPECTED_MINIMUM_WRITER_VERSION,
        },
        "attempt_budget": 1,
        "consumed": False,
        "retry_authorized": False,
        "static_validation_reads_runtime": False,
        "raw_node_id_tracked_or_printed": False,
        "projection_alone_authorizes_quarantine": False,
        "projection_alone_authorizes_revocation": False,
        "projection_alone_authorizes_cleanup": False,
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
        raise ReconciliationError("authorization_invalid") from exc
    if observed != _expected_authorization():
        raise ReconciliationError("authorization_invalid")
    for required in (
        RECONCILIATION_ID,
        PARENT_COMMIT,
        PARENT_TREE,
        "exact six-path allowlist",
        "one-shot",
        "does not authorize quarantine",
        "does not authorize revocation",
        "does not authorize cleanup",
        "does not authorize Attempt 010",
        "release remains false",
        "UAT remains false",
    ):
        if required not in document:
            raise ReconciliationError("authorization_invalid")


def validate_static_candidate(repo_root: Path) -> tuple[str, str]:
    validate_authorization(repo_root)
    commit, tree = candidate_identity(repo_root)
    if _git(repo_root, "status", "--porcelain"):
        raise ReconciliationError("candidate_worktree_dirty")
    parents = _git(repo_root, "show", "-s", "--format=%P", commit).split()
    if parents != [PARENT_COMMIT]:
        raise ReconciliationError("candidate_parent_invalid")
    if _git(repo_root, "rev-parse", f"{PARENT_COMMIT}^{{tree}}") != PARENT_TREE:
        raise ReconciliationError("candidate_parent_invalid")
    changed = sorted(
        line
        for line in _git(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            commit,
        ).splitlines()
        if line
    )
    if changed != CANDIDATE_PATH_ALLOWLIST:
        raise ReconciliationError("candidate_scope_invalid")
    return commit, tree


def build_report(repo_root: Path = ROOT) -> JsonObject:
    failures: list[str] = []
    commit: str | None = None
    tree: str | None = None
    try:
        commit, tree = validate_static_candidate(repo_root)
    except ReconciliationError as exc:
        failures.append(exc.code)
    return {
        "reconciliation_id": RECONCILIATION_ID,
        "candidate_commit": commit,
        "candidate_tree": tree,
        "static_candidate_valid": not failures,
        "static_failures": cast(list[JsonValue], failures),
        "attempt_budget": 1,
        "tracked_consumed": False,
        "execution_available": not failures,
        "live_exclusive_consumption_still_required": True,
        "static_validation_reads_runtime": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _open_directory(parent_fd: int, name: str, *, private: bool) -> tuple[int, FileIdentity]:
    if "/" in name or name in {"", ".", ".."}:
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    try:
        descriptor = os.open(name, _OPEN_DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError as exc:
        raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    identity = FileIdentity.from_stat(os.fstat(descriptor))
    if (
        not stat.S_ISDIR(identity.mode)
        or identity.uid != os.geteuid()
        or (stat.S_IMODE(identity.mode) & (0o077 if private else 0o022))
    ):
        os.close(descriptor)
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    return descriptor, identity


def _open_chain(repo_root: Path) -> tuple[list[int], list[FileIdentity]]:
    try:
        root = os.open(repo_root, _OPEN_DIRECTORY_FLAGS)
    except OSError as exc:
        raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    descriptors = [root]
    identities = [FileIdentity.from_stat(os.fstat(root))]
    try:
        if (
            identities[0].uid != os.geteuid()
            or not stat.S_ISDIR(identities[0].mode)
            or stat.S_IMODE(identities[0].mode) & 0o022
        ):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        current = root
        for index, component in enumerate(RUNTIME_COMPONENTS):
            current, identity = _open_directory(
                current,
                component,
                private=index > 0,
            )
            descriptors.append(current)
            identities.append(identity)
        return descriptors, identities
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _sidecars_absent(directory_fd: int) -> bool:
    for name in SIDECAR_NAMES:
        try:
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
        return False
    return True


def _revalidate_chain(
    repo_root: Path,
    descriptors: list[int],
    identities: list[FileIdentity],
) -> None:
    try:
        root_path_identity = FileIdentity.from_stat(os.stat(repo_root, follow_symlinks=False))
    except OSError as exc:
        raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    if root_path_identity != identities[0]:
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    for index, component in enumerate(RUNTIME_COMPONENTS, start=1):
        try:
            path_identity = FileIdentity.from_stat(
                os.stat(
                    component,
                    dir_fd=descriptors[index - 1],
                    follow_symlinks=False,
                )
            )
        except OSError as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
        if (
            path_identity != identities[index]
            or FileIdentity.from_stat(os.fstat(descriptors[index])) != identities[index]
        ):
            raise ReconciliationError("identity_unresolved_reconciliation_required")


def _read_database_snapshot(repo_root: Path) -> bytearray:
    directories, identities = _open_chain(repo_root)
    database_fd = -1
    try:
        database_directory = directories[-1]
        if not _sidecars_absent(database_directory):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        try:
            database_fd = os.open(
                DATABASE_NAME,
                _OPEN_FILE_FLAGS,
                dir_fd=database_directory,
            )
        except OSError as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
        before = FileIdentity.from_stat(os.fstat(database_fd))
        if (
            not stat.S_ISREG(before.mode)
            or before.uid != os.geteuid()
            or before.links != 1
            or before.size <= 0
            or before.size > MAX_DATABASE_BYTES
            or stat.S_IMODE(before.mode) & 0o022
        ):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        data = bytearray()
        while len(data) <= MAX_DATABASE_BYTES:
            block = os.read(database_fd, min(1024 * 1024, MAX_DATABASE_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        if len(data) != before.size or len(data) > MAX_DATABASE_BYTES:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        if not data.startswith(b"SQLite format 3\x00"):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        after = FileIdentity.from_stat(os.fstat(database_fd))
        try:
            path_after = FileIdentity.from_stat(
                os.stat(
                    DATABASE_NAME,
                    dir_fd=database_directory,
                    follow_symlinks=False,
                )
            )
        except OSError as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
        if after != before or path_after != before or not _sidecars_absent(database_directory):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        _revalidate_chain(repo_root, directories, identities)
        return data
    finally:
        if database_fd >= 0:
            os.close(database_fd)
        for descriptor in reversed(directories):
            os.close(descriptor)


_ALLOWED_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "app_metadata": frozenset({"key", "value"}),
    "node_enrollment_codes": frozenset(
        {
            "workspace_id",
            "display_name",
            "consumed_at",
            "consumed_node_id",
            "evidence_status",
        }
    ),
    "nodes": frozenset(
        {
            "node_id",
            "principal_id",
            "workspace_id",
            "display_name",
            "status",
            "evidence_status",
            "descriptor_hash",
            "enrolled_at",
            "updated_at",
            "last_seen_at",
            "revoked_at",
            "last_heartbeat_hash",
            "last_node_version",
            "last_configuration_digest",
            "last_mission_id",
            "desired_configuration_generation",
            "desired_configuration_digest",
            "acknowledged_configuration_generation",
            "acknowledged_configuration_digest",
            "acknowledged_configuration_signing_key_id",
            "acknowledged_active_configuration_signing_key_id",
            "configuration_acknowledged_at",
            "configuration_acknowledgment_status",
        }
    ),
    "node_nonces": frozenset(),
    "node_identity_key_rotations": frozenset(),
    "node_configurations": frozenset({"node_id"}),
    "node_configuration_trust_transitions": frozenset({"node_id"}),
    "missions": frozenset({"target_node_id"}),
    "mission_audit_evidence_bindings": frozenset(),
    "mission_transition_attempts": frozenset(),
    "mission_claims": frozenset({"node_id"}),
    "mission_report_receipts": frozenset({"node_id"}),
    "mission_report_nonces": frozenset({"node_id"}),
    **{table: frozenset() for table in PIS005A_TABLES},
}


def _projection_authorizer(
    action: int,
    argument_one: str | None,
    argument_two: str | None,
    _database: str | None,
    _trigger: str | None,
) -> int:
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and argument_two == "count":
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        table = argument_one or ""
        column = argument_two or ""
        allowed = _ALLOWED_COLUMNS.get(table)
        if allowed is not None and (column == "" or column in allowed):
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _single_row(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[str, ...] = (),
) -> sqlite3.Row:
    rows = connection.execute(query, parameters).fetchall()
    if len(rows) != 1:
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    return cast(sqlite3.Row, rows[0])


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _validate_schema_shape(connection: sqlite3.Connection) -> dict[str, str]:
    for table, expected_columns in _EXPECTED_TABLE_COLUMNS.items():
        table_rows = connection.execute(
            "SELECT type, ncol FROM pragma_table_list(?) WHERE schema = 'main' AND name = ?",
            (table, table),
        ).fetchall()
        if table_rows != [("table", len(expected_columns))]:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        observed_columns = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM pragma_table_info(?) ORDER BY cid",
                (table,),
            ).fetchall()
        )
        if observed_columns != expected_columns:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
    rows = connection.execute(
        "SELECT key, value FROM app_metadata "
        "WHERE key IN ('schema_version', 'minimum_writer_version')"
    ).fetchall()
    versions = {str(row[0]): str(row[1]) for row in rows}
    v4 = {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "minimum_writer_version": EXPECTED_MINIMUM_WRITER_VERSION,
    }
    v6 = {
        "schema_version": PIS004A_SCHEMA_VERSION,
        "minimum_writer_version": PIS004A_MINIMUM_WRITER_VERSION,
    }
    v7 = {
        "schema_version": PIS005A_SCHEMA_VERSION,
        "minimum_writer_version": PIS005A_MINIMUM_WRITER_VERSION,
    }
    if len(rows) != 2 or versions not in (v4, v6, v7):
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    if versions in (v6, v7):
        if expected_pis004a_schema_fingerprint() != EXPECTED_PIS004A_SCHEMA_FINGERPRINT:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        try:
            verify_pis004a_schema(connection)
        except (DatabaseMigrationError, sqlite3.DatabaseError) as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    if versions == v7:
        if expected_pis005a_schema_fingerprint() != EXPECTED_PIS005A_SCHEMA_FINGERPRINT:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        try:
            verify_pis005a_schema(connection)
            _require_empty_pis005a_tables(connection)
        except (DatabaseMigrationError, sqlite3.DatabaseError) as exc:
            raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    return versions


def _require_empty_pis005a_tables(connection: sqlite3.Connection) -> None:
    for table in PIS005A_TABLES:
        row = connection.execute(f"SELECT count(*) FROM {table}").fetchone()
        if row != (0,):
            raise ReconciliationError("identity_unresolved_reconciliation_required")


def project_identity(snapshot: bytes | bytearray) -> JsonObject:
    connection = sqlite3.connect(":memory:")
    try:
        connection.enable_load_extension(False)
        connection.deserialize(bytes(snapshot))
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        expected_versions = _validate_schema_shape(connection)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_projection_authorizer)
        versions = connection.execute(
            "SELECT key, value FROM app_metadata "
            "WHERE key IN ('schema_version', 'minimum_writer_version')"
        ).fetchall()
        if {str(row["key"]): str(row["value"]) for row in versions} != expected_versions:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        if expected_versions["schema_version"] == PIS005A_SCHEMA_VERSION:
            _require_empty_pis005a_tables(connection)
        if (
            _single_row(connection, "SELECT count(*) AS count FROM node_enrollment_codes")["count"]
            != 1
        ):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        enrollment = _single_row(
            connection,
            "SELECT workspace_id, display_name, consumed_at, consumed_node_id, "
            "evidence_status FROM node_enrollment_codes",
        )
        if _single_row(connection, "SELECT count(*) AS count FROM nodes")["count"] != 1:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        node = _single_row(
            connection,
            "SELECT node_id, principal_id, workspace_id, display_name, status, "
            "evidence_status, descriptor_hash, enrolled_at, updated_at, last_seen_at, "
            "revoked_at, last_heartbeat_hash, last_node_version, "
            "last_configuration_digest, last_mission_id, "
            "desired_configuration_generation, desired_configuration_digest, "
            "acknowledged_configuration_generation, acknowledged_configuration_digest, "
            "acknowledged_configuration_signing_key_id, "
            "acknowledged_active_configuration_signing_key_id, "
            "configuration_acknowledged_at, configuration_acknowledgment_status "
            "FROM nodes",
        )
        if _single_row(connection, "SELECT count(*) AS count FROM node_nonces")["count"] != 0:
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        if (
            _single_row(
                connection,
                "SELECT count(*) AS count FROM node_identity_key_rotations",
            )["count"]
            != 0
        ):
            raise ReconciliationError("identity_unresolved_reconciliation_required")
        activity_queries = (
            "SELECT count(*) AS count FROM node_configurations",
            "SELECT count(*) AS count FROM node_configuration_trust_transitions",
            "SELECT count(*) AS count FROM missions",
            "SELECT count(*) AS count FROM mission_audit_evidence_bindings",
            "SELECT count(*) AS count FROM mission_transition_attempts",
            "SELECT count(*) AS count FROM mission_claims",
            "SELECT count(*) AS count FROM mission_report_receipts",
            "SELECT count(*) AS count FROM mission_report_nonces",
        )
        for query in activity_queries:
            count = _single_row(connection, query)["count"]
            if count != 0:
                raise ReconciliationError("identity_unresolved_reconciliation_required")
    except (sqlite3.DatabaseError, sqlite3.NotSupportedError) as exc:
        raise ReconciliationError("identity_unresolved_reconciliation_required") from exc
    finally:
        connection.close()

    node_id = node["node_id"]
    consumed_at = enrollment["consumed_at"]
    consumed_instant = _parse_timestamp(consumed_at)
    updated_instant = _parse_timestamp(node["updated_at"])
    if (
        not isinstance(node_id, str)
        or not _NODE_ID.fullmatch(node_id)
        or enrollment["workspace_id"] != WORKSPACE_ID
        or enrollment["display_name"] != DISPLAY_NAME
        or enrollment["evidence_status"] != "complete"
        or enrollment["consumed_node_id"] != node_id
        or consumed_instant is None
        or node["principal_id"] != f"agent:node.{node_id}"
        or node["workspace_id"] != WORKSPACE_ID
        or node["display_name"] != DISPLAY_NAME
        or node["evidence_status"] != "complete"
        or node["descriptor_hash"] != EXPECTED_DESCRIPTOR_DIGEST
        or node["enrolled_at"] != consumed_at
        or updated_instant is None
    ):
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    inactive_fields = (
        "last_seen_at",
        "last_heartbeat_hash",
        "last_node_version",
        "last_configuration_digest",
        "last_mission_id",
        "desired_configuration_generation",
        "desired_configuration_digest",
        "acknowledged_configuration_generation",
        "acknowledged_configuration_digest",
        "acknowledged_configuration_signing_key_id",
        "acknowledged_active_configuration_signing_key_id",
        "configuration_acknowledged_at",
        "configuration_acknowledgment_status",
    )
    if any(node[field] is not None for field in inactive_fields):
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    status = node["status"]
    revoked_at = node["revoked_at"]
    revoked_instant = _parse_timestamp(revoked_at)
    if status == "enrolled" and revoked_at is None and node["updated_at"] == consumed_at:
        classification = "identity_bound_active_quarantine_required"
    elif (
        status == "revoked"
        and revoked_instant is not None
        and revoked_instant >= consumed_instant
        and node["updated_at"] == revoked_at
    ):
        classification = "identity_bound_revoked"
    else:
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    identity_digest = (
        "sha256:"
        + hashlib.sha256(
            b"ITHILDIN-ATTEMPT008-NODE-ID-V1\x00" + node_id.encode("ascii")
        ).hexdigest()
    )
    return {
        "classification": classification,
        "node_id": node_id,
        "node_identity_digest": identity_digest,
        "principal_id": f"agent:node.{node_id}",
        "workspace_id": WORKSPACE_ID,
        "display_name": DISPLAY_NAME,
        "descriptor_digest": EXPECTED_DESCRIPTOR_DIGEST,
        "status": status,
        "evidence_status": "complete",
        "enrolled_at": consumed_at,
        "revoked_at": revoked_at,
        "quarantine_confirmed": False,
        "revocation_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _open_or_create_receipt_base(repo_root: Path) -> tuple[int, list[int]]:
    root = os.open(repo_root, _OPEN_DIRECTORY_FLAGS)
    held = [root]
    current = root
    try:
        for index, component in enumerate(RECEIPT_BASE_COMPONENTS):
            try:
                next_fd, _identity = _open_directory(
                    current,
                    component,
                    private=index > 0,
                )
            except ReconciliationError:
                try:
                    os.mkdir(component, 0o700, dir_fd=current)
                    os.fsync(current)
                except OSError as exc:
                    raise ReconciliationError("receipt_write_failed") from exc
                next_fd, _identity = _open_directory(
                    current,
                    component,
                    private=index > 0,
                )
            held.append(next_fd)
            current = next_fd
        return current, held
    except BaseException:
        for descriptor in reversed(held):
            os.close(descriptor)
        raise


def _write_exclusive(directory_fd: int, name: str, record: JsonObject) -> None:
    content = (canonical_json(record) + "\n").encode()
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        written = os.write(descriptor, content)
        os.fsync(descriptor)
        details = os.fstat(descriptor)
        if (
            written != len(content)
            or not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_size != len(content)
        ):
            raise ReconciliationError("receipt_write_failed")
        os.fsync(directory_fd)
    except FileExistsError as exc:
        raise ReconciliationError("attempt_budget_already_consumed") from exc
    except OSError as exc:
        raise ReconciliationError("receipt_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def consume_budget(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> tuple[int, list[int]]:
    base_fd, held = _open_or_create_receipt_base(repo_root)
    try:
        try:
            os.mkdir(RECEIPT_DIRECTORY, 0o700, dir_fd=base_fd)
            os.fsync(base_fd)
        except FileExistsError as exc:
            raise ReconciliationError("attempt_budget_already_consumed") from exc
        except OSError as exc:
            raise ReconciliationError("receipt_write_failed") from exc
        receipt_fd, _identity = _open_directory(base_fd, RECEIPT_DIRECTORY, private=True)
        held.append(receipt_fd)
        _write_exclusive(
            receipt_fd,
            CONSUMED_RECEIPT,
            {
                "schema_version": "1",
                "record_type": "attempt008_node_identity_reconciliation_consumption",
                "reconciliation_id": RECONCILIATION_ID,
                "candidate_commit": candidate_commit,
                "candidate_tree": candidate_tree,
                "run_id": RUN_ID,
                "compose_project": PROJECT,
                "consumed_before_database_open": True,
                "attempt_budget": 0,
                "retry_authorized": False,
                "release_allowed": False,
                "uat_complete": False,
            },
        )
        return receipt_fd, held
    except BaseException:
        for descriptor in reversed(held):
            os.close(descriptor)
        raise


def _public_projection(private: JsonObject) -> JsonObject:
    digest = private.get("node_identity_digest")
    classification = private.get("classification")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    if classification not in {
        "identity_bound_active_quarantine_required",
        "identity_bound_revoked",
    }:
        raise ReconciliationError("identity_unresolved_reconciliation_required")
    return {
        "reconciliation_id": RECONCILIATION_ID,
        "classification": classification,
        "node_identity_digest": digest,
        "quarantine_confirmed": False,
        "revocation_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def run_live(repo_root: Path = ROOT) -> JsonObject:
    report = build_report(repo_root)
    if report["static_candidate_valid"] is not True or report["execution_available"] is not True:
        raise ReconciliationError("identity_reconciliation_not_authorized")
    candidate_commit = cast(str, report["candidate_commit"])
    candidate_tree = cast(str, report["candidate_tree"])
    receipt_fd, held = consume_budget(
        repo_root,
        candidate_commit=candidate_commit,
        candidate_tree=candidate_tree,
    )
    snapshot = bytearray()
    try:
        snapshot = _read_database_snapshot(repo_root)
        private = project_identity(snapshot)
        database_digest = "sha256:" + hashlib.sha256(snapshot).hexdigest()
        _write_exclusive(
            receipt_fd,
            RESULT_RECEIPT,
            {
                "schema_version": "1",
                "record_type": "attempt008_node_identity_reconciliation_result",
                "reconciliation_id": RECONCILIATION_ID,
                "candidate_commit": candidate_commit,
                "candidate_tree": candidate_tree,
                "database_snapshot_size": len(snapshot),
                "database_snapshot_sha256": database_digest,
                "database_source_unchanged": True,
                "database_sidecars_absent": True,
                **private,
            },
        )
        return _public_projection(private)
    except BaseException:
        try:
            _write_exclusive(
                receipt_fd,
                RESULT_RECEIPT,
                {
                    "schema_version": "1",
                    "record_type": ("attempt008_node_identity_reconciliation_result"),
                    "reconciliation_id": RECONCILIATION_ID,
                    "candidate_commit": candidate_commit,
                    "candidate_tree": candidate_tree,
                    "classification": ("identity_unresolved_reconciliation_required"),
                    "failure_code": ("identity_unresolved_reconciliation_required"),
                    "quarantine_confirmed": False,
                    "revocation_authorized": False,
                    "cleanup_authorized": False,
                    "successor_o4_authorized": False,
                    "release_allowed": False,
                    "uat_complete": False,
                },
            )
        except ReconciliationError:
            pass
        raise ReconciliationError("identity_unresolved_reconciliation_required") from None
    finally:
        for index in range(len(snapshot)):
            snapshot[index] = 0
        for descriptor in reversed(held):
            os.close(descriptor)


def main(arguments: Iterable[str] | None = None) -> int:
    effective = list(sys.argv[1:] if arguments is None else arguments)
    if effective:
        print("attempt008_node_identity_reconciliation_error: arguments_not_allowed")
        return 2
    try:
        projection = run_live()
    except ReconciliationError as exc:
        print(f"attempt008_node_identity_reconciliation_error: {exc.code}")
        return 1
    except KeyboardInterrupt:
        print("attempt008_node_identity_reconciliation_error: interrupted")
        return 1
    except Exception:
        print("attempt008_node_identity_reconciliation_error: unexpected_failure")
        return 1
    print(f"attempt008_node_identity_reconciliation_status: {projection['classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
