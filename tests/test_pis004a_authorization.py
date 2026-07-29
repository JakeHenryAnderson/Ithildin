from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.enterprise_authorization import (
    ApprovalClass,
    ApprovalRequestRecord,
    AuthorizationAuthorityUnavailableError,
    AuthorizationDecision,
    EnterpriseAction,
    EnterpriseApprovalRequestStore,
    EnterpriseAuthorizationEngine,
    EnterpriseAuthorizationPolicy,
    ServerOwnedResourceScope,
)
from ithildin_api.enterprise_identity import (
    CallerAuthorityRejectedError,
    EnterpriseIdentityStore,
    EnterprisePrincipalType,
    OrganizationRole,
    WorkspaceRole,
    reject_caller_authority_fields,
)
from ithildin_api.enterprise_sessions import (
    AuthenticationMethod,
    EnterpriseSessionStore,
    SessionClientMaterial,
    SessionContext,
    SessionDigestKeyRing,
    SessionMutationRejectedError,
    SessionRevokedError,
)
from pydantic import ValidationError

ISSUER = "https://identity.example.test/tenant-a"
ORIGIN = "http://127.0.0.1:5173"


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@dataclass
class PolicyState:
    current: EnterpriseAuthorizationPolicy

    def __call__(self) -> EnterpriseAuthorizationPolicy:
        return self.current


@dataclass(frozen=True)
class AuthorizationFixture:
    db_path: Path
    identities: EnterpriseIdentityStore
    sessions: EnterpriseSessionStore
    engine: EnterpriseAuthorizationEngine
    approvals: EnterpriseApprovalRequestStore
    policies: PolicyState
    clock: MutableClock
    session: SessionClientMaterial
    principal_id: str
    organization_id: str
    provider_configuration_id: str


def make_fixture(
    tmp_path: Path,
    *,
    authentication_method: AuthenticationMethod = AuthenticationMethod.OIDC_FIXTURE,
    policy: EnterpriseAuthorizationPolicy | None = None,
) -> AuthorizationFixture:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    clock = MutableClock()
    identities = EnterpriseIdentityStore(db_path, clock=clock)
    organization = identities.create_organization()
    provider = identities.add_provider_configuration(
        organization.organization_id,
        exact_issuer=ISSUER,
    )
    identity = identities.provision_human_identity(
        organization.organization_id,
        provider.provider_configuration_id,
        exact_issuer=ISSUER,
        subject="subject-Aa-001",
    )
    identities.set_organization_membership(
        organization.organization_id,
        identity.principal_id,
        roles={OrganizationRole.MEMBER},
    )
    for workspace_id in ("alpha", "beta", "gamma"):
        identities.create_workspace(organization.organization_id, workspace_id)
    identities.set_workspace_membership(
        organization.organization_id,
        "alpha",
        identity.principal_id,
        roles={
            WorkspaceRole.READER,
            WorkspaceRole.CONTRIBUTOR,
            WorkspaceRole.APPROVER,
        },
    )
    identities.set_workspace_membership(
        organization.organization_id,
        "beta",
        identity.principal_id,
        roles={WorkspaceRole.CONTRIBUTOR},
    )
    sessions = EnterpriseSessionStore(
        db_path,
        key_ring=SessionDigestKeyRing({1: b"A" * 32}, active_generation=1),
        allowed_origins=frozenset({ORIGIN}),
        clock=clock,
    )
    authority = identities.current_organization_authority(
        identity.principal_id,
        organization.organization_id,
    )
    authentication_grant_id = "agrant_" + uuid4().hex
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO identity_authentication_grants (
                authentication_grant_id, assertion_audit_id,
                organization_id, provider_configuration_id,
                provider_configuration_generation, principal_id, identity_generation,
                membership_generation, authentication_method,
                authentication_time, created_at, expires_at,
                status, consumed_at
            ) VALUES (?, ?, ?, ?, (
                SELECT generation
                FROM identity_provider_configurations
                WHERE organization_id = ? AND provider_configuration_id = ?
            ), ?, ?, ?, 'oidc_fixture', ?, ?, ?,
                      'active', NULL)
            """,
            (
                authentication_grant_id,
                "oaud_" + uuid4().hex,
                organization.organization_id,
                provider.provider_configuration_id,
                organization.organization_id,
                provider.provider_configuration_id,
                identity.principal_id,
                authority.identity_generation,
                authority.membership_generation,
                clock.now.isoformat(),
                clock.now.isoformat(),
                (clock.now + timedelta(minutes=1)).isoformat(),
            ),
        )
    issued = sessions.issue_session(authentication_grant_id)
    if authentication_method is AuthenticationMethod.LOCAL_RECOVERY:
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                UPDATE identity_sessions
                SET authentication_method = 'local_recovery'
                WHERE session_id = ?
                """,
                (issued.context.session_id,),
            )
        issued = issued.model_copy(
            update={
                "context": issued.context.model_copy(
                    update={"authentication_method": AuthenticationMethod.LOCAL_RECOVERY}
                )
            }
        )
    policies = PolicyState(current=policy or EnterpriseAuthorizationPolicy(policy_generation=1))
    approvals = EnterpriseApprovalRequestStore(db_path, clock=clock)
    engine = EnterpriseAuthorizationEngine.from_stores(
        sessions=sessions,
        identities=identities,
        approval_requests=approvals,
        policy_provider=policies,
        clock=clock,
    )
    return AuthorizationFixture(
        db_path=db_path,
        identities=identities,
        sessions=sessions,
        engine=engine,
        approvals=approvals,
        policies=policies,
        clock=clock,
        session=issued,
        principal_id=identity.principal_id,
        organization_id=organization.organization_id,
        provider_configuration_id=provider.provider_configuration_id,
    )


def scope(fixture: AuthorizationFixture, workspace_id: str) -> ServerOwnedResourceScope:
    return ServerOwnedResourceScope(
        organization_id=fixture.organization_id,
        workspace_id=workspace_id,
    )


def approval_request(
    fixture: AuthorizationFixture,
    *,
    requester_principal_id: str,
    approval_class: ApprovalClass,
    workspace_id: str = "alpha",
) -> ApprovalRequestRecord:
    session = (
        fixture.session
        if requester_principal_id == fixture.principal_id
        else issue_session_for_principal(
            fixture,
            principal_id=requester_principal_id,
            organization_id=fixture.organization_id,
        )
    )
    request_method = {
        ApprovalClass.STANDARD: fixture.engine.request_standard_change_approval,
        ApprovalClass.TRUSTED_HOST_PLACEMENT: (
            fixture.engine.request_trusted_host_placement_approval
        ),
        ApprovalClass.HIGH_RISK: fixture.engine.request_high_risk_change_approval,
    }[approval_class]
    return request_method(
        session.handle,
        allowed_origin=ORIGIN,
        csrf_token=session.csrf_token,
        scope=ServerOwnedResourceScope(
            organization_id=fixture.organization_id,
            workspace_id=workspace_id,
        ),
    )


def evaluate_approval(
    fixture: AuthorizationFixture,
    request: ApprovalRequestRecord,
) -> AuthorizationDecision:
    return fixture.engine.authorize_approval(
        fixture.session.handle,
        approval_request_id=request.approval_request_id,
        allowed_origin=ORIGIN,
        csrf_token=fixture.session.csrf_token,
    )


def provision_other_human(
    fixture: AuthorizationFixture,
    *,
    subject: str,
) -> str:
    identity = fixture.identities.provision_human_identity(
        fixture.organization_id,
        fixture.provider_configuration_id,
        exact_issuer=ISSUER,
        subject=subject,
    )
    fixture.identities.set_organization_membership(
        fixture.organization_id,
        identity.principal_id,
        roles={OrganizationRole.MEMBER},
    )
    fixture.identities.set_workspace_membership(
        fixture.organization_id,
        "alpha",
        identity.principal_id,
        roles={WorkspaceRole.READER, WorkspaceRole.CONTRIBUTOR},
    )
    return identity.principal_id


def issue_session_for_principal(
    fixture: AuthorizationFixture,
    *,
    principal_id: str,
    organization_id: str,
) -> SessionClientMaterial:
    authority = fixture.identities.current_organization_authority(
        principal_id,
        organization_id,
    )
    authentication_grant_id = "agrant_" + uuid4().hex
    with sqlite3.connect(fixture.db_path) as connection:
        provider = connection.execute(
            """
            SELECT b.provider_configuration_id, pc.generation
            FROM identity_bindings AS b
            JOIN identity_provider_configurations AS pc
              ON pc.organization_id = b.organization_id
             AND pc.provider_configuration_id = b.provider_configuration_id
            WHERE b.organization_id = ? AND b.principal_id = ?
            """,
            (organization_id, principal_id),
        ).fetchone()
        assert provider is not None
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
                "oaud_" + uuid4().hex,
                organization_id,
                str(provider[0]),
                int(provider[1]),
                principal_id,
                authority.identity_generation,
                authority.membership_generation,
                fixture.clock.now.isoformat(),
                fixture.clock.now.isoformat(),
                (fixture.clock.now + timedelta(minutes=1)).isoformat(),
            ),
        )
    return fixture.sessions.issue_session(authentication_grant_id)


def test_allowed_decision_binds_all_current_server_authority(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    decision = fixture.engine.authorize(
        fixture.session.handle,
        scope=scope(fixture, "alpha"),
        action=EnterpriseAction.READ,
    )

    assert decision.allowed
    assert decision.reason_code == "authorized"
    assert decision.principal_id == fixture.principal_id
    assert decision.principal_type is EnterprisePrincipalType.HUMAN
    assert decision.authenticated_organization_id == fixture.organization_id
    assert decision.organization_id == fixture.organization_id
    assert decision.workspace_id == "alpha"
    assert decision.identity_generation == fixture.session.context.identity_generation
    assert decision.membership_generation == fixture.session.context.membership_generation
    assert decision.session_id == fixture.session.context.session_id
    assert decision.session_audit_id == fixture.session.context.session_audit_id
    assert decision.authentication_method is AuthenticationMethod.OIDC_FIXTURE
    assert decision.recent_auth_satisfied
    assert decision.policy_generation == 1

    serialized = json.dumps(decision.safe_audit_metadata(), sort_keys=True)
    assert fixture.session.handle not in serialized
    assert fixture.session.csrf_token not in serialized
    assert ISSUER not in serialized
    assert "subject-Aa-001" not in serialized
    assert "claims" not in serialized
    assert "credential" not in serialized


def test_current_roles_grant_only_their_bounded_actions(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)

    contribute = fixture.engine.authorize_mutation(
        fixture.session.handle,
        allowed_origin=ORIGIN,
        csrf_token=fixture.session.csrf_token,
        scope=scope(fixture, "beta"),
        action=EnterpriseAction.CONTRIBUTE,
    )
    approve = evaluate_approval(
        fixture,
        approval_request(
            fixture,
            requester_principal_id=fixture.principal_id,
            approval_class=ApprovalClass.STANDARD,
            workspace_id="beta",
        ),
    )

    assert contribute.allowed
    assert not approve.allowed
    assert approve.reason_code == "role_not_authorized"


def test_direct_approval_without_server_owned_request_context_is_denied(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)

    decision = fixture.engine.authorize(
        fixture.session.handle,
        scope=scope(fixture, "alpha"),
        action=EnterpriseAction.APPROVE,
    )

    assert not decision.allowed
    assert decision.reason_code == "mutation_origin_and_csrf_required"


@pytest.mark.parametrize(
    "action",
    [
        EnterpriseAction.CONTRIBUTE,
        EnterpriseAction.MANAGE_MEMBERSHIP,
        EnterpriseAction.DESTRUCTIVE,
    ],
)
def test_mutation_authorization_requires_exact_origin_and_session_csrf(
    tmp_path: Path,
    action: EnterpriseAction,
) -> None:
    fixture = make_fixture(tmp_path)

    for origin, csrf_token in (
        ("http://localhost:5173", fixture.session.csrf_token),
        (ORIGIN, "0" * 43),
    ):
        with pytest.raises(SessionMutationRejectedError):
            fixture.engine.authorize_mutation(
                fixture.session.handle,
                allowed_origin=origin,
                csrf_token=csrf_token,
                scope=scope(fixture, "alpha"),
                action=action,
            )

    if action is EnterpriseAction.CONTRIBUTE:
        without_mutation_proof = fixture.engine.authorize(
            fixture.session.handle,
            scope=scope(fixture, "beta"),
            action=action,
        )
        assert not without_mutation_proof.allowed
        assert without_mutation_proof.reason_code == "mutation_origin_and_csrf_required"


def test_approval_uses_opaque_server_record_and_requires_mutation_proof(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    request = approval_request(
        fixture,
        requester_principal_id=fixture.principal_id,
        approval_class=ApprovalClass.HIGH_RISK,
    )
    forged_local_copy = request.model_copy(
        update={
            "requester_principal_id": "prn_" + ("f" * 32),
            "approval_class": ApprovalClass.STANDARD,
            "workspace_id": "beta",
        }
    )
    assert forged_local_copy.approval_request_id == request.approval_request_id

    for origin, csrf_token in (
        ("http://localhost:5173", fixture.session.csrf_token),
        (ORIGIN, "0" * 43),
    ):
        with pytest.raises(SessionMutationRejectedError):
            fixture.engine.authorize_approval(
                fixture.session.handle,
                approval_request_id=forged_local_copy.approval_request_id,
                allowed_origin=origin,
                csrf_token=csrf_token,
            )

    decision = fixture.engine.authorize_approval(
        fixture.session.handle,
        approval_request_id=forged_local_copy.approval_request_id,
        allowed_origin=ORIGIN,
        csrf_token=fixture.session.csrf_token,
    )
    assert not decision.allowed
    assert decision.reason_code == "self_approval_forbidden"
    assert decision.workspace_id == "alpha"
    assert decision.approval_request_generation == 1
    assert decision.effect_authority is False


@pytest.mark.parametrize("authority_change", ["identity_disabled", "membership_changed"])
def test_queued_approval_revalidates_exact_requester_authority(
    tmp_path: Path,
    authority_change: str,
) -> None:
    fixture = make_fixture(tmp_path)
    requester_principal_id = provision_other_human(
        fixture,
        subject="subject-queued-requester",
    )
    request = approval_request(
        fixture,
        requester_principal_id=requester_principal_id,
        approval_class=ApprovalClass.HIGH_RISK,
    )
    created_authority = fixture.identities.current_authority_state(
        requester_principal_id,
        fixture.organization_id,
        "alpha",
    )
    assert request.requester_identity_generation == created_authority.identity_generation
    assert request.requester_membership_generation == created_authority.membership_generation

    if authority_change == "identity_disabled":
        fixture.identities.set_principal_enabled(
            requester_principal_id,
            enabled=False,
        )
    else:
        fixture.identities.set_workspace_membership(
            fixture.organization_id,
            "alpha",
            requester_principal_id,
            roles={WorkspaceRole.CONTRIBUTOR},
        )

    decision = evaluate_approval(fixture, request)

    assert not decision.allowed
    assert decision.reason_code == "stale_requester_authority"
    assert decision.approval_request_id == request.approval_request_id
    assert decision.effect_authority is False


def test_organization_membership_reenable_does_not_revive_queued_request(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    requester_principal_id = provision_other_human(
        fixture,
        subject="subject-reenabled-requester",
    )
    request = approval_request(
        fixture,
        requester_principal_id=requester_principal_id,
        approval_class=ApprovalClass.HIGH_RISK,
    )

    fixture.identities.set_organization_membership(
        fixture.organization_id,
        requester_principal_id,
        roles={OrganizationRole.MEMBER},
        enabled=False,
    )
    fixture.identities.set_organization_membership(
        fixture.organization_id,
        requester_principal_id,
        roles={OrganizationRole.MEMBER},
        enabled=True,
    )

    decision = evaluate_approval(fixture, request)

    assert not decision.allowed
    assert decision.reason_code == "stale_requester_authority"
    assert (
        fixture.identities.list_workspace_memberships(
            requester_principal_id,
            fixture.organization_id,
        )
        == ()
    )


def test_unknown_and_cross_organization_approval_ids_are_indistinguishable(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    other_organization = fixture.identities.create_organization()
    other_provider = fixture.identities.add_provider_configuration(
        other_organization.organization_id,
        exact_issuer=ISSUER,
    )
    other_identity = fixture.identities.provision_human_identity(
        other_organization.organization_id,
        other_provider.provider_configuration_id,
        exact_issuer=ISSUER,
        subject="subject-other-org",
    )
    fixture.identities.set_organization_membership(
        other_organization.organization_id,
        other_identity.principal_id,
        roles={OrganizationRole.MEMBER},
    )
    fixture.identities.create_workspace(
        other_organization.organization_id,
        "outside",
    )
    fixture.identities.set_workspace_membership(
        other_organization.organization_id,
        "outside",
        other_identity.principal_id,
        roles={WorkspaceRole.CONTRIBUTOR, WorkspaceRole.APPROVER},
    )
    other_session = issue_session_for_principal(
        fixture,
        principal_id=other_identity.principal_id,
        organization_id=other_organization.organization_id,
    )
    other_request = fixture.engine.request_high_risk_change_approval(
        other_session.handle,
        allowed_origin=ORIGIN,
        csrf_token=other_session.csrf_token,
        scope=ServerOwnedResourceScope(
            organization_id=other_organization.organization_id,
            workspace_id="outside",
        ),
    )

    failures: list[str] = []
    for approval_request_id in (
        "apr_" + ("f" * 32),
        other_request.approval_request_id,
        "malformed",
    ):
        with pytest.raises(
            AuthorizationAuthorityUnavailableError,
            match="approval request is unavailable",
        ) as exc_info:
            fixture.engine.authorize_approval(
                fixture.session.handle,
                approval_request_id=approval_request_id,
                allowed_origin=ORIGIN,
                csrf_token=fixture.session.csrf_token,
            )
        failures.append(str(exc_info.value))
    assert len(set(failures)) == 1


def test_self_approval_is_denied_for_every_approval_class(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    separate_requester = provision_other_human(
        fixture,
        subject="subject-Aa-002",
    )

    for approval_class in ApprovalClass:
        self_decision = evaluate_approval(
            fixture,
            approval_request(
                fixture,
                requester_principal_id=fixture.principal_id,
                approval_class=approval_class,
            ),
        )
        assert not self_decision.allowed
        assert self_decision.reason_code == "self_approval_forbidden"

    high_risk_separate = evaluate_approval(
        fixture,
        approval_request(
            fixture,
            requester_principal_id=separate_requester,
            approval_class=ApprovalClass.HIGH_RISK,
        ),
    )

    assert high_risk_separate.allowed


def test_recovery_authentication_and_stale_auth_cannot_approve(tmp_path: Path) -> None:
    recovery = make_fixture(
        tmp_path / "recovery",
        authentication_method=AuthenticationMethod.LOCAL_RECOVERY,
    )
    recovery_decision = evaluate_approval(
        recovery,
        approval_request(
            recovery,
            requester_principal_id=recovery.principal_id,
            approval_class=ApprovalClass.HIGH_RISK,
        ),
    )
    assert not recovery_decision.allowed
    assert recovery_decision.reason_code == "recent_human_authentication_required"
    assert not recovery_decision.recent_auth_satisfied

    stale = make_fixture(tmp_path / "stale")
    stale.clock.advance(timedelta(minutes=10))
    stale_decision = evaluate_approval(
        stale,
        approval_request(
            stale,
            requester_principal_id=stale.principal_id,
            approval_class=ApprovalClass.HIGH_RISK,
        ),
    )
    assert not stale_decision.allowed
    assert stale_decision.reason_code == "recent_human_authentication_required"


def test_cross_organization_and_unjoined_workspace_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    other_organization = fixture.identities.create_organization()

    wrong_organization = fixture.engine.authorize(
        fixture.session.handle,
        scope=ServerOwnedResourceScope(
            organization_id=other_organization.organization_id,
            workspace_id="alpha",
        ),
        action=EnterpriseAction.READ,
    )
    unjoined_workspace = fixture.engine.authorize(
        fixture.session.handle,
        scope=scope(fixture, "gamma"),
        action=EnterpriseAction.READ,
    )

    assert not wrong_organization.allowed
    assert wrong_organization.reason_code == "organization_scope_mismatch"
    assert wrong_organization.authenticated_organization_id != wrong_organization.organization_id
    assert not unjoined_workspace.allowed
    assert unjoined_workspace.reason_code == "workspace_authority_unavailable"


def test_bulk_read_denies_any_cross_workspace_item_and_enforces_limit(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(
        tmp_path,
        policy=EnterpriseAuthorizationPolicy(
            policy_generation=1,
            maximum_bulk_items=2,
        ),
    )
    alpha = scope(fixture, "alpha")

    allowed = fixture.engine.authorize_bulk_read(
        fixture.session.handle,
        scope=alpha,
        resource_scopes=(alpha, alpha),
    )
    cross_scope = fixture.engine.authorize_bulk_read(
        fixture.session.handle,
        scope=alpha,
        resource_scopes=(alpha, scope(fixture, "beta")),
    )
    over_limit = fixture.engine.authorize_bulk_read(
        fixture.session.handle,
        scope=alpha,
        resource_scopes=(alpha, alpha, alpha),
    )

    assert allowed.allowed
    assert not cross_scope.allowed
    assert cross_scope.reason_code == "cross_scope_bulk_forbidden"
    assert not over_limit.allowed
    assert over_limit.reason_code == "bulk_limit_exceeded"


def test_listing_has_no_scope_input_and_returns_only_current_memberships(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    other_organization = fixture.identities.create_organization()
    fixture.identities.create_workspace(other_organization.organization_id, "outside")

    listed = fixture.engine.list_authorized_workspaces(fixture.session.handle)

    assert [(item.organization_id, item.workspace_id) for item in listed] == [
        (fixture.organization_id, "alpha"),
        (fixture.organization_id, "beta"),
    ]
    assert all(item.decision.allowed for item in listed)
    assert all(item.decision.organization_id == fixture.organization_id for item in listed)


def test_policy_generation_is_loaded_server_side_for_each_decision(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    first = fixture.engine.authorize(
        fixture.session.handle,
        scope=scope(fixture, "alpha"),
        action=EnterpriseAction.READ,
    )
    fixture.policies.current = EnterpriseAuthorizationPolicy(policy_generation=7)
    second = fixture.engine.authorize(
        fixture.session.handle,
        scope=scope(fixture, "alpha"),
        action=EnterpriseAction.READ,
    )

    assert first.policy_generation == 1
    assert second.policy_generation == 7


def test_decision_is_snapshot_only_and_closed_request_requires_new_evaluation(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    requester = provision_other_human(
        fixture,
        subject="subject-Aa-003",
    )
    request = approval_request(
        fixture,
        requester_principal_id=requester,
        approval_class=ApprovalClass.HIGH_RISK,
    )
    decision = evaluate_approval(fixture, request)
    assert decision.allowed
    assert decision.effect_authority is False
    assert decision.approval_request_generation == 1

    with sqlite3.connect(fixture.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_approval_requests
            SET status = 'cancelled', request_generation = 2, updated_at = ?
            WHERE approval_request_id = ?
            """,
            (fixture.clock.now.isoformat(), request.approval_request_id),
        )

    with pytest.raises(
        AuthorizationAuthorityUnavailableError,
        match="approval request is unavailable",
    ):
        evaluate_approval(fixture, request)


def test_membership_generation_change_invalidates_before_authorization(
    tmp_path: Path,
) -> None:
    fixture = make_fixture(tmp_path)
    fixture.identities.set_workspace_membership(
        fixture.organization_id,
        "alpha",
        fixture.principal_id,
        roles={WorkspaceRole.READER},
    )

    with pytest.raises(SessionRevokedError, match="generation changed"):
        fixture.engine.authorize(
            fixture.session.handle,
            scope=scope(fixture, "alpha"),
            action=EnterpriseAction.READ,
        )


class StaticSessionValidator:
    def __init__(self, context: SessionContext) -> None:
        self.context = context

    def validate_session(self, handle: str) -> SessionContext:
        del handle
        return self.context

    def validate_mutation(
        self,
        handle: str,
        *,
        allowed_origin: str,
        csrf_token: str,
    ) -> SessionContext:
        del handle, allowed_origin, csrf_token
        return self.context


@pytest.mark.parametrize(
    ("principal_type", "organization_role", "workspace_role"),
    [
        (
            EnterprisePrincipalType.NODE,
            OrganizationRole.NODE_OPERATOR,
            WorkspaceRole.NODE,
        ),
        (
            EnterprisePrincipalType.SERVICE,
            OrganizationRole.SERVICE_OPERATOR,
            WorkspaceRole.SERVICE,
        ),
    ],
)
def test_node_or_service_role_cannot_satisfy_human_approval(
    tmp_path: Path,
    principal_type: EnterprisePrincipalType,
    organization_role: OrganizationRole,
    workspace_role: WorkspaceRole,
) -> None:
    fixture = make_fixture(tmp_path)
    principal = fixture.identities.create_nonhuman_principal(principal_type)
    fixture.identities.set_organization_membership(
        fixture.organization_id,
        principal.principal_id,
        roles={organization_role},
    )
    generation = fixture.identities.set_workspace_membership(
        fixture.organization_id,
        "alpha",
        principal.principal_id,
        roles={workspace_role},
    )
    context = SessionContext(
        session_id="sess_" + ("f" * 32),
        family_id="sfam_" + ("f" * 32),
        session_audit_id="saud_" + ("f" * 32),
        principal_id=principal.principal_id,
        organization_id=fixture.organization_id,
        identity_generation=principal.identity_generation,
        membership_generation=generation,
        authentication_method=AuthenticationMethod.OIDC_FIXTURE,
        recent_auth_at=fixture.clock.now,
        absolute_expires_at=fixture.clock.now + timedelta(hours=1),
    )
    engine = EnterpriseAuthorizationEngine(
        sessions=StaticSessionValidator(context),
        identities=fixture.identities,
        approval_requests=fixture.approvals,
        policy_provider=fixture.policies,
        clock=fixture.clock,
    )
    request = approval_request(
        fixture,
        requester_principal_id=fixture.principal_id,
        approval_class=ApprovalClass.HIGH_RISK,
    )

    decision = engine.authorize_approval(
        "nonhuman-fixture-handle",
        approval_request_id=request.approval_request_id,
        allowed_origin=ORIGIN,
        csrf_token="fixture-csrf",
    )

    assert not decision.allowed
    assert decision.reason_code == "human_principal_required"
    assert decision.principal_type is principal_type


def test_disabled_or_corrupt_workspace_authority_denies_without_enumeration(
    tmp_path: Path,
) -> None:
    disabled = make_fixture(tmp_path / "disabled")
    with sqlite3.connect(disabled.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_workspaces SET enabled = 0
            WHERE organization_id = ? AND workspace_id = 'alpha'
            """,
            (disabled.organization_id,),
        )
    denied = disabled.engine.authorize(
        disabled.session.handle,
        scope=scope(disabled, "alpha"),
        action=EnterpriseAction.READ,
    )
    assert not denied.allowed
    assert denied.reason_code == "workspace_authority_unavailable"

    corrupt = make_fixture(tmp_path / "corrupt")
    with sqlite3.connect(corrupt.db_path) as connection:
        connection.execute(
            """
            UPDATE identity_workspace_memberships
            SET roles_json = '["reader","reader"]'
            WHERE organization_id = ? AND workspace_id = 'alpha'
              AND principal_id = ?
            """,
            (corrupt.organization_id, corrupt.principal_id),
        )
    corrupt_denial = corrupt.engine.authorize(
        corrupt.session.handle,
        scope=scope(corrupt, "alpha"),
        action=EnterpriseAction.READ,
    )
    assert not corrupt_denial.allowed
    assert corrupt_denial.reason_code == "workspace_authority_unavailable"


def test_caller_authority_injection_and_unsafe_policy_shapes_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(CallerAuthorityRejectedError):
        reject_caller_authority_fields(
            {
                "operation": {"artifact_id": "artifact-1"},
                "authorization": {"workspace_id": "beta", "role": "approver"},
            }
        )
    with pytest.raises(ValidationError, match="approval"):
        EnterpriseAuthorizationPolicy(
            policy_generation=1,
            recent_authentication_actions=frozenset({EnterpriseAction.MANAGE_MEMBERSHIP}),
        )
    with pytest.raises(ValidationError, match="non-strong"):
        EnterpriseAuthorizationPolicy(
            policy_generation=1,
            recent_authentication_methods=frozenset({AuthenticationMethod.LOCAL_RECOVERY}),
        )
    with pytest.raises(ValidationError, match="all approval classes"):
        EnterpriseAuthorizationPolicy(
            policy_generation=1,
            self_approval_denied_for=frozenset(
                {
                    ApprovalClass.TRUSTED_HOST_PLACEMENT,
                    ApprovalClass.HIGH_RISK,
                }
            ),
        )
    assert EnterpriseAuthorizationPolicy(
        policy_generation=1,
        recent_authentication_maximum_age=timedelta(minutes=10),
    ).recent_authentication_maximum_age == timedelta(minutes=10)
    for excessive_age in (
        timedelta(minutes=10, microseconds=1),
        timedelta(days=365),
    ):
        with pytest.raises(ValidationError, match="ten-minute ceiling"):
            EnterpriseAuthorizationPolicy(
                policy_generation=1,
                recent_authentication_maximum_age=excessive_age,
            )
    fixture = make_fixture(tmp_path)
    assert not hasattr(fixture.approvals, "create_pending")
    assert not hasattr(fixture.engine, "request_approval")
    high_risk_request = fixture.engine.request_high_risk_change_approval(
        fixture.session.handle,
        allowed_origin=ORIGIN,
        csrf_token=fixture.session.csrf_token,
        scope=scope(fixture, "alpha"),
    )
    assert high_risk_request.approval_class is ApprovalClass.HIGH_RISK
    assert high_risk_request.effect_authority is False


def test_invalid_policy_provider_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    engine = EnterpriseAuthorizationEngine(
        sessions=fixture.sessions,
        identities=fixture.identities,
        approval_requests=fixture.approvals,
        policy_provider=lambda: cast(EnterpriseAuthorizationPolicy, object()),
        clock=fixture.clock,
    )

    with pytest.raises(AuthorizationAuthorityUnavailableError, match="invalid"):
        engine.authorize(
            fixture.session.handle,
            scope=scope(fixture, "alpha"),
            action=EnterpriseAction.READ,
        )
