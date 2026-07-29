"""Opaque, server-owned PIS-004A sessions and preauthentication transactions."""

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
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import cast
from urllib.parse import SplitResult, urlsplit
from uuid import uuid4

from authlib.oauth2.rfc7636 import create_s256_code_challenge  # type: ignore[import-untyped]
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ithildin_schemas import JsonObject
from pydantic import BaseModel, ConfigDict

from ithildin_api.enterprise_identity import (
    EnterpriseAuditOutcome,
    EnterpriseAuditReasonCode,
    EnterpriseIdentityError,
    EnterpriseIdentityStore,
    EnterprisePrincipalType,
    OrganizationAuthorityState,
    OrganizationRole,
    validate_safe_audit_labels,
)
from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

_OPAQUE_SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,256}$")
_AUTHENTICATION_GRANT_ID_PATTERN = re.compile(r"^agrant_[0-9a-f]{32}$")
_ASSERTION_AUDIT_ID_PATTERN = re.compile(r"^oaud_[0-9a-f]{32}$")
_HMAC_PREFIX = "hmac-sha256:"


class EnterpriseSessionError(RuntimeError):
    """Base class for fail-closed session errors."""


class SessionConfigurationError(EnterpriseSessionError):
    """Raised when trusted session configuration is unavailable or invalid."""


class SessionAuthenticationError(EnterpriseSessionError):
    """Raised when an opaque client credential does not authenticate."""


class SessionExpiredError(SessionAuthenticationError):
    """Raised when idle or absolute session expiry has elapsed."""


class SessionRevokedError(SessionAuthenticationError):
    """Raised when a session family has been revoked."""


class SessionReplayError(SessionRevokedError):
    """Raised when a rotated session handle is replayed."""


class SessionMutationRejectedError(SessionAuthenticationError):
    """Raised when origin or session-bound CSRF validation fails."""


class PreauthenticationError(EnterpriseSessionError):
    """Raised when a preauthentication transaction fails closed."""


class PreauthenticationReplayError(PreauthenticationError):
    """Raised when a one-use preauthentication transaction is replayed."""


class AuthenticationMethod(StrEnum):
    OIDC_FIXTURE = "oidc_fixture"
    LOCAL_RECOVERY = "local_recovery"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SessionContext(_FrozenModel):
    session_id: str
    family_id: str
    session_audit_id: str
    principal_id: str
    organization_id: str
    identity_generation: int
    membership_generation: int
    authentication_method: AuthenticationMethod
    recent_auth_at: datetime
    absolute_expires_at: datetime

    def has_recent_authentication(
        self,
        *,
        now: datetime,
        maximum_age: timedelta,
        allowed_methods: frozenset[AuthenticationMethod] | None = None,
    ) -> bool:
        trusted_now = _require_aware_utc(now)
        if maximum_age <= timedelta(0):
            raise SessionConfigurationError("recent-auth maximum age must be positive")
        if allowed_methods is not None and self.authentication_method not in allowed_methods:
            return False
        return self.recent_auth_at <= trusted_now < self.recent_auth_at + maximum_age

    def safe_audit_metadata(
        self,
        *,
        outcome: EnterpriseAuditOutcome,
        reason_code: EnterpriseAuditReasonCode,
    ) -> JsonObject:
        safe_outcome, safe_reason_code = validate_safe_audit_labels(
            outcome=outcome,
            reason_code=reason_code,
        )
        return {
            "session_audit_id": self.session_audit_id,
            "principal_id": self.principal_id,
            "organization_id": self.organization_id,
            "identity_generation": self.identity_generation,
            "membership_generation": self.membership_generation,
            "authentication_method": self.authentication_method.value,
            "outcome": safe_outcome,
            "reason_code": safe_reason_code,
        }


class SessionClientMaterial(_FrozenModel):
    handle: str
    csrf_token: str
    context: SessionContext


class PreauthenticationClientMaterial(_FrozenModel):
    transaction_handle: str
    transaction_audit_id: str
    state: str
    nonce: str
    pkce_challenge: str
    expires_at: datetime


class ConsumedPreauthentication(_FrozenModel):
    transaction_id: str
    transaction_audit_id: str
    organization_id: str
    provider_configuration_id: str
    exact_issuer: str
    configured_redirect_uri: str
    allowed_origin: str
    nonce_digest: str
    digest_key_generation: int
    pkce_verifier: str
    consumed_at: datetime

    def safe_audit_metadata(
        self,
        *,
        outcome: EnterpriseAuditOutcome,
        reason_code: EnterpriseAuditReasonCode,
    ) -> JsonObject:
        safe_outcome, safe_reason_code = validate_safe_audit_labels(
            outcome=outcome,
            reason_code=reason_code,
        )
        return {
            "transaction_audit_id": self.transaction_audit_id,
            "organization_id": self.organization_id,
            "provider_configuration_id": self.provider_configuration_id,
            "outcome": safe_outcome,
            "reason_code": safe_reason_code,
        }


class SessionDigestKeyRing:
    """Explicit generation-indexed HMAC keys; missing generations fail closed."""

    def __init__(self, keys: Mapping[int, bytes], *, active_generation: int) -> None:
        normalized = dict(keys)
        if active_generation < 1 or active_generation not in normalized:
            raise SessionConfigurationError("active digest-key generation is unavailable")
        if any(generation < 1 for generation in normalized):
            raise SessionConfigurationError("digest-key generations must be positive")
        if any(generation > active_generation for generation in normalized):
            raise SessionConfigurationError(
                "digest-key generations newer than the active generation are forbidden"
            )
        if any(len(key) < 32 for key in normalized.values()):
            raise SessionConfigurationError("digest keys must contain at least 256 bits")
        self._keys = normalized
        self.active_generation = active_generation

    @property
    def generations(self) -> tuple[int, ...]:
        return tuple(sorted(self._keys))

    def digest(self, generation: int, *, purpose: str, value: str) -> str:
        key = self._require_key(generation)
        payload = purpose.encode("ascii") + b"\x00" + value.encode("utf-8")
        return _HMAC_PREFIX + hmac.new(key, payload, hashlib.sha256).hexdigest()

    def seal(
        self,
        generation: int,
        *,
        plaintext: str,
        associated_data: bytes,
        nonce: bytes,
    ) -> str:
        if len(nonce) != 12:
            raise SessionConfigurationError("PKCE envelope nonce must be 96 bits")
        key = self._derive_envelope_key(generation)
        ciphertext = AESGCM(key).encrypt(
            nonce,
            plaintext.encode("ascii"),
            associated_data,
        )
        payload = base64.urlsafe_b64encode(nonce + ciphertext).rstrip(b"=")
        return "aes256gcm:v1:" + payload.decode("ascii")

    def open(
        self,
        generation: int,
        *,
        envelope: str,
        associated_data: bytes,
    ) -> str:
        prefix = "aes256gcm:v1:"
        if not envelope.startswith(prefix):
            raise SessionConfigurationError("PKCE verifier envelope is malformed")
        encoded = envelope.removeprefix(prefix).encode("ascii")
        padding = b"=" * (-len(encoded) % 4)
        try:
            payload = base64.b64decode(
                encoded + padding,
                altchars=b"-_",
                validate=True,
            )
        except (ValueError, binascii.Error) as exc:
            raise SessionConfigurationError("PKCE verifier envelope is malformed") from exc
        if len(payload) < 29:
            raise SessionConfigurationError("PKCE verifier envelope is malformed")
        nonce, ciphertext = payload[:12], payload[12:]
        try:
            plaintext = AESGCM(self._derive_envelope_key(generation)).decrypt(
                nonce,
                ciphertext,
                associated_data,
            )
            value = plaintext.decode("ascii")
        except (InvalidTag, UnicodeDecodeError) as exc:
            raise SessionConfigurationError("PKCE verifier envelope did not authenticate") from exc
        if not _OPAQUE_SECRET_PATTERN.fullmatch(value):
            raise SessionConfigurationError("PKCE verifier envelope plaintext is malformed")
        return value

    def _derive_envelope_key(self, generation: int) -> bytes:
        return hmac.new(
            self._require_key(generation),
            b"ithildin-pis004a-pkce-envelope-v1",
            hashlib.sha256,
        ).digest()

    def _require_key(self, generation: int) -> bytes:
        key = self._keys.get(generation)
        if key is None:
            raise SessionConfigurationError(f"digest-key generation {generation} is unavailable")
        return key


class EnterpriseSessionStore:
    """SQLite session authority with opaque handles and atomic one-use state."""

    def __init__(
        self,
        db_path: Path,
        *,
        key_ring: SessionDigestKeyRing,
        allowed_origins: frozenset[str],
        clock: Callable[[], datetime] | None = None,
        secret_factory: Callable[[int], str] | None = None,
        nonce_factory: Callable[[int], bytes] | None = None,
        id_factory: Callable[[str], str] | None = None,
        idle_ttl: timedelta = timedelta(minutes=30),
        absolute_ttl: timedelta = timedelta(hours=12),
        preauthentication_ttl: timedelta = timedelta(minutes=5),
        authentication_grant_ttl: timedelta = timedelta(minutes=1),
    ) -> None:
        verify_database_v2(db_path)
        if not allowed_origins:
            raise SessionConfigurationError("at least one allowed origin is required")
        for origin in allowed_origins:
            _validate_origin(origin)
        if idle_ttl <= timedelta(0):
            raise SessionConfigurationError("idle session lifetime must be positive")
        if absolute_ttl < idle_ttl:
            raise SessionConfigurationError(
                "absolute session lifetime must cover the idle lifetime"
            )
        if preauthentication_ttl <= timedelta(0):
            raise SessionConfigurationError("preauthentication lifetime must be positive")
        if not timedelta(0) < authentication_grant_ttl <= timedelta(minutes=5):
            raise SessionConfigurationError("authentication-grant lifetime is out of bounds")
        self.db_path = db_path
        self._key_ring = key_ring
        self._allowed_origins = allowed_origins
        self._clock = clock or _utc_now
        self._secret_factory = secret_factory or secrets.token_urlsafe
        self._nonce_factory = nonce_factory or secrets.token_bytes
        self._id_factory = id_factory or _random_id
        self._idle_ttl = idle_ttl
        self._absolute_ttl = absolute_ttl
        self._preauthentication_ttl = preauthentication_ttl
        self._authentication_grant_ttl = authentication_grant_ttl
        self._identity_store = EnterpriseIdentityStore(db_path, clock=self._clock)
        self._reconcile_digest_key_generations()

    def create_preauthentication(
        self,
        organization_id: str,
        provider_configuration_id: str,
        *,
        exact_issuer: str,
        configured_redirect_uri: str,
        allowed_origin: str,
    ) -> PreauthenticationClientMaterial:
        _validate_redirect_uri(configured_redirect_uri)
        _validate_origin(allowed_origin)
        if allowed_origin not in self._allowed_origins:
            raise PreauthenticationError("request origin is not allowed")
        if _redirect_origin(configured_redirect_uri) != allowed_origin:
            raise PreauthenticationError("redirect origin is not the allowed origin")
        now = _require_aware_utc(self._clock())
        expires_at = now + self._preauthentication_ttl
        handle = self._new_secret(32)
        state = self._new_secret(32)
        nonce = self._new_secret(32)
        pkce_verifier = self._new_secret(48)
        generation = self._key_ring.active_generation
        transaction_id = self._id_factory("patx_")
        transaction_audit_id = self._id_factory("paud_")
        envelope_nonce = self._nonce_factory(12)
        if len(envelope_nonce) != 12:
            raise SessionConfigurationError("PKCE envelope nonce source did not provide 96 bits")
        pkce_verifier_envelope = self._key_ring.seal(
            generation,
            plaintext=pkce_verifier,
            associated_data=_preauthentication_aad(
                transaction_id=transaction_id,
                organization_id=organization_id,
                provider_configuration_id=provider_configuration_id,
                exact_issuer=exact_issuer,
                configured_redirect_uri=configured_redirect_uri,
                allowed_origin=allowed_origin,
            ),
            nonce=envelope_nonce,
        )
        with self._transaction() as connection:
            self._require_active_digest_generation(connection)
            provider = connection.execute(
                """
                SELECT pc.exact_issuer, pc.enabled, o.enabled
                FROM identity_provider_configurations AS pc
                JOIN identity_organizations AS o
                  ON o.organization_id = pc.organization_id
                WHERE pc.organization_id = ?
                  AND pc.provider_configuration_id = ?
                """,
                (organization_id, provider_configuration_id),
            ).fetchone()
            if provider is None:
                raise PreauthenticationError("provider configuration is unavailable")
            if not bool(provider["enabled"]) or not bool(provider[2]):
                raise PreauthenticationError("provider configuration is disabled")
            if str(provider["exact_issuer"]) != exact_issuer:
                raise PreauthenticationError("configured issuer mismatch")
            connection.execute(
                """
                INSERT INTO identity_preauthentication_transactions (
                    transaction_id, handle_digest, digest_key_generation,
                    transaction_audit_id, organization_id,
                    provider_configuration_id, exact_issuer,
                    configured_redirect_uri, allowed_origin, state_digest,
                    nonce_digest, pkce_verifier_envelope, created_at, expires_at,
                    status, consumed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL)
                """,
                (
                    transaction_id,
                    self._key_ring.digest(
                        generation,
                        purpose="preauthentication-handle",
                        value=handle,
                    ),
                    generation,
                    transaction_audit_id,
                    organization_id,
                    provider_configuration_id,
                    exact_issuer,
                    configured_redirect_uri,
                    allowed_origin,
                    self._key_ring.digest(
                        generation,
                        purpose="preauthentication-state",
                        value=state,
                    ),
                    self._key_ring.digest(
                        generation,
                        purpose="preauthentication-nonce",
                        value=nonce,
                    ),
                    pkce_verifier_envelope,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
        return PreauthenticationClientMaterial(
            transaction_handle=handle,
            transaction_audit_id=transaction_audit_id,
            state=state,
            nonce=nonce,
            pkce_challenge=_pkce_challenge(pkce_verifier),
            expires_at=expires_at,
        )

    def consume_preauthentication(
        self,
        transaction_handle: str,
        *,
        state: str,
        exact_issuer: str,
        configured_redirect_uri: str,
        allowed_origin: str,
    ) -> ConsumedPreauthentication:
        if _OPAQUE_SECRET_PATTERN.fullmatch(state) is None:
            raise PreauthenticationError("preauthentication state did not authenticate")
        now = _require_aware_utc(self._clock())
        failure: PreauthenticationError | None = None
        consumed: ConsumedPreauthentication | None = None
        pkce_verifier: str | None = None
        with self._transaction() as connection:
            located = self._find_by_opaque_handle(
                connection,
                table="identity_preauthentication_transactions",
                purpose="preauthentication-handle",
                handle=transaction_handle,
            )
            if located is None:
                failure = PreauthenticationError(
                    "preauthentication credential did not authenticate"
                )
            else:
                row, located_generation = located
                stored_generation = int(row["digest_key_generation"])
                if stored_generation != located_generation:
                    failure = PreauthenticationError(
                        "preauthentication digest-key generation is inconsistent"
                    )
                elif str(row["status"]) != "active":
                    failure = PreauthenticationReplayError(
                        "preauthentication transaction is no longer active"
                    )
                elif now >= _parse_datetime(str(row["expires_at"])):
                    connection.execute(
                        """
                        UPDATE identity_preauthentication_transactions
                        SET status = 'revoked', consumed_at = ?,
                            pkce_verifier_envelope = ?
                        WHERE transaction_id = ? AND status = 'active'
                        """,
                        (
                            now.isoformat(),
                            _redacted_envelope(str(row["pkce_verifier_envelope"])),
                            str(row["transaction_id"]),
                        ),
                    )
                    failure = PreauthenticationError("preauthentication transaction has expired")
                elif (
                    str(row["exact_issuer"]) != exact_issuer
                    or str(row["configured_redirect_uri"]) != configured_redirect_uri
                    or str(row["allowed_origin"]) != allowed_origin
                    or allowed_origin not in self._allowed_origins
                ):
                    failure = PreauthenticationError("preauthentication binding mismatch")
                elif not hmac.compare_digest(
                    str(row["state_digest"]),
                    self._key_ring.digest(
                        stored_generation,
                        purpose="preauthentication-state",
                        value=state,
                    ),
                ):
                    failure = PreauthenticationError("preauthentication state did not authenticate")
                else:
                    try:
                        pkce_verifier = self._key_ring.open(
                            stored_generation,
                            envelope=str(row["pkce_verifier_envelope"]),
                            associated_data=_preauthentication_aad_from_row(row),
                        )
                    except SessionConfigurationError:
                        failure = PreauthenticationError("protected PKCE verifier is unavailable")
                        pkce_verifier = None
                if failure is None and pkce_verifier is not None:
                    updated = connection.execute(
                        """
                        UPDATE identity_preauthentication_transactions
                        SET status = 'consumed', consumed_at = ?,
                            pkce_verifier_envelope = ?
                        WHERE transaction_id = ? AND status = 'active'
                        """,
                        (
                            now.isoformat(),
                            _redacted_envelope(str(row["pkce_verifier_envelope"])),
                            str(row["transaction_id"]),
                        ),
                    )
                    if updated.rowcount != 1:
                        failure = PreauthenticationReplayError(
                            "preauthentication transaction was consumed concurrently"
                        )
                    else:
                        consumed = ConsumedPreauthentication(
                            transaction_id=str(row["transaction_id"]),
                            transaction_audit_id=str(row["transaction_audit_id"]),
                            organization_id=str(row["organization_id"]),
                            provider_configuration_id=str(row["provider_configuration_id"]),
                            exact_issuer=str(row["exact_issuer"]),
                            configured_redirect_uri=str(row["configured_redirect_uri"]),
                            allowed_origin=str(row["allowed_origin"]),
                            nonce_digest=str(row["nonce_digest"]),
                            digest_key_generation=stored_generation,
                            pkce_verifier=pkce_verifier,
                            consumed_at=now,
                        )
        if failure is not None:
            raise failure
        if consumed is None:
            raise PreauthenticationError("preauthentication transaction failed closed")
        return consumed

    def validate_preauthentication_nonce(
        self,
        transaction: ConsumedPreauthentication,
        *,
        nonce: str,
    ) -> None:
        if _OPAQUE_SECRET_PATTERN.fullmatch(nonce) is None:
            raise PreauthenticationError("preauthentication nonce did not authenticate")
        with self._connection() as connection:
            generation = connection.execute(
                """
                SELECT status
                FROM identity_session_digest_key_generations
                WHERE digest_key_generation = ?
                """,
                (transaction.digest_key_generation,),
            ).fetchone()
        if generation is None or str(generation[0]) not in {"active", "retained"}:
            raise PreauthenticationError("preauthentication digest-key generation is retired")
        expected = self._key_ring.digest(
            transaction.digest_key_generation,
            purpose="preauthentication-nonce",
            value=nonce,
        )
        if not hmac.compare_digest(transaction.nonce_digest, expected):
            raise PreauthenticationError("preauthentication nonce did not authenticate")

    def _record_oidc_authentication_grant(
        self,
        *,
        assertion_audit_id: str,
        organization_id: str,
        provider_configuration_id: str,
        exact_issuer: str,
        subject: str,
        authentication_time: datetime,
        token_expires_at: datetime,
    ) -> str:
        if _ASSERTION_AUDIT_ID_PATTERN.fullmatch(assertion_audit_id) is None:
            raise SessionAuthenticationError("OIDC assertion evidence identifier is malformed")
        now = _require_aware_utc(self._clock())
        trusted_authentication_time = _require_aware_utc(authentication_time)
        trusted_token_expires_at = _require_aware_utc(token_expires_at)
        if (
            trusted_authentication_time >= trusted_token_expires_at
            or trusted_token_expires_at <= now
        ):
            raise SessionAuthenticationError("OIDC assertion evidence is not currently valid")
        resolution = self._identity_store.resolve_identity(
            organization_id,
            provider_configuration_id,
            exact_issuer=exact_issuer,
            subject=subject,
        )
        authority = self._current_organization_authority(
            resolution.principal_id,
            organization_id,
        )
        if (
            authority.principal_type is not EnterprisePrincipalType.HUMAN
            or resolution.principal_type is not EnterprisePrincipalType.HUMAN
            or resolution.identity_generation != authority.identity_generation
        ):
            raise SessionAuthenticationError(
                "OIDC assertion does not resolve current human authority"
            )
        authentication_grant_id = self._id_factory("agrant_")
        expires_at = min(
            trusted_token_expires_at,
            now + self._authentication_grant_ttl,
        )
        with self._transaction() as connection:
            self._require_matching_authority(connection, authority)
            provider = connection.execute(
                """
                SELECT pc.enabled AS provider_enabled,
                       pc.generation AS provider_generation,
                       o.enabled AS organization_enabled,
                       b.principal_id
                FROM identity_provider_configurations AS pc
                JOIN identity_organizations AS o
                  ON o.organization_id = pc.organization_id
                JOIN identity_bindings AS b
                  ON b.organization_id = pc.organization_id
                 AND b.provider_configuration_id = pc.provider_configuration_id
                 AND b.exact_issuer = pc.exact_issuer
                WHERE pc.organization_id = ?
                  AND pc.provider_configuration_id = ?
                  AND pc.exact_issuer = ?
                  AND b.subject = ?
                """,
                (
                    organization_id,
                    provider_configuration_id,
                    exact_issuer,
                    subject,
                ),
            ).fetchone()
            if (
                provider is None
                or not bool(provider["provider_enabled"])
                or not bool(provider["organization_enabled"])
                or str(provider["principal_id"]) != authority.principal_id
            ):
                raise SessionAuthenticationError("OIDC assertion identity authority is unavailable")
            connection.execute(
                """
                INSERT INTO identity_authentication_grants (
                    authentication_grant_id, assertion_audit_id,
                    organization_id, provider_configuration_id,
                    provider_configuration_generation, principal_id, identity_generation,
                    membership_generation, authentication_method,
                    authentication_time, created_at, expires_at,
                    status, consumed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'oidc_fixture', ?, ?, ?,
                          'active', NULL)
                """,
                (
                    authentication_grant_id,
                    assertion_audit_id,
                    organization_id,
                    provider_configuration_id,
                    int(provider["provider_generation"]),
                    authority.principal_id,
                    authority.identity_generation,
                    authority.membership_generation,
                    trusted_authentication_time.isoformat(),
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
        return authentication_grant_id

    def issue_session(
        self,
        authentication_grant_id: str,
    ) -> SessionClientMaterial:
        if _AUTHENTICATION_GRANT_ID_PATTERN.fullmatch(authentication_grant_id) is None:
            raise SessionAuthenticationError("authentication grant did not authenticate")
        now = _require_aware_utc(self._clock())
        family_id = self._id_factory("sfam_")
        session_id = self._id_factory("sess_")
        session_audit_id = self._id_factory("saud_")
        handle = self._new_secret(32)
        csrf_token = self._new_secret(32)
        generation = self._key_ring.active_generation
        absolute_expires_at = now + self._absolute_ttl
        idle_expires_at = min(now + self._idle_ttl, absolute_expires_at)
        with self._transaction() as connection:
            self._require_active_digest_generation(connection)
            grant = connection.execute(
                """
                SELECT organization_id, provider_configuration_id,
                       provider_configuration_generation, principal_id,
                       identity_generation, membership_generation,
                       authentication_method, authentication_time,
                       expires_at, status
                FROM identity_authentication_grants
                WHERE authentication_grant_id = ?
                """,
                (authentication_grant_id,),
            ).fetchone()
            if (
                grant is None
                or str(grant["status"]) != "active"
                or str(grant["authentication_method"]) != AuthenticationMethod.OIDC_FIXTURE.value
                or now >= _parse_datetime(str(grant["expires_at"]))
            ):
                raise SessionAuthenticationError("authentication grant did not authenticate")
            organization_id = str(grant["organization_id"])
            principal_id = str(grant["principal_id"])
            authority = self._organization_authority_from_connection(
                connection,
                principal_id=principal_id,
                organization_id=organization_id,
            )
            if authority is None:
                raise SessionAuthenticationError("authentication grant authority is stale")
            if authority.principal_type is not EnterprisePrincipalType.HUMAN:
                raise SessionAuthenticationError("interactive sessions require a human principal")
            if authority.identity_generation != int(
                grant["identity_generation"]
            ) or authority.membership_generation != int(grant["membership_generation"]):
                raise SessionAuthenticationError("authentication grant authority is stale")
            provider = connection.execute(
                """
                SELECT pc.enabled AS provider_enabled,
                       pc.generation AS provider_generation,
                       o.enabled AS organization_enabled,
                       b.principal_id
                FROM identity_provider_configurations AS pc
                JOIN identity_organizations AS o
                  ON o.organization_id = pc.organization_id
                JOIN identity_bindings AS b
                  ON b.organization_id = pc.organization_id
                 AND b.provider_configuration_id = pc.provider_configuration_id
                WHERE pc.organization_id = ?
                  AND pc.provider_configuration_id = ?
                  AND b.principal_id = ?
                """,
                (
                    organization_id,
                    str(grant["provider_configuration_id"]),
                    principal_id,
                ),
            ).fetchone()
            if (
                provider is None
                or not bool(provider["provider_enabled"])
                or not bool(provider["organization_enabled"])
                or str(provider["principal_id"]) != principal_id
                or int(provider["provider_generation"])
                != int(grant["provider_configuration_generation"])
            ):
                raise SessionAuthenticationError(
                    "authentication grant provider configuration is stale"
                )
            consumed = connection.execute(
                """
                UPDATE identity_authentication_grants
                SET status = 'consumed', consumed_at = ?
                WHERE authentication_grant_id = ? AND status = 'active'
                """,
                (now.isoformat(), authentication_grant_id),
            )
            if consumed.rowcount != 1:
                raise SessionAuthenticationError("authentication grant was consumed concurrently")
            connection.execute(
                """
                INSERT INTO identity_session_families (
                    family_id, organization_id, principal_id,
                    identity_generation, membership_generation,
                    created_at, revoked_at, revocation_reason
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    family_id,
                    organization_id,
                    principal_id,
                    authority.identity_generation,
                    authority.membership_generation,
                    now.isoformat(),
                ),
            )
            self._insert_session(
                connection,
                session_id=session_id,
                family_id=family_id,
                session_audit_id=session_audit_id,
                handle=handle,
                csrf_token=csrf_token,
                digest_key_generation=generation,
                authentication_method=AuthenticationMethod.OIDC_FIXTURE,
                recent_auth_at=_parse_datetime(str(grant["authentication_time"])),
                created_at=now,
                idle_expires_at=idle_expires_at,
                absolute_expires_at=absolute_expires_at,
            )
        context = SessionContext(
            session_id=session_id,
            family_id=family_id,
            session_audit_id=session_audit_id,
            principal_id=principal_id,
            organization_id=organization_id,
            identity_generation=authority.identity_generation,
            membership_generation=authority.membership_generation,
            authentication_method=AuthenticationMethod.OIDC_FIXTURE,
            recent_auth_at=_parse_datetime(str(grant["authentication_time"])),
            absolute_expires_at=absolute_expires_at,
        )
        return SessionClientMaterial(
            handle=handle,
            csrf_token=csrf_token,
            context=context,
        )

    def validate_session(self, handle: str) -> SessionContext:
        return self._validate_session(
            handle,
            allowed_origin=None,
            csrf_token=None,
            touch=True,
        )

    def validate_mutation(
        self,
        handle: str,
        *,
        allowed_origin: str,
        csrf_token: str,
    ) -> SessionContext:
        return self._validate_session(
            handle,
            allowed_origin=allowed_origin,
            csrf_token=csrf_token,
            touch=True,
        )

    def rotate_session(self, handle: str) -> SessionClientMaterial:
        now = _require_aware_utc(self._clock())
        failure: EnterpriseSessionError | None = None
        material: SessionClientMaterial | None = None
        with self._transaction() as connection:
            self._require_active_digest_generation(connection)
            row, context, failure = self._evaluate_session_locked(
                connection,
                handle=handle,
                now=now,
            )
            if row is not None and context is not None and failure is None:
                new_session_id = self._id_factory("sess_")
                new_session_audit_id = self._id_factory("saud_")
                new_handle = self._new_secret(32)
                new_csrf_token = self._new_secret(32)
                generation = self._key_ring.active_generation
                idle_expires_at = min(
                    now + self._idle_ttl,
                    context.absolute_expires_at,
                )
                self._insert_session(
                    connection,
                    session_id=new_session_id,
                    family_id=context.family_id,
                    session_audit_id=new_session_audit_id,
                    handle=new_handle,
                    csrf_token=new_csrf_token,
                    digest_key_generation=generation,
                    authentication_method=context.authentication_method,
                    recent_auth_at=context.recent_auth_at,
                    created_at=now,
                    idle_expires_at=idle_expires_at,
                    absolute_expires_at=context.absolute_expires_at,
                )
                updated = connection.execute(
                    """
                    UPDATE identity_sessions
                    SET status = 'rotated', rotated_to_session_id = ?
                    WHERE session_id = ? AND status = 'active'
                    """,
                    (new_session_id, context.session_id),
                )
                if updated.rowcount != 1:
                    raise SessionAuthenticationError("session rotation lost an atomic update")
                material = SessionClientMaterial(
                    handle=new_handle,
                    csrf_token=new_csrf_token,
                    context=context.model_copy(
                        update={
                            "session_id": new_session_id,
                            "session_audit_id": new_session_audit_id,
                        }
                    ),
                )
        if failure is not None:
            raise failure
        if material is None:
            raise SessionAuthenticationError("session rotation failed closed")
        return material

    def revoke_family(self, handle: str, *, reason_code: str) -> None:
        if not 1 <= len(reason_code) <= 64:
            raise SessionConfigurationError("revocation reason is malformed")
        now = _require_aware_utc(self._clock())
        failure: EnterpriseSessionError | None = None
        with self._transaction() as connection:
            located = self._find_by_opaque_handle(
                connection,
                table="identity_sessions",
                purpose="session-handle",
                handle=handle,
            )
            if located is None:
                failure = SessionAuthenticationError("session credential did not authenticate")
            else:
                row, located_generation = located
                if int(row["digest_key_generation"]) != located_generation:
                    failure = SessionConfigurationError(
                        "stored session digest-key generation is inconsistent"
                    )
                else:
                    self._revoke_family_locked(
                        connection,
                        family_id=str(row["family_id"]),
                        now=now,
                        reason_code=reason_code,
                    )
        if failure is not None:
            raise failure

    def _validate_session(
        self,
        handle: str,
        *,
        allowed_origin: str | None,
        csrf_token: str | None,
        touch: bool,
    ) -> SessionContext:
        now = _require_aware_utc(self._clock())
        failure: EnterpriseSessionError | None = None
        result: SessionContext | None = None
        with self._transaction() as connection:
            row, context, failure = self._evaluate_session_locked(
                connection,
                handle=handle,
                now=now,
            )
            if row is not None and context is not None and failure is None:
                if allowed_origin is not None:
                    if allowed_origin not in self._allowed_origins:
                        failure = SessionMutationRejectedError("request origin is not allowed")
                    elif csrf_token is None:
                        failure = SessionMutationRejectedError(
                            "session-bound CSRF credential is required"
                        )
                    elif _OPAQUE_SECRET_PATTERN.fullmatch(csrf_token) is None:
                        failure = SessionMutationRejectedError(
                            "session-bound CSRF credential did not authenticate"
                        )
                    else:
                        generation = int(row["digest_key_generation"])
                        expected_csrf = self._key_ring.digest(
                            generation,
                            purpose="session-csrf",
                            value=csrf_token,
                        )
                        if not hmac.compare_digest(
                            str(row["csrf_digest"]),
                            expected_csrf,
                        ):
                            failure = SessionMutationRejectedError(
                                "session-bound CSRF credential did not authenticate"
                            )
                if failure is None and touch:
                    idle_expires_at = min(
                        now + self._idle_ttl,
                        context.absolute_expires_at,
                    )
                    updated = connection.execute(
                        """
                        UPDATE identity_sessions
                        SET last_seen_at = ?, idle_expires_at = ?
                        WHERE session_id = ? AND status = 'active'
                        """,
                        (
                            now.isoformat(),
                            idle_expires_at.isoformat(),
                            context.session_id,
                        ),
                    )
                    if updated.rowcount != 1:
                        failure = SessionAuthenticationError("session changed concurrently")
                if failure is None:
                    result = context
        if failure is not None:
            raise failure
        if result is None:
            raise SessionAuthenticationError("session validation failed closed")
        return result

    def _evaluate_session_locked(
        self,
        connection: sqlite3.Connection,
        *,
        handle: str,
        now: datetime,
    ) -> tuple[sqlite3.Row | None, SessionContext | None, EnterpriseSessionError | None]:
        located = self._find_by_opaque_handle(
            connection,
            table="identity_sessions",
            purpose="session-handle",
            handle=handle,
        )
        if located is None:
            return (
                None,
                None,
                SessionAuthenticationError("session credential did not authenticate"),
            )
        row, located_generation = located
        if int(row["digest_key_generation"]) != located_generation:
            return (
                row,
                None,
                SessionConfigurationError("stored session digest-key generation is inconsistent"),
            )
        family_id = str(row["family_id"])
        status = str(row["status"])
        if status == "rotated":
            self._revoke_family_locked(
                connection,
                family_id=family_id,
                now=now,
                reason_code="rotated_handle_replay",
            )
            return (
                row,
                None,
                SessionReplayError("rotated session replay revoked the session family"),
            )
        if status != "active" or row["family_revoked_at"] is not None:
            return row, None, SessionRevokedError("session family is revoked")
        idle_expires_at = _parse_datetime(str(row["idle_expires_at"]))
        absolute_expires_at = _parse_datetime(str(row["absolute_expires_at"]))
        last_seen_at = _parse_datetime(str(row["last_seen_at"]))
        if now < last_seen_at:
            self._revoke_family_locked(
                connection,
                family_id=family_id,
                now=now,
                reason_code="trusted_clock_regressed",
            )
            return row, None, SessionRevokedError("trusted session clock regressed")
        if now >= idle_expires_at or now >= absolute_expires_at:
            connection.execute(
                """
                UPDATE identity_sessions
                SET status = 'expired', revoked_at = ?
                WHERE session_id = ? AND status = 'active'
                """,
                (now.isoformat(), str(row["session_id"])),
            )
            return row, None, SessionExpiredError("session has expired")
        authority = self._organization_authority_from_connection(
            connection,
            principal_id=str(row["principal_id"]),
            organization_id=str(row["organization_id"]),
        )
        if authority is None:
            self._revoke_family_locked(
                connection,
                family_id=family_id,
                now=now,
                reason_code="authority_unavailable",
            )
            return row, None, SessionRevokedError("session authority is unavailable")
        if authority.principal_type is not EnterprisePrincipalType.HUMAN:
            self._revoke_family_locked(
                connection,
                family_id=family_id,
                now=now,
                reason_code="nonhuman_session_forbidden",
            )
            return (
                row,
                None,
                SessionRevokedError("interactive session principal is not human"),
            )
        if authority.identity_generation != int(
            row["identity_generation"]
        ) or authority.membership_generation != int(row["membership_generation"]):
            self._revoke_family_locked(
                connection,
                family_id=family_id,
                now=now,
                reason_code="authority_generation_changed",
            )
            return (
                row,
                None,
                SessionRevokedError("session authority generation changed"),
            )
        context = SessionContext(
            session_id=str(row["session_id"]),
            family_id=family_id,
            session_audit_id=str(row["session_audit_id"]),
            principal_id=authority.principal_id,
            organization_id=authority.organization_id,
            identity_generation=authority.identity_generation,
            membership_generation=authority.membership_generation,
            authentication_method=AuthenticationMethod(str(row["authentication_method"])),
            recent_auth_at=_parse_datetime(str(row["recent_auth_at"])),
            absolute_expires_at=absolute_expires_at,
        )
        return row, context, None

    def _find_by_opaque_handle(
        self,
        connection: sqlite3.Connection,
        *,
        table: str,
        purpose: str,
        handle: str,
    ) -> tuple[sqlite3.Row, int] | None:
        if table not in {
            "identity_sessions",
            "identity_preauthentication_transactions",
        }:
            raise SessionConfigurationError("opaque lookup table is invalid")
        if _OPAQUE_SECRET_PATTERN.fullmatch(handle) is None:
            return None
        usable_generations = {
            int(row[0])
            for row in connection.execute(
                """
                SELECT digest_key_generation
                FROM identity_session_digest_key_generations
                WHERE status IN ('active', 'retained')
                """
            ).fetchall()
        }
        matches: list[tuple[sqlite3.Row, int]] = []
        for generation in (
            value for value in self._key_ring.generations if value in usable_generations
        ):
            digest = self._key_ring.digest(
                generation,
                purpose=purpose,
                value=handle,
            )
            if table == "identity_sessions":
                row = connection.execute(
                    """
                    SELECT s.*, f.organization_id, f.principal_id,
                           f.identity_generation, f.membership_generation,
                           f.revoked_at AS family_revoked_at
                    FROM identity_sessions AS s
                    JOIN identity_session_families AS f
                      ON f.family_id = s.family_id
                    WHERE s.handle_digest = ?
                    """,
                    (digest,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM identity_preauthentication_transactions
                    WHERE handle_digest = ?
                    """,
                    (digest,),
                ).fetchone()
            if row is not None:
                matches.append((cast(sqlite3.Row, row), generation))
        if len(matches) > 1:
            raise SessionConfigurationError("opaque credential lookup is ambiguous")
        return matches[0] if matches else None

    def _reconcile_digest_key_generations(self) -> None:
        now = _require_aware_utc(self._clock())
        supplied = set(self._key_ring.generations)
        active_generation = self._key_ring.active_generation
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT digest_key_generation, status
                FROM identity_session_digest_key_generations
                ORDER BY digest_key_generation
                """
            ).fetchall()
            persisted = {int(row[0]): str(row[1]) for row in rows}
            if not persisted:
                for generation in sorted(supplied):
                    status = "active" if generation == active_generation else "retained"
                    connection.execute(
                        """
                        INSERT INTO identity_session_digest_key_generations (
                            digest_key_generation, status, first_seen_at,
                            activated_at, retired_at
                        ) VALUES (?, ?, ?, ?, NULL)
                        """,
                        (
                            generation,
                            status,
                            now.isoformat(),
                            now.isoformat() if status == "active" else None,
                        ),
                    )
                return

            if any(
                status == "retired" and generation in supplied
                for generation, status in persisted.items()
            ):
                raise SessionConfigurationError("retired digest-key generation cannot be restored")
            maximum_seen = max(persisted)
            if any(
                generation not in persisted and generation <= maximum_seen
                for generation in supplied
            ):
                raise SessionConfigurationError("digest-key generation reuse is forbidden")
            current_active = next(
                (generation for generation, status in persisted.items() if status == "active"),
                None,
            )
            if current_active is None:
                raise SessionConfigurationError(
                    "persisted digest-key authority has no active generation"
                )
            if active_generation < current_active:
                raise SessionConfigurationError("digest-key active generation cannot move backward")
            if active_generation != current_active and active_generation <= maximum_seen:
                raise SessionConfigurationError(
                    "digest-key activation must use a new monotonic generation"
                )

            retired = {
                generation
                for generation, status in persisted.items()
                if status in {"active", "retained"} and generation not in supplied
            }
            for generation in sorted(retired):
                connection.execute(
                    """
                    UPDATE identity_session_digest_key_generations
                    SET status = 'retired', retired_at = ?
                    WHERE digest_key_generation = ?
                      AND status IN ('active', 'retained')
                    """,
                    (now.isoformat(), generation),
                )
            if retired:
                self._revoke_retired_generations_locked(
                    connection,
                    generations=retired,
                    now=now,
                )

            if active_generation != current_active:
                connection.execute(
                    """
                    UPDATE identity_session_digest_key_generations
                    SET status = 'retained'
                    WHERE digest_key_generation = ? AND status = 'active'
                    """,
                    (current_active,),
                )
            for generation in sorted(supplied - set(persisted)):
                status = "active" if generation == active_generation else "retained"
                connection.execute(
                    """
                    INSERT INTO identity_session_digest_key_generations (
                        digest_key_generation, status, first_seen_at,
                        activated_at, retired_at
                    ) VALUES (?, ?, ?, ?, NULL)
                    """,
                    (
                        generation,
                        status,
                        now.isoformat(),
                        now.isoformat() if status == "active" else None,
                    ),
                )
            if active_generation in persisted:
                connection.execute(
                    """
                    UPDATE identity_session_digest_key_generations
                    SET status = 'active',
                        activated_at = COALESCE(activated_at, ?)
                    WHERE digest_key_generation = ? AND status != 'retired'
                    """,
                    (now.isoformat(), active_generation),
                )
            self._require_active_digest_generation(connection)

    @staticmethod
    def _revoke_retired_generations_locked(
        connection: sqlite3.Connection,
        *,
        generations: set[int],
        now: datetime,
    ) -> None:
        placeholders = ", ".join("?" for _ in generations)
        parameters = tuple(sorted(generations))
        connection.execute(
            f"""
            UPDATE identity_session_families
            SET revoked_at = COALESCE(revoked_at, ?),
                revocation_reason = COALESCE(
                    revocation_reason,
                    'digest_key_generation_retired'
                )
            WHERE family_id IN (
                SELECT family_id FROM identity_sessions
                WHERE digest_key_generation IN ({placeholders})
            )
            """,
            (now.isoformat(), *parameters),
        )
        connection.execute(
            f"""
            UPDATE identity_sessions
            SET status = 'revoked', revoked_at = ?
            WHERE digest_key_generation IN ({placeholders})
              AND status IN ('active', 'rotated')
            """,
            (now.isoformat(), *parameters),
        )
        rows = connection.execute(
            f"""
            SELECT transaction_id, pkce_verifier_envelope
            FROM identity_preauthentication_transactions
            WHERE digest_key_generation IN ({placeholders})
              AND status = 'active'
            """,
            parameters,
        ).fetchall()
        for row in rows:
            connection.execute(
                """
                UPDATE identity_preauthentication_transactions
                SET status = 'revoked', consumed_at = ?,
                    pkce_verifier_envelope = ?
                WHERE transaction_id = ? AND status = 'active'
                """,
                (
                    now.isoformat(),
                    _redacted_envelope(str(row[1])),
                    str(row[0]),
                ),
            )

    def _require_active_digest_generation(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        row = connection.execute(
            """
            SELECT status FROM identity_session_digest_key_generations
            WHERE digest_key_generation = ?
            """,
            (self._key_ring.active_generation,),
        ).fetchone()
        if row is None or str(row[0]) != "active":
            raise SessionConfigurationError(
                "active digest-key generation is not current server authority"
            )

    def _insert_session(
        self,
        connection: sqlite3.Connection,
        *,
        session_id: str,
        family_id: str,
        session_audit_id: str,
        handle: str,
        csrf_token: str,
        digest_key_generation: int,
        authentication_method: AuthenticationMethod,
        recent_auth_at: datetime,
        created_at: datetime,
        idle_expires_at: datetime,
        absolute_expires_at: datetime,
    ) -> None:
        connection.execute(
            """
            INSERT INTO identity_sessions (
                session_id, family_id, handle_digest, digest_key_generation,
                session_audit_id, csrf_digest, authentication_method,
                recent_auth_at, created_at, last_seen_at, idle_expires_at,
                absolute_expires_at, status, rotated_to_session_id, revoked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL, NULL)
            """,
            (
                session_id,
                family_id,
                self._key_ring.digest(
                    digest_key_generation,
                    purpose="session-handle",
                    value=handle,
                ),
                digest_key_generation,
                session_audit_id,
                self._key_ring.digest(
                    digest_key_generation,
                    purpose="session-csrf",
                    value=csrf_token,
                ),
                authentication_method.value,
                recent_auth_at.isoformat(),
                created_at.isoformat(),
                created_at.isoformat(),
                idle_expires_at.isoformat(),
                absolute_expires_at.isoformat(),
            ),
        )

    @staticmethod
    def _revoke_family_locked(
        connection: sqlite3.Connection,
        *,
        family_id: str,
        now: datetime,
        reason_code: str,
    ) -> None:
        connection.execute(
            """
            UPDATE identity_session_families
            SET revoked_at = COALESCE(revoked_at, ?),
                revocation_reason = COALESCE(revocation_reason, ?)
            WHERE family_id = ?
            """,
            (now.isoformat(), reason_code, family_id),
        )
        connection.execute(
            """
            UPDATE identity_sessions
            SET status = 'revoked', revoked_at = ?
            WHERE family_id = ? AND status = 'active'
            """,
            (now.isoformat(), family_id),
        )

    def _current_organization_authority(
        self,
        principal_id: str,
        organization_id: str,
    ) -> OrganizationAuthorityState:
        try:
            return self._identity_store.current_organization_authority(
                principal_id,
                organization_id,
            )
        except EnterpriseIdentityError as exc:
            raise SessionAuthenticationError("organization authority is unavailable") from exc

    @staticmethod
    def _require_matching_authority(
        connection: sqlite3.Connection,
        expected: OrganizationAuthorityState,
    ) -> None:
        current = EnterpriseSessionStore._organization_authority_from_connection(
            connection,
            principal_id=expected.principal_id,
            organization_id=expected.organization_id,
        )
        if current is None or current != expected:
            raise SessionAuthenticationError(
                "organization authority changed during session issuance"
            )

    @staticmethod
    def _organization_authority_from_connection(
        connection: sqlite3.Connection,
        *,
        principal_id: str,
        organization_id: str,
    ) -> OrganizationAuthorityState | None:
        row = connection.execute(
            """
            SELECT p.principal_type, p.enabled, p.identity_generation,
                   o.enabled, om.enabled, om.membership_generation,
                   om.roles_json
            FROM identity_principals AS p
            JOIN identity_organization_memberships AS om
              ON om.principal_id = p.principal_id
             AND om.organization_id = ?
            JOIN identity_organizations AS o
              ON o.organization_id = om.organization_id
            WHERE p.principal_id = ?
            """,
            (organization_id, principal_id),
        ).fetchone()
        if row is None or any(not bool(row[index]) for index in (1, 3, 4)):
            return None
        try:
            raw_roles = json.loads(str(row[6]))
            if not isinstance(raw_roles, list) or not all(
                isinstance(value, str) for value in raw_roles
            ):
                return None
            organization_roles = tuple(
                sorted(
                    (OrganizationRole(value) for value in raw_roles),
                    key=lambda role: role.value,
                )
            )
            principal_type = EnterprisePrincipalType(str(row[0]))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        return OrganizationAuthorityState(
            principal_id=principal_id,
            principal_type=principal_type,
            organization_id=organization_id,
            identity_generation=int(row[2]),
            membership_generation=int(row[5]),
            organization_roles=organization_roles,
        )

    def _new_secret(self, entropy_bytes: int) -> str:
        value = self._secret_factory(entropy_bytes)
        if not _OPAQUE_SECRET_PATTERN.fullmatch(value):
            raise SessionConfigurationError(
                "opaque secret source did not provide a high-entropy-shaped value"
            )
        return value

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _transaction(self) -> _ImmediateTransaction:
        return _ImmediateTransaction(self._connection())


class _ImmediateTransaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> sqlite3.Connection:
        self.connection.isolation_level = None
        self.connection.execute("BEGIN IMMEDIATE")
        return self.connection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        try:
            self.connection.execute("ROLLBACK" if exc_type is not None else "COMMIT")
        finally:
            self.connection.close()


def _pkce_challenge(verifier: str) -> str:
    return str(create_s256_code_challenge(verifier))


def _preauthentication_aad(
    *,
    transaction_id: str,
    organization_id: str,
    provider_configuration_id: str,
    exact_issuer: str,
    configured_redirect_uri: str,
    allowed_origin: str,
) -> bytes:
    return json.dumps(
        [
            "ithildin-pis004a-pkce-envelope-v1",
            transaction_id,
            organization_id,
            provider_configuration_id,
            exact_issuer,
            configured_redirect_uri,
            allowed_origin,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")


def _preauthentication_aad_from_row(row: sqlite3.Row) -> bytes:
    return _preauthentication_aad(
        transaction_id=str(row["transaction_id"]),
        organization_id=str(row["organization_id"]),
        provider_configuration_id=str(row["provider_configuration_id"]),
        exact_issuer=str(row["exact_issuer"]),
        configured_redirect_uri=str(row["configured_redirect_uri"]),
        allowed_origin=str(row["allowed_origin"]),
    )


def _redacted_envelope(envelope: str) -> str:
    return "redacted:" + hashlib.sha256(envelope.encode("ascii")).hexdigest()


def _validate_origin(value: str) -> None:
    parsed = _split_url(value, label="allowed origin")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.scheme not in {"http", "https"}
        or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "::1", "localhost"})
    ):
        raise SessionConfigurationError("allowed origin is malformed")


def _validate_redirect_uri(value: str) -> None:
    parsed = _split_url(value, label="configured redirect URI")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.scheme not in {"http", "https"}
        or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "::1", "localhost"})
    ):
        raise SessionConfigurationError("configured redirect URI is malformed")


def _redirect_origin(value: str) -> str:
    parsed = _split_url(value, label="configured redirect URI")
    host = parsed.hostname
    if host is None:
        raise SessionConfigurationError("configured redirect URI is malformed")
    rendered_host = f"[{host}]" if ":" in host else host
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{rendered_host}{port}"


def _split_url(value: str, *, label: str) -> SplitResult:
    if (
        not value
        or value != value.strip()
        or len(value) > 2048
        or any(
            ord(character) < 0x20 or ord(character) == 0x7F or character.isspace()
            for character in value
        )
        or not _is_valid_utf8(value)
        or "\\" in value
    ):
        raise SessionConfigurationError(f"{label} is malformed")
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError as exc:
        raise SessionConfigurationError(f"{label} is malformed") from exc
    if (
        not parsed.netloc
        or parsed.hostname is None
        or parsed.netloc.endswith(":")
        or (parsed_port is not None and not 1 <= parsed_port <= 65535)
    ):
        raise SessionConfigurationError(f"{label} is malformed")
    return parsed


def _is_valid_utf8(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _parse_datetime(value: str) -> datetime:
    try:
        return _require_aware_utc(datetime.fromisoformat(value))
    except ValueError as exc:
        raise SessionConfigurationError("stored session time is malformed") from exc


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise SessionConfigurationError("trusted clock is unavailable")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _random_id(prefix: str) -> str:
    return prefix + uuid4().hex
