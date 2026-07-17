"""Signed per-Node configuration trust transitions for bounded signer rotation."""

from __future__ import annotations

import base64
import binascii
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from ithildin_schemas.models import SHA256_PATTERN, StrictBaseModel
from pydantic import Field

from ithildin_api.node_configuration import NodeConfigurationSigner, NodeConfigurationTrust

TRUST_TRANSITION_SIGNATURE_CONTEXT = "ITHILDIN-NODE-CONFIG-TRUST-V1"
TRUST_TRANSITION_SIGNATURE_TYPE = "ithildin.node_configuration_trust_transition"
TRUST_TRANSITION_FORMAT_VERSION = "1"
TRUST_TRANSITION_ACK_STATUS = "staged_not_active"
_EVIDENCE_PENDING = "pending"
_EVIDENCE_COMPLETE = "complete"
_TRANSITION_ID = re.compile(r"^nct_[0-9a-f]{32}$")


class NodeConfigurationTrustTransitionError(RuntimeError):
    """Raised when configuration trust transition cannot proceed safely."""


class NodeConfigurationTrustTransitionNotFoundError(NodeConfigurationTrustTransitionError):
    """Raised when a transition or target Node is absent."""


class NodeConfigurationTrustTransitionConflictError(NodeConfigurationTrustTransitionError):
    """Raised when transition state conflicts with the requested operation."""


class NodeConfigurationTrustTransitionVerificationError(NodeConfigurationTrustTransitionError):
    """Raised when a signed trust transition fails verification."""


class NodeConfigurationTrustTransitionAssignmentPayload(StrictBaseModel):
    expected_current_key_id: str = Field(pattern=SHA256_PATTERN)
    next_public_key: str = Field(min_length=1, max_length=256)
    validity_seconds: int = Field(default=86_400, ge=600, le=604_800)


class NodeConfigurationTrustTransitionRequestPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    known_transition_id: str | None = Field(default=None, pattern=r"^nct_[0-9a-f]{32}$")

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json", exclude_none=True))


class NodeConfigurationTrustTransitionAcknowledgmentPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    transition_id: str = Field(pattern=r"^nct_[0-9a-f]{32}$")
    transition_digest: str = Field(pattern=SHA256_PATTERN)
    status: Literal["staged_not_active"]

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json"))


@dataclass(frozen=True)
class NodeConfigurationTrustTransitionRecord:
    transition_id: str
    node_id: str
    transition_digest: str
    current_key_id: str
    next_key_id: str
    next_public_key: str
    bundle: JsonObject
    issued_at: str
    expires_at: str
    evidence_status: str
    acknowledgment_status: str | None
    acknowledgment_evidence_status: str | None
    acknowledged_at: str | None

    def summary(self, *, include_bundle: bool = False) -> JsonObject:
        result: JsonObject = {
            "transition_id": self.transition_id,
            "node_id": self.node_id,
            "transition_digest": self.transition_digest,
            "current_key_id": self.current_key_id,
            "next_key_id": self.next_key_id,
            "next_public_key": self.next_public_key,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "evidence_status": self.evidence_status,
            "acknowledgment_status": self.acknowledgment_status,
            "acknowledgment_evidence_status": self.acknowledgment_evidence_status,
            "acknowledged_at": self.acknowledged_at,
            "activation_proven": False,
        }
        if include_bundle:
            result["bundle"] = self.bundle
        return result


class NodeConfigurationTrustTransitionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS node_configuration_trust_transitions (
                    transition_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    transition_digest TEXT NOT NULL,
                    current_key_id TEXT NOT NULL,
                    next_key_id TEXT NOT NULL,
                    next_public_key TEXT NOT NULL,
                    bundle_json TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    evidence_status TEXT NOT NULL,
                    acknowledgment_status TEXT,
                    acknowledgment_evidence_status TEXT,
                    acknowledged_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_node_configuration_trust_transition_node
                    ON node_configuration_trust_transitions(node_id, issued_at DESC);
                """
            )
            connection.commit()

    def assign(
        self,
        *,
        node_id: str,
        payload: NodeConfigurationTrustTransitionAssignmentPayload,
        signer: NodeConfigurationSigner,
        now: datetime | None = None,
    ) -> NodeConfigurationTrustTransitionRecord:
        effective_now = now or datetime.now(UTC)
        next_trust = configuration_trust_from_public_key(payload.next_public_key)
        if signer.trust.key_id != payload.expected_current_key_id:
            raise NodeConfigurationTrustTransitionConflictError(
                "Gateway configuration signing key changed"
            )
        if next_trust.key_id == signer.trust.key_id:
            raise NodeConfigurationTrustTransitionConflictError(
                "next configuration signing key must differ from current"
            )
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
                raise NodeConfigurationTrustTransitionNotFoundError("unknown Node")
            if str(node[2]) != "enrolled":
                raise NodeConfigurationTrustTransitionConflictError("Node is revoked")
            if str(node[3]) != _EVIDENCE_COMPLETE:
                raise NodeConfigurationTrustTransitionConflictError("Node evidence is incomplete")
            latest = connection.execute(
                """
                SELECT expires_at FROM node_configuration_trust_transitions
                WHERE node_id = ? ORDER BY issued_at DESC LIMIT 1
                """,
                (node_id,),
            ).fetchone()
            if latest is not None and _parse_datetime(str(latest[0])) > effective_now:
                raise NodeConfigurationTrustTransitionConflictError(
                    "Node already has an active trust transition"
                )
            transition_id = f"nct_{uuid4().hex}"
            issued_at = effective_now.isoformat()
            expires_at = (effective_now + timedelta(seconds=payload.validity_seconds)).isoformat()
            transition: JsonObject = {
                "schema_version": "1",
                "current_key_id": signer.trust.key_id,
                "next_trust": next_trust.summary(),
                "activation_mode": "explicit_gateway_restart",
                "acknowledgment_status": TRUST_TRANSITION_ACK_STATUS,
            }
            transition_digest = sha256_digest(transition)
            unsigned: JsonObject = {
                "signature_type": TRUST_TRANSITION_SIGNATURE_TYPE,
                "format_version": TRUST_TRANSITION_FORMAT_VERSION,
                "transition_id": transition_id,
                "node_id": node_id,
                "principal_id": str(node[0]),
                "workspace_id": str(node[1]),
                "issued_at": issued_at,
                "not_before": issued_at,
                "expires_at": expires_at,
                "transition_digest": transition_digest,
                "transition": transition,
            }
            signature = signer.private_key.sign(_signature_message(unsigned))
            bundle: JsonObject = {
                **unsigned,
                "signature": {
                    "algorithm": "ed25519",
                    "key_id": signer.trust.key_id,
                    "signature": base64.b64encode(signature).decode("ascii"),
                },
            }
            connection.execute(
                """
                INSERT INTO node_configuration_trust_transitions (
                    transition_id, node_id, transition_digest, current_key_id, next_key_id,
                    next_public_key, bundle_json, issued_at, expires_at, evidence_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transition_id,
                    node_id,
                    transition_digest,
                    signer.trust.key_id,
                    next_trust.key_id,
                    next_trust.public_key,
                    canonical_json(bundle),
                    issued_at,
                    expires_at,
                    _EVIDENCE_PENDING,
                ),
            )
            connection.commit()
        return self.get(node_id, transition_id)

    def mark_assignment_evidence_complete(
        self, node_id: str, transition_id: str
    ) -> NodeConfigurationTrustTransitionRecord:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE node_configuration_trust_transitions SET evidence_status = ?
                WHERE node_id = ? AND transition_id = ? AND evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, node_id, transition_id, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConfigurationTrustTransitionConflictError(
                    "trust transition evidence state changed"
                )
            connection.commit()
        return self.get(node_id, transition_id)

    def desired(
        self, node_id: str, *, now: datetime | None = None
    ) -> NodeConfigurationTrustTransitionRecord:
        records = self.list(node_id, limit=1)
        if not records:
            raise NodeConfigurationTrustTransitionNotFoundError(
                "Node has no configuration trust transition"
            )
        record = records[0]
        if record.evidence_status != _EVIDENCE_COMPLETE:
            raise NodeConfigurationTrustTransitionConflictError(
                "trust transition evidence is incomplete"
            )
        if _parse_datetime(record.expires_at) <= (now or datetime.now(UTC)):
            raise NodeConfigurationTrustTransitionConflictError("trust transition expired")
        return record

    def acknowledge_pending(
        self,
        *,
        node_id: str,
        payload: NodeConfigurationTrustTransitionAcknowledgmentPayload,
        now: datetime | None = None,
    ) -> None:
        effective_now = now or datetime.now(UTC)
        desired = self.desired(node_id, now=effective_now)
        if (
            desired.transition_id != payload.transition_id
            or desired.transition_digest != payload.transition_digest
        ):
            raise NodeConfigurationTrustTransitionConflictError(
                "trust transition acknowledgment is not current"
            )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            node = connection.execute(
                "SELECT status, evidence_status FROM nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
            if node is None:
                raise NodeConfigurationTrustTransitionNotFoundError("unknown Node")
            if str(node[0]) != "enrolled":
                raise NodeConfigurationTrustTransitionConflictError("Node is revoked")
            if str(node[1]) != _EVIDENCE_COMPLETE:
                raise NodeConfigurationTrustTransitionConflictError("Node evidence is incomplete")
            updated = connection.execute(
                """
                UPDATE node_configuration_trust_transitions
                SET acknowledgment_status = ?, acknowledgment_evidence_status = ?,
                    acknowledged_at = ?
                WHERE node_id = ? AND transition_id = ?
                  AND acknowledgment_status IS NULL
                  AND acknowledgment_evidence_status IS NULL
                """,
                (
                    payload.status,
                    _EVIDENCE_PENDING,
                    effective_now.isoformat(),
                    node_id,
                    payload.transition_id,
                ),
            )
            if updated.rowcount != 1:
                raise NodeConfigurationTrustTransitionConflictError(
                    "trust transition acknowledgment state changed"
                )
            connection.commit()

    def mark_acknowledgment_evidence_complete(
        self, node_id: str, transition_id: str
    ) -> NodeConfigurationTrustTransitionRecord:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE node_configuration_trust_transitions
                SET acknowledgment_evidence_status = ?
                WHERE node_id = ? AND transition_id = ?
                  AND acknowledgment_evidence_status = ?
                """,
                (_EVIDENCE_COMPLETE, node_id, transition_id, _EVIDENCE_PENDING),
            )
            if updated.rowcount != 1:
                raise NodeConfigurationTrustTransitionConflictError(
                    "trust transition acknowledgment evidence state changed"
                )
            connection.commit()
        return self.get(node_id, transition_id)

    def get(self, node_id: str, transition_id: str) -> NodeConfigurationTrustTransitionRecord:
        if not _TRANSITION_ID.fullmatch(transition_id):
            raise NodeConfigurationTrustTransitionNotFoundError("unknown trust transition")
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT transition_id, node_id, transition_digest, current_key_id, next_key_id,
                       next_public_key, bundle_json, issued_at, expires_at, evidence_status,
                       acknowledgment_status, acknowledgment_evidence_status, acknowledged_at
                FROM node_configuration_trust_transitions
                WHERE node_id = ? AND transition_id = ?
                """,
                (node_id, transition_id),
            ).fetchone()
        if row is None:
            raise NodeConfigurationTrustTransitionNotFoundError("unknown trust transition")
        return _record(row)

    def list(
        self, node_id: str, *, limit: int = 20
    ) -> list[NodeConfigurationTrustTransitionRecord]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT transition_id, node_id, transition_digest, current_key_id, next_key_id,
                       next_public_key, bundle_json, issued_at, expires_at, evidence_status,
                       acknowledgment_status, acknowledgment_evidence_status, acknowledged_at
                FROM node_configuration_trust_transitions WHERE node_id = ?
                ORDER BY issued_at DESC LIMIT ?
                """,
                (node_id, max(1, min(limit, 100))),
            ).fetchall()
        return [_record(row) for row in rows]


def configuration_trust_from_public_key(public_key: str) -> NodeConfigurationTrust:
    try:
        raw = base64.b64decode(public_key, validate=True)
        if len(raw) != 32:
            raise ValueError
        Ed25519PublicKey.from_public_bytes(raw)
    except (binascii.Error, ValueError) as exc:
        raise NodeConfigurationTrustTransitionVerificationError(
            "configuration trust public key is invalid"
        ) from exc
    return NodeConfigurationTrust(key_id=sha256_digest(public_key), public_key=public_key)


def verify_configuration_trust_transition(
    bundle: JsonObject,
    *,
    current_trust: NodeConfigurationTrust,
    node_id: str,
    principal_id: str,
    workspace_id: str,
    now: datetime | None = None,
) -> JsonObject:
    expected_envelope_keys = {
        "signature_type",
        "format_version",
        "transition_id",
        "node_id",
        "principal_id",
        "workspace_id",
        "issued_at",
        "not_before",
        "expires_at",
        "transition_digest",
        "transition",
        "signature",
    }
    if set(bundle) != expected_envelope_keys:
        raise NodeConfigurationTrustTransitionVerificationError(
            "trust transition envelope is invalid"
        )
    try:
        signature = _object(bundle.get("signature"), "signature")
        if set(signature) != {"algorithm", "key_id", "signature"}:
            raise NodeConfigurationTrustTransitionVerificationError(
                "trust transition signature envelope is invalid"
            )
        if signature.get("algorithm") != "ed25519":
            raise NodeConfigurationTrustTransitionVerificationError(
                "unsupported trust transition signature"
            )
        if signature.get("key_id") != current_trust.key_id:
            raise NodeConfigurationTrustTransitionVerificationError(
                "trust transition current key mismatch"
            )
        signature_bytes = base64.b64decode(
            _string(signature.get("signature"), "signature.signature"), validate=True
        )
        unsigned = {key: value for key, value in bundle.items() if key != "signature"}
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(current_trust.public_key, validate=True)
        )
        public_key.verify(signature_bytes, _signature_message(unsigned))
    except NodeConfigurationTrustTransitionVerificationError:
        raise
    except (binascii.Error, ValueError, InvalidSignature) as exc:
        raise NodeConfigurationTrustTransitionVerificationError(
            "invalid trust transition signature"
        ) from exc

    _expect(bundle, "signature_type", TRUST_TRANSITION_SIGNATURE_TYPE)
    _expect(bundle, "format_version", TRUST_TRANSITION_FORMAT_VERSION)
    _expect(bundle, "node_id", node_id)
    _expect(bundle, "principal_id", principal_id)
    _expect(bundle, "workspace_id", workspace_id)
    transition_id = _string(bundle.get("transition_id"), "transition_id")
    if not _TRANSITION_ID.fullmatch(transition_id):
        raise NodeConfigurationTrustTransitionVerificationError("invalid trust transition ID")
    effective_now = now or datetime.now(UTC)
    issued_at = _parse_datetime(_string(bundle.get("issued_at"), "issued_at"))
    not_before = _parse_datetime(_string(bundle.get("not_before"), "not_before"))
    expires_at = _parse_datetime(_string(bundle.get("expires_at"), "expires_at"))
    if issued_at != not_before or expires_at <= not_before:
        raise NodeConfigurationTrustTransitionVerificationError(
            "trust transition validity window is invalid"
        )
    if effective_now < not_before:
        raise NodeConfigurationTrustTransitionVerificationError("trust transition is not active")
    if effective_now >= expires_at:
        raise NodeConfigurationTrustTransitionVerificationError("trust transition expired")
    transition = _object(bundle.get("transition"), "transition")
    if sha256_digest(transition) != _string(bundle.get("transition_digest"), "transition_digest"):
        raise NodeConfigurationTrustTransitionVerificationError("trust transition digest mismatch")
    expected_keys = {
        "schema_version",
        "current_key_id",
        "next_trust",
        "activation_mode",
        "acknowledgment_status",
    }
    if set(transition) != expected_keys:
        raise NodeConfigurationTrustTransitionVerificationError(
            "trust transition payload is invalid"
        )
    _expect(transition, "schema_version", "1")
    _expect(transition, "current_key_id", current_trust.key_id)
    _expect(transition, "activation_mode", "explicit_gateway_restart")
    _expect(transition, "acknowledgment_status", TRUST_TRANSITION_ACK_STATUS)
    next_trust_document = _object(transition.get("next_trust"), "next_trust")
    if set(next_trust_document) != {"algorithm", "key_id", "public_key", "signature_context"}:
        raise NodeConfigurationTrustTransitionVerificationError(
            "next configuration trust is invalid"
        )
    _expect(next_trust_document, "algorithm", "ed25519")
    _expect(next_trust_document, "signature_context", "ITHILDIN-NODE-CONFIG-V1")
    next_trust = configuration_trust_from_public_key(
        _string(next_trust_document.get("public_key"), "next_trust.public_key")
    )
    _expect(next_trust_document, "key_id", next_trust.key_id)
    if next_trust.key_id == current_trust.key_id:
        raise NodeConfigurationTrustTransitionVerificationError(
            "next configuration trust matches current"
        )
    return bundle


def transition_next_trust(bundle: JsonObject) -> NodeConfigurationTrust:
    transition = _object(bundle.get("transition"), "transition")
    next_trust = _object(transition.get("next_trust"), "next_trust")
    public_key = _string(next_trust.get("public_key"), "next_trust.public_key")
    trust = configuration_trust_from_public_key(public_key)
    if next_trust.get("key_id") != trust.key_id:
        raise NodeConfigurationTrustTransitionVerificationError(
            "next configuration trust key ID mismatch"
        )
    return trust


def _record(row: tuple[object, ...]) -> NodeConfigurationTrustTransitionRecord:
    bundle = json.loads(str(row[6]))
    if not isinstance(bundle, dict):
        raise NodeConfigurationTrustTransitionError("stored trust transition bundle is invalid")
    return NodeConfigurationTrustTransitionRecord(
        transition_id=str(row[0]),
        node_id=str(row[1]),
        transition_digest=str(row[2]),
        current_key_id=str(row[3]),
        next_key_id=str(row[4]),
        next_public_key=str(row[5]),
        bundle=cast(JsonObject, bundle),
        issued_at=str(row[7]),
        expires_at=str(row[8]),
        evidence_status=str(row[9]),
        acknowledgment_status=str(row[10]) if row[10] is not None else None,
        acknowledgment_evidence_status=str(row[11]) if row[11] is not None else None,
        acknowledged_at=str(row[12]) if row[12] is not None else None,
    )


def _signature_message(envelope: JsonObject) -> bytes:
    return f"{TRUST_TRANSITION_SIGNATURE_CONTEXT}\n{canonical_json(envelope)}".encode()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise NodeConfigurationTrustTransitionVerificationError(
            "trust transition timestamp must include timezone"
        )
    return parsed.astimezone(UTC)


def _object(value: object, label: str) -> JsonObject:
    if not isinstance(value, dict):
        raise NodeConfigurationTrustTransitionVerificationError(f"{label} must be an object")
    return cast(JsonObject, value)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NodeConfigurationTrustTransitionVerificationError(f"{label} must be a string")
    return value


def _expect(document: JsonObject, key: str, expected: object) -> None:
    if document.get(key) != expected:
        raise NodeConfigurationTrustTransitionVerificationError(f"{key} mismatch")
