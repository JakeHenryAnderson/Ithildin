from __future__ import annotations

import base64
import json
import socket
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.enterprise_identity import (
    EnterpriseAuditOutcome,
    EnterpriseAuditReasonCode,
    EnterpriseIdentityStore,
    OrganizationRole,
)
from ithildin_api.enterprise_sessions import (
    EnterpriseSessionStore,
    SessionAuthenticationError,
    SessionConfigurationError,
    SessionDigestKeyRing,
)
from ithildin_api.oidc_fixture_conformance import (
    FixtureCallback,
    OidcFixtureConfigurationError,
    OidcFixtureReplayError,
    OidcFixtureValidationError,
    OidcIdentityAssertion,
    OidcNetworkForbiddenError,
    ZeroNetworkOidcFixtureAdapter,
    authorization_code_fixture_digest,
)
from pydantic import ValidationError

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "pis004a_oidc"
DISCOVERY_BYTES = (FIXTURE_DIRECTORY / "discovery.json").read_bytes()
JWKS_BYTES = (FIXTURE_DIRECTORY / "jwks.json").read_bytes()
CALLBACK_DOCUMENT = cast(
    dict[str, Any],
    json.loads((FIXTURE_DIRECTORY / "callback.json").read_text()),
)
TOKEN_DOCUMENT = cast(
    dict[str, Any],
    json.loads((FIXTURE_DIRECTORY / "tokens.json").read_text()),
)
TOKENS = cast(dict[str, str], TOKEN_DOCUMENT["tokens"])

ISSUER = "https://identity.example.test/tenant-a"
ORIGIN = "http://127.0.0.1:5173"
REDIRECT_URI = f"{ORIGIN}/identity/callback"
AUDIENCE = "ithildin-local-fixture"
EXPECTED_NONCE = "fixture_nonce_20260729_AAAAAAAAAAAAAAAAAAAAA"
AUTHORIZATION_CODE = "synthetic-authorization-code-never-persisted"


class FixedClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class DeterministicFactories:
    def __init__(self) -> None:
        self.ids: defaultdict[str, int] = defaultdict(int)
        self.secret_count = 0
        self.envelope_nonce_count = 0

    def identifier(self, prefix: str) -> str:
        self.ids[prefix] += 1
        return prefix + f"{self.ids[prefix]:032x}"

    def secret(self, entropy_bytes: int) -> str:
        self.secret_count += 1
        transaction = ((self.secret_count - 1) // 4) + 1
        position = (self.secret_count - 1) % 4
        if position == 2:
            return EXPECTED_NONCE
        width = 43 if entropy_bytes <= 32 else 64
        marker = ("H", "S", "N", "V")[position]
        return marker + f"{transaction:0{width - 1}d}"

    def envelope_nonce(self, length: int) -> bytes:
        assert length == 12
        self.envelope_nonce_count += 1
        return self.envelope_nonce_count.to_bytes(length, "big")


@dataclass(frozen=True)
class OidcFixture:
    db_path: Path
    identity: EnterpriseIdentityStore
    sessions: EnterpriseSessionStore
    adapter: ZeroNetworkOidcFixtureAdapter
    clock: FixedClock
    organization_id: str
    provider_configuration_id: str

    def callback(self, **overrides: str) -> FixtureCallback:
        transaction = self.sessions.create_preauthentication(
            self.organization_id,
            self.provider_configuration_id,
            exact_issuer=ISSUER,
            configured_redirect_uri=REDIRECT_URI,
            allowed_origin=ORIGIN,
        )
        assert transaction.nonce == EXPECTED_NONCE
        values = {
            "transaction_handle": transaction.transaction_handle,
            "state": transaction.state,
            "response_issuer": str(CALLBACK_DOCUMENT["response_issuer"]),
            "redirect_uri": str(CALLBACK_DOCUMENT["redirect_uri"]),
            "origin": str(CALLBACK_DOCUMENT["origin"]),
            "authorization_code": str(CALLBACK_DOCUMENT["authorization_code"]),
            "captured_authorization_request_code_challenge": (transaction.pkce_challenge),
        }
        values.update(overrides)
        return FixtureCallback(**values)

    def validate(
        self,
        *,
        token_name: str = "valid",
        callback: FixtureCallback | None = None,
        compact_token: str | None = None,
    ) -> OidcIdentityAssertion:
        return self.adapter.validate_callback(
            callback or self.callback(),
            compact_id_token=compact_token or TOKENS[token_name],
        )


def make_fixture(
    tmp_path: Path,
    *,
    discovery: bytes = DISCOVERY_BYTES,
    jwks: bytes = JWKS_BYTES,
) -> OidcFixture:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    clock = FixedClock()
    factories = DeterministicFactories()
    identity = EnterpriseIdentityStore(
        db_path,
        clock=clock,
        id_factory=factories.identifier,
    )
    organization = identity.create_organization()
    provider = identity.add_provider_configuration(
        organization.organization_id,
        exact_issuer=ISSUER,
    )
    resolution = identity.provision_human_identity(
        organization.organization_id,
        provider.provider_configuration_id,
        exact_issuer=ISSUER,
        subject="synthetic-subject-Aa-001",
    )
    identity.set_organization_membership(
        organization.organization_id,
        resolution.principal_id,
        roles={OrganizationRole.MEMBER},
    )
    sessions = EnterpriseSessionStore(
        db_path,
        key_ring=SessionDigestKeyRing({1: b"A" * 32}, active_generation=1),
        allowed_origins=frozenset({ORIGIN}),
        clock=clock,
        secret_factory=factories.secret,
        nonce_factory=factories.envelope_nonce,
        id_factory=factories.identifier,
    )
    adapter = ZeroNetworkOidcFixtureAdapter(
        db_path,
        sessions=sessions,
        configured_exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
        expected_audience=AUDIENCE,
        discovery_fixture=discovery,
        jwks_fixture=jwks,
        expected_authorization_code_digest=authorization_code_fixture_digest(AUTHORIZATION_CODE),
        clock=clock,
        clock_skew=timedelta(seconds=60),
        id_factory=factories.identifier,
    )
    return OidcFixture(
        db_path=db_path,
        identity=identity,
        sessions=sessions,
        adapter=adapter,
        clock=clock,
        organization_id=organization.organization_id,
        provider_configuration_id=provider.provider_configuration_id,
    )


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_valid_fixture_binds_identity_code_and_replay_state_without_secrets(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    assertion = fixture.adapter.validate_callback(
        fixture.callback(),
        compact_id_token=TOKENS["valid"],
    )

    assert assertion.organization_id == fixture.organization_id
    assert assertion.provider_configuration_id == fixture.provider_configuration_id
    assert assertion.exact_issuer == ISSUER
    assert assertion.subject == "synthetic-subject-Aa-001"
    assert assertion.authentication_time == datetime(
        2026,
        7,
        29,
        11,
        59,
        tzinfo=UTC,
    )
    resolution = fixture.identity.resolve_identity(
        assertion.organization_id,
        assertion.provider_configuration_id,
        exact_issuer=assertion.exact_issuer,
        subject=assertion.subject,
    )
    assert (
        fixture.identity.resolve_identity(
            assertion.organization_id,
            assertion.provider_configuration_id,
            exact_issuer=assertion.exact_issuer,
            subject=assertion.subject,
        ).principal_id
        == resolution.principal_id
    )
    issued = fixture.sessions.issue_session(assertion.authentication_grant_id)
    assert issued.context.principal_id == resolution.principal_id
    assert issued.context.recent_auth_at == assertion.authentication_time
    with pytest.raises(
        SessionAuthenticationError,
        match="authentication grant did not authenticate",
    ):
        fixture.sessions.issue_session(assertion.authentication_grant_id)

    with sqlite3.connect(fixture.db_path) as connection:
        replay_rows = connection.execute(
            """
            SELECT credential_digest, first_seen_at, expires_at
            FROM identity_oidc_replays
            ORDER BY credential_digest
            """
        ).fetchall()
    assert len(replay_rows) == 2
    assert all(str(row[0]).startswith("sha256:") for row in replay_rows)
    assert all(str(row[2]) > str(row[1]) for row in replay_rows)

    database_bytes = fixture.db_path.read_bytes()
    assert AUTHORIZATION_CODE.encode() not in database_bytes
    assert TOKENS["valid"].encode() not in database_bytes
    audit = json.dumps(
        assertion.safe_audit_metadata(
            outcome=EnterpriseAuditOutcome.ACCEPTED,
            reason_code=EnterpriseAuditReasonCode.FIXTURE_CONFORMANCE_VALID,
        ),
        sort_keys=True,
    )
    for forbidden in (
        assertion.subject,
        assertion.exact_issuer,
        AUTHORIZATION_CODE,
        TOKENS["valid"],
        "claims",
        "credential",
    ):
        assert forbidden not in audit


def test_oidc_grant_rejects_provider_disable_and_reenable_generation_drift(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    assertion = fixture.validate()

    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_provider_configurations
            SET enabled = 0, generation = generation + 1
            WHERE provider_configuration_id = ?
            """,
            (fixture.provider_configuration_id,),
        )
    with pytest.raises(SessionAuthenticationError, match="provider configuration is stale"):
        fixture.sessions.issue_session(assertion.authentication_grant_id)

    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_provider_configurations
            SET enabled = 1
            WHERE provider_configuration_id = ?
            """,
            (fixture.provider_configuration_id,),
        )
    with pytest.raises(SessionAuthenticationError, match="provider configuration is stale"):
        fixture.sessions.issue_session(assertion.authentication_grant_id)


def test_token_or_authorization_code_replay_is_denied_across_transactions(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    fixture.validate()

    with pytest.raises(OidcFixtureReplayError, match="replay"):
        fixture.validate()
    with pytest.raises(OidcFixtureReplayError, match="replay"):
        fixture.validate(token_name="skew_iat_boundary")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "response_issuer",
            "https://identity.example.test/tenant-b",
            "issuer",
        ),
        ("redirect_uri", f"{ORIGIN}/other-callback", "redirect"),
        ("origin", "http://localhost:5173", "origin"),
        ("state", "Z" * 43, "preauthentication"),
        (
            "captured_authorization_request_code_challenge",
            "Z" * 43,
            "PKCE",
        ),
        (
            "authorization_code",
            "another-synthetic-code",
            "fixture binding",
        ),
    ],
)
def test_callback_binding_mismatches_fail_closed(
    tmp_path: Path,
    field: str,
    value: str,
    match: str,
) -> None:
    fixture = make_fixture(tmp_path)
    callback = fixture.callback(**{field: value})

    with pytest.raises(OidcFixtureValidationError, match=match):
        fixture.validate(callback=callback)


@pytest.mark.parametrize(
    "token_name",
    [
        "wrong_issuer",
        "wrong_audience",
        "expired",
        "future_iat",
        "future_nbf",
        "future_auth_time",
        "wrong_nonce",
        "no_nonce",
        "multi_audience_no_azp",
        "wrong_alg",
        "unknown_kid",
        "missing_kid",
        "skew_exp_boundary",
        "array_claims",
        "duplicate_claims",
    ],
)
def test_signed_negative_tokens_fail_closed(
    tmp_path: Path,
    token_name: str,
) -> None:
    fixture = make_fixture(tmp_path)

    with pytest.raises(OidcFixtureValidationError):
        fixture.validate(token_name=token_name)


@pytest.mark.parametrize(
    "token_name",
    [
        "skew_iat_boundary",
        "skew_nbf_boundary",
    ],
)
def test_exact_clock_skew_boundaries_are_accepted(
    tmp_path: Path,
    token_name: str,
) -> None:
    fixture = make_fixture(tmp_path)

    fixture.validate(token_name=token_name)


@pytest.mark.parametrize(
    "mutation",
    [
        {"issuer": "https://identity.example.test/tenant-b"},
        {"authorization_endpoint": "http://identity.example.test/authorize"},
        {"response_types_supported": ["code id_token"]},
        {"unexpected_authority": True},
    ],
)
def test_discovery_profile_is_exact_and_https_only(
    tmp_path: Path,
    mutation: dict[str, object],
) -> None:
    discovery = cast(dict[str, object], json.loads(DISCOVERY_BYTES))
    discovery.update(mutation)

    with pytest.raises(OidcFixtureValidationError):
        make_fixture(tmp_path / "mutated", discovery=_json_bytes(discovery))


@pytest.mark.parametrize("case", ["duplicate", "private", "wrong_alg", "weak"])
def test_every_jwk_must_be_unique_public_and_fixed_profile(
    tmp_path: Path,
    case: str,
) -> None:
    jwks = cast(dict[str, Any], json.loads(JWKS_BYTES))
    original = cast(dict[str, object], jwks["keys"][0])
    if case == "duplicate":
        jwks["keys"] = [original, dict(original)]
    elif case == "private":
        jwks["keys"] = [original, {**original, "d": "forbidden-private-value"}]
    elif case == "wrong_alg":
        jwks["keys"] = [{**original, "alg": "RS384"}]
    else:
        jwks["keys"] = [{**original, "n": "AQAB"}]

    with pytest.raises(OidcFixtureValidationError):
        make_fixture(tmp_path / "mutated", jwks=_json_bytes(jwks))


@pytest.mark.parametrize(
    ("discovery", "jwks", "error_type"),
    [
        (
            b"https://identity.example.test/discovery",
            JWKS_BYTES,
            OidcNetworkForbiddenError,
        ),
        (
            DISCOVERY_BYTES,
            b"https://identity.example.test/jwks",
            OidcNetworkForbiddenError,
        ),
        (
            b'{"issuer":"one","issuer":"two"}',
            JWKS_BYTES,
            OidcFixtureValidationError,
        ),
        (
            b"{" + b"x" * 65536,
            JWKS_BYTES,
            OidcFixtureValidationError,
        ),
    ],
)
def test_malformed_oversize_or_network_reference_fixture_is_denied(
    tmp_path: Path,
    discovery: bytes,
    jwks: bytes,
    error_type: type[OidcFixtureValidationError],
) -> None:
    with pytest.raises(error_type):
        make_fixture(tmp_path, discovery=discovery, jwks=jwks)


def test_malformed_compact_token_is_denied(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    with pytest.raises(OidcFixtureValidationError):
        fixture.validate(compact_token="not-a-compact-token")


def test_non_object_or_duplicate_protected_headers_are_denied(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    array_header = base64.urlsafe_b64encode(b"[]").rstrip(b"=")
    duplicate_header = base64.urlsafe_b64encode(
        b'{"alg":"RS256","alg":"RS256","kid":"fixture","typ":"JWT"}'
    ).rstrip(b"=")

    for header in (array_header, duplicate_header):
        with pytest.raises(OidcFixtureValidationError):
            fixture.adapter.validate_callback(
                fixture.callback(),
                compact_id_token=(header + b".e30.invalid").decode(),
            )


def test_unrelated_private_jwk_is_denied_before_key_selection(tmp_path: Path) -> None:
    jwks = cast(dict[str, Any], json.loads(JWKS_BYTES))
    original = cast(dict[str, object], jwks["keys"][0])
    jwks["keys"] = [
        original,
        {
            **original,
            "kid": "unrelated-private-key",
            "d": "forbidden-private-value",
        },
    ]

    with pytest.raises(OidcFixtureValidationError, match="public"):
        make_fixture(tmp_path, jwks=_json_bytes(jwks))


def test_fixture_validation_opens_no_socket(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted_network: list[str] = []

    def forbidden_connection(*args: object, **kwargs: object) -> object:
        del args, kwargs
        attempted_network.append("create_connection")
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", forbidden_connection)
    fixture = make_fixture(tmp_path)
    fixture.validate()
    assert attempted_network == []


def test_provider_disable_and_cross_database_composition_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path / "primary")
    callback = fixture.callback()
    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_provider_configurations
            SET enabled = 0
            WHERE provider_configuration_id = ?
            """,
            (fixture.provider_configuration_id,),
        )
        connection.commit()

    with pytest.raises(OidcFixtureValidationError, match="unavailable"):
        fixture.validate(callback=callback)

    other = make_fixture(tmp_path / "other")
    with pytest.raises(OidcFixtureConfigurationError, match="one database"):
        ZeroNetworkOidcFixtureAdapter(
            fixture.db_path,
            sessions=other.sessions,
            configured_exact_issuer=ISSUER,
            configured_redirect_uri=REDIRECT_URI,
            allowed_origin=ORIGIN,
            expected_audience=AUDIENCE,
            discovery_fixture=DISCOVERY_BYTES,
            jwks_fixture=JWKS_BYTES,
            expected_authorization_code_digest=(
                authorization_code_fixture_digest(AUTHORIZATION_CODE)
            ),
            clock=fixture.clock,
        )


def test_issuer_configuration_rejects_query_or_non_https(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    for issuer in (
        "https://identity.example.test/tenant-a?alternate=true",
        "http://identity.example.test/tenant-a",
    ):
        with pytest.raises(OidcFixtureConfigurationError):
            ZeroNetworkOidcFixtureAdapter(
                fixture.db_path,
                sessions=fixture.sessions,
                configured_exact_issuer=issuer,
                configured_redirect_uri=REDIRECT_URI,
                allowed_origin=ORIGIN,
                expected_audience=AUDIENCE,
                discovery_fixture=DISCOVERY_BYTES,
                jwks_fixture=JWKS_BYTES,
                expected_authorization_code_digest=(
                    authorization_code_fixture_digest(AUTHORIZATION_CODE)
                ),
                clock=fixture.clock,
            )


def test_callback_model_hides_malformed_secret_inputs(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    callback = fixture.callback()
    sensitive = "do-not-echo-this-code\n"

    with pytest.raises(ValidationError) as caught:
        FixtureCallback.model_validate(
            {
                **callback.model_dump(),
                "authorization_code": sensitive,
            }
        )
    assert sensitive.strip() not in str(caught.value)


@pytest.mark.parametrize(
    "malformed",
    [
        "http://127.0.0.1:99999/callback",
        "http://127.0.0.1:\t5173/callback",
        "http://:/callback",
        "http://[not-an-ipv6]/callback",
        "http://\ud800/callback",
    ],
)
def test_session_preauthentication_url_parser_failures_are_normalized(
    tmp_path: Path,
    malformed: str,
) -> None:
    fixture = make_fixture(tmp_path)

    with pytest.raises(SessionConfigurationError, match="malformed"):
        fixture.sessions.create_preauthentication(
            fixture.organization_id,
            fixture.provider_configuration_id,
            exact_issuer=ISSUER,
            configured_redirect_uri=malformed,
            allowed_origin=ORIGIN,
        )
