"""Signed desired-configuration generations for local-preview Ithildin Nodes."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from ithildin_schemas.models import SHA256_PATTERN, StrictBaseModel
from pydantic import Field, field_validator

CONFIGURATION_SIGNATURE_CONTEXT = "ITHILDIN-NODE-CONFIG-V1"
CONFIGURATION_SIGNATURE_TYPE = "ithildin.node_configuration"
CONFIGURATION_FORMAT_VERSION = "1"
CONFIGURATION_ALGORITHM = "ed25519"
CONFIGURATION_ACK_STATUS = "stored_not_enforced"
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")
_EVIDENCE_PENDING = "pending"
_EVIDENCE_COMPLETE = "complete"


class NodeConfigurationError(RuntimeError):
    """Raised when signed Node configuration cannot proceed safely."""


class NodeConfigurationNotFoundError(NodeConfigurationError):
    """Raised when a desired configuration does not exist."""


class NodeConfigurationConflictError(NodeConfigurationError):
    """Raised when desired or acknowledged configuration state conflicts."""


class NodeConfigurationSigningError(NodeConfigurationError):
    """Raised when the configuration signing trust root is unavailable or invalid."""


class NodeConfigurationVerificationError(NodeConfigurationError):
    """Raised when a signed configuration bundle fails closed verification."""


class NodeConfigurationAssignmentPayload(StrictBaseModel):
    minimum_node_version: str = Field(min_length=1, max_length=128)
    heartbeat_interval_seconds: int = Field(default=30, ge=15, le=300)
    offline_posture: Literal["deny_governed_actions"] = "deny_governed_actions"
    evidence_buffer_max_events: int = Field(default=1000, ge=100, le=10_000)
    validity_seconds: int = Field(default=3600, ge=300, le=86_400)

    @field_validator("minimum_node_version")
    @classmethod
    def _safe_version(cls, value: str) -> str:
        if not _SAFE_LABEL.fullmatch(value) or ".." in value:
            raise ValueError("unsafe Node version")
        return value

    def configuration(
        self,
        *,
        policy_version: str,
        policy_digest: str,
        manifest_lock_digest: str,
    ) -> JsonObject:
        return {
            "schema_version": "1",
            "policy_version": policy_version,
            "policy_digest": policy_digest,
            "manifest_lock_digest": manifest_lock_digest,
            "minimum_node_version": self.minimum_node_version,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "offline_posture": self.offline_posture,
            "evidence_buffer_max_events": self.evidence_buffer_max_events,
            "enforcement_status": CONFIGURATION_ACK_STATUS,
        }


class NodeConfigurationRequestPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    known_generation: int | None = Field(default=None, ge=0)

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json", exclude_none=True))


class NodeConfigurationAcknowledgmentPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    generation: int = Field(ge=1)
    configuration_digest: str = Field(pattern=SHA256_PATTERN)
    status: Literal["stored_not_enforced"]

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json"))


@dataclass(frozen=True)
class NodeConfigurationTrust:
    key_id: str
    public_key: str

    def summary(self) -> JsonObject:
        return {
            "algorithm": CONFIGURATION_ALGORITHM,
            "key_id": self.key_id,
            "public_key": self.public_key,
            "signature_context": CONFIGURATION_SIGNATURE_CONTEXT,
        }


@dataclass(frozen=True)
class NodeConfigurationSigner:
    private_key: Ed25519PrivateKey
    trust: NodeConfigurationTrust

    @classmethod
    def load(cls, private_key_path: Path, public_key_path: Path) -> NodeConfigurationSigner:
        private_key = _load_private_key(private_key_path)
        public_key = _load_public_key(public_key_path)
        derived = private_key.public_key()
        if _public_key_raw(derived) != _public_key_raw(public_key):
            raise NodeConfigurationSigningError("Node configuration signing keys do not match")
        return cls(private_key=private_key, trust=_trust(derived))

    def sign(self, envelope: JsonObject) -> JsonObject:
        signature = self.private_key.sign(_signature_message(envelope))
        return {
            **envelope,
            "signature": {
                "algorithm": CONFIGURATION_ALGORITHM,
                "key_id": self.trust.key_id,
                "signature": base64.b64encode(signature).decode("ascii"),
            },
        }


@dataclass(frozen=True)
class NodeConfigurationRecord:
    configuration_id: str
    node_id: str
    generation: int
    configuration_digest: str
    bundle: JsonObject
    issued_at: str
    expires_at: str
    evidence_status: str

    def summary(self, *, include_bundle: bool = False) -> JsonObject:
        result: JsonObject = {
            "configuration_id": self.configuration_id,
            "node_id": self.node_id,
            "generation": self.generation,
            "configuration_digest": self.configuration_digest,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "evidence_status": self.evidence_status,
        }
        if include_bundle:
            result["bundle"] = self.bundle
        return result


class NodeConfigurationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS node_configurations (
                    configuration_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    configuration_digest TEXT NOT NULL,
                    bundle_json TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    evidence_status TEXT NOT NULL,
                    UNIQUE (node_id, generation)
                );
                CREATE INDEX IF NOT EXISTS idx_node_configurations_node_generation
                    ON node_configurations(node_id, generation DESC);
                """
            )
            for column, definition in (
                ("desired_configuration_generation", "INTEGER"),
                ("desired_configuration_digest", "TEXT"),
                ("acknowledged_configuration_generation", "INTEGER"),
                ("acknowledged_configuration_digest", "TEXT"),
                ("configuration_acknowledged_at", "TEXT"),
                ("configuration_acknowledgment_status", "TEXT"),
            ):
                _ensure_column(connection, "nodes", column, definition)
            connection.commit()

    def assign(
        self,
        *,
        node_id: str,
        payload: NodeConfigurationAssignmentPayload,
        signer: NodeConfigurationSigner,
        policy_version: str,
        policy_digest: str,
        manifest_lock_digest: str,
        now: datetime | None = None,
    ) -> NodeConfigurationRecord:
        effective_now = now or datetime.now(UTC)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            node = connection.execute(
                """
                SELECT principal_id, workspace_id, status, evidence_status
                FROM nodes WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
            if node is None:
                raise NodeConfigurationNotFoundError("unknown Node")
            if str(node[2]) != "enrolled":
                raise NodeConfigurationConflictError("Node is revoked")
            if str(node[3]) != _EVIDENCE_COMPLETE:
                raise NodeConfigurationConflictError("Node evidence is incomplete")
            previous = connection.execute(
                "SELECT COALESCE(MAX(generation), 0) FROM node_configurations WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            generation = int(previous[0]) + 1
            configuration_id = f"ncfg_{uuid4().hex}"
            issued_at = effective_now.isoformat()
            expires_at = (effective_now + timedelta(seconds=payload.validity_seconds)).isoformat()
            configuration = payload.configuration(
                policy_version=policy_version,
                policy_digest=policy_digest,
                manifest_lock_digest=manifest_lock_digest,
            )
            configuration_digest = sha256_digest(configuration)
            envelope: JsonObject = {
                "signature_type": CONFIGURATION_SIGNATURE_TYPE,
                "format_version": CONFIGURATION_FORMAT_VERSION,
                "configuration_id": configuration_id,
                "generation": generation,
                "node_id": node_id,
                "principal_id": str(node[0]),
                "workspace_id": str(node[1]),
                "issued_at": issued_at,
                "not_before": issued_at,
                "expires_at": expires_at,
                "configuration_digest": configuration_digest,
                "configuration": configuration,
            }
            bundle = signer.sign(envelope)
            connection.execute(
                """
                INSERT INTO node_configurations (
                    configuration_id, node_id, generation, configuration_digest, bundle_json,
                    issued_at, expires_at, evidence_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    configuration_id,
                    node_id,
                    generation,
                    configuration_digest,
                    canonical_json(bundle),
                    issued_at,
                    expires_at,
                    _EVIDENCE_PENDING,
                ),
            )
            connection.execute(
                """
                UPDATE nodes
                SET desired_configuration_generation = ?, desired_configuration_digest = ?,
                    updated_at = ?
                WHERE node_id = ?
                """,
                (generation, configuration_digest, issued_at, node_id),
            )
            connection.commit()
        return self.get(node_id, generation)

    def mark_assignment_evidence_complete(
        self, node_id: str, generation: int
    ) -> NodeConfigurationRecord:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE node_configurations SET evidence_status = ?
                WHERE node_id = ? AND generation = ? AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, node_id, generation, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConfigurationConflictError("configuration evidence state changed")
            connection.commit()
        return self.get(node_id, generation)

    def desired(self, node_id: str, *, now: datetime | None = None) -> NodeConfigurationRecord:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT c.configuration_id, c.node_id, c.generation, c.configuration_digest,
                       c.bundle_json, c.issued_at, c.expires_at, c.evidence_status
                FROM node_configurations c
                JOIN nodes n ON n.node_id = c.node_id
                WHERE c.node_id = ? AND c.generation = n.desired_configuration_generation
                """,
                (node_id,),
            ).fetchone()
        if row is None:
            raise NodeConfigurationNotFoundError("Node has no desired configuration")
        record = _record(row)
        if record.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeConfigurationConflictError("configuration evidence is incomplete")
        if _parse_datetime(record.expires_at) <= (now or datetime.now(UTC)):
            raise NodeConfigurationConflictError("desired configuration expired")
        return record

    def get(self, node_id: str, generation: int) -> NodeConfigurationRecord:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT configuration_id, node_id, generation, configuration_digest, bundle_json,
                       issued_at, expires_at, evidence_status
                FROM node_configurations WHERE node_id = ? AND generation = ?
                """,
                (node_id, generation),
            ).fetchone()
        if row is None:
            raise NodeConfigurationNotFoundError("unknown Node configuration")
        return _record(row)

    def acknowledge_pending(
        self,
        *,
        node_id: str,
        payload: NodeConfigurationAcknowledgmentPayload,
        now: datetime | None = None,
    ) -> None:
        effective_now = now or datetime.now(UTC)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, evidence_status, desired_configuration_generation,
                       desired_configuration_digest
                FROM nodes WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
            if row is None:
                raise NodeConfigurationNotFoundError("unknown Node")
            if str(row[0]) != "enrolled":
                raise NodeConfigurationConflictError("Node is revoked")
            if str(row[1]) != _EVIDENCE_COMPLETE:
                raise NodeConfigurationConflictError("Node evidence is incomplete")
            if row[2] != payload.generation or row[3] != payload.configuration_digest:
                raise NodeConfigurationConflictError("configuration acknowledgment is not current")
            config = connection.execute(
                """
                SELECT evidence_status, expires_at FROM node_configurations
                WHERE node_id = ? AND generation = ? AND configuration_digest = ?
                """,
                (node_id, payload.generation, payload.configuration_digest),
            ).fetchone()
            if config is None or str(config[0]) != _EVIDENCE_COMPLETE:
                raise NodeConfigurationConflictError("configuration evidence is incomplete")
            if _parse_datetime(str(config[1])) <= effective_now:
                raise NodeConfigurationConflictError("configuration acknowledgment expired")
            connection.execute(
                """
                UPDATE nodes SET evidence_status = ?, acknowledged_configuration_generation = ?,
                    acknowledged_configuration_digest = ?, configuration_acknowledged_at = ?,
                    configuration_acknowledgment_status = ?, updated_at = ?
                WHERE node_id = ?
                """,
                (
                    _EVIDENCE_PENDING,
                    payload.generation,
                    payload.configuration_digest,
                    effective_now.isoformat(),
                    payload.status,
                    effective_now.isoformat(),
                    node_id,
                ),
            )
            connection.commit()


def configuration_state(
    *,
    node_status: str,
    node_evidence_status: str,
    desired_generation: int | None,
    desired_digest: str | None,
    acknowledged_generation: int | None,
    acknowledged_digest: str | None,
    acknowledgment_status: str | None,
) -> str:
    if node_status == "revoked":
        return "revoked"
    if node_evidence_status != _EVIDENCE_COMPLETE:
        return "evidence_incomplete"
    if desired_generation is None or desired_digest is None:
        return "unassigned"
    if acknowledged_generation is None or acknowledged_digest is None:
        return "awaiting_node_storage"
    if (
        acknowledged_generation == desired_generation
        and acknowledged_digest == desired_digest
        and acknowledgment_status == CONFIGURATION_ACK_STATUS
    ):
        return "stored_current_not_enforced"
    return "configuration_drift"


def verify_configuration_bundle(
    bundle: JsonObject,
    *,
    trust: NodeConfigurationTrust,
    node_id: str,
    principal_id: str,
    workspace_id: str,
    minimum_generation: int,
    expected_manifest_lock_digest: str | None = None,
    now: datetime | None = None,
) -> JsonObject:
    try:
        signature = _object(bundle.get("signature"), "signature")
        if signature.get("algorithm") != CONFIGURATION_ALGORITHM:
            raise NodeConfigurationVerificationError("unsupported configuration signature")
        if signature.get("key_id") != trust.key_id:
            raise NodeConfigurationVerificationError("configuration signing key mismatch")
        signature_bytes = base64.b64decode(
            _string(signature.get("signature"), "signature.signature"), validate=True
        )
        unsigned = {key: value for key, value in bundle.items() if key != "signature"}
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(trust.public_key, validate=True)
        )
        public_key.verify(signature_bytes, _signature_message(unsigned))
    except NodeConfigurationVerificationError:
        raise
    except (binascii.Error, ValueError, InvalidSignature) as exc:
        raise NodeConfigurationVerificationError("invalid configuration signature") from exc

    _expect(bundle, "signature_type", CONFIGURATION_SIGNATURE_TYPE)
    _expect(bundle, "format_version", CONFIGURATION_FORMAT_VERSION)
    _expect(bundle, "node_id", node_id)
    _expect(bundle, "principal_id", principal_id)
    _expect(bundle, "workspace_id", workspace_id)
    generation = _integer(bundle.get("generation"), "generation")
    if generation < minimum_generation:
        raise NodeConfigurationVerificationError("configuration generation regressed")
    effective_now = now or datetime.now(UTC)
    if effective_now < _parse_datetime(_string(bundle.get("not_before"), "not_before")):
        raise NodeConfigurationVerificationError("configuration is not active yet")
    if effective_now >= _parse_datetime(_string(bundle.get("expires_at"), "expires_at")):
        raise NodeConfigurationVerificationError("configuration expired")
    configuration = _object(bundle.get("configuration"), "configuration")
    digest = _string(bundle.get("configuration_digest"), "configuration_digest")
    if sha256_digest(configuration) != digest:
        raise NodeConfigurationVerificationError("configuration digest mismatch")
    if configuration.get("enforcement_status") != CONFIGURATION_ACK_STATUS:
        raise NodeConfigurationVerificationError("configuration enforcement status is invalid")
    if expected_manifest_lock_digest is not None:
        if configuration.get("manifest_lock_digest") != expected_manifest_lock_digest:
            raise NodeConfigurationVerificationError("manifest-lock digest mismatch")
    return bundle


def generate_node_configuration_signing_keypair(
    private_key_path: Path, public_key_path: Path
) -> NodeConfigurationTrust:
    if private_key_path.exists() or public_key_path.exists():
        raise NodeConfigurationSigningError("Node configuration signing key already exists")
    private_key = Ed25519PrivateKey.generate()
    _write_new(
        private_key_path,
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        0o600,
    )
    _write_new(
        public_key_path,
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
        0o644,
    )
    return _trust(private_key.public_key())


def _record(row: tuple[object, ...]) -> NodeConfigurationRecord:
    bundle = json.loads(str(row[4]))
    if not isinstance(bundle, dict):
        raise NodeConfigurationError("stored configuration bundle is invalid")
    return NodeConfigurationRecord(
        configuration_id=str(row[0]),
        node_id=str(row[1]),
        generation=int(str(row[2])),
        configuration_digest=str(row[3]),
        bundle=cast(JsonObject, bundle),
        issued_at=str(row[5]),
        expires_at=str(row[6]),
        evidence_status=str(row[7]),
    )


def _signature_message(envelope: JsonObject) -> bytes:
    return f"{CONFIGURATION_SIGNATURE_CONTEXT}\n{canonical_json(envelope)}".encode()


def _trust(public_key: Ed25519PublicKey) -> NodeConfigurationTrust:
    raw = _public_key_raw(public_key)
    encoded = base64.b64encode(raw).decode("ascii")
    return NodeConfigurationTrust(key_id=sha256_digest(encoded), public_key=encoded)


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(_read_secure(path, 0o077), password=None)
    except (TypeError, ValueError) as exc:
        raise NodeConfigurationSigningError("configuration private key is invalid") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise NodeConfigurationSigningError("configuration private key must be Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(_read_secure(path, 0o022))
    except (TypeError, ValueError) as exc:
        raise NodeConfigurationSigningError("configuration public key is invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise NodeConfigurationSigningError("configuration public key must be Ed25519")
    return key


def _read_secure(path: Path, forbidden_mode: int) -> bytes:
    flags = os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise NodeConfigurationSigningError("configuration signing key is unavailable") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or stat.S_IMODE(status.st_mode) & forbidden_mode:
            raise NodeConfigurationSigningError("configuration signing key permissions are unsafe")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_new(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise NodeConfigurationSigningError("failed to write configuration signing key") from exc


def _public_key_raw(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise NodeConfigurationVerificationError("invalid configuration timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise NodeConfigurationVerificationError("configuration timestamp is not timezone-aware")
    return parsed


def _object(value: object, field: str) -> JsonObject:
    if not isinstance(value, dict):
        raise NodeConfigurationVerificationError(f"{field} must be an object")
    return cast(JsonObject, value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise NodeConfigurationVerificationError(f"{field} must be a string")
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise NodeConfigurationVerificationError(f"{field} must be an integer")
    return value


def _expect(document: JsonObject, field: str, expected: str) -> None:
    if document.get(field) != expected:
        raise NodeConfigurationVerificationError(f"configuration {field} mismatch")


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
