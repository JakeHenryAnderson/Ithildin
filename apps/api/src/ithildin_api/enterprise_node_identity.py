"""Dormant, fixture-only PIS-005A Node workload-identity foundation.

This module deliberately has no application-route, startup, MCP, listener, or
transport registration.  It validates synthetic X.509 fixtures and persists
only local SQLite bindings, digests, fingerprints, generations, and replay
state.  It never creates or accepts custody of a private key.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Self, cast
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.x509.oid import (
    ExtendedKeyUsageOID,
    ExtensionOID,
    SignatureAlgorithmOID,
)
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ithildin_api.nodes import node_identity_key_id
from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

ENROLLMENT_SECRET_PURPOSE = "node-workload-enrollment-secret-v1"
ENROLLMENT_BINDING_DOMAIN = b"ITHILDIN-PIS005A-ENROLLMENT-BINDING-V1\x00"
REQUEST_BINDING_DOMAIN = b"ITHILDIN-PIS005A-REQUEST-BINDING-V1\x00"
FINGERPRINT_SCHEME = "ed25519_raw_sha256_v1"
MAX_CERTIFICATE_LIFETIME_SECONDS = 86_400
MAX_ENROLLMENT_LIFETIME_SECONDS = 3_600
MAX_REQUEST_CLOCK_SKEW_SECONDS = 300
REQUEST_NONCE_RETENTION_SECONDS = 600

_HMAC_PREFIX = "hmac-sha256:"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_NODE_ID_PATTERN = re.compile(r"^node_[0-9a-f]{32}$")
_PRINCIPAL_ID_PATTERN = re.compile(r"^prn_[0-9a-f]{32}$")
_DEPLOYMENT_ID_PATTERN = re.compile(r"^ndep_[0-9a-f]{32}$")
_ENROLLMENT_ID_PATTERN = re.compile(r"^nenr_[0-9a-f]{32}$")
_WORKSPACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_METHOD_PATTERN = re.compile(r"^[A-Z]{1,16}$")
_NONCE_PATTERN = re.compile(r"^[0-9a-f]{32,128}$")
_ORGANIZATION_ROLES_JSON = '["member","node_operator"]'
_WORKSPACE_ROLES_JSON = '["node"]'
_ED25519_ALGORITHM_IDENTIFIER_DER = b"\x30\x05\x06\x03\x2b\x65\x70"
_LEAF_EXTENSION_OIDS = frozenset(
    {
        ExtensionOID.BASIC_CONSTRAINTS,
        ExtensionOID.KEY_USAGE,
        ExtensionOID.EXTENDED_KEY_USAGE,
        ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
    }
)


class NodeWorkloadIdentityError(RuntimeError):
    """Base class for PIS-005A fail-closed fixture errors."""


class NodeWorkloadConfigurationError(NodeWorkloadIdentityError):
    """Raised when local fixture configuration cannot preserve stored authority."""


class NodeWorkloadNotFoundError(NodeWorkloadIdentityError):
    """Raised when server-owned PIS-005A state is absent."""


class NodeWorkloadConflictError(NodeWorkloadIdentityError):
    """Raised when one-use or immutable PIS-005A state would be reused."""


class NodeWorkloadAuthenticationError(NodeWorkloadIdentityError):
    """Raised when enrollment or request conformance fails closed."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class FixtureNodeCertificateTrust(_FrozenModel):
    """One injected synthetic Node CA certificate, never its private key."""

    certificate_der: bytes = Field(repr=False, min_length=1, max_length=65_536)
    certificate_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)

    @classmethod
    def from_der(cls, certificate_der: bytes) -> Self:
        return cls(
            certificate_der=certificate_der,
            certificate_fingerprint=_bytes_sha256(certificate_der),
        )

    @model_validator(mode="after")
    def _validate_fixture_ca(self) -> Self:
        if not hmac.compare_digest(
            self.certificate_fingerprint,
            _bytes_sha256(self.certificate_der),
        ):
            raise ValueError("fixture trust-anchor fingerprint mismatch")
        _load_and_validate_fixture_ca(self.certificate_der)
        return self

    def certificate(self) -> x509.Certificate:
        return _load_and_validate_fixture_ca(self.certificate_der)

    def safe_evidence(self, *, timestamp: datetime) -> JsonObject:
        return {
            "certificate_fingerprint": self.certificate_fingerprint,
            "reason_code": "fixture_trust_anchor_valid",
            "timestamp": _require_aware_utc(timestamp).isoformat(),
        }


class NodeWorkloadDigestKeyRing:
    """Generation-indexed enrollment HMAC keys with explicit retirement."""

    def __init__(
        self,
        keys: Mapping[int, bytes],
        *,
        active_generation: int,
        retired_generations: tuple[int, ...] = (),
    ) -> None:
        normalized = {int(generation): bytes(key) for generation, key in keys.items()}
        retired = frozenset(retired_generations)
        if active_generation < 1 or active_generation not in normalized:
            raise NodeWorkloadConfigurationError(
                "active enrollment digest-key generation is unavailable"
            )
        if any(generation < 1 for generation in normalized) or any(
            generation < 1 for generation in retired
        ):
            raise NodeWorkloadConfigurationError("digest-key generations must be positive")
        if any(generation > active_generation for generation in set(normalized) | retired):
            raise NodeWorkloadConfigurationError(
                "future enrollment digest-key generations are forbidden"
            )
        if retired & normalized.keys():
            raise NodeWorkloadConfigurationError("retired digest-key material must be absent")
        if any(len(key) < 32 for key in normalized.values()):
            raise NodeWorkloadConfigurationError(
                "enrollment digest keys must contain at least 256 bits"
            )
        self._keys = normalized
        self.active_generation = active_generation
        self.retired_generations = retired

    @property
    def generations(self) -> tuple[int, ...]:
        return tuple(sorted(self._keys))

    def digest(self, generation: int, secret: str) -> str:
        key = self._keys.get(generation)
        if key is None:
            raise NodeWorkloadConfigurationError("enrollment digest-key generation is unavailable")
        payload = ENROLLMENT_SECRET_PURPOSE.encode("ascii") + b"\x00" + secret.encode("utf-8")
        return _HMAC_PREFIX + hmac.new(key, payload, hashlib.sha256).hexdigest()


class NodeWorkloadDeployment(_FrozenModel):
    deployment_id: str = Field(pattern=_DEPLOYMENT_ID_PATTERN.pattern)
    organization_id: str
    workspace_id: str
    certificate_trust_anchor_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    deployment_generation: int = Field(ge=1)
    status: Literal["active", "revoked"]
    created_at: datetime
    updated_at: datetime

    def safe_evidence(self) -> JsonObject:
        return {
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "deployment_generation": self.deployment_generation,
            "reason_code": f"deployment_{self.status}",
            "timestamp": self.updated_at.isoformat(),
        }


class NodeEnrollmentClientMaterial(_FrozenModel):
    """Server-owned enrollment allocation plus its one-time returned secret."""

    enrollment_transaction_id: str = Field(pattern=_ENROLLMENT_ID_PATTERN.pattern)
    enrollment_secret: str = Field(repr=False, min_length=32, max_length=256)
    digest_key_generation: int = Field(ge=1)
    deployment_id: str = Field(pattern=_DEPLOYMENT_ID_PATTERN.pattern)
    organization_id: str
    workspace_id: str
    deployment_generation: int = Field(ge=1)
    node_id: str = Field(pattern=_NODE_ID_PATTERN.pattern)
    principal_id: str = Field(pattern=_PRINCIPAL_ID_PATTERN.pattern)
    replaces_node_id: str | None = Field(default=None, pattern=_NODE_ID_PATTERN.pattern)
    identity_generation: int = Field(ge=1)
    certificate_generation: int = Field(ge=1)
    application_key_generation: int = Field(ge=1)
    configuration_generation: int = Field(ge=1)
    certificate_trust_anchor_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    created_at: datetime
    expires_at: datetime
    expected_san_uris: tuple[str, str, str, str, str]

    def safe_evidence(self) -> JsonObject:
        return {
            "node_id": self.node_id,
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "principal_id": self.principal_id,
            "deployment_generation": self.deployment_generation,
            "identity_generation": self.identity_generation,
            "certificate_generation": self.certificate_generation,
            "application_key_generation": self.application_key_generation,
            "configuration_generation": self.configuration_generation,
            "reason_code": "enrollment_issued",
            "timestamp": self.created_at.isoformat(),
        }


class NodeEnrollmentProof(_FrozenModel):
    enrollment_transaction_id: str = Field(pattern=_ENROLLMENT_ID_PATTERN.pattern)
    enrollment_secret: str = Field(repr=False, min_length=32, max_length=256)
    certificate_der: bytes = Field(repr=False, min_length=1, max_length=65_536)
    application_public_key: str = Field(repr=False, min_length=44, max_length=44)
    certificate_proof_signature: str = Field(repr=False, min_length=88, max_length=88)
    application_proof_signature: str = Field(repr=False, min_length=88, max_length=88)

    @field_validator("application_public_key")
    @classmethod
    def _canonical_application_key(cls, value: str) -> str:
        _decode_ed25519_public_key(value)
        return value

    @field_validator("certificate_proof_signature", "application_proof_signature")
    @classmethod
    def _canonical_proof_signature(cls, value: str) -> str:
        _decode_ed25519_signature(value)
        return value


class NodeWorkloadBinding(_FrozenModel):
    node_id: str = Field(pattern=_NODE_ID_PATTERN.pattern)
    principal_id: str = Field(pattern=_PRINCIPAL_ID_PATTERN.pattern)
    deployment_id: str = Field(pattern=_DEPLOYMENT_ID_PATTERN.pattern)
    organization_id: str
    workspace_id: str
    enrollment_transaction_id: str = Field(pattern=_ENROLLMENT_ID_PATTERN.pattern)
    deployment_generation: int = Field(ge=1)
    identity_generation: int = Field(ge=1)
    certificate_generation: int = Field(ge=1)
    application_key_generation: int = Field(ge=1)
    configuration_generation: int = Field(ge=1)
    certificate_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    certificate_trust_anchor_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    certificate_key_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    application_key_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    application_key_id: str = Field(pattern=_SHA256_PATTERN.pattern)
    status: Literal["active", "revoked", "replaced"]
    created_at: datetime
    updated_at: datetime
    replaces_node_id: str | None = Field(default=None, pattern=_NODE_ID_PATTERN.pattern)

    def safe_evidence(self) -> JsonObject:
        return {
            "node_id": self.node_id,
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "principal_id": self.principal_id,
            "certificate_fingerprint": self.certificate_fingerprint,
            "application_key_fingerprint": self.application_key_fingerprint,
            "deployment_generation": self.deployment_generation,
            "identity_generation": self.identity_generation,
            "certificate_generation": self.certificate_generation,
            "application_key_generation": self.application_key_generation,
            "configuration_generation": self.configuration_generation,
            "reason_code": f"node_workload_binding_{self.status}",
            "timestamp": self.updated_at.isoformat(),
        }


class NodeWorkloadRequestEnvelope(_FrozenModel):
    node_id: str = Field(pattern=_NODE_ID_PATTERN.pattern)
    certificate_der: bytes = Field(repr=False, min_length=1, max_length=65_536)
    method: str = Field(min_length=1, max_length=16)
    path: str = Field(min_length=1, max_length=2_048)
    request_timestamp: int
    nonce: str = Field(repr=False, pattern=_NONCE_PATTERN.pattern)
    declared_request_digest: str = Field(pattern=_SHA256_PATTERN.pattern)
    request_body: bytes = Field(repr=False, max_length=1_048_576)
    deployment_generation: int = Field(ge=1)
    identity_generation: int = Field(ge=1)
    certificate_generation: int = Field(ge=1)
    application_key_generation: int = Field(ge=1)
    configuration_generation: int = Field(ge=1)
    application_signature: str = Field(repr=False, min_length=88, max_length=88)

    @field_validator("method")
    @classmethod
    def _closed_method(cls, value: str) -> str:
        if not _METHOD_PATTERN.fullmatch(value):
            raise ValueError("request method must be canonical uppercase ASCII")
        return value

    @field_validator("path")
    @classmethod
    def _closed_path(cls, value: str) -> str:
        if not value.startswith("/") or any(
            ord(character) < 33 or ord(character) > 126 for character in value
        ):
            raise ValueError("request path must be canonical visible ASCII")
        return value

    @field_validator("application_signature")
    @classmethod
    def _canonical_application_signature(cls, value: str) -> str:
        _decode_ed25519_signature(value)
        return value


class NodeRequestVerificationSnapshot(_FrozenModel):
    node_id: str = Field(pattern=_NODE_ID_PATTERN.pattern)
    deployment_id: str = Field(pattern=_DEPLOYMENT_ID_PATTERN.pattern)
    organization_id: str
    workspace_id: str
    principal_id: str = Field(pattern=_PRINCIPAL_ID_PATTERN.pattern)
    certificate_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    application_key_fingerprint: str = Field(pattern=_SHA256_PATTERN.pattern)
    deployment_generation: int = Field(ge=1)
    identity_generation: int = Field(ge=1)
    certificate_generation: int = Field(ge=1)
    application_key_generation: int = Field(ge=1)
    configuration_generation: int = Field(ge=1)
    request_digest: str = Field(pattern=_SHA256_PATTERN.pattern)
    nonce_outcome: Literal["consumed"]
    reason_code: Literal["fixture_request_valid"]
    timestamp: datetime
    effect_authority: Literal[False] = False
    live_transport_verified: Literal[False] = False

    def safe_evidence(self) -> JsonObject:
        return {
            "node_id": self.node_id,
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "principal_id": self.principal_id,
            "certificate_fingerprint": self.certificate_fingerprint,
            "application_key_fingerprint": self.application_key_fingerprint,
            "deployment_generation": self.deployment_generation,
            "identity_generation": self.identity_generation,
            "certificate_generation": self.certificate_generation,
            "application_key_generation": self.application_key_generation,
            "configuration_generation": self.configuration_generation,
            "request_digest": self.request_digest,
            "nonce_outcome": self.nonce_outcome,
            "reason_code": self.reason_code,
            "timestamp": self.timestamp.isoformat(),
        }


class NodeRevocationSnapshot(_FrozenModel):
    node_id: str = Field(pattern=_NODE_ID_PATTERN.pattern)
    deployment_id: str = Field(pattern=_DEPLOYMENT_ID_PATTERN.pattern)
    organization_id: str
    workspace_id: str
    principal_id: str = Field(pattern=_PRINCIPAL_ID_PATTERN.pattern)
    deployment_generation: int = Field(ge=1)
    identity_generation: int = Field(ge=2)
    certificate_generation: int = Field(ge=2)
    application_key_generation: int = Field(ge=2)
    configuration_generation: int = Field(ge=2)
    reason_code: Literal["operator_revoked", "key_compromise", "scope_revoked"]
    timestamp: datetime
    effect_authority: Literal[False] = False

    def safe_evidence(self) -> JsonObject:
        return {
            "node_id": self.node_id,
            "deployment_id": self.deployment_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "principal_id": self.principal_id,
            "deployment_generation": self.deployment_generation,
            "identity_generation": self.identity_generation,
            "certificate_generation": self.certificate_generation,
            "application_key_generation": self.application_key_generation,
            "configuration_generation": self.configuration_generation,
            "reason_code": self.reason_code,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class _ValidatedLeaf:
    certificate: x509.Certificate
    certificate_fingerprint: str
    certificate_public_key: str
    certificate_key_fingerprint: str
    not_before_epoch_seconds: int
    not_after_epoch_seconds: int


@dataclass(frozen=True)
class _EnrollmentRecord:
    enrollment_transaction_id: str
    enrollment_digest: str
    digest_key_generation: int
    deployment_id: str
    organization_id: str
    workspace_id: str
    deployment_generation: int
    node_id: str
    principal_id: str
    replaces_node_id: str | None
    status: str
    created_at: datetime
    expires_at: datetime
    certificate_trust_anchor_fingerprint: str

    def client_material(self, *, enrollment_secret: str) -> NodeEnrollmentClientMaterial:
        return NodeEnrollmentClientMaterial(
            enrollment_transaction_id=self.enrollment_transaction_id,
            enrollment_secret=enrollment_secret,
            digest_key_generation=self.digest_key_generation,
            deployment_id=self.deployment_id,
            organization_id=self.organization_id,
            workspace_id=self.workspace_id,
            deployment_generation=self.deployment_generation,
            node_id=self.node_id,
            principal_id=self.principal_id,
            replaces_node_id=self.replaces_node_id,
            identity_generation=1,
            certificate_generation=1,
            application_key_generation=1,
            configuration_generation=1,
            certificate_trust_anchor_fingerprint=self.certificate_trust_anchor_fingerprint,
            created_at=self.created_at,
            expires_at=self.expires_at,
            expected_san_uris=expected_node_certificate_san_uris(
                node_id=self.node_id,
                organization_id=self.organization_id,
                workspace_id=self.workspace_id,
                deployment_id=self.deployment_id,
                enrollment_transaction_id=self.enrollment_transaction_id,
            ),
        )


class NodeWorkloadIdentityStore:
    """Local SQLite PIS-005A store with no serving or effect-execution seam."""

    def __init__(
        self,
        db_path: Path,
        *,
        digest_keys: NodeWorkloadDigestKeyRing,
        certificate_trust: FixtureNodeCertificateTrust,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.db_path = db_path
        self._digest_keys = digest_keys
        self._certificate_trust = certificate_trust
        self._clock = clock or (lambda: datetime.now(UTC))

    def initialize_fixture_foundation(self) -> None:
        """Register configured HMAC generations; this does not enable a runtime feature."""

        with self._transaction() as connection:
            now = _require_aware_utc(self._clock()).isoformat()
            rows = connection.execute(
                """
                SELECT digest_key_generation, status
                FROM node_workload_enrollment_digest_key_generations
                ORDER BY digest_key_generation
                """
            ).fetchall()
            observed = {int(row["digest_key_generation"]): str(row["status"]) for row in rows}
            active_rows = [
                generation for generation, status in observed.items() if status == "active"
            ]
            if len(active_rows) > 1:
                raise NodeWorkloadConfigurationError(
                    "stored enrollment digest-key authority is ambiguous"
                )
            if active_rows and active_rows[0] > self._digest_keys.active_generation:
                raise NodeWorkloadConfigurationError(
                    "configured enrollment digest-key generation is stale"
                )
            if active_rows and active_rows[0] != self._digest_keys.active_generation:
                connection.execute(
                    """
                    UPDATE node_workload_enrollment_digest_key_generations
                    SET status = 'retained'
                    WHERE digest_key_generation = ? AND status = 'active'
                    """,
                    (active_rows[0],),
                )
                observed[active_rows[0]] = "retained"
            for generation in self._digest_keys.generations:
                desired_status = (
                    "active" if generation == self._digest_keys.active_generation else "retained"
                )
                status = observed.get(generation)
                if status == "retired":
                    raise NodeWorkloadConfigurationError(
                        "retired enrollment digest-key generation cannot be restored"
                    )
                if status is None:
                    connection.execute(
                        """
                        INSERT INTO node_workload_enrollment_digest_key_generations (
                            digest_key_generation, status, first_seen_at,
                            activated_at, retired_at
                        ) VALUES (?, ?, ?, ?, NULL)
                        """,
                        (generation, desired_status, now, now),
                    )
                elif status != desired_status:
                    connection.execute(
                        """
                        UPDATE node_workload_enrollment_digest_key_generations
                        SET status = ?, activated_at = COALESCE(activated_at, ?)
                        WHERE digest_key_generation = ?
                        """,
                        (desired_status, now, generation),
                    )
            for generation in sorted(self._digest_keys.retired_generations):
                status = observed.get(generation)
                if status is None:
                    raise NodeWorkloadConfigurationError(
                        "unknown enrollment digest-key generation cannot be retired"
                    )
                if status == "active":
                    raise NodeWorkloadConfigurationError(
                        "active enrollment digest-key generation cannot be retired"
                    )
                if status != "retired":
                    connection.execute(
                        """
                        UPDATE node_workload_enrollment_digest_key_generations
                        SET status = 'retired', retired_at = ?
                        WHERE digest_key_generation = ?
                        """,
                        (now, generation),
                    )
            row = connection.execute(
                """
                SELECT digest_key_generation
                FROM node_workload_enrollment_digest_key_generations
                WHERE status = 'active'
                """
            ).fetchone()
            if (
                row is None
                or int(row["digest_key_generation"]) != self._digest_keys.active_generation
            ):
                raise NodeWorkloadConfigurationError(
                    "active enrollment digest-key generation was not established"
                )

    def create_deployment(
        self,
        *,
        organization_id: str,
        workspace_id: str,
    ) -> NodeWorkloadDeployment:
        if not _WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
            raise NodeWorkloadConfigurationError(
                "workspace is ineligible for exact PIS-005A URI binding"
            )
        deployment_id = self._new_id("ndep_", _DEPLOYMENT_ID_PATTERN)
        with self._transaction() as connection:
            now = _require_aware_utc(self._clock())
            self._require_active_scope(connection, organization_id, workspace_id)
            connection.execute(
                """
                INSERT INTO node_workload_deployments (
                    deployment_id, organization_id, workspace_id,
                    certificate_trust_anchor_fingerprint,
                    deployment_generation, status, created_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, 1, 'active', ?, ?, NULL)
                """,
                (
                    deployment_id,
                    organization_id,
                    workspace_id,
                    self._certificate_trust.certificate_fingerprint,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return NodeWorkloadDeployment(
            deployment_id=deployment_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            certificate_trust_anchor_fingerprint=(self._certificate_trust.certificate_fingerprint),
            deployment_generation=1,
            status="active",
            created_at=now,
            updated_at=now,
        )

    def issue_enrollment(
        self,
        deployment_id: str,
        *,
        lifetime_seconds: int = 900,
    ) -> NodeEnrollmentClientMaterial:
        return self._issue_enrollment(
            deployment_id=deployment_id,
            replaces_node_id=None,
            lifetime_seconds=lifetime_seconds,
        )

    def issue_replacement_enrollment(
        self,
        revoked_node_id: str,
        *,
        lifetime_seconds: int = 900,
    ) -> NodeEnrollmentClientMaterial:
        if not _NODE_ID_PATTERN.fullmatch(revoked_node_id):
            raise NodeWorkloadNotFoundError("revoked Node identity was not found")
        self._validate_enrollment_lifetime(lifetime_seconds)
        secret = self._new_secret()
        enrollment_id = self._new_id("nenr_", _ENROLLMENT_ID_PATTERN)
        node_id = self._new_id("node_", _NODE_ID_PATTERN)
        principal_id = self._new_id("prn_", _PRINCIPAL_ID_PATTERN)
        generation = self._digest_keys.active_generation
        enrollment_digest = self._digest_keys.digest(generation, secret)
        try:
            with self._transaction() as connection:
                now = _require_aware_utc(self._clock())
                now_text = now.isoformat()
                expires_at = now + timedelta(seconds=lifetime_seconds)
                old = connection.execute(
                    """
                    SELECT node_id, deployment_id, organization_id, workspace_id,
                           status, replacement_node_id
                    FROM node_workload_identities
                    WHERE node_id = ?
                    """,
                    (revoked_node_id,),
                ).fetchone()
                if old is None:
                    raise NodeWorkloadNotFoundError("revoked Node identity was not found")
                if old["status"] != "revoked" or old["replacement_node_id"] is not None:
                    raise NodeWorkloadConflictError(
                        "Node identity is not eligible for one-way replacement"
                    )
                connection.execute(
                    """
                    UPDATE node_workload_enrollment_transactions
                    SET status = 'expired', terminal_at = ?
                    WHERE replaces_node_id = ? AND status = 'pending'
                      AND expires_at <= ?
                    """,
                    (now_text, revoked_node_id, now_text),
                )
                active_replacement = connection.execute(
                    """
                    SELECT enrollment_transaction_id
                    FROM node_workload_enrollment_transactions
                    WHERE replaces_node_id = ? AND status = 'pending'
                    """,
                    (revoked_node_id,),
                ).fetchone()
                if active_replacement is not None:
                    raise NodeWorkloadConflictError(
                        "replacement enrollment transaction is already active"
                    )
                deployment = self._require_active_deployment(
                    connection,
                    cast(str, old["deployment_id"]),
                )
                if (
                    deployment["organization_id"] != old["organization_id"]
                    or deployment["workspace_id"] != old["workspace_id"]
                ):
                    raise NodeWorkloadConflictError("stored replacement scope is inconsistent")
                self._require_active_digest_generation(connection, generation)
                record = self._insert_enrollment(
                    connection,
                    enrollment_id=enrollment_id,
                    enrollment_digest=enrollment_digest,
                    digest_key_generation=generation,
                    deployment=deployment,
                    node_id=node_id,
                    principal_id=principal_id,
                    replaces_node_id=revoked_node_id,
                    created_at=now,
                    expires_at=expires_at,
                )
        except sqlite3.IntegrityError as exc:
            raise NodeWorkloadConflictError(
                "replacement enrollment transaction is already active"
            ) from exc
        return record.client_material(enrollment_secret=secret)

    def complete_enrollment(self, proof: NodeEnrollmentProof) -> NodeWorkloadBinding:
        connection = self._connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            now = _require_aware_utc(self._clock())
            record = self._require_enrollment(
                connection,
                proof.enrollment_transaction_id,
            )
            if record.status != "pending":
                raise NodeWorkloadConflictError("enrollment transaction is no longer active")
            if now >= record.expires_at:
                expired = connection.execute(
                    """
                    UPDATE node_workload_enrollment_transactions
                    SET status = 'expired', terminal_at = ?
                    WHERE enrollment_transaction_id = ? AND status = 'pending'
                    """,
                    (now.isoformat(), record.enrollment_transaction_id),
                )
                if expired.rowcount != 1:
                    raise NodeWorkloadConflictError(
                        "enrollment transaction expiry changed concurrently"
                    )
                connection.execute("COMMIT")
                raise NodeWorkloadAuthenticationError("enrollment transaction is not valid")
            self._require_active_digest_generation(
                connection,
                record.digest_key_generation,
                allow_retained=True,
            )
            presented_digest = self._digest_keys.digest(
                record.digest_key_generation,
                proof.enrollment_secret,
            )
            if not hmac.compare_digest(record.enrollment_digest, presented_digest):
                raise NodeWorkloadAuthenticationError("enrollment proof is invalid")
            deployment = self._require_active_deployment(
                connection,
                record.deployment_id,
            )
            if (
                deployment["organization_id"] != record.organization_id
                or deployment["workspace_id"] != record.workspace_id
                or int(deployment["deployment_generation"]) != record.deployment_generation
            ):
                raise NodeWorkloadAuthenticationError("enrollment deployment binding is stale")
            material = record.client_material(enrollment_secret=proof.enrollment_secret)
            validated_leaf, application_fingerprint, application_key_id, message = (
                _validated_enrollment_message(
                    material=material,
                    certificate_der=proof.certificate_der,
                    application_public_key=proof.application_public_key,
                    certificate_trust=self._certificate_trust,
                    at=now,
                )
            )
            _verify_ed25519_signature(
                validated_leaf.certificate_public_key,
                proof.certificate_proof_signature,
                message,
            )
            _verify_ed25519_signature(
                proof.application_public_key,
                proof.application_proof_signature,
                message,
            )
            now_text = now.isoformat()
            connection.execute(
                """
                INSERT INTO identity_principals (
                    principal_id, principal_type, enabled, identity_generation,
                    created_at, updated_at
                ) VALUES (?, 'node', 1, 1, ?, ?)
                """,
                (record.principal_id, now_text, now_text),
            )
            connection.execute(
                """
                INSERT INTO identity_organization_memberships (
                    organization_id, principal_id, enabled, membership_generation,
                    roles_json, created_at, updated_at
                ) VALUES (?, ?, 1, 1, ?, ?, ?)
                """,
                (
                    record.organization_id,
                    record.principal_id,
                    _ORGANIZATION_ROLES_JSON,
                    now_text,
                    now_text,
                ),
            )
            connection.execute(
                """
                INSERT INTO identity_workspace_memberships (
                    organization_id, workspace_id, principal_id, enabled,
                    roles_json, created_at, updated_at
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    record.organization_id,
                    record.workspace_id,
                    record.principal_id,
                    _WORKSPACE_ROLES_JSON,
                    now_text,
                    now_text,
                ),
            )
            key_rows = (
                (
                    validated_leaf.certificate_key_fingerprint,
                    "certificate",
                    validated_leaf.certificate_public_key,
                ),
                (
                    application_fingerprint,
                    "application",
                    proof.application_public_key,
                ),
            )
            for key_fingerprint, key_role, canonical_public_key in key_rows:
                connection.execute(
                    """
                    INSERT INTO node_workload_public_keys (
                        key_fingerprint, node_id, enrollment_transaction_id,
                        key_role, key_generation, canonical_public_key,
                        status, created_at, retired_at
                    ) VALUES (?, ?, ?, ?, 1, ?, 'active', ?, NULL)
                    """,
                    (
                        key_fingerprint,
                        record.node_id,
                        record.enrollment_transaction_id,
                        key_role,
                        canonical_public_key,
                        now_text,
                    ),
                )
            connection.execute(
                """
                INSERT INTO node_workload_identities (
                    node_id, principal_id, deployment_id, organization_id,
                    workspace_id, enrollment_transaction_id,
                    deployment_generation, identity_generation,
                    certificate_generation, application_key_generation,
                    configuration_generation, certificate_fingerprint,
                    certificate_trust_anchor_fingerprint,
                    certificate_key_fingerprint,
                    certificate_not_before_epoch_seconds,
                    certificate_not_after_epoch_seconds,
                    application_key_fingerprint, application_key_id,
                    status, created_at, updated_at, revoked_at,
                    revocation_reason_code, replacement_completed_at,
                    replacement_node_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, 1, ?, ?, ?, ?, ?, ?, ?,
                    'active', ?, ?, NULL, NULL, NULL, NULL
                )
                """,
                (
                    record.node_id,
                    record.principal_id,
                    record.deployment_id,
                    record.organization_id,
                    record.workspace_id,
                    record.enrollment_transaction_id,
                    record.deployment_generation,
                    validated_leaf.certificate_fingerprint,
                    record.certificate_trust_anchor_fingerprint,
                    validated_leaf.certificate_key_fingerprint,
                    validated_leaf.not_before_epoch_seconds,
                    validated_leaf.not_after_epoch_seconds,
                    application_fingerprint,
                    application_key_id,
                    now_text,
                    now_text,
                ),
            )
            consumed = connection.execute(
                """
                UPDATE node_workload_enrollment_transactions
                SET status = 'consumed', terminal_at = ?
                WHERE enrollment_transaction_id = ? AND status = 'pending'
                """,
                (now_text, record.enrollment_transaction_id),
            )
            if consumed.rowcount != 1:
                raise NodeWorkloadConflictError(
                    "enrollment transaction was consumed concurrently"
                )
            if record.replaces_node_id is not None:
                replaced = connection.execute(
                    """
                    UPDATE node_workload_identities
                    SET status = 'replaced', updated_at = ?,
                        replacement_completed_at = ?,
                        replacement_node_id = ?
                    WHERE node_id = ? AND status = 'revoked'
                      AND replacement_node_id IS NULL
                    """,
                    (now_text, now_text, record.node_id, record.replaces_node_id),
                )
                if replaced.rowcount != 1:
                    raise NodeWorkloadConflictError("replacement lineage changed concurrently")
            binding = self._require_binding(connection, record.node_id)
            connection.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise NodeWorkloadConflictError(
                "Node workload identity or public key is already registered"
            ) from exc
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return binding

    def revoke_node(
        self,
        node_id: str,
        *,
        reason_code: Literal["operator_revoked", "key_compromise", "scope_revoked"],
    ) -> NodeRevocationSnapshot:
        if reason_code not in {"operator_revoked", "key_compromise", "scope_revoked"}:
            raise NodeWorkloadConfigurationError("revocation reason is not in the closed set")
        with self._transaction() as connection:
            now = _require_aware_utc(self._clock())
            now_text = now.isoformat()
            row = connection.execute(
                """
                SELECT node_id, principal_id, deployment_id, organization_id,
                       workspace_id, deployment_generation, identity_generation,
                       certificate_generation, application_key_generation,
                       configuration_generation, status
                FROM node_workload_identities WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
            if row is None:
                raise NodeWorkloadNotFoundError("Node workload identity was not found")
            if row["status"] != "active":
                raise NodeWorkloadConflictError("Node workload identity is not active")
            identity_generation = int(row["identity_generation"]) + 1
            certificate_generation = int(row["certificate_generation"]) + 1
            application_generation = int(row["application_key_generation"]) + 1
            configuration_generation = int(row["configuration_generation"]) + 1
            updated = connection.execute(
                """
                UPDATE node_workload_identities
                SET status = 'revoked', identity_generation = ?,
                    certificate_generation = ?, application_key_generation = ?,
                    configuration_generation = ?, updated_at = ?, revoked_at = ?,
                    revocation_reason_code = ?
                WHERE node_id = ? AND status = 'active'
                """,
                (
                    identity_generation,
                    certificate_generation,
                    application_generation,
                    configuration_generation,
                    now_text,
                    now_text,
                    reason_code,
                    node_id,
                ),
            )
            principal = connection.execute(
                """
                UPDATE identity_principals
                SET enabled = 0, identity_generation = identity_generation + 1,
                    updated_at = ?
                WHERE principal_id = ? AND enabled = 1
                  AND identity_generation = ?
                """,
                (now_text, row["principal_id"], row["identity_generation"]),
            )
            organization_membership = connection.execute(
                """
                UPDATE identity_organization_memberships
                SET enabled = 0, membership_generation = membership_generation + 1,
                    updated_at = ?
                WHERE organization_id = ? AND principal_id = ? AND enabled = 1
                """,
                (now_text, row["organization_id"], row["principal_id"]),
            )
            workspace_membership = connection.execute(
                """
                UPDATE identity_workspace_memberships
                SET enabled = 0, updated_at = ?
                WHERE organization_id = ? AND workspace_id = ?
                  AND principal_id = ? AND enabled = 1
                """,
                (
                    now_text,
                    row["organization_id"],
                    row["workspace_id"],
                    row["principal_id"],
                ),
            )
            retired_keys = connection.execute(
                """
                UPDATE node_workload_public_keys
                SET status = 'retired', retired_at = ?
                WHERE node_id = ? AND status = 'active'
                """,
                (now_text, node_id),
            )
            connection.execute(
                """
                UPDATE node_workload_enrollment_transactions
                SET status = 'revoked', terminal_at = ?
                WHERE node_id = ? AND status = 'pending'
                """,
                (now_text, node_id),
            )
            if (
                updated.rowcount != 1
                or principal.rowcount != 1
                or organization_membership.rowcount != 1
                or workspace_membership.rowcount != 1
                or retired_keys.rowcount != 2
            ):
                raise NodeWorkloadConflictError("Node revocation authority changed concurrently")
        return NodeRevocationSnapshot(
            node_id=node_id,
            deployment_id=cast(str, row["deployment_id"]),
            organization_id=cast(str, row["organization_id"]),
            workspace_id=cast(str, row["workspace_id"]),
            principal_id=cast(str, row["principal_id"]),
            deployment_generation=int(row["deployment_generation"]),
            identity_generation=identity_generation,
            certificate_generation=certificate_generation,
            application_key_generation=application_generation,
            configuration_generation=configuration_generation,
            reason_code=reason_code,
            timestamp=now,
        )

    def verify_request(
        self,
        envelope: NodeWorkloadRequestEnvelope,
    ) -> NodeRequestVerificationSnapshot:
        computed_digest = request_body_digest(envelope.request_body)
        if not hmac.compare_digest(computed_digest, envelope.declared_request_digest):
            raise NodeWorkloadAuthenticationError("request body digest mismatch")
        nonce_digest = sha256_digest(
            {
                "schema_version": "1",
                "node_id": envelope.node_id,
                "nonce": envelope.nonce,
            }
        )
        with self._transaction() as connection:
            now = _require_aware_utc(self._clock())
            now_epoch = int(now.timestamp())
            if abs(envelope.request_timestamp - now_epoch) > MAX_REQUEST_CLOCK_SKEW_SECONDS:
                raise NodeWorkloadAuthenticationError(
                    "request timestamp is outside the fixture window"
                )
            binding = self._require_binding(connection, envelope.node_id)
            if binding.status != "active":
                raise NodeWorkloadAuthenticationError("Node workload identity is not active")
            deployment = self._require_active_deployment(connection, binding.deployment_id)
            self._require_active_scope(
                connection,
                binding.organization_id,
                binding.workspace_id,
            )
            if (
                deployment["organization_id"] != binding.organization_id
                or deployment["workspace_id"] != binding.workspace_id
                or int(deployment["deployment_generation"]) != binding.deployment_generation
            ):
                raise NodeWorkloadAuthenticationError("deployment scope binding is stale")
            if not hmac.compare_digest(
                binding.certificate_trust_anchor_fingerprint,
                cast(str, deployment["certificate_trust_anchor_fingerprint"]),
            ) or not hmac.compare_digest(
                binding.certificate_trust_anchor_fingerprint,
                self._certificate_trust.certificate_fingerprint,
            ):
                raise NodeWorkloadAuthenticationError(
                    "Node identity trust-anchor binding is stale"
                )
            self._require_current_node_authority(connection, binding)
            claimed_generations = (
                envelope.deployment_generation,
                envelope.identity_generation,
                envelope.certificate_generation,
                envelope.application_key_generation,
                envelope.configuration_generation,
            )
            stored_generations = (
                binding.deployment_generation,
                binding.identity_generation,
                binding.certificate_generation,
                binding.application_key_generation,
                binding.configuration_generation,
            )
            if claimed_generations != stored_generations:
                raise NodeWorkloadAuthenticationError("request authority generation is stale")
            certificate_key = self._require_active_key(
                connection,
                node_id=binding.node_id,
                role="certificate",
                generation=binding.certificate_generation,
            )
            application_key = self._require_active_key(
                connection,
                node_id=binding.node_id,
                role="application",
                generation=binding.application_key_generation,
            )
            validated_leaf = _validate_leaf_certificate(
                certificate_der=envelope.certificate_der,
                certificate_trust=self._certificate_trust,
                expected_san_uris=expected_node_certificate_san_uris(
                    node_id=binding.node_id,
                    organization_id=binding.organization_id,
                    workspace_id=binding.workspace_id,
                    deployment_id=binding.deployment_id,
                    enrollment_transaction_id=binding.enrollment_transaction_id,
                ),
                at=now,
            )
            if (
                validated_leaf.certificate_fingerprint != binding.certificate_fingerprint
                or validated_leaf.certificate_key_fingerprint != binding.certificate_key_fingerprint
                or certificate_key["key_fingerprint"] != binding.certificate_key_fingerprint
                or certificate_key["canonical_public_key"] != validated_leaf.certificate_public_key
                or application_key["key_fingerprint"] != binding.application_key_fingerprint
            ):
                raise NodeWorkloadAuthenticationError("presented certificate binding is stale")
            application_public_key = cast(str, application_key["canonical_public_key"])
            try:
                application_key_id = node_identity_key_id(application_public_key)
            except ValueError as exc:
                raise NodeWorkloadAuthenticationError(
                    "stored Node application key is invalid"
                ) from exc
            if not hmac.compare_digest(application_key_id, binding.application_key_id):
                raise NodeWorkloadAuthenticationError(
                    "Node application key identifier binding is stale"
                )
            message = canonical_node_workload_request_message(
                binding=binding,
                method=envelope.method,
                path=envelope.path,
                request_timestamp=envelope.request_timestamp,
                nonce=envelope.nonce,
                request_digest=computed_digest,
            )
            _verify_ed25519_signature(
                application_public_key,
                envelope.application_signature,
                message,
            )
            connection.execute(
                """
                DELETE FROM node_workload_request_nonces
                WHERE expires_at < ?
                """,
                (now_epoch,),
            )
            try:
                connection.execute(
                    """
                    INSERT INTO node_workload_request_nonces (
                        node_id, nonce_digest, deployment_generation,
                        identity_generation, certificate_generation,
                        application_key_generation, configuration_generation,
                        request_digest, request_timestamp, accepted_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        binding.node_id,
                        nonce_digest,
                        binding.deployment_generation,
                        binding.identity_generation,
                        binding.certificate_generation,
                        binding.application_key_generation,
                        binding.configuration_generation,
                        computed_digest,
                        envelope.request_timestamp,
                        now_epoch,
                        now_epoch + REQUEST_NONCE_RETENTION_SECONDS,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise NodeWorkloadAuthenticationError("request nonce was already consumed") from exc
        return NodeRequestVerificationSnapshot(
            node_id=binding.node_id,
            deployment_id=binding.deployment_id,
            organization_id=binding.organization_id,
            workspace_id=binding.workspace_id,
            principal_id=binding.principal_id,
            certificate_fingerprint=binding.certificate_fingerprint,
            application_key_fingerprint=binding.application_key_fingerprint,
            deployment_generation=binding.deployment_generation,
            identity_generation=binding.identity_generation,
            certificate_generation=binding.certificate_generation,
            application_key_generation=binding.application_key_generation,
            configuration_generation=binding.configuration_generation,
            request_digest=computed_digest,
            nonce_outcome="consumed",
            reason_code="fixture_request_valid",
            timestamp=now,
        )

    def _issue_enrollment(
        self,
        *,
        deployment_id: str,
        replaces_node_id: str | None,
        lifetime_seconds: int,
    ) -> NodeEnrollmentClientMaterial:
        self._validate_enrollment_lifetime(lifetime_seconds)
        secret = self._new_secret()
        enrollment_id = self._new_id("nenr_", _ENROLLMENT_ID_PATTERN)
        node_id = self._new_id("node_", _NODE_ID_PATTERN)
        principal_id = self._new_id("prn_", _PRINCIPAL_ID_PATTERN)
        generation = self._digest_keys.active_generation
        enrollment_digest = self._digest_keys.digest(generation, secret)
        with self._transaction() as connection:
            now = _require_aware_utc(self._clock())
            expires_at = now + timedelta(seconds=lifetime_seconds)
            deployment = self._require_active_deployment(connection, deployment_id)
            self._require_active_digest_generation(connection, generation)
            record = self._insert_enrollment(
                connection,
                enrollment_id=enrollment_id,
                enrollment_digest=enrollment_digest,
                digest_key_generation=generation,
                deployment=deployment,
                node_id=node_id,
                principal_id=principal_id,
                replaces_node_id=replaces_node_id,
                created_at=now,
                expires_at=expires_at,
            )
        return record.client_material(enrollment_secret=secret)

    def _insert_enrollment(
        self,
        connection: sqlite3.Connection,
        *,
        enrollment_id: str,
        enrollment_digest: str,
        digest_key_generation: int,
        deployment: sqlite3.Row,
        node_id: str,
        principal_id: str,
        replaces_node_id: str | None,
        created_at: datetime,
        expires_at: datetime,
    ) -> _EnrollmentRecord:
        connection.execute(
            """
            INSERT INTO node_workload_enrollment_transactions (
                enrollment_transaction_id, enrollment_digest,
                digest_key_generation, deployment_id, organization_id,
                workspace_id, deployment_generation, node_id, principal_id,
                replaces_node_id, status, created_at, expires_at, terminal_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL)
            """,
            (
                enrollment_id,
                enrollment_digest,
                digest_key_generation,
                deployment["deployment_id"],
                deployment["organization_id"],
                deployment["workspace_id"],
                deployment["deployment_generation"],
                node_id,
                principal_id,
                replaces_node_id,
                created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        return _EnrollmentRecord(
            enrollment_transaction_id=enrollment_id,
            enrollment_digest=enrollment_digest,
            digest_key_generation=digest_key_generation,
            deployment_id=cast(str, deployment["deployment_id"]),
            organization_id=cast(str, deployment["organization_id"]),
            workspace_id=cast(str, deployment["workspace_id"]),
            deployment_generation=int(deployment["deployment_generation"]),
            node_id=node_id,
            principal_id=principal_id,
            replaces_node_id=replaces_node_id,
            status="pending",
            created_at=created_at,
            expires_at=expires_at,
            certificate_trust_anchor_fingerprint=cast(
                str,
                deployment["certificate_trust_anchor_fingerprint"],
            ),
        )

    def _require_enrollment(
        self,
        connection: sqlite3.Connection,
        enrollment_transaction_id: str,
    ) -> _EnrollmentRecord:
        row = connection.execute(
            """
            SELECT e.enrollment_transaction_id, e.enrollment_digest,
                   e.digest_key_generation, e.deployment_id, e.organization_id,
                   e.workspace_id, e.deployment_generation, e.node_id,
                   e.principal_id, e.replaces_node_id, e.status, e.created_at,
                   e.expires_at, d.certificate_trust_anchor_fingerprint
            FROM node_workload_enrollment_transactions AS e
            JOIN node_workload_deployments AS d
              ON d.deployment_id = e.deployment_id
            WHERE e.enrollment_transaction_id = ?
            """,
            (enrollment_transaction_id,),
        ).fetchone()
        if row is None:
            raise NodeWorkloadNotFoundError("enrollment transaction was not found")
        return _EnrollmentRecord(
            enrollment_transaction_id=cast(str, row["enrollment_transaction_id"]),
            enrollment_digest=cast(str, row["enrollment_digest"]),
            digest_key_generation=int(row["digest_key_generation"]),
            deployment_id=cast(str, row["deployment_id"]),
            organization_id=cast(str, row["organization_id"]),
            workspace_id=cast(str, row["workspace_id"]),
            deployment_generation=int(row["deployment_generation"]),
            node_id=cast(str, row["node_id"]),
            principal_id=cast(str, row["principal_id"]),
            replaces_node_id=cast(str | None, row["replaces_node_id"]),
            status=cast(str, row["status"]),
            created_at=_parse_datetime(cast(str, row["created_at"])),
            expires_at=_parse_datetime(cast(str, row["expires_at"])),
            certificate_trust_anchor_fingerprint=cast(
                str,
                row["certificate_trust_anchor_fingerprint"],
            ),
        )

    def _require_binding(
        self,
        connection: sqlite3.Connection,
        node_id: str,
    ) -> NodeWorkloadBinding:
        row = connection.execute(
            """
            SELECT i.node_id, i.principal_id, i.deployment_id,
                   i.organization_id, i.workspace_id,
                   i.enrollment_transaction_id, i.deployment_generation,
                   i.identity_generation, i.certificate_generation,
                   i.application_key_generation, i.configuration_generation,
                   i.certificate_fingerprint,
                   i.certificate_trust_anchor_fingerprint,
                   i.certificate_key_fingerprint,
                   i.application_key_fingerprint, i.application_key_id,
                   i.status, i.created_at, i.updated_at, e.replaces_node_id
            FROM node_workload_identities AS i
            JOIN node_workload_enrollment_transactions AS e
              ON e.enrollment_transaction_id = i.enrollment_transaction_id
            WHERE i.node_id = ?
            """,
            (node_id,),
        ).fetchone()
        if row is None:
            raise NodeWorkloadNotFoundError("Node workload identity was not found")
        return NodeWorkloadBinding(
            node_id=cast(str, row["node_id"]),
            principal_id=cast(str, row["principal_id"]),
            deployment_id=cast(str, row["deployment_id"]),
            organization_id=cast(str, row["organization_id"]),
            workspace_id=cast(str, row["workspace_id"]),
            enrollment_transaction_id=cast(str, row["enrollment_transaction_id"]),
            deployment_generation=int(row["deployment_generation"]),
            identity_generation=int(row["identity_generation"]),
            certificate_generation=int(row["certificate_generation"]),
            application_key_generation=int(row["application_key_generation"]),
            configuration_generation=int(row["configuration_generation"]),
            certificate_fingerprint=cast(str, row["certificate_fingerprint"]),
            certificate_trust_anchor_fingerprint=cast(
                str,
                row["certificate_trust_anchor_fingerprint"],
            ),
            certificate_key_fingerprint=cast(str, row["certificate_key_fingerprint"]),
            application_key_fingerprint=cast(str, row["application_key_fingerprint"]),
            application_key_id=cast(str, row["application_key_id"]),
            status=cast(Literal["active", "revoked", "replaced"], row["status"]),
            created_at=_parse_datetime(cast(str, row["created_at"])),
            updated_at=_parse_datetime(cast(str, row["updated_at"])),
            replaces_node_id=cast(str | None, row["replaces_node_id"]),
        )

    def _require_active_deployment(
        self,
        connection: sqlite3.Connection,
        deployment_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT deployment_id, organization_id, workspace_id,
                   certificate_trust_anchor_fingerprint,
                   deployment_generation, status
            FROM node_workload_deployments WHERE deployment_id = ?
            """,
            (deployment_id,),
        ).fetchone()
        if row is None:
            raise NodeWorkloadNotFoundError("Node deployment was not found")
        if row["status"] != "active":
            raise NodeWorkloadAuthenticationError("Node deployment is not active")
        if not hmac.compare_digest(
            cast(str, row["certificate_trust_anchor_fingerprint"]),
            self._certificate_trust.certificate_fingerprint,
        ):
            raise NodeWorkloadAuthenticationError("Node deployment trust anchor is unavailable")
        self._require_active_scope(
            connection,
            cast(str, row["organization_id"]),
            cast(str, row["workspace_id"]),
        )
        return cast(sqlite3.Row, row)

    @staticmethod
    def _require_active_scope(
        connection: sqlite3.Connection,
        organization_id: str,
        workspace_id: str,
    ) -> None:
        row = connection.execute(
            """
            SELECT o.enabled AS organization_enabled,
                   w.enabled AS workspace_enabled
            FROM identity_organizations AS o
            JOIN identity_workspaces AS w
              ON w.organization_id = o.organization_id
            WHERE o.organization_id = ? AND w.workspace_id = ?
            """,
            (organization_id, workspace_id),
        ).fetchone()
        if (
            row is None
            or int(row["organization_enabled"]) != 1
            or int(row["workspace_enabled"]) != 1
        ):
            raise NodeWorkloadAuthenticationError("organization or workspace scope is not active")

    def _require_active_digest_generation(
        self,
        connection: sqlite3.Connection,
        generation: int,
        *,
        allow_retained: bool = False,
    ) -> None:
        row = connection.execute(
            """
            SELECT status FROM node_workload_enrollment_digest_key_generations
            WHERE digest_key_generation = ?
            """,
            (generation,),
        ).fetchone()
        allowed = {"active", "retained"} if allow_retained else {"active"}
        if row is None or row["status"] not in allowed:
            raise NodeWorkloadAuthenticationError("enrollment digest-key generation is not usable")
        if generation not in self._digest_keys.generations:
            raise NodeWorkloadConfigurationError("enrollment digest-key generation is unavailable")

    @staticmethod
    def _require_current_node_authority(
        connection: sqlite3.Connection,
        binding: NodeWorkloadBinding,
    ) -> None:
        principal = connection.execute(
            """
            SELECT principal_type, enabled, identity_generation
            FROM identity_principals WHERE principal_id = ?
            """,
            (binding.principal_id,),
        ).fetchone()
        organization_membership = connection.execute(
            """
            SELECT enabled, membership_generation, roles_json
            FROM identity_organization_memberships
            WHERE organization_id = ? AND principal_id = ?
            """,
            (binding.organization_id, binding.principal_id),
        ).fetchone()
        workspace_membership = connection.execute(
            """
            SELECT enabled, roles_json
            FROM identity_workspace_memberships
            WHERE organization_id = ? AND workspace_id = ? AND principal_id = ?
            """,
            (binding.organization_id, binding.workspace_id, binding.principal_id),
        ).fetchone()
        if (
            principal is None
            or principal["principal_type"] != "node"
            or int(principal["enabled"]) != 1
            or int(principal["identity_generation"]) != binding.identity_generation
            or organization_membership is None
            or int(organization_membership["enabled"]) != 1
            or int(organization_membership["membership_generation"]) < 1
            or not _roles_are_exact(
                cast(str, organization_membership["roles_json"]),
                {"member", "node_operator"},
            )
            or workspace_membership is None
            or int(workspace_membership["enabled"]) != 1
            or not _roles_are_exact(
                cast(str, workspace_membership["roles_json"]),
                {"node"},
            )
        ):
            raise NodeWorkloadAuthenticationError(
                "current Node principal or membership authority is invalid"
            )

    @staticmethod
    def _require_active_key(
        connection: sqlite3.Connection,
        *,
        node_id: str,
        role: Literal["certificate", "application"],
        generation: int,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT key_fingerprint, canonical_public_key, status
            FROM node_workload_public_keys
            WHERE node_id = ? AND key_role = ? AND key_generation = ?
            """,
            (node_id, role, generation),
        ).fetchone()
        if row is None or row["status"] != "active":
            raise NodeWorkloadAuthenticationError("current Node public key is unavailable")
        try:
            fingerprint = ed25519_raw_public_key_fingerprint(cast(str, row["canonical_public_key"]))
        except ValueError as exc:
            raise NodeWorkloadAuthenticationError("stored Node public key is invalid") from exc
        if not hmac.compare_digest(fingerprint, cast(str, row["key_fingerprint"])):
            raise NodeWorkloadAuthenticationError("stored Node public-key binding is invalid")
        return cast(sqlite3.Row, row)

    def _connection(self) -> sqlite3.Connection:
        verify_database_v2(self.db_path)
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _transaction(self) -> _ImmediateTransaction:
        return _ImmediateTransaction(self._connection())

    def _new_id(self, prefix: str, pattern: re.Pattern[str]) -> str:
        value = prefix + uuid4().hex
        if not pattern.fullmatch(value):
            raise NodeWorkloadConfigurationError("server identifier factory returned invalid data")
        return value

    @staticmethod
    def _new_secret() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _validate_enrollment_lifetime(lifetime_seconds: int) -> None:
        if not 1 <= lifetime_seconds <= MAX_ENROLLMENT_LIFETIME_SECONDS:
            raise NodeWorkloadConfigurationError(
                "enrollment lifetime is outside the closed fixture window"
            )


class _ImmediateTransaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        self.connection.execute("BEGIN IMMEDIATE")
        return self.connection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        try:
            self.connection.execute("ROLLBACK" if exc_type is not None else "COMMIT")
        finally:
            self.connection.close()


def ed25519_raw_public_key_fingerprint(canonical_public_key: str) -> str:
    """Return the explicitly versioned raw-byte Ed25519 fingerprint value."""

    return _bytes_sha256(_decode_ed25519_public_key(canonical_public_key))


def request_body_digest(request_body: bytes) -> str:
    return _bytes_sha256(request_body)


def safe_validation_error_evidence(
    error: ValidationError,
    *,
    timestamp: datetime,
) -> JsonObject:
    """Return the only PIS-005A evidence-safe projection of a validation error."""

    return {
        "validation_error_count": error.error_count(),
        "reason_code": "fixture_input_validation_failed",
        "timestamp": _require_aware_utc(timestamp).isoformat(),
    }


def expected_node_certificate_san_uris(
    *,
    node_id: str,
    organization_id: str,
    workspace_id: str,
    deployment_id: str,
    enrollment_transaction_id: str,
) -> tuple[str, str, str, str, str]:
    if not _NODE_ID_PATTERN.fullmatch(node_id):
        raise ValueError("invalid Node identifier")
    if not _WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
        raise ValueError("workspace identifier is not PIS-005A eligible")
    if not _DEPLOYMENT_ID_PATTERN.fullmatch(deployment_id):
        raise ValueError("invalid deployment identifier")
    if not _ENROLLMENT_ID_PATTERN.fullmatch(enrollment_transaction_id):
        raise ValueError("invalid enrollment transaction identifier")
    if not organization_id or any(ord(character) > 127 for character in organization_id):
        raise ValueError("invalid organization identifier")
    return (
        f"urn:ithildin:node:{node_id}",
        f"urn:ithildin:organization:{organization_id}",
        f"urn:ithildin:workspace:{workspace_id}",
        f"urn:ithildin:deployment:{deployment_id}",
        f"urn:ithildin:enrollment:{enrollment_transaction_id}",
    )


def canonical_enrollment_proof_message(
    *,
    material: NodeEnrollmentClientMaterial,
    certificate_der: bytes,
    application_public_key: str,
    certificate_trust: FixtureNodeCertificateTrust,
    at: datetime,
) -> bytes:
    """Construct the one message both fixture-held private keys must sign."""

    _, _, _, message = _validated_enrollment_message(
        material=material,
        certificate_der=certificate_der,
        application_public_key=application_public_key,
        certificate_trust=certificate_trust,
        at=at,
    )
    return message


def canonical_node_workload_request_message(
    *,
    binding: NodeWorkloadBinding,
    method: str,
    path: str,
    request_timestamp: int,
    nonce: str,
    request_digest: str,
) -> bytes:
    if not _METHOD_PATTERN.fullmatch(method):
        raise ValueError("request method must be canonical uppercase ASCII")
    if not path.startswith("/") or any(
        ord(character) < 33 or ord(character) > 126 for character in path
    ):
        raise ValueError("request path must be canonical visible ASCII")
    if not _NONCE_PATTERN.fullmatch(nonce):
        raise ValueError("request nonce is invalid")
    if not _SHA256_PATTERN.fullmatch(request_digest):
        raise ValueError("request digest is invalid")
    payload: JsonObject = {
        "schema_version": "1",
        "node_id": binding.node_id,
        "principal_id": binding.principal_id,
        "deployment_id": binding.deployment_id,
        "organization_id": binding.organization_id,
        "workspace_id": binding.workspace_id,
        "enrollment_transaction_id": binding.enrollment_transaction_id,
        "certificate_fingerprint": binding.certificate_fingerprint,
        "certificate_trust_anchor_fingerprint": (
            binding.certificate_trust_anchor_fingerprint
        ),
        "certificate_key_fingerprint": binding.certificate_key_fingerprint,
        "application_key_fingerprint": binding.application_key_fingerprint,
        "application_key_id": binding.application_key_id,
        "deployment_generation": binding.deployment_generation,
        "identity_generation": binding.identity_generation,
        "certificate_generation": binding.certificate_generation,
        "application_key_generation": binding.application_key_generation,
        "configuration_generation": binding.configuration_generation,
        "method": method,
        "path": path,
        "request_timestamp": request_timestamp,
        "nonce": nonce,
        "request_digest": request_digest,
    }
    return REQUEST_BINDING_DOMAIN + canonical_json(payload).encode("utf-8")


def _validated_enrollment_message(
    *,
    material: NodeEnrollmentClientMaterial,
    certificate_der: bytes,
    application_public_key: str,
    certificate_trust: FixtureNodeCertificateTrust,
    at: datetime,
) -> tuple[_ValidatedLeaf, str, str, bytes]:
    if not hmac.compare_digest(
        material.certificate_trust_anchor_fingerprint,
        certificate_trust.certificate_fingerprint,
    ):
        raise NodeWorkloadAuthenticationError("fixture trust anchor does not match enrollment")
    if material.expected_san_uris != expected_node_certificate_san_uris(
        node_id=material.node_id,
        organization_id=material.organization_id,
        workspace_id=material.workspace_id,
        deployment_id=material.deployment_id,
        enrollment_transaction_id=material.enrollment_transaction_id,
    ):
        raise NodeWorkloadAuthenticationError("enrollment SAN allocation is invalid")
    validated_leaf = _validate_leaf_certificate(
        certificate_der=certificate_der,
        certificate_trust=certificate_trust,
        expected_san_uris=material.expected_san_uris,
        at=at,
    )
    application_fingerprint = ed25519_raw_public_key_fingerprint(application_public_key)
    if hmac.compare_digest(
        validated_leaf.certificate_key_fingerprint,
        application_fingerprint,
    ):
        raise NodeWorkloadAuthenticationError("certificate and application public keys must differ")
    application_key_id = node_identity_key_id(application_public_key)
    payload: JsonObject = {
        "schema_version": "1",
        "enrollment_transaction_id": material.enrollment_transaction_id,
        "enrollment_expires_at": material.expires_at.isoformat(),
        "deployment_id": material.deployment_id,
        "organization_id": material.organization_id,
        "workspace_id": material.workspace_id,
        "node_id": material.node_id,
        "principal_id": material.principal_id,
        "replaces_node_id": material.replaces_node_id,
        "certificate_trust_anchor_fingerprint": (material.certificate_trust_anchor_fingerprint),
        "certificate_fingerprint": validated_leaf.certificate_fingerprint,
        "certificate_key_fingerprint": validated_leaf.certificate_key_fingerprint,
        "application_key_fingerprint": application_fingerprint,
        "deployment_generation": material.deployment_generation,
        "identity_generation": material.identity_generation,
        "certificate_generation": material.certificate_generation,
        "application_key_generation": material.application_key_generation,
        "configuration_generation": material.configuration_generation,
    }
    return (
        validated_leaf,
        application_fingerprint,
        application_key_id,
        ENROLLMENT_BINDING_DOMAIN + canonical_json(payload).encode("utf-8"),
    )


def _validate_leaf_certificate(
    *,
    certificate_der: bytes,
    certificate_trust: FixtureNodeCertificateTrust,
    expected_san_uris: tuple[str, str, str, str, str],
    at: datetime,
) -> _ValidatedLeaf:
    try:
        _require_exact_ed25519_certificate_algorithms(certificate_der)
    except ValueError as exc:
        raise NodeWorkloadAuthenticationError(
            "fixture certificate AlgorithmIdentifier is invalid"
        ) from exc
    try:
        certificate = x509.load_der_x509_certificate(certificate_der)
    except ValueError as exc:
        raise NodeWorkloadAuthenticationError("fixture certificate DER is invalid") from exc
    if certificate.public_bytes(serialization.Encoding.DER) != certificate_der:
        raise NodeWorkloadAuthenticationError("fixture certificate DER is noncanonical")
    trust = certificate_trust.certificate()
    if certificate.issuer != trust.subject or certificate.subject != x509.Name([]):
        raise NodeWorkloadAuthenticationError("fixture certificate issuer or subject is invalid")
    if (
        certificate.version is not x509.Version.v3
        or certificate.signature_algorithm_oid != SignatureAlgorithmOID.ED25519
        or not isinstance(certificate.public_key(), Ed25519PublicKey)
    ):
        raise NodeWorkloadAuthenticationError("fixture certificate algorithm is invalid")
    try:
        cast(Ed25519PublicKey, trust.public_key()).verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,
        )
    except (InvalidSignature, ValueError) as exc:
        raise NodeWorkloadAuthenticationError("fixture certificate signature is invalid") from exc
    if {extension.oid for extension in certificate.extensions} != _LEAF_EXTENSION_OIDS:
        raise NodeWorkloadAuthenticationError("fixture certificate extension inventory is invalid")
    try:
        basic = certificate.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
        key_usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
        extended_key_usage = certificate.extensions.get_extension_for_oid(
            ExtensionOID.EXTENDED_KEY_USAGE
        )
        san = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    except x509.ExtensionNotFound as exc:
        raise NodeWorkloadAuthenticationError("fixture certificate profile is incomplete") from exc
    basic_value = cast(x509.BasicConstraints, basic.value)
    key_usage_value = cast(x509.KeyUsage, key_usage.value)
    extended_key_usage_value = cast(x509.ExtendedKeyUsage, extended_key_usage.value)
    san_value = cast(x509.SubjectAlternativeName, san.value)
    if (
        not basic.critical
        or basic_value.ca
        or basic_value.path_length is not None
        or not key_usage.critical
        or not key_usage_value.digital_signature
        or key_usage_value.content_commitment
        or key_usage_value.key_encipherment
        or key_usage_value.data_encipherment
        or key_usage_value.key_agreement
        or key_usage_value.key_cert_sign
        or key_usage_value.crl_sign
        or extended_key_usage.critical
        or tuple(extended_key_usage_value) != (ExtendedKeyUsageOID.CLIENT_AUTH,)
        or not san.critical
    ):
        raise NodeWorkloadAuthenticationError("fixture certificate profile is invalid")
    general_names: tuple[x509.GeneralName, ...] = tuple(san_value)
    if len(general_names) != 5 or any(
        not isinstance(name, x509.UniformResourceIdentifier) for name in general_names
    ):
        raise NodeWorkloadAuthenticationError("fixture certificate SAN shape is invalid")
    observed_uris = tuple(
        cast(x509.UniformResourceIdentifier, name).value for name in general_names
    )
    if len(set(observed_uris)) != 5 or set(observed_uris) != set(expected_san_uris):
        raise NodeWorkloadAuthenticationError("fixture certificate SAN binding is invalid")
    current = _require_aware_utc(at)
    not_before = certificate.not_valid_before_utc
    not_after = certificate.not_valid_after_utc
    lifetime = int((not_after - not_before).total_seconds())
    if (
        current < not_before
        or current >= not_after
        or lifetime < 1
        or lifetime > MAX_CERTIFICATE_LIFETIME_SECONDS
    ):
        raise NodeWorkloadAuthenticationError("fixture certificate validity is invalid")
    public_key = cast(Ed25519PublicKey, certificate.public_key())
    raw_public_key = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    canonical_public_key = base64.b64encode(raw_public_key).decode("ascii")
    return _ValidatedLeaf(
        certificate=certificate,
        certificate_fingerprint=_bytes_sha256(certificate_der),
        certificate_public_key=canonical_public_key,
        certificate_key_fingerprint=_bytes_sha256(raw_public_key),
        not_before_epoch_seconds=int(not_before.timestamp()),
        not_after_epoch_seconds=int(not_after.timestamp()),
    )


def _load_and_validate_fixture_ca(certificate_der: bytes) -> x509.Certificate:
    _require_exact_ed25519_certificate_algorithms(certificate_der)
    try:
        certificate = x509.load_der_x509_certificate(certificate_der)
    except ValueError as exc:
        raise ValueError("fixture trust anchor DER is invalid") from exc
    if certificate.public_bytes(serialization.Encoding.DER) != certificate_der:
        raise ValueError("fixture trust anchor DER is noncanonical")
    public_key = certificate.public_key()
    if (
        certificate.version is not x509.Version.v3
        or certificate.signature_algorithm_oid != SignatureAlgorithmOID.ED25519
        or not isinstance(public_key, Ed25519PublicKey)
        or certificate.issuer != certificate.subject
    ):
        raise ValueError("fixture trust anchor profile is invalid")
    try:
        basic = certificate.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
        key_usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
    except x509.ExtensionNotFound as exc:
        raise ValueError("fixture trust anchor profile is incomplete") from exc
    basic_value = cast(x509.BasicConstraints, basic.value)
    key_usage_value = cast(x509.KeyUsage, key_usage.value)
    if (
        not basic.critical
        or not basic_value.ca
        or basic_value.path_length != 0
        or not key_usage.critical
        or key_usage_value.digital_signature
        or key_usage_value.content_commitment
        or key_usage_value.key_encipherment
        or key_usage_value.data_encipherment
        or key_usage_value.key_agreement
        or not key_usage_value.key_cert_sign
        or not key_usage_value.crl_sign
    ):
        raise ValueError("fixture trust anchor key usage is invalid")
    try:
        public_key.verify(certificate.signature, certificate.tbs_certificate_bytes)
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("fixture trust anchor self-signature is invalid") from exc
    return certificate


def _require_exact_ed25519_certificate_algorithms(certificate_der: bytes) -> None:
    outer_tag, outer_content, outer_end = _der_tlv_bounds(certificate_der, 0)
    if outer_tag != 0x30 or outer_end != len(certificate_der):
        raise ValueError("certificate is not one exact DER SEQUENCE")

    tbs_start = outer_content
    tbs_tag, tbs_content, tbs_end = _der_tlv_bounds(certificate_der, tbs_start)
    outer_algorithm_start = tbs_end
    outer_algorithm_tag, _, outer_algorithm_end = _der_tlv_bounds(
        certificate_der,
        outer_algorithm_start,
    )
    signature_tag, _, signature_end = _der_tlv_bounds(
        certificate_der,
        outer_algorithm_end,
    )
    if (
        tbs_tag != 0x30
        or outer_algorithm_tag != 0x30
        or signature_tag != 0x03
        or signature_end != outer_end
    ):
        raise ValueError("certificate outer structure is invalid")
    outer_algorithm = certificate_der[outer_algorithm_start:outer_algorithm_end]

    offset = tbs_content
    first_tag, _, first_end = _der_tlv_bounds(certificate_der, offset)
    if first_tag == 0xA0:
        offset = first_end
    serial_tag, _, serial_end = _der_tlv_bounds(certificate_der, offset)
    inner_algorithm_start = serial_end
    inner_algorithm_tag, _, inner_algorithm_end = _der_tlv_bounds(
        certificate_der,
        inner_algorithm_start,
    )
    issuer_tag, _, issuer_end = _der_tlv_bounds(
        certificate_der,
        inner_algorithm_end,
    )
    validity_tag, _, validity_end = _der_tlv_bounds(certificate_der, issuer_end)
    subject_tag, _, subject_end = _der_tlv_bounds(certificate_der, validity_end)
    spki_start = subject_end
    spki_tag, spki_content, spki_end = _der_tlv_bounds(certificate_der, spki_start)
    spki_algorithm_tag, _, spki_algorithm_end = _der_tlv_bounds(
        certificate_der,
        spki_content,
    )
    if (
        serial_tag != 0x02
        or inner_algorithm_tag != 0x30
        or issuer_tag != 0x30
        or validity_tag != 0x30
        or subject_tag != 0x30
        or spki_tag != 0x30
        or spki_algorithm_tag != 0x30
        or spki_end > tbs_end
    ):
        raise ValueError("certificate TBS structure is invalid")
    inner_algorithm = certificate_der[inner_algorithm_start:inner_algorithm_end]
    spki_algorithm = certificate_der[spki_content:spki_algorithm_end]
    if (
        inner_algorithm != outer_algorithm
        or inner_algorithm != _ED25519_ALGORITHM_IDENTIFIER_DER
        or spki_algorithm != _ED25519_ALGORITHM_IDENTIFIER_DER
    ):
        raise ValueError("certificate algorithms are not exact parameter-absent Ed25519")


def _der_tlv_bounds(data: bytes, offset: int) -> tuple[int, int, int]:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError("truncated DER value")
    tag = data[offset]
    length_octet = data[offset + 1]
    cursor = offset + 2
    if length_octet < 0x80:
        length = length_octet
    else:
        length_octets = length_octet & 0x7F
        if (
            length_octets == 0
            or length_octets > 4
            or cursor + length_octets > len(data)
            or data[cursor] == 0
        ):
            raise ValueError("invalid DER length")
        length = int.from_bytes(data[cursor : cursor + length_octets], "big")
        if length < 0x80:
            raise ValueError("noncanonical DER length")
        cursor += length_octets
    end = cursor + length
    if end > len(data):
        raise ValueError("truncated DER content")
    return tag, cursor, end


def _decode_ed25519_public_key(value: str) -> bytes:
    decoded = _decode_canonical_base64(value, expected_bytes=32, label="public key")
    try:
        Ed25519PublicKey.from_public_bytes(decoded)
    except ValueError as exc:
        raise ValueError("invalid Ed25519 public key") from exc
    return decoded


def _decode_ed25519_signature(value: str) -> bytes:
    return _decode_canonical_base64(value, expected_bytes=64, label="signature")


def _decode_canonical_base64(value: str, *, expected_bytes: int, label: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"invalid Ed25519 {label}") from exc
    if len(decoded) != expected_bytes or base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"invalid Ed25519 {label}")
    return decoded


def _verify_ed25519_signature(
    canonical_public_key: str,
    canonical_signature: str,
    message: bytes,
) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(_decode_ed25519_public_key(canonical_public_key)).verify(
            _decode_ed25519_signature(canonical_signature),
            message,
        )
    except (InvalidSignature, ValueError) as exc:
        raise NodeWorkloadAuthenticationError("Ed25519 proof is invalid") from exc


def _roles_are_exact(payload: str, expected: set[str]) -> bool:
    try:
        roles = json.loads(payload)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(roles, list)
        and all(isinstance(role, str) for role in roles)
        and len(roles) == len(set(roles))
        and set(roles) == expected
    )


def _bytes_sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise NodeWorkloadConfigurationError("trusted fixture clock must be timezone-aware")
    return value.astimezone(UTC)


def _parse_datetime(value: str) -> datetime:
    try:
        return _require_aware_utc(datetime.fromisoformat(value))
    except ValueError as exc:
        raise NodeWorkloadConfigurationError("stored PIS-005A timestamp is invalid") from exc
