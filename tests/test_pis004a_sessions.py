from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.enterprise_identity import (
    EnterpriseAuditOutcome,
    EnterpriseAuditReasonCode,
    EnterpriseIdentityStore,
    EnterprisePrincipalType,
    OrganizationRole,
)
from ithildin_api.enterprise_sessions import (
    AuthenticationMethod,
    EnterpriseSessionStore,
    PreauthenticationError,
    PreauthenticationReplayError,
    SessionAuthenticationError,
    SessionClientMaterial,
    SessionConfigurationError,
    SessionDigestKeyRing,
    SessionExpiredError,
    SessionMutationRejectedError,
    SessionReplayError,
    SessionRevokedError,
)

ISSUER = "https://identity.example.test/tenant-a"
ORIGIN = "http://127.0.0.1:5173"
REDIRECT_URI = f"{ORIGIN}/identity/callback"


class MutableClock:
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
        width = 43 if entropy_bytes <= 32 else 64
        return f"{self.secret_count:0{width}d}"

    def envelope_nonce(self, length: int) -> bytes:
        assert length == 12
        self.envelope_nonce_count += 1
        return self.envelope_nonce_count.to_bytes(length, "big")


@dataclass(frozen=True)
class SessionFixture:
    db_path: Path
    identity: EnterpriseIdentityStore
    sessions: EnterpriseSessionStore
    clock: MutableClock
    organization_id: str
    provider_configuration_id: str
    principal_id: str


def make_fixture(
    tmp_path: Path,
    *,
    key_ring: SessionDigestKeyRing | None = None,
    idle_ttl: timedelta = timedelta(minutes=30),
    absolute_ttl: timedelta = timedelta(hours=12),
    preauthentication_ttl: timedelta = timedelta(minutes=5),
) -> SessionFixture:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    clock = MutableClock()
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
        subject="subject-Aa-001",
    )
    identity.set_organization_membership(
        organization.organization_id,
        resolution.principal_id,
        roles={OrganizationRole.MEMBER, OrganizationRole.APPROVER},
    )
    sessions = EnterpriseSessionStore(
        db_path,
        key_ring=key_ring or SessionDigestKeyRing({1: b"A" * 32}, active_generation=1),
        allowed_origins=frozenset({ORIGIN}),
        clock=clock,
        secret_factory=factories.secret,
        nonce_factory=factories.envelope_nonce,
        id_factory=factories.identifier,
        idle_ttl=idle_ttl,
        absolute_ttl=absolute_ttl,
        preauthentication_ttl=preauthentication_ttl,
    )
    return SessionFixture(
        db_path=db_path,
        identity=identity,
        sessions=sessions,
        clock=clock,
        organization_id=organization.organization_id,
        provider_configuration_id=provider.provider_configuration_id,
        principal_id=resolution.principal_id,
    )


def create_authentication_grant(
    fixture: SessionFixture,
    *,
    principal_id: str | None = None,
    authentication_time: datetime | None = None,
) -> str:
    authority = fixture.identity.current_organization_authority(
        principal_id or fixture.principal_id,
        fixture.organization_id,
    )
    grant_id = "agrant_" + uuid4().hex
    now = fixture.clock.now
    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            INSERT INTO identity_authentication_grants (
                authentication_grant_id, assertion_audit_id,
                organization_id, principal_id, identity_generation,
                membership_generation, authentication_method,
                authentication_time, created_at, expires_at,
                status, consumed_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'oidc_fixture', ?, ?, ?,
                      'active', NULL)
            """,
            (
                grant_id,
                "oaud_" + uuid4().hex,
                fixture.organization_id,
                authority.principal_id,
                authority.identity_generation,
                authority.membership_generation,
                (authentication_time or now).isoformat(),
                now.isoformat(),
                (now + timedelta(minutes=1)).isoformat(),
            ),
        )
    return grant_id


def issue_session(
    fixture: SessionFixture,
    *,
    principal_id: str | None = None,
    authentication_method: AuthenticationMethod = AuthenticationMethod.OIDC_FIXTURE,
    recent_auth_at: datetime | None = None,
) -> SessionClientMaterial:
    issued = fixture.sessions.issue_session(
        create_authentication_grant(
            fixture,
            principal_id=principal_id,
            authentication_time=recent_auth_at,
        )
    )
    if authentication_method is AuthenticationMethod.OIDC_FIXTURE:
        return issued
    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_sessions
            SET authentication_method = ?
            WHERE session_id = ?
            """,
            (authentication_method.value, issued.context.session_id),
        )
    return issued.model_copy(
        update={
            "context": issued.context.model_copy(
                update={"authentication_method": authentication_method}
            )
        }
    )


def test_only_keyed_session_and_csrf_digests_are_persisted(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )

    with sqlite3.connect(fixture.db_path) as connection:
        row = connection.execute(
            """
            SELECT handle_digest, digest_key_generation, session_audit_id,
                   csrf_digest, authentication_method
            FROM identity_sessions
            """
        ).fetchone()
    assert row is not None
    assert str(row[0]).startswith("hmac-sha256:")
    assert len(str(row[0])) == 76
    assert row[1] == 1
    assert str(row[2]).startswith("saud_")
    assert str(row[2]) != issued.handle
    assert str(row[3]).startswith("hmac-sha256:")
    assert row[4] == "oidc_fixture"
    database_bytes = fixture.db_path.read_bytes()
    assert issued.handle.encode() not in database_bytes
    assert issued.csrf_token.encode() not in database_bytes

    validated = fixture.sessions.validate_session(issued.handle)
    assert validated == issued.context
    serialized_audit = json.dumps(
        validated.safe_audit_metadata(
            outcome=EnterpriseAuditOutcome.ALLOWED,
            reason_code=EnterpriseAuditReasonCode.SESSION_VALID,
        ),
        sort_keys=True,
    )
    assert issued.handle not in serialized_audit
    assert issued.csrf_token not in serialized_audit

    with pytest.raises(SessionAuthenticationError, match="did not authenticate"):
        fixture.sessions.validate_session(issued.context.session_audit_id)


def test_session_digest_key_configuration_and_retirement_fail_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(SessionConfigurationError, match="active.*unavailable"):
        SessionDigestKeyRing({1: b"A" * 32}, active_generation=2)
    with pytest.raises(SessionConfigurationError, match="256 bits"):
        SessionDigestKeyRing({1: b"short"}, active_generation=1)

    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    preauthentication = fixture.sessions.create_preauthentication(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    consumed_client = fixture.sessions.create_preauthentication(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    consumed_transaction = fixture.sessions.consume_preauthentication(
        consumed_client.transaction_handle,
        state=consumed_client.state,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    retired_store = EnterpriseSessionStore(
        fixture.db_path,
        key_ring=SessionDigestKeyRing({2: b"B" * 32}, active_generation=2),
        allowed_origins=frozenset({ORIGIN}),
        clock=fixture.clock,
    )
    with pytest.raises(SessionAuthenticationError, match="did not authenticate"):
        retired_store.validate_session(issued.handle)
    with pytest.raises(SessionAuthenticationError, match="did not authenticate"):
        fixture.sessions.validate_session(issued.handle)
    with pytest.raises(SessionConfigurationError, match="cannot be restored"):
        EnterpriseSessionStore(
            fixture.db_path,
            key_ring=SessionDigestKeyRing(
                {1: b"A" * 32, 2: b"B" * 32},
                active_generation=2,
            ),
            allowed_origins=frozenset({ORIGIN}),
            clock=fixture.clock,
        )
    with pytest.raises(PreauthenticationError, match="did not authenticate"):
        retired_store.consume_preauthentication(
            preauthentication.transaction_handle,
            state=preauthentication.state,
            exact_issuer=ISSUER,
            configured_redirect_uri=REDIRECT_URI,
            allowed_origin=ORIGIN,
        )
    with pytest.raises(PreauthenticationError, match="generation is retired"):
        fixture.sessions.validate_preauthentication_nonce(
            consumed_transaction,
            nonce=consumed_client.nonce,
        )
    with sqlite3.connect(fixture.db_path) as connection:
        key_generations = connection.execute(
            """
            SELECT digest_key_generation, status
            FROM identity_session_digest_key_generations
            ORDER BY digest_key_generation
            """
        ).fetchall()
        family = connection.execute(
            "SELECT revocation_reason FROM identity_session_families"
        ).fetchone()
        preauthentication_statuses = connection.execute(
            """
            SELECT status, pkce_verifier_envelope
            FROM identity_preauthentication_transactions
            ORDER BY transaction_id
            """
        ).fetchall()
    assert key_generations == [(1, "retired"), (2, "active")]
    assert family == ("digest_key_generation_retired",)
    assert sorted(str(row[0]) for row in preauthentication_statuses) == [
        "consumed",
        "revoked",
    ]
    assert all(str(row[1]).startswith("redacted:") for row in preauthentication_statuses)


def test_key_rotation_reads_retained_generation_and_writes_active_generation(
    tmp_path: Path,
) -> None:
    initial = make_fixture(tmp_path)
    issued = issue_session(
        initial,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    rotated_key_store = EnterpriseSessionStore(
        initial.db_path,
        key_ring=SessionDigestKeyRing(
            {1: b"A" * 32, 2: b"B" * 32},
            active_generation=2,
        ),
        allowed_origins=frozenset({ORIGIN}),
        clock=initial.clock,
    )

    successor = rotated_key_store.rotate_session(issued.handle)

    with sqlite3.connect(initial.db_path) as connection:
        generations = connection.execute(
            """
            SELECT digest_key_generation FROM identity_sessions
            ORDER BY created_at, session_id
            """
        ).fetchall()
    assert generations == [(1,), (2,)]
    assert rotated_key_store.validate_session(successor.handle) == successor.context


def test_authentication_grant_is_atomic_one_use_and_generation_bound(
    tmp_path: Path,
) -> None:
    concurrent = make_fixture(tmp_path / "concurrent")
    grant_id = create_authentication_grant(concurrent)
    stores = tuple(
        EnterpriseSessionStore(
            concurrent.db_path,
            key_ring=SessionDigestKeyRing(
                {1: b"A" * 32},
                active_generation=1,
            ),
            allowed_origins=frozenset({ORIGIN}),
            clock=concurrent.clock,
        )
        for _ in range(2)
    )

    def consume(store: EnterpriseSessionStore) -> str:
        try:
            return store.issue_session(grant_id).context.session_id
        except SessionAuthenticationError:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(consume, stores))

    assert results.count("denied") == 1
    assert len([result for result in results if result.startswith("sess_")]) == 1

    stale = make_fixture(tmp_path / "stale")
    stale_grant_id = create_authentication_grant(stale)
    stale.identity.set_organization_membership(
        stale.organization_id,
        stale.principal_id,
        roles={OrganizationRole.MEMBER},
    )
    with pytest.raises(SessionAuthenticationError, match="authority is stale"):
        stale.sessions.issue_session(stale_grant_id)


@pytest.mark.parametrize(
    ("principal_type", "role"),
    [
        (EnterprisePrincipalType.NODE, OrganizationRole.NODE_OPERATOR),
        (EnterprisePrincipalType.SERVICE, OrganizationRole.SERVICE_OPERATOR),
    ],
)
def test_node_and_service_principals_cannot_receive_interactive_sessions(
    tmp_path: Path,
    principal_type: EnterprisePrincipalType,
    role: OrganizationRole,
) -> None:
    fixture = make_fixture(tmp_path)
    principal = fixture.identity.create_nonhuman_principal(principal_type)
    fixture.identity.set_organization_membership(
        fixture.organization_id,
        principal.principal_id,
        roles={role},
    )

    with pytest.raises(SessionAuthenticationError, match="human principal"):
        issue_session(
            fixture,
            principal_id=principal.principal_id,
            authentication_method=AuthenticationMethod.OIDC_FIXTURE,
        )


def test_legacy_nonhuman_session_family_is_revoked_on_validation(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    node = fixture.identity.create_nonhuman_principal(EnterprisePrincipalType.NODE)
    generation = fixture.identity.set_organization_membership(
        fixture.organization_id,
        node.principal_id,
        roles={OrganizationRole.NODE_OPERATOR},
    )
    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            UPDATE identity_session_families
            SET principal_id = ?, identity_generation = ?,
                membership_generation = ?
            WHERE family_id = ?
            """,
            (
                node.principal_id,
                node.identity_generation,
                generation,
                issued.context.family_id,
            ),
        )

    with pytest.raises(SessionRevokedError, match="not human"):
        fixture.sessions.validate_session(issued.handle)

    with sqlite3.connect(fixture.db_path) as connection:
        family = connection.execute(
            """
            SELECT revocation_reason FROM identity_session_families
            WHERE family_id = ?
            """,
            (issued.context.family_id,),
        ).fetchone()
    assert family == ("nonhuman_session_forbidden",)


def test_idle_expiry_and_absolute_expiry_use_the_injected_clock(tmp_path: Path) -> None:
    idle = make_fixture(
        tmp_path / "idle",
        idle_ttl=timedelta(minutes=5),
        absolute_ttl=timedelta(hours=1),
    )
    issued_idle = issue_session(
        idle,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    idle.clock.advance(timedelta(minutes=5))
    with pytest.raises(SessionExpiredError, match="expired"):
        idle.sessions.validate_session(issued_idle.handle)

    absolute = make_fixture(
        tmp_path / "absolute",
        idle_ttl=timedelta(minutes=5),
        absolute_ttl=timedelta(minutes=12),
    )
    issued_absolute = issue_session(
        absolute,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    absolute.clock.advance(timedelta(minutes=4))
    absolute.sessions.validate_session(issued_absolute.handle)
    absolute.clock.advance(timedelta(minutes=4))
    absolute.sessions.validate_session(issued_absolute.handle)
    absolute.clock.advance(timedelta(minutes=4))
    with pytest.raises(SessionExpiredError, match="expired"):
        absolute.sessions.validate_session(issued_absolute.handle)


def test_rotated_handle_replay_revokes_the_entire_family(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    successor = fixture.sessions.rotate_session(issued.handle)
    assert fixture.sessions.validate_session(successor.handle) == successor.context

    with pytest.raises(SessionReplayError, match="replay"):
        fixture.sessions.validate_session(issued.handle)
    with pytest.raises(SessionRevokedError, match="revoked"):
        fixture.sessions.validate_session(successor.handle)

    with sqlite3.connect(fixture.db_path) as connection:
        family = connection.execute(
            """
            SELECT revoked_at, revocation_reason
            FROM identity_session_families
            """
        ).fetchone()
    assert family is not None
    assert family[0] is not None
    assert family[1] == "rotated_handle_replay"


def test_explicit_family_revocation_invalidates_active_handle(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.LOCAL_RECOVERY,
    )

    fixture.sessions.revoke_family(issued.handle, reason_code="operator_logout")

    with pytest.raises(SessionRevokedError, match="revoked"):
        fixture.sessions.validate_session(issued.handle)


@pytest.mark.parametrize("change", ["membership", "identity"])
def test_server_generation_change_invalidates_session(
    tmp_path: Path,
    change: str,
) -> None:
    fixture = make_fixture(tmp_path)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    if change == "membership":
        fixture.identity.set_organization_membership(
            fixture.organization_id,
            fixture.principal_id,
            roles={OrganizationRole.MEMBER},
        )
    else:
        fixture.identity.set_principal_enabled(fixture.principal_id, enabled=False)

    with pytest.raises(SessionRevokedError, match="(generation changed|unavailable)"):
        fixture.sessions.validate_session(issued.handle)


def test_mutation_requires_exact_origin_and_session_bound_csrf(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    first = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )
    second = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
    )

    for origin, csrf_token in (
        ("http://localhost:5173", first.csrf_token),
        (ORIGIN, "0" * 43),
        (ORIGIN, second.csrf_token),
    ):
        with pytest.raises(SessionMutationRejectedError):
            fixture.sessions.validate_mutation(
                first.handle,
                allowed_origin=origin,
                csrf_token=csrf_token,
            )

    assert (
        fixture.sessions.validate_mutation(
            first.handle,
            allowed_origin=ORIGIN,
            csrf_token=first.csrf_token,
        )
        == first.context
    )


def test_preauthentication_is_bound_one_use_and_does_not_persist_raw_secrets(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    transaction = fixture.sessions.create_preauthentication(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(f"{4:064d}".encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert transaction.pkce_challenge == expected_challenge

    with sqlite3.connect(fixture.db_path) as connection:
        stored = connection.execute(
            """
            SELECT handle_digest, state_digest, nonce_digest,
                   pkce_verifier_envelope
            FROM identity_preauthentication_transactions
            """
        ).fetchone()
    assert stored is not None
    assert all(str(stored[index]).startswith("hmac-sha256:") for index in range(3))
    assert str(stored[3]).startswith("aes256gcm:v1:")
    database_bytes = fixture.db_path.read_bytes()
    assert transaction.transaction_handle.encode() not in database_bytes
    assert transaction.state.encode() not in database_bytes
    assert transaction.nonce.encode() not in database_bytes
    raw_pkce_verifier = f"{4:064d}"
    assert raw_pkce_verifier.encode() not in database_bytes

    for changes in (
        {"state": "9" * 43},
        {"exact_issuer": f"{ISSUER}/"},
        {"configured_redirect_uri": f"{ORIGIN}/other"},
        {"allowed_origin": "http://localhost:5173"},
    ):
        arguments = {
            "state": transaction.state,
            "exact_issuer": ISSUER,
            "configured_redirect_uri": REDIRECT_URI,
            "allowed_origin": ORIGIN,
        }
        arguments.update(changes)
        with pytest.raises(PreauthenticationError):
            fixture.sessions.consume_preauthentication(
                transaction.transaction_handle,
                **arguments,
            )

    consumed = fixture.sessions.consume_preauthentication(
        transaction.transaction_handle,
        state=transaction.state,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    fixture.sessions.validate_preauthentication_nonce(
        consumed,
        nonce=transaction.nonce,
    )
    assert consumed.pkce_verifier == raw_pkce_verifier
    with sqlite3.connect(fixture.db_path) as connection:
        consumed_envelope = connection.execute(
            """
            SELECT pkce_verifier_envelope
            FROM identity_preauthentication_transactions
            """
        ).fetchone()
    assert consumed_envelope is not None
    assert str(consumed_envelope[0]).startswith("redacted:")
    assert consumed.pkce_verifier.encode() not in fixture.db_path.read_bytes()
    with pytest.raises(PreauthenticationError, match="nonce"):
        fixture.sessions.validate_preauthentication_nonce(
            consumed,
            nonce="8" * 43,
        )
    with pytest.raises(PreauthenticationReplayError, match="no longer active"):
        fixture.sessions.consume_preauthentication(
            transaction.transaction_handle,
            state=transaction.state,
            exact_issuer=ISSUER,
            configured_redirect_uri=REDIRECT_URI,
            allowed_origin=ORIGIN,
        )


def test_preauthentication_consumption_has_one_atomic_winner(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    transaction = fixture.sessions.create_preauthentication(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )

    def consume() -> str:
        try:
            fixture.sessions.consume_preauthentication(
                transaction.transaction_handle,
                state=transaction.state,
                exact_issuer=ISSUER,
                configured_redirect_uri=REDIRECT_URI,
                allowed_origin=ORIGIN,
            )
        except PreauthenticationReplayError:
            return "replay"
        return "consumed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: consume(), range(2)))

    assert outcomes == ["consumed", "replay"]


def test_expired_preauthentication_is_revoked_atomically(tmp_path: Path) -> None:
    fixture = make_fixture(
        tmp_path,
        preauthentication_ttl=timedelta(seconds=10),
    )
    transaction = fixture.sessions.create_preauthentication(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        configured_redirect_uri=REDIRECT_URI,
        allowed_origin=ORIGIN,
    )
    fixture.clock.advance(timedelta(seconds=10))

    with pytest.raises(PreauthenticationError, match="expired"):
        fixture.sessions.consume_preauthentication(
            transaction.transaction_handle,
            state=transaction.state,
            exact_issuer=ISSUER,
            configured_redirect_uri=REDIRECT_URI,
            allowed_origin=ORIGIN,
        )

    with sqlite3.connect(fixture.db_path) as connection:
        status = connection.execute(
            """
            SELECT status, pkce_verifier_envelope
            FROM identity_preauthentication_transactions
            """
        ).fetchone()
    assert status is not None
    assert status[0] == "revoked"
    assert str(status[1]).startswith("redacted:")
    assert f"{4:064d}".encode() not in fixture.db_path.read_bytes()


def test_recent_authentication_binds_method_and_maximum_age(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    recent_auth_at = fixture.clock.now - timedelta(minutes=4)
    issued = issue_session(
        fixture,
        authentication_method=AuthenticationMethod.LOCAL_RECOVERY,
        recent_auth_at=recent_auth_at,
    )

    assert issued.context.has_recent_authentication(
        now=fixture.clock.now,
        maximum_age=timedelta(minutes=5),
        allowed_methods=frozenset({AuthenticationMethod.LOCAL_RECOVERY}),
    )
    assert not issued.context.has_recent_authentication(
        now=fixture.clock.now,
        maximum_age=timedelta(minutes=5),
        allowed_methods=frozenset({AuthenticationMethod.OIDC_FIXTURE}),
    )
    fixture.clock.advance(timedelta(minutes=1))
    assert not issued.context.has_recent_authentication(
        now=fixture.clock.now,
        maximum_age=timedelta(minutes=5),
    )


@pytest.mark.parametrize(
    ("origin", "redirect"),
    [
        ("https://preview.example.test/path", REDIRECT_URI),
        ("http://preview.example.test", "http://preview.example.test/callback"),
        (ORIGIN, "https://user@preview.example.test/callback"),
    ],
)
def test_malformed_or_nonlocal_cleartext_origin_configuration_is_rejected(
    tmp_path: Path,
    origin: str,
    redirect: str,
) -> None:
    fixture = make_fixture(tmp_path)
    with pytest.raises((SessionConfigurationError, PreauthenticationError)):
        fixture.sessions.create_preauthentication(
            fixture.organization_id,
            fixture.provider_configuration_id,
            exact_issuer=ISSUER,
            configured_redirect_uri=redirect,
            allowed_origin=origin,
        )
