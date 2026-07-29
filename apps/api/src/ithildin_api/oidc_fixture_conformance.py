"""Zero-network, fixture-only OIDC conformance seam for PIS-004A."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit
from uuid import uuid4

from authlib.oauth2.rfc7636 import create_s256_code_challenge  # type: ignore[import-untyped]
from ithildin_schemas import JsonObject
from joserfc import jwk, jwt
from joserfc.errors import JoseError
from joserfc.jwt import JWTClaimsRegistry
from pydantic import BaseModel, ConfigDict, Field

from ithildin_api.enterprise_sessions import (
    AuthenticationMethod,
    EnterpriseSessionStore,
    PreauthenticationError,
)
from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

_FIXED_ALGORITHMS = frozenset({"RS256"})
_TOKEN_HEADER_KEYS = frozenset({"alg", "kid", "typ"})
_TOKEN_CLAIM_KEYS = frozenset(
    {
        "iss",
        "sub",
        "aud",
        "azp",
        "exp",
        "iat",
        "nbf",
        "nonce",
        "auth_time",
        "jti",
    }
)
_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_JWK_KEYS = frozenset({"kty", "kid", "use", "alg", "key_ops", "n", "e"})
_PRIVATE_JWK_KEYS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth"})
_DISCOVERY_KEYS = frozenset(
    {
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "jwks_uri",
        "response_types_supported",
        "subject_types_supported",
        "id_token_signing_alg_values_supported",
        "code_challenge_methods_supported",
    }
)


class OidcFixtureError(RuntimeError):
    """Base class for fixture-conformance denials."""


class OidcFixtureConfigurationError(OidcFixtureError):
    """Raised when the trusted fixture adapter is misconfigured."""


class OidcFixtureValidationError(OidcFixtureError):
    """Raised when callback, discovery, JWK, or token input is denied."""


class OidcFixtureReplayError(OidcFixtureValidationError):
    """Raised when a previously accepted synthetic token is replayed."""


class OidcNetworkForbiddenError(OidcFixtureValidationError):
    """Raised when a URL is supplied where captured fixture bytes are required."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )


class FixtureCallback(_FrozenModel):
    transaction_handle: str = Field(
        min_length=43,
        max_length=256,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    state: str = Field(
        min_length=43,
        max_length=256,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    response_issuer: str = Field(min_length=8, max_length=2048)
    redirect_uri: str = Field(min_length=12, max_length=2048)
    origin: str = Field(min_length=8, max_length=2048)
    authorization_code: str = Field(
        min_length=1,
        max_length=2048,
        pattern=r"^[\x21-\x7e]+$",
    )
    captured_authorization_request_code_challenge: str = Field(
        min_length=43,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


class OidcIdentityAssertion(_FrozenModel):
    assertion_audit_id: str
    organization_id: str
    provider_configuration_id: str
    exact_issuer: str
    subject: str
    authentication_method: AuthenticationMethod
    authentication_time: datetime
    token_expires_at: datetime

    def safe_audit_metadata(self, *, outcome: str, reason_code: str) -> JsonObject:
        return {
            "assertion_audit_id": self.assertion_audit_id,
            "organization_id": self.organization_id,
            "provider_configuration_id": self.provider_configuration_id,
            "authentication_method": self.authentication_method.value,
            "outcome": outcome,
            "reason_code": reason_code,
        }


class ZeroNetworkOidcFixtureAdapter:
    """Validate captured synthetic OIDC material without any network surface."""

    def __init__(
        self,
        db_path: Path,
        *,
        sessions: EnterpriseSessionStore,
        configured_exact_issuer: str,
        configured_redirect_uri: str,
        allowed_origin: str,
        expected_audience: str,
        discovery_fixture: bytes,
        jwks_fixture: bytes,
        expected_authorization_code_digest: str,
        clock: Callable[[], datetime],
        clock_skew: timedelta = timedelta(seconds=60),
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        verify_database_v2(db_path)
        if sessions.db_path.resolve() != db_path.resolve():
            raise OidcFixtureConfigurationError(
                "OIDC and session authority must share one database"
            )
        _validate_issuer_url(configured_exact_issuer)
        _validate_redirect_uri(configured_redirect_uri)
        _validate_origin(allowed_origin)
        if _redirect_origin(configured_redirect_uri) != allowed_origin:
            raise OidcFixtureConfigurationError(
                "configured redirect and origin are inconsistent"
            )
        if (
            not 1 <= len(expected_audience) <= 512
            or _has_control(expected_audience)
            or not _is_valid_utf8(expected_audience)
        ):
            raise OidcFixtureConfigurationError("configured audience is malformed")
        if _SHA256_DIGEST_PATTERN.fullmatch(
            expected_authorization_code_digest
        ) is None:
            raise OidcFixtureConfigurationError(
                "authorization-code fixture digest is malformed"
            )
        if not timedelta(0) <= clock_skew <= timedelta(minutes=5):
            raise OidcFixtureConfigurationError("OIDC clock skew is out of bounds")
        self.db_path = db_path
        self._sessions = sessions
        self._configured_exact_issuer = configured_exact_issuer
        self._configured_redirect_uri = configured_redirect_uri
        self._allowed_origin = allowed_origin
        self._expected_audience = expected_audience
        self._expected_authorization_code_digest = (
            expected_authorization_code_digest
        )
        self._clock = clock
        self._clock_skew = clock_skew
        self._id_factory = id_factory or _random_id
        discovery = _load_json_object(
            discovery_fixture,
            label="discovery",
            maximum_bytes=65536,
        )
        self._validate_discovery(discovery)
        self._public_keys = self._load_public_keys(jwks_fixture)

    def validate_callback(
        self,
        callback: FixtureCallback,
        *,
        compact_id_token: str,
    ) -> OidcIdentityAssertion:
        now = _require_aware_utc(self._clock())
        self._validate_callback_shape(callback)
        if callback.response_issuer != self._configured_exact_issuer:
            raise OidcFixtureValidationError("authorization response issuer mismatch")
        if not hmac.compare_digest(
            authorization_code_fixture_digest(callback.authorization_code),
            self._expected_authorization_code_digest,
        ):
            raise OidcFixtureValidationError(
                "authorization-code fixture binding mismatch"
            )
        try:
            transaction = self._sessions.consume_preauthentication(
                callback.transaction_handle,
                state=callback.state,
                exact_issuer=callback.response_issuer,
                configured_redirect_uri=callback.redirect_uri,
                allowed_origin=callback.origin,
            )
        except PreauthenticationError as exc:
            raise OidcFixtureValidationError(
                "preauthentication transaction was denied"
            ) from exc
        if (
            transaction.exact_issuer != self._configured_exact_issuer
            or transaction.configured_redirect_uri != self._configured_redirect_uri
            or transaction.allowed_origin != self._allowed_origin
        ):
            raise OidcFixtureValidationError(
                "preauthentication configuration binding mismatch"
            )
        expected_challenge = str(
            create_s256_code_challenge(transaction.pkce_verifier)
        )
        if not hmac.compare_digest(
            expected_challenge,
            callback.captured_authorization_request_code_challenge,
        ):
            raise OidcFixtureValidationError("PKCE binding mismatch")

        header = _strict_protected_header(compact_id_token)
        key = self._select_verification_key(header)
        claims = self._decode_and_validate_claims(
            compact_id_token,
            key=key,
            now=now,
        )
        nonce = _require_string_claim(claims, "nonce", maximum_length=512)
        try:
            self._sessions.validate_preauthentication_nonce(
                transaction,
                nonce=nonce,
            )
        except PreauthenticationError as exc:
            raise OidcFixtureValidationError(
                "preauthentication nonce was denied"
            ) from exc
        expires_at = _numeric_date(claims, "exp")
        authentication_time = _numeric_date(claims, "auth_time")
        self._record_replay(
            organization_id=transaction.organization_id,
            provider_configuration_id=transaction.provider_configuration_id,
            exact_issuer=transaction.exact_issuer,
            authorization_code=callback.authorization_code,
            compact_id_token=compact_id_token,
            now=now,
            token_expires_at=expires_at,
        )
        return OidcIdentityAssertion(
            assertion_audit_id=self._id_factory("oaud_"),
            organization_id=transaction.organization_id,
            provider_configuration_id=transaction.provider_configuration_id,
            exact_issuer=self._configured_exact_issuer,
            subject=_require_string_claim(claims, "sub", maximum_length=512),
            authentication_method=AuthenticationMethod.OIDC_FIXTURE,
            authentication_time=authentication_time,
            token_expires_at=expires_at,
        )

    def _validate_callback_shape(self, callback: FixtureCallback) -> None:
        if (
            callback.redirect_uri != self._configured_redirect_uri
            or callback.origin != self._allowed_origin
        ):
            raise OidcFixtureValidationError("callback redirect or origin mismatch")
        if (
            _has_control(callback.authorization_code)
            or _has_control(callback.state)
            or _has_control(callback.transaction_handle)
        ):
            raise OidcFixtureValidationError("callback input is malformed")

    def _validate_discovery(self, discovery: Mapping[str, object]) -> None:
        if set(discovery) != _DISCOVERY_KEYS:
            raise OidcFixtureValidationError("discovery fields are not the fixed profile")
        if discovery.get("issuer") != self._configured_exact_issuer:
            raise OidcFixtureValidationError("discovery issuer mismatch")
        for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            value = discovery.get(key)
            if not isinstance(value, str):
                raise OidcFixtureValidationError("discovery endpoint is malformed")
            try:
                _validate_https_url(value)
            except OidcFixtureConfigurationError as exc:
                raise OidcFixtureValidationError(
                    "discovery endpoint is malformed"
                ) from exc
        if discovery.get("response_types_supported") != ["code"]:
            raise OidcFixtureValidationError("discovery response type is unsupported")
        if discovery.get("subject_types_supported") != ["public"]:
            raise OidcFixtureValidationError("discovery subject type is unsupported")
        if discovery.get("id_token_signing_alg_values_supported") != ["RS256"]:
            raise OidcFixtureValidationError("discovery algorithm profile is unsupported")
        if discovery.get("code_challenge_methods_supported") != ["S256"]:
            raise OidcFixtureValidationError("discovery PKCE profile is unsupported")

    def _load_public_keys(
        self,
        jwks_fixture: bytes,
    ) -> dict[str, jwk.RSAKey]:
        jwks = _load_json_object(
            jwks_fixture,
            label="JWK set",
            maximum_bytes=65536,
        )
        if set(jwks) != {"keys"}:
            raise OidcFixtureValidationError("JWK set fields are malformed")
        raw_keys = jwks.get("keys")
        if (
            not isinstance(raw_keys, list)
            or not 1 <= len(raw_keys) <= 8
            or not all(isinstance(item, dict) for item in raw_keys)
        ):
            raise OidcFixtureValidationError("JWK set is malformed")
        public_keys: dict[str, jwk.RSAKey] = {}
        for raw_key in raw_keys:
            if set(raw_key) != _JWK_KEYS or set(raw_key) & _PRIVATE_JWK_KEYS:
                raise OidcFixtureValidationError(
                    "JWK is not the fixed public profile"
                )
            key_identifier = raw_key.get("kid")
            if (
                not isinstance(key_identifier, str)
                or not key_identifier
                or _has_control(key_identifier)
                or key_identifier in public_keys
            ):
                raise OidcFixtureValidationError("JWK key identifier is ambiguous")
            if (
                raw_key.get("kty") != "RSA"
                or raw_key.get("use") != "sig"
                or raw_key.get("alg") != "RS256"
                or raw_key.get("key_ops") != ["verify"]
            ):
                raise OidcFixtureValidationError("JWK authority is incompatible")
            try:
                imported_key = jwk.import_key(raw_key)
            except (JoseError, TypeError, ValueError) as exc:
                raise OidcFixtureValidationError(
                    "JWK could not be imported"
                ) from exc
            if (
                not isinstance(imported_key, jwk.RSAKey)
                or imported_key.raw_value.key_size < 2048
            ):
                raise OidcFixtureValidationError("JWK strength is insufficient")
            public_keys[key_identifier] = imported_key
        return public_keys

    def _select_verification_key(
        self,
        header: Mapping[str, object],
    ) -> jwk.RSAKey:
        if set(header) != _TOKEN_HEADER_KEYS:
            raise OidcFixtureValidationError("token header is not the fixed profile")
        if header.get("alg") not in _FIXED_ALGORITHMS:
            raise OidcFixtureValidationError("token algorithm is not allowed")
        if header.get("typ") != "JWT":
            raise OidcFixtureValidationError("token type is not allowed")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid or _has_control(kid):
            raise OidcFixtureValidationError("token key identifier is malformed")
        try:
            return self._public_keys[kid]
        except KeyError as exc:
            raise OidcFixtureValidationError(
                "token key identifier is unavailable"
            ) from exc

    def _decode_and_validate_claims(
        self,
        compact_id_token: str,
        *,
        key: jwk.RSAKey,
        now: datetime,
    ) -> dict[str, Any]:
        if not 1 <= len(compact_id_token) <= 16384 or _has_control(
            compact_id_token
        ):
            raise OidcFixtureValidationError("ID token is malformed")
        try:
            token = jwt.decode(
                compact_id_token,
                key,
                algorithms=_FIXED_ALGORITHMS,
                decoder_cls=_StrictJsonDecoder,
            )
            if not isinstance(token.claims, dict) or not all(
                isinstance(name, str) for name in token.claims
            ):
                raise OidcFixtureValidationError(
                    "ID token claims must be a JSON object"
                )
            claims = dict(token.claims)
        except (JoseError, TypeError, ValueError, RecursionError) as exc:
            raise OidcFixtureValidationError(
                "ID token signature or payload is invalid"
            ) from exc
        if not set(claims) <= _TOKEN_CLAIM_KEYS:
            raise OidcFixtureValidationError("ID token claims exceed the fixed profile")
        now_timestamp = int(now.timestamp())
        skew_seconds = int(self._clock_skew.total_seconds())
        registry = JWTClaimsRegistry(
            now=now_timestamp,
            leeway=skew_seconds,
            iss={"essential": True, "value": self._configured_exact_issuer},
            sub={"essential": True},
            aud={"essential": True, "value": self._expected_audience},
            exp={"essential": True},
            iat={"essential": True},
            nbf={"essential": True},
            nonce={"essential": True},
            auth_time={"essential": True},
        )
        try:
            registry.validate(claims)
        except JoseError as exc:
            raise OidcFixtureValidationError("ID token claims are invalid") from exc
        subject = _require_string_claim(claims, "sub", maximum_length=512)
        nonce = _require_string_claim(claims, "nonce", maximum_length=512)
        del subject, nonce
        if "jti" in claims:
            _require_string_claim(claims, "jti", maximum_length=512)
        if "azp" in claims:
            _require_string_claim(claims, "azp", maximum_length=512)
        issued_at = _numeric_date(claims, "iat")
        expires_at = _numeric_date(claims, "exp")
        not_before = _numeric_date(claims, "nbf")
        authentication_time = _numeric_date(claims, "auth_time")
        if expires_at <= now - self._clock_skew:
            raise OidcFixtureValidationError("ID token has expired")
        if expires_at <= issued_at or expires_at - issued_at > timedelta(hours=1):
            raise OidcFixtureValidationError("ID token lifetime is invalid")
        if not_before > issued_at + self._clock_skew:
            raise OidcFixtureValidationError("ID token not-before is invalid")
        if (
            authentication_time > now + self._clock_skew
            or authentication_time > issued_at + self._clock_skew
        ):
            raise OidcFixtureValidationError("authentication time is invalid")
        audience = claims.get("aud")
        if isinstance(audience, list) and len(audience) > 1:
            if claims.get("azp") != self._expected_audience:
                raise OidcFixtureValidationError(
                    "authorized party is required for multiple audiences"
                )
        elif "azp" in claims and claims.get("azp") != self._expected_audience:
            raise OidcFixtureValidationError("authorized party is invalid")
        return claims

    def _record_replay(
        self,
        *,
        organization_id: str,
        provider_configuration_id: str,
        exact_issuer: str,
        authorization_code: str,
        compact_id_token: str,
        now: datetime,
        token_expires_at: datetime,
    ) -> None:
        replay_digests = (
            _replay_digest("authorization-code", authorization_code),
            _replay_digest("id-token", compact_id_token),
        )
        replay_expires_at = max(
            token_expires_at + self._clock_skew + timedelta(seconds=1),
            now + timedelta(seconds=1),
        )
        with closing(self._connection()) as connection:
            connection.isolation_level = None
            try:
                connection.execute("BEGIN IMMEDIATE")
                authority = connection.execute(
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
                if (
                    authority is None
                    or str(authority[0]) != exact_issuer
                    or not bool(authority[1])
                    or not bool(authority[2])
                ):
                    raise OidcFixtureValidationError(
                        "provider configuration is unavailable"
                    )
                connection.execute(
                    "DELETE FROM identity_oidc_replays WHERE expires_at <= ?",
                    (now.isoformat(),),
                )
                connection.executemany(
                    """
                    INSERT INTO identity_oidc_replays (
                        organization_id, provider_configuration_id,
                        credential_digest, first_seen_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    tuple(
                        (
                            organization_id,
                            provider_configuration_id,
                            replay_digest,
                            now.isoformat(),
                            replay_expires_at.isoformat(),
                        )
                        for replay_digest in replay_digests
                    ),
                )
            except sqlite3.IntegrityError as exc:
                _rollback_quietly(connection)
                raise OidcFixtureReplayError(
                    "OIDC fixture credential replay was denied"
                ) from exc
            except sqlite3.Error as exc:
                _rollback_quietly(connection)
                raise OidcFixtureValidationError(
                    "OIDC replay authority is unavailable"
                ) from exc
            except BaseException:
                _rollback_quietly(connection)
                raise
            else:
                connection.execute("COMMIT")

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class _DuplicateJsonKeyError(ValueError):
    pass


class _StrictJsonDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["object_pairs_hook"] = _unique_object
        kwargs["parse_constant"] = _reject_json_constant
        super().__init__(*args, **kwargs)


def _unique_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    del value
    raise ValueError("non-standard JSON constant")


def _load_json_object(
    payload: bytes,
    *,
    label: str,
    maximum_bytes: int,
) -> dict[str, object]:
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= maximum_bytes:
        raise OidcFixtureValidationError(f"{label} fixture is malformed")
    stripped = payload.lstrip()
    if stripped.startswith((b"http://", b"https://")):
        raise OidcNetworkForbiddenError(
            f"{label} must be captured bytes, not a network reference"
        )
    try:
        value = json.loads(payload, cls=_StrictJsonDecoder)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise OidcFixtureValidationError(f"{label} fixture is malformed") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise OidcFixtureValidationError(f"{label} fixture is malformed")
    return value


def _strict_protected_header(compact_token: str) -> dict[str, object]:
    if not 1 <= len(compact_token) <= 16384 or _has_control(compact_token):
        raise OidcFixtureValidationError("ID token is malformed")
    parts = compact_token.split(".")
    if len(parts) != 3 or any(not part for part in parts):
        raise OidcFixtureValidationError("ID token is malformed")
    try:
        encoded = parts[0].encode("ascii")
        padding = b"=" * (-len(encoded) % 4)
        header_bytes = base64.b64decode(
            encoded + padding,
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, ValueError, binascii.Error) as exc:
        raise OidcFixtureValidationError("ID token header is malformed") from exc
    return _load_json_object(
        header_bytes,
        label="ID token header",
        maximum_bytes=4096,
    )


def _require_string_claim(
    claims: Mapping[str, object],
    name: str,
    *,
    maximum_length: int,
) -> str:
    value = claims.get(name)
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum_length
        or _has_control(value)
        or not _is_valid_utf8(value)
    ):
        raise OidcFixtureValidationError(f"ID token {name} claim is malformed")
    return value


def _numeric_date(claims: Mapping[str, object], name: str) -> datetime:
    value = claims.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OidcFixtureValidationError(f"ID token {name} claim is malformed")
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise OidcFixtureValidationError(
            f"ID token {name} claim is malformed"
        ) from exc


def _validate_https_url(value: str) -> None:
    parsed = _split_url(value, label="trusted HTTPS URL")
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise OidcFixtureConfigurationError("trusted HTTPS URL is malformed")


def _validate_issuer_url(value: str) -> None:
    _validate_https_url(value)
    if _split_url(value, label="trusted issuer URL").query:
        raise OidcFixtureConfigurationError("trusted issuer URL is malformed")


def _validate_redirect_uri(value: str) -> None:
    parsed = _split_url(value, label="configured redirect URI")
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (
            parsed.scheme == "http"
            and parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        )
    ):
        raise OidcFixtureConfigurationError("configured redirect URI is malformed")


def _validate_origin(value: str) -> None:
    parsed = _split_url(value, label="allowed origin")
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or (
            parsed.scheme == "http"
            and parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        )
    ):
        raise OidcFixtureConfigurationError("allowed origin is malformed")


def _redirect_origin(value: str) -> str:
    parsed = _split_url(value, label="configured redirect URI")
    host = parsed.hostname
    assert host is not None
    rendered_host = f"[{host}]" if ":" in host else host
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{rendered_host}{port}"


def _split_url(value: str, *, label: str) -> SplitResult:
    if (
        not value
        or value != value.strip()
        or len(value) > 2048
        or _has_control(value)
        or not _is_valid_utf8(value)
        or any(character.isspace() for character in value)
        or "\\" in value
    ):
        raise OidcFixtureConfigurationError(f"{label} is malformed")
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError as exc:
        raise OidcFixtureConfigurationError(f"{label} is malformed") from exc
    if (
        not parsed.netloc
        or parsed.hostname is None
        or parsed.netloc.endswith(":")
        or (parsed_port is not None and not 1 <= parsed_port <= 65535)
    ):
        raise OidcFixtureConfigurationError(f"{label} is malformed")
    return parsed


def _has_control(value: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)


def _is_valid_utf8(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def authorization_code_fixture_digest(authorization_code: str) -> str:
    """Return the domain-separated digest for one synthetic fixture code."""

    if (
        not 1 <= len(authorization_code) <= 2048
        or any(
            ord(character) < 0x21 or ord(character) > 0x7E
            for character in authorization_code
        )
    ):
        raise OidcFixtureConfigurationError(
            "authorization-code fixture is malformed"
        )
    return _replay_digest("authorization-code", authorization_code)


def _replay_digest(purpose: str, credential: str) -> str:
    digest = hashlib.sha256(
        (
            "ithildin-pis004a-oidc-replay-v1:"
            + purpose
            + "\N{NULL}"
            + credential
        ).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise OidcFixtureConfigurationError("trusted OIDC clock is unavailable")
    return value.astimezone(UTC)


def _random_id(prefix: str) -> str:
    return prefix + uuid4().hex
