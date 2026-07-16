"""Local-preview Ithildin Node enrollment and signed heartbeat state."""

from __future__ import annotations

import base64
import binascii
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

NODE_PROTOCOL_VERSION = "1"
NODE_SIGNATURE_CONTEXT = "ITHILDIN-NODE-V1"
NODE_PRINCIPAL_PREFIX = "agent:node."
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")
_DISPLAY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.,:@()-]{0,127}$")
_NODE_ID_PATTERN = re.compile(r"^node_[0-9a-f]{32}$")
_NONCE_PATTERN = re.compile(r"^[0-9a-f]{32,128}$")
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

    @field_validator("node_version", "runner_adapter")
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

    @field_validator("node_version", "runner_adapter", "mission_id")
    @classmethod
    def _safe_labels(cls, value: str | None) -> str | None:
        return _safe_label(value) if value is not None else None

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json", exclude_none=True))


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
    last_configuration_digest: str | None
    last_mission_id: str | None

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
            "last_configuration_digest": self.last_configuration_digest,
            "last_mission_id": self.last_mission_id,
            "identity_source": "gateway_derived",
            "connectivity_source": "gateway_accepted_heartbeat",
            "runner_health_known": False,
            "model_health_known": False,
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
                    last_configuration_digest TEXT,
                    last_mission_id TEXT
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
                """
            )
            _ensure_column(
                connection,
                table="node_enrollment_codes",
                column="evidence_status",
                definition="TEXT NOT NULL DEFAULT 'complete'",
            )
            _ensure_column(
                connection,
                table="nodes",
                column="evidence_status",
                definition="TEXT NOT NULL DEFAULT 'complete'",
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
                       revoked_at, last_heartbeat_hash, last_configuration_digest, last_mission_id
                FROM nodes WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
        if row is None:
            raise NodeNotFoundError("unknown Node")
        return _record(row)

    def list(self, *, limit: int = 50, stale_after_seconds: int = 90) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT node_id, principal_id, workspace_id, display_name, status, evidence_status,
                       public_key,
                       descriptor_hash, descriptor_json, enrolled_at, updated_at, last_seen_at,
                       revoked_at, last_heartbeat_hash, last_configuration_digest, last_mission_id
                FROM nodes ORDER BY updated_at DESC LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [
            _record(row).summary(stale_after_seconds=stale_after_seconds) for row in rows
        ]

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
                    last_configuration_digest = ?, last_mission_id = ?
                WHERE node_id = ?
                """,
                (
                    _EVIDENCE_PENDING,
                    effective_now.isoformat(),
                    effective_now.isoformat(),
                    heartbeat_hash,
                    payload.configuration_digest,
                    payload.mission_id,
                    node_id,
                ),
            )
            connection.commit()
        return self.get(node_id)


def canonical_signature_message(
    *, method: str, path: str, timestamp: str, nonce: str, body_hash: str
) -> bytes:
    return (
        f"{NODE_SIGNATURE_CONTEXT}\n{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
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
        last_configuration_digest=str(row[14]) if row[14] is not None else None,
        last_mission_id=str(row[15]) if row[15] is not None else None,
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
