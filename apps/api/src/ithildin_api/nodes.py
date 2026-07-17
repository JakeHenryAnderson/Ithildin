"""Local-preview Ithildin Node enrollment and signed heartbeat state."""

from __future__ import annotations

import base64
import binascii
import builtins
import json
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from ithildin_schemas.models import SHA256_PATTERN, StrictBaseModel
from pydantic import Field, field_validator

from ithildin_api.node_configuration import configuration_state
from ithildin_api.node_versions import validate_node_version

NODE_PROTOCOL_VERSION = "1"
NODE_SIGNATURE_CONTEXT = "ITHILDIN-NODE-V1"
NODE_IDENTITY_ROTATION_PROOF_CONTEXT = "ITHILDIN-NODE-IDENTITY-ROTATION-V1"
NODE_PRINCIPAL_PREFIX = "agent:node."
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")
_DISPLAY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.,:@()-]{0,127}$")
_NODE_ID_PATTERN = re.compile(r"^node_[0-9a-f]{32}$")
_NONCE_PATTERN = re.compile(r"^[0-9a-f]{32,128}$")
_ROTATION_ID_PATTERN = re.compile(r"^nkr_[0-9a-f]{32}$")
_ACTIVE_STATUS = "enrolled"
_REVOKED_STATUS = "revoked"
_EVIDENCE_PENDING = "pending"
_EVIDENCE_COMPLETE = "complete"


class NodeError(RuntimeError):
    """Raised when Node enrollment or authentication fails closed."""


class NodeNotFoundError(NodeError):
    """Raised when a Node identity is unknown."""


class NodeAuthenticationError(NodeError):
    """Raised when a signed Node request is invalid."""


class NodeConflictError(NodeError):
    """Raised when a one-time or state transition invariant is violated."""


class EnrollmentCodeIssuePayload(StrictBaseModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)

    @field_validator("workspace_id")
    @classmethod
    def _safe_labels(cls, value: str) -> str:
        return _safe_label(value)

    @field_validator("display_name")
    @classmethod
    def _safe_display_name(cls, value: str) -> str:
        if not _DISPLAY_NAME_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("unsafe display name")
        if any(ord(character) < 32 for character in value):
            raise ValueError("control characters are not allowed")
        return value


class NodeEnrollmentPayload(StrictBaseModel):
    enrollment_code: str = Field(min_length=32, max_length=256)
    public_key: str = Field(min_length=40, max_length=64)
    protocol_version: Literal["1"]
    node_version: str = Field(min_length=1, max_length=128)
    runner_adapter: str = Field(min_length=1, max_length=128)
    deployment_topology: Literal["local_process", "docker_sidecar", "server_service"]

    @field_validator("node_version")
    @classmethod
    def _closed_node_version(cls, value: str) -> str:
        return validate_node_version(value)

    @field_validator("runner_adapter")
    @classmethod
    def _safe_labels(cls, value: str) -> str:
        return _safe_label(value)

    @field_validator("public_key")
    @classmethod
    def _public_key_is_raw_ed25519(cls, value: str) -> str:
        _decode_public_key(value)
        return value

    def descriptor(self) -> JsonObject:
        return {
            "protocol_version": self.protocol_version,
            "node_version": self.node_version,
            "runner_adapter": self.runner_adapter,
            "deployment_topology": self.deployment_topology,
        }


class NodeHeartbeatPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    node_version: str = Field(min_length=1, max_length=128)
    runner_adapter: str = Field(min_length=1, max_length=128)
    deployment_topology: Literal["local_process", "docker_sidecar", "server_service"]
    configuration_digest: str = Field(pattern=SHA256_PATTERN)
    mission_id: str | None = Field(default=None, max_length=128)

    @field_validator("node_version")
    @classmethod
    def _closed_node_version(cls, value: str) -> str:
        return validate_node_version(value)

    @field_validator("runner_adapter", "mission_id")
    @classmethod
    def _safe_labels(cls, value: str | None) -> str | None:
        return _safe_label(value) if value is not None else None

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json", exclude_none=True))


class NodeIdentityRotationChallengePayload(StrictBaseModel):
    protocol_version: Literal["1"]


class NodeIdentityRotationActivationPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    rotation_id: str = Field(pattern=r"^nkr_[0-9a-f]{32}$")
    challenge: str = Field(min_length=40, max_length=64)
    next_public_key: str = Field(min_length=40, max_length=64)
    next_key_proof: str = Field(min_length=80, max_length=128)

    @field_validator("next_public_key")
    @classmethod
    def _public_key_is_raw_ed25519(cls, value: str) -> str:
        _decode_public_key(value)
        return value


class NodeIdentityRotationStatusPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    rotation_id: str = Field(pattern=r"^nkr_[0-9a-f]{32}$")


@dataclass(frozen=True)
class IssuedEnrollmentCode:
    code_id: str
    enrollment_code: str
    workspace_id: str
    display_name: str
    created_at: str
    expires_at: str

    def response(self) -> JsonObject:
        return {
            "code_id": self.code_id,
            "enrollment_code": self.enrollment_code,
            "workspace_id": self.workspace_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "secret_returned_once": True,
        }


@dataclass(frozen=True)
class NodeIdentityRotationRecord:
    rotation_id: str
    node_id: str
    principal_id: str
    workspace_id: str
    current_key_id: str
    challenge_digest: str
    created_at: str
    expires_at: str
    status: str
    evidence_status: str
    next_key_id: str | None
    activated_at: str | None

    def summary(self, *, now: datetime | None = None) -> JsonObject:
        effective_status = self.status
        if (
            effective_status == "pending"
            and _parse_datetime(self.expires_at) <= (now or datetime.now(UTC))
        ):
            effective_status = "expired"
        return {
            "rotation_id": self.rotation_id,
            "node_id": self.node_id,
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "current_key_id": self.current_key_id,
            "next_key_id": self.next_key_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "activated_at": self.activated_at,
            "status": effective_status,
            "evidence_status": self.evidence_status,
            "private_key_received": False,
            "retired_key_request_authority": False,
        }


@dataclass(frozen=True)
class IssuedNodeIdentityRotation:
    record: NodeIdentityRotationRecord
    challenge: str

    def response(self) -> JsonObject:
        return {**self.record.summary(), "challenge": self.challenge}


@dataclass(frozen=True)
class NodeRecord:
    node_id: str
    principal_id: str
    workspace_id: str
    display_name: str
    status: str
    evidence_status: str
    public_key: str
    descriptor_hash: str
    descriptor: JsonObject
    enrolled_at: str
    updated_at: str
    last_seen_at: str | None
    revoked_at: str | None
    last_heartbeat_hash: str | None
    last_node_version: str | None
    last_configuration_digest: str | None
    last_mission_id: str | None
    desired_configuration_generation: int | None
    desired_configuration_digest: str | None
    acknowledged_configuration_generation: int | None
    acknowledged_configuration_digest: str | None
    acknowledged_configuration_signing_key_id: str | None
    acknowledged_active_configuration_signing_key_id: str | None
    configuration_acknowledged_at: str | None
    configuration_acknowledgment_status: str | None

    def summary(
        self,
        *,
        now: datetime | None = None,
        stale_after_seconds: int = 90,
    ) -> JsonObject:
        observed_state = _observed_state(
            status=self.status,
            evidence_status=self.evidence_status,
            last_seen_at=self.last_seen_at,
            now=now or datetime.now(UTC),
            stale_after_seconds=stale_after_seconds,
        )
        return {
            "node_id": self.node_id,
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "display_name": self.display_name,
            "status": self.status,
            "evidence_status": self.evidence_status,
            "observed_state": observed_state,
            "descriptor_hash": self.descriptor_hash,
            "descriptor": self.descriptor,
            "enrolled_at": self.enrolled_at,
            "updated_at": self.updated_at,
            "last_seen_at": self.last_seen_at,
            "revoked_at": self.revoked_at,
            "last_heartbeat_hash": self.last_heartbeat_hash,
            "last_observed_node_version": self.last_node_version,
            "last_configuration_digest": self.last_configuration_digest,
            "last_mission_id": self.last_mission_id,
            "desired_configuration_generation": self.desired_configuration_generation,
            "desired_configuration_digest": self.desired_configuration_digest,
            "acknowledged_configuration_generation": self.acknowledged_configuration_generation,
            "acknowledged_configuration_digest": self.acknowledged_configuration_digest,
            "acknowledged_configuration_signing_key_id": (
                self.acknowledged_configuration_signing_key_id
            ),
            "acknowledged_active_configuration_signing_key_id": (
                self.acknowledged_active_configuration_signing_key_id
            ),
            "configuration_acknowledged_at": self.configuration_acknowledged_at,
            "configuration_acknowledgment_status": self.configuration_acknowledgment_status,
            "configuration_state": configuration_state(
                node_status=self.status,
                node_evidence_status=self.evidence_status,
                desired_generation=self.desired_configuration_generation,
                desired_digest=self.desired_configuration_digest,
                acknowledged_generation=self.acknowledged_configuration_generation,
                acknowledged_digest=self.acknowledged_configuration_digest,
                acknowledgment_status=self.configuration_acknowledgment_status,
            ),
            "identity_source": "gateway_derived",
            "connectivity_source": "gateway_accepted_heartbeat",
            "runner_health_known": False,
            "model_health_known": False,
            "active_identity_key_id": node_identity_key_id(self.public_key),
        }


class NodeStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS node_enrollment_codes (
                    code_id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL UNIQUE,
                    workspace_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    consumed_at TEXT,
                    consumed_node_id TEXT,
                    evidence_status TEXT NOT NULL DEFAULT 'complete'
                );
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL UNIQUE,
                    workspace_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_status TEXT NOT NULL DEFAULT 'complete',
                    public_key TEXT NOT NULL,
                    descriptor_hash TEXT NOT NULL,
                    descriptor_json TEXT NOT NULL,
                    enrolled_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    revoked_at TEXT,
                    last_heartbeat_hash TEXT,
                    last_node_version TEXT,
                    last_configuration_digest TEXT,
                    last_mission_id TEXT,
                    desired_configuration_generation INTEGER,
                    desired_configuration_digest TEXT,
                    acknowledged_configuration_generation INTEGER,
                    acknowledged_configuration_digest TEXT,
                    acknowledged_configuration_signing_key_id TEXT,
                    acknowledged_active_configuration_signing_key_id TEXT,
                    configuration_acknowledged_at TEXT,
                    configuration_acknowledgment_status TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_nodes_updated_at ON nodes(updated_at);
                CREATE TABLE IF NOT EXISTS node_nonces (
                    node_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    PRIMARY KEY (node_id, nonce)
                );
                CREATE INDEX IF NOT EXISTS idx_node_nonces_accepted_at
                    ON node_nonces(accepted_at);
                CREATE TABLE IF NOT EXISTS node_identity_key_rotations (
                    rotation_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    principal_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    current_key_id TEXT NOT NULL,
                    current_public_key TEXT NOT NULL,
                    challenge_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_status TEXT NOT NULL,
                    next_public_key TEXT,
                    next_key_id TEXT,
                    activated_at TEXT,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
                );
                CREATE INDEX IF NOT EXISTS idx_node_identity_key_rotations_node_created
                    ON node_identity_key_rotations(node_id, created_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_node_identity_key_rotations_one_pending
                    ON node_identity_key_rotations(node_id) WHERE status = 'pending';
                """
            )
            _ensure_column(
                connection,
                table="node_enrollment_codes",
                column="evidence_status",
                definition="TEXT NOT NULL DEFAULT 'complete'",
            )
            for column, definition in (
                ("desired_configuration_generation", "INTEGER"),
                ("desired_configuration_digest", "TEXT"),
                ("acknowledged_configuration_generation", "INTEGER"),
                ("acknowledged_configuration_digest", "TEXT"),
                ("acknowledged_configuration_signing_key_id", "TEXT"),
                ("acknowledged_active_configuration_signing_key_id", "TEXT"),
                ("configuration_acknowledged_at", "TEXT"),
                ("configuration_acknowledgment_status", "TEXT"),
            ):
                _ensure_column(
                    connection,
                    table="nodes",
                    column=column,
                    definition=definition,
                )
            _ensure_column(
                connection,
                table="nodes",
                column="last_node_version",
                definition="TEXT",
            )
            _ensure_column(
                connection,
                table="nodes",
                column="evidence_status",
                definition="TEXT NOT NULL DEFAULT 'complete'",
            )
            _ensure_column(
                connection,
                table="node_identity_key_rotations",
                column="current_public_key",
                definition="TEXT",
            )
            connection.commit()

    def issue_enrollment_code(
        self,
        payload: EnrollmentCodeIssuePayload,
        *,
        expires_in_seconds: int,
        now: datetime | None = None,
    ) -> IssuedEnrollmentCode:
        effective_now = now or datetime.now(UTC)
        enrollment_code = secrets.token_urlsafe(32)
        code_id = f"ncode_{uuid4().hex}"
        expires_at = effective_now + timedelta(seconds=expires_in_seconds)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO node_enrollment_codes (
                    code_id, code_hash, workspace_id, display_name, created_at, expires_at,
                    evidence_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code_id,
                    _secret_digest(enrollment_code),
                    payload.workspace_id,
                    payload.display_name,
                    effective_now.isoformat(),
                    expires_at.isoformat(),
                    _EVIDENCE_PENDING,
                ),
            )
            connection.commit()
        return IssuedEnrollmentCode(
            code_id=code_id,
            enrollment_code=enrollment_code,
            workspace_id=payload.workspace_id,
            display_name=payload.display_name,
            created_at=effective_now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

    def mark_enrollment_code_evidence_complete(self, code_id: str) -> None:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE node_enrollment_codes SET evidence_status = ?
                WHERE code_id = ? AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, code_id, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConflictError("enrollment-code evidence state changed")
            connection.commit()

    def enroll(
        self,
        payload: NodeEnrollmentPayload,
        *,
        now: datetime | None = None,
    ) -> NodeRecord:
        effective_now = now or datetime.now(UTC)
        code_hash = _secret_digest(payload.enrollment_code)
        descriptor = payload.descriptor()
        descriptor_hash = sha256_digest(descriptor)
        node_id = f"node_{uuid4().hex}"
        principal_id = f"{NODE_PRINCIPAL_PREFIX}{node_id}"
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT code_id, workspace_id, display_name, expires_at, consumed_at,
                       evidence_status
                FROM node_enrollment_codes WHERE code_hash = ?
                """,
                (code_hash,),
            ).fetchone()
            if row is None:
                raise NodeAuthenticationError("invalid enrollment code")
            if row[4] is not None:
                raise NodeConflictError("enrollment code already consumed")
            if row[5] != _EVIDENCE_COMPLETE:
                raise NodeAuthenticationError("enrollment code evidence is incomplete")
            if _parse_datetime(str(row[3])) <= effective_now:
                raise NodeAuthenticationError("enrollment code expired")
            workspace_id = str(row[1])
            display_name = str(row[2])
            now_text = effective_now.isoformat()
            connection.execute(
                """
                INSERT INTO nodes (
                    node_id, principal_id, workspace_id, display_name, status, evidence_status,
                    public_key,
                    descriptor_hash, descriptor_json, enrolled_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    principal_id,
                    workspace_id,
                    display_name,
                    _ACTIVE_STATUS,
                    _EVIDENCE_PENDING,
                    payload.public_key,
                    descriptor_hash,
                    canonical_json(descriptor),
                    now_text,
                    now_text,
                ),
            )
            updated = connection.execute(
                """
                UPDATE node_enrollment_codes
                SET consumed_at = ?, consumed_node_id = ?
                WHERE code_id = ? AND consumed_at IS NULL
                """,
                (now_text, node_id, str(row[0])),
            )
            if updated.rowcount != 1:
                raise NodeConflictError("enrollment code already consumed")
            connection.commit()
        return self.get(node_id)

    def mark_node_evidence_complete(self, node_id: str) -> NodeRecord:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE nodes SET evidence_status = ?
                WHERE node_id = ? AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, node_id, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConflictError("Node evidence state changed")
            connection.commit()
        return self.get(node_id)

    def get(self, node_id: str) -> NodeRecord:
        if not _NODE_ID_PATTERN.fullmatch(node_id):
            raise NodeNotFoundError("unknown Node")
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT node_id, principal_id, workspace_id, display_name, status, evidence_status,
                       public_key,
                       descriptor_hash, descriptor_json, enrolled_at, updated_at, last_seen_at,
                       revoked_at, last_heartbeat_hash, last_node_version,
                       last_configuration_digest, last_mission_id
                       , desired_configuration_generation, desired_configuration_digest,
                       acknowledged_configuration_generation, acknowledged_configuration_digest,
                       configuration_acknowledged_at, configuration_acknowledgment_status,
                       acknowledged_configuration_signing_key_id,
                       acknowledged_active_configuration_signing_key_id
                FROM nodes WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
        if row is None:
            raise NodeNotFoundError("unknown Node")
        return _record(row)

    def list(
        self, *, limit: int = 50, stale_after_seconds: int = 90
    ) -> builtins.list[JsonObject]:
        return [
            record.summary(stale_after_seconds=stale_after_seconds)
            for record in self.list_records(limit=limit)
        ]

    def list_records(self, *, limit: int = 50) -> builtins.list[NodeRecord]:
        bounded_limit = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT node_id, principal_id, workspace_id, display_name, status, evidence_status,
                       public_key,
                       descriptor_hash, descriptor_json, enrolled_at, updated_at, last_seen_at,
                       revoked_at, last_heartbeat_hash, last_node_version,
                       last_configuration_digest, last_mission_id
                       , desired_configuration_generation, desired_configuration_digest,
                       acknowledged_configuration_generation, acknowledged_configuration_digest,
                       configuration_acknowledged_at, configuration_acknowledgment_status,
                       acknowledged_configuration_signing_key_id,
                       acknowledged_active_configuration_signing_key_id
                FROM nodes ORDER BY updated_at DESC LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [_record(row) for row in rows]

    def revoke(self, node_id: str, *, now: datetime | None = None) -> NodeRecord:
        effective_now = now or datetime.now(UTC)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, evidence_status FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if row is None:
                raise NodeNotFoundError("unknown Node")
            if str(row[0]) == _REVOKED_STATUS:
                raise NodeConflictError("Node already revoked")
            if str(row[1]) != _EVIDENCE_COMPLETE:
                raise NodeConflictError("Node evidence is incomplete")
            now_text = effective_now.isoformat()
            connection.execute(
                """
                UPDATE nodes
                SET status = ?, evidence_status = ?, revoked_at = ?, updated_at = ?
                WHERE node_id = ?
                """,
                (_REVOKED_STATUS, _EVIDENCE_PENDING, now_text, now_text, node_id),
            )
            connection.commit()
        return self.get(node_id)

    def accept_heartbeat(
        self,
        *,
        node_id: str,
        timestamp: str,
        nonce: str,
        signature: str,
        payload: NodeHeartbeatPayload,
        path: str,
        max_clock_skew_seconds: int,
        now: datetime | None = None,
    ) -> NodeRecord:
        effective_now = now or datetime.now(UTC)
        if not _NONCE_PATTERN.fullmatch(nonce):
            raise NodeAuthenticationError("invalid Node nonce")
        try:
            timestamp_value = int(timestamp)
        except ValueError as exc:
            raise NodeAuthenticationError("invalid Node timestamp") from exc
        if abs(int(effective_now.timestamp()) - timestamp_value) > max_clock_skew_seconds:
            raise NodeAuthenticationError("stale Node timestamp")
        record = self.get(node_id)
        if record.status != _ACTIVE_STATUS:
            raise NodeAuthenticationError("Node is revoked")
        if record.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeAuthenticationError("Node evidence is incomplete")
        body = payload.safe_payload()
        body_hash = sha256_digest(body)
        message = canonical_signature_message(
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body_hash=body_hash,
        )
        _verify_signature(record.public_key, signature, message)
        heartbeat_hash = sha256_digest(
            {"node_id": node_id, "timestamp": timestamp, "nonce": nonce, "body": body}
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status, evidence_status, public_key FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if current is None:
                raise NodeAuthenticationError("unknown Node")
            if (
                str(current[0]) != _ACTIVE_STATUS
                or str(current[1]) != _EVIDENCE_COMPLETE
                or str(current[2]) != record.public_key
            ):
                raise NodeAuthenticationError("Node is not active")
            try:
                connection.execute(
                    "INSERT INTO node_nonces (node_id, nonce, accepted_at) VALUES (?, ?, ?)",
                    (node_id, nonce, effective_now.isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise NodeAuthenticationError("replayed Node nonce") from exc
            connection.execute(
                """
                UPDATE nodes
                SET evidence_status = ?, updated_at = ?, last_seen_at = ?, last_heartbeat_hash = ?,
                    last_node_version = ?, last_configuration_digest = ?, last_mission_id = ?
                WHERE node_id = ?
                """,
                (
                    _EVIDENCE_PENDING,
                    effective_now.isoformat(),
                    effective_now.isoformat(),
                    heartbeat_hash,
                    payload.node_version,
                    payload.configuration_digest,
                    payload.mission_id,
                    node_id,
                ),
            )
            connection.commit()
        return self.get(node_id)

    def authenticate_request(
        self,
        *,
        node_id: str,
        timestamp: str,
        nonce: str,
        signature: str,
        body: JsonObject,
        path: str,
        max_clock_skew_seconds: int,
        now: datetime | None = None,
    ) -> NodeRecord:
        """Authenticate a non-heartbeat Node request and consume its replay nonce."""
        effective_now = now or datetime.now(UTC)
        if not _NONCE_PATTERN.fullmatch(nonce):
            raise NodeAuthenticationError("invalid Node nonce")
        try:
            timestamp_value = int(timestamp)
        except ValueError as exc:
            raise NodeAuthenticationError("invalid Node timestamp") from exc
        if abs(int(effective_now.timestamp()) - timestamp_value) > max_clock_skew_seconds:
            raise NodeAuthenticationError("stale Node timestamp")
        record = self.get(node_id)
        if record.status != _ACTIVE_STATUS:
            raise NodeAuthenticationError("Node is revoked")
        if record.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeAuthenticationError("Node evidence is incomplete")
        message = canonical_signature_message(
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body_hash=sha256_digest(body),
        )
        _verify_signature(record.public_key, signature, message)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status, evidence_status, public_key FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if current is None:
                raise NodeAuthenticationError("unknown Node")
            if (
                str(current[0]) != _ACTIVE_STATUS
                or str(current[1]) != _EVIDENCE_COMPLETE
                or str(current[2]) != record.public_key
            ):
                raise NodeAuthenticationError("Node is not active")
            try:
                connection.execute(
                    "INSERT INTO node_nonces (node_id, nonce, accepted_at) VALUES (?, ?, ?)",
                    (node_id, nonce, effective_now.isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise NodeAuthenticationError("replayed Node nonce") from exc
            connection.commit()
        return record

    def issue_identity_rotation_challenge(
        self,
        node_id: str,
        *,
        expires_in_seconds: int = 300,
        now: datetime | None = None,
    ) -> IssuedNodeIdentityRotation:
        effective_now = now or datetime.now(UTC)
        record = self.get(node_id)
        if record.status != _ACTIVE_STATUS:
            raise NodeAuthenticationError("Node is revoked")
        if record.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeAuthenticationError("Node evidence is incomplete")
        rotation_id = f"nkr_{uuid4().hex}"
        challenge = secrets.token_urlsafe(32)
        expires_at = effective_now + timedelta(seconds=expires_in_seconds)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status, evidence_status, public_key FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if (
                current is None
                or str(current[0]) != _ACTIVE_STATUS
                or str(current[1]) != _EVIDENCE_COMPLETE
                or str(current[2]) != record.public_key
            ):
                raise NodeAuthenticationError("Node is not active")
            connection.execute(
                """
                UPDATE node_identity_key_rotations SET status = 'expired'
                WHERE node_id = ? AND status = 'pending' AND expires_at <= ?
                """,
                (node_id, effective_now.isoformat()),
            )
            try:
                connection.execute(
                    """
                    INSERT INTO node_identity_key_rotations (
                        rotation_id, node_id, principal_id, workspace_id, current_key_id,
                        current_public_key, challenge_digest, created_at, expires_at, status,
                        evidence_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        rotation_id,
                        node_id,
                        record.principal_id,
                        record.workspace_id,
                        node_identity_key_id(record.public_key),
                        record.public_key,
                        sha256_digest(challenge),
                        effective_now.isoformat(),
                        expires_at.isoformat(),
                        _EVIDENCE_PENDING,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise NodeConflictError("Node already has a pending identity-key rotation") from exc
            connection.commit()
        return IssuedNodeIdentityRotation(self.get_identity_rotation(rotation_id), challenge)

    def mark_identity_rotation_challenge_evidence_complete(
        self, rotation_id: str
    ) -> NodeIdentityRotationRecord:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE node_identity_key_rotations SET evidence_status = ?
                WHERE rotation_id = ? AND status = 'pending' AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, rotation_id, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConflictError("identity-key rotation evidence state changed")
            connection.commit()
        return self.get_identity_rotation(rotation_id)

    def activate_identity_rotation(
        self,
        node_id: str,
        payload: NodeIdentityRotationActivationPayload,
        *,
        now: datetime | None = None,
    ) -> tuple[NodeRecord, NodeIdentityRotationRecord]:
        effective_now = now or datetime.now(UTC)
        node = self.get(node_id)
        rotation = self.get_identity_rotation(payload.rotation_id)
        if rotation.node_id != node_id:
            raise NodeAuthenticationError("identity-key rotation target mismatch")
        if rotation.status != "pending":
            raise NodeConflictError("identity-key rotation is not pending")
        if rotation.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeAuthenticationError("identity-key rotation evidence is incomplete")
        if _parse_datetime(rotation.expires_at) <= effective_now:
            raise NodeAuthenticationError("identity-key rotation expired")
        current_key_id = node_identity_key_id(node.public_key)
        if current_key_id != rotation.current_key_id:
            raise NodeConflictError("Node identity key changed")
        next_key_id = node_identity_key_id(payload.next_public_key)
        if next_key_id == current_key_id:
            raise NodeConflictError("identity-key rotation must change the key")
        if sha256_digest(payload.challenge) != rotation.challenge_digest:
            raise NodeAuthenticationError("identity-key rotation challenge mismatch")
        proof = canonical_identity_rotation_proof_message(
            rotation=rotation,
            next_key_id=next_key_id,
        )
        _verify_signature(payload.next_public_key, payload.next_key_proof, proof)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status, evidence_status, public_key FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            transition = connection.execute(
                """
                SELECT status, evidence_status, current_key_id, challenge_digest, expires_at
                FROM node_identity_key_rotations WHERE rotation_id = ? AND node_id = ?
                """,
                (payload.rotation_id, node_id),
            ).fetchone()
            if current is None or transition is None:
                raise NodeAuthenticationError("unknown Node identity-key rotation")
            if (
                str(current[0]) != _ACTIVE_STATUS
                or str(current[1]) != _EVIDENCE_COMPLETE
                or str(current[2]) != node.public_key
                or str(transition[0]) != "pending"
                or str(transition[1]) != _EVIDENCE_COMPLETE
                or str(transition[2]) != current_key_id
                or str(transition[3]) != rotation.challenge_digest
                or _parse_datetime(str(transition[4])) <= effective_now
            ):
                raise NodeConflictError("identity-key rotation state changed")
            now_text = effective_now.isoformat()
            connection.execute(
                """
                UPDATE nodes SET public_key = ?, evidence_status = ?, updated_at = ?
                WHERE node_id = ?
                """,
                (payload.next_public_key, _EVIDENCE_PENDING, now_text, node_id),
            )
            connection.execute(
                """
                UPDATE node_identity_key_rotations
                SET status = 'activated', evidence_status = ?, next_public_key = ?,
                    next_key_id = ?, activated_at = ?
                WHERE rotation_id = ?
                """,
                (
                    _EVIDENCE_PENDING,
                    payload.next_public_key,
                    next_key_id,
                    now_text,
                    payload.rotation_id,
                ),
            )
            connection.commit()
        return self.get(node_id), self.get_identity_rotation(payload.rotation_id)

    def mark_identity_rotation_activation_evidence_complete(
        self, rotation_id: str
    ) -> tuple[NodeRecord, NodeIdentityRotationRecord]:
        rotation = self.get_identity_rotation(rotation_id)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            transition = connection.execute(
                """
                UPDATE node_identity_key_rotations SET evidence_status = ?
                WHERE rotation_id = ? AND status = 'activated' AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, rotation_id, _EVIDENCE_PENDING),
            )
            node = connection.execute(
                """
                UPDATE nodes SET evidence_status = ?
                WHERE node_id = ? AND evidence_status = ? AND public_key = (
                    SELECT next_public_key FROM node_identity_key_rotations
                    WHERE rotation_id = ?
                )
                """,
                (_EVIDENCE_COMPLETE, rotation.node_id, _EVIDENCE_PENDING, rotation_id),
            )
            if transition.rowcount != 1 or node.rowcount != 1:
                raise NodeConflictError("identity-key rotation evidence state changed")
            connection.commit()
        return self.get(rotation.node_id), self.get_identity_rotation(rotation_id)

    def abort_identity_rotation_after_audit_failure(
        self, rotation_id: str
    ) -> tuple[NodeRecord, NodeIdentityRotationRecord]:
        """Restore the pre-rotation key only when activation evidence was never durable."""
        rotation = self.get_identity_rotation(rotation_id)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT current_public_key, next_public_key, status, evidence_status
                FROM node_identity_key_rotations WHERE rotation_id = ?
                """,
                (rotation_id,),
            ).fetchone()
            node = connection.execute(
                "SELECT public_key, evidence_status FROM nodes WHERE node_id = ?",
                (rotation.node_id,),
            ).fetchone()
            if (
                row is None
                or node is None
                or str(row[2]) != "activated"
                or str(row[3]) != _EVIDENCE_PENDING
                or str(node[0]) != str(row[1])
                or str(node[1]) != _EVIDENCE_PENDING
            ):
                raise NodeConflictError("identity-key rotation cannot be compensated")
            connection.execute(
                """
                UPDATE nodes SET public_key = ?, evidence_status = ? WHERE node_id = ?
                """,
                (str(row[0]), _EVIDENCE_COMPLETE, rotation.node_id),
            )
            connection.execute(
                """
                UPDATE node_identity_key_rotations
                SET status = 'audit_failed', evidence_status = ? WHERE rotation_id = ?
                """,
                (_EVIDENCE_COMPLETE, rotation_id),
            )
            connection.commit()
        return self.get(rotation.node_id), self.get_identity_rotation(rotation_id)

    def get_identity_rotation(self, rotation_id: str) -> NodeIdentityRotationRecord:
        if not _ROTATION_ID_PATTERN.fullmatch(rotation_id):
            raise NodeNotFoundError("unknown Node identity-key rotation")
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT rotation_id, node_id, principal_id, workspace_id, current_key_id,
                       challenge_digest, created_at, expires_at, status, evidence_status,
                       next_key_id, activated_at
                FROM node_identity_key_rotations WHERE rotation_id = ?
                """,
                (rotation_id,),
            ).fetchone()
        if row is None:
            raise NodeNotFoundError("unknown Node identity-key rotation")
        return _identity_rotation_record(row)

    def latest_identity_rotation(self, node_id: str) -> NodeIdentityRotationRecord | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT rotation_id, node_id, principal_id, workspace_id, current_key_id,
                       challenge_digest, created_at, expires_at, status, evidence_status,
                       next_key_id, activated_at
                FROM node_identity_key_rotations WHERE node_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (node_id,),
            ).fetchone()
        return _identity_rotation_record(row) if row is not None else None


def canonical_signature_message(
    *, method: str, path: str, timestamp: str, nonce: str, body_hash: str
) -> bytes:
    return (
        f"{NODE_SIGNATURE_CONTEXT}\n{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    ).encode()


def node_identity_key_id(public_key: str) -> str:
    _decode_public_key(public_key)
    return sha256_digest(public_key)


def canonical_identity_rotation_proof_message(
    *, rotation: NodeIdentityRotationRecord, next_key_id: str
) -> bytes:
    return (
        f"{NODE_IDENTITY_ROTATION_PROOF_CONTEXT}\n"
        f"{NODE_PROTOCOL_VERSION}\n{rotation.rotation_id}\n{rotation.node_id}\n"
        f"{rotation.principal_id}\n{rotation.workspace_id}\n{rotation.current_key_id}\n"
        f"{next_key_id}\n{rotation.challenge_digest}\n{rotation.expires_at}"
    ).encode()


def enrollment_audit_metadata(issued: IssuedEnrollmentCode) -> JsonObject:
    return {
        "code_id": issued.code_id,
        "workspace_id": issued.workspace_id,
        "expires_at": issued.expires_at,
        "secret_recorded": False,
    }


def node_audit_metadata(record: NodeRecord) -> JsonObject:
    return {
        "node_id": record.node_id,
        "principal_id": record.principal_id,
        "workspace_id": record.workspace_id,
        "status": record.status,
        "evidence_status": record.evidence_status,
        "descriptor_hash": record.descriptor_hash,
        "last_heartbeat_hash": record.last_heartbeat_hash,
        "identity_source": "gateway_derived",
    }


def identity_rotation_audit_metadata(
    rotation: NodeIdentityRotationRecord,
) -> JsonObject:
    return {
        **rotation.summary(),
        "challenge_digest": rotation.challenge_digest,
        "public_key_recorded": False,
        "private_key_received": False,
    }


def _record(row: tuple[object, ...]) -> NodeRecord:
    descriptor = json.loads(str(row[8]))
    if not isinstance(descriptor, dict):
        raise NodeError("invalid stored Node descriptor")
    return NodeRecord(
        node_id=str(row[0]),
        principal_id=str(row[1]),
        workspace_id=str(row[2]),
        display_name=str(row[3]),
        status=str(row[4]),
        evidence_status=str(row[5]),
        public_key=str(row[6]),
        descriptor_hash=str(row[7]),
        descriptor=cast(JsonObject, descriptor),
        enrolled_at=str(row[9]),
        updated_at=str(row[10]),
        last_seen_at=str(row[11]) if row[11] is not None else None,
        revoked_at=str(row[12]) if row[12] is not None else None,
        last_heartbeat_hash=str(row[13]) if row[13] is not None else None,
        last_node_version=str(row[14]) if row[14] is not None else None,
        last_configuration_digest=str(row[15]) if row[15] is not None else None,
        last_mission_id=str(row[16]) if row[16] is not None else None,
        desired_configuration_generation=int(str(row[17])) if row[17] is not None else None,
        desired_configuration_digest=str(row[18]) if row[18] is not None else None,
        acknowledged_configuration_generation=(
            int(str(row[19])) if row[19] is not None else None
        ),
        acknowledged_configuration_digest=str(row[20]) if row[20] is not None else None,
        configuration_acknowledged_at=str(row[21]) if row[21] is not None else None,
        configuration_acknowledgment_status=str(row[22]) if row[22] is not None else None,
        acknowledged_configuration_signing_key_id=(
            str(row[23]) if row[23] is not None else None
        ),
        acknowledged_active_configuration_signing_key_id=(
            str(row[24]) if row[24] is not None else None
        ),
    )


def _identity_rotation_record(row: tuple[object, ...]) -> NodeIdentityRotationRecord:
    return NodeIdentityRotationRecord(
        rotation_id=str(row[0]),
        node_id=str(row[1]),
        principal_id=str(row[2]),
        workspace_id=str(row[3]),
        current_key_id=str(row[4]),
        challenge_digest=str(row[5]),
        created_at=str(row[6]),
        expires_at=str(row[7]),
        status=str(row[8]),
        evidence_status=str(row[9]),
        next_key_id=str(row[10]) if row[10] is not None else None,
        activated_at=str(row[11]) if row[11] is not None else None,
    )


def _safe_label(value: str) -> str:
    if not _LABEL_PATTERN.fullmatch(value) or ".." in value:
        raise ValueError("unsafe label")
    if any(ord(character) < 32 for character in value):
        raise ValueError("control characters are not allowed")
    return value


def _decode_public_key(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid Ed25519 public key") from exc
    if len(decoded) != 32:
        raise ValueError("invalid Ed25519 public key")
    Ed25519PublicKey.from_public_bytes(decoded)
    return decoded


def _verify_signature(public_key: str, signature: str, message: bytes) -> None:
    try:
        signature_bytes = base64.b64decode(signature, validate=True)
        key = Ed25519PublicKey.from_public_bytes(_decode_public_key(public_key))
        key.verify(signature_bytes, message)
    except (binascii.Error, ValueError, InvalidSignature) as exc:
        raise NodeAuthenticationError("invalid Node signature") from exc


def _secret_digest(secret: str) -> str:
    return f"sha256:{sha256(secret.encode()).hexdigest()}"


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NodeError("stored Node timestamp is not timezone-aware")
    return parsed


def _observed_state(
    *,
    status: str,
    evidence_status: str,
    last_seen_at: str | None,
    now: datetime,
    stale_after_seconds: int,
) -> str:
    if evidence_status != _EVIDENCE_COMPLETE:
        return "evidence_incomplete"
    if status == _REVOKED_STATUS:
        return "revoked"
    if last_seen_at is None:
        return "never_observed"
    age = now - _parse_datetime(last_seen_at)
    return "observed_connected" if age <= timedelta(seconds=stale_after_seconds) else "stale"


def _ensure_column(
    connection: sqlite3.Connection,
    *,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
