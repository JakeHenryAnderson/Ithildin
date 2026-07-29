"""Server-state-only organization/workspace authorization for PIS-004A."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Collection
from contextlib import closing
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from ithildin_schemas import JsonObject
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ithildin_api.enterprise_identity import (
    EnterpriseIdentityError,
    EnterpriseIdentityStore,
    EnterprisePrincipalType,
    MembershipAuthorityState,
    OrganizationAuthorityState,
    OrganizationRole,
    WorkspaceMembershipReference,
    WorkspaceRole,
)
from ithildin_api.enterprise_sessions import (
    AuthenticationMethod,
    EnterpriseSessionStore,
    SessionContext,
)
from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

_APPROVAL_REQUEST_ID_PATTERN = re.compile(r"^apr_[0-9a-f]{32}$")


class EnterpriseAuthorizationError(RuntimeError):
    """Base class for fail-closed authorization-engine errors."""


class AuthorizationAuthorityUnavailableError(EnterpriseAuthorizationError):
    """Raised when current server authority cannot be loaded consistently."""


class EnterpriseAction(StrEnum):
    READ = "read"
    LIST = "list"
    BULK_READ = "bulk_read"
    CONTRIBUTE = "contribute"
    APPROVE = "approve"
    MANAGE_MEMBERSHIP = "manage_membership"
    AUDIT = "audit"
    DESTRUCTIVE = "destructive"


class ApprovalClass(StrEnum):
    STANDARD = "standard"
    TRUSTED_HOST_PLACEMENT = "trusted_host_placement"
    HIGH_RISK = "high_risk"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EnterpriseAuthorizationPolicy(_FrozenModel):
    policy_generation: int = Field(ge=1)
    recent_authentication_maximum_age: timedelta = timedelta(minutes=10)
    recent_authentication_methods: frozenset[AuthenticationMethod] = frozenset(
        {AuthenticationMethod.OIDC_FIXTURE}
    )
    recent_authentication_actions: frozenset[EnterpriseAction] = frozenset(
        {
            EnterpriseAction.APPROVE,
            EnterpriseAction.MANAGE_MEMBERSHIP,
            EnterpriseAction.DESTRUCTIVE,
        }
    )
    self_approval_denied_for: frozenset[ApprovalClass] = frozenset(
        {
            ApprovalClass.TRUSTED_HOST_PLACEMENT,
            ApprovalClass.HIGH_RISK,
        }
    )
    maximum_bulk_items: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_policy(self) -> EnterpriseAuthorizationPolicy:
        if self.recent_authentication_maximum_age <= timedelta(0):
            raise ValueError("recent-auth maximum age must be positive")
        if not self.recent_authentication_methods:
            raise ValueError("recent-auth method set must not be empty")
        if EnterpriseAction.APPROVE not in self.recent_authentication_actions:
            raise ValueError("human approval must require recent authentication")
        return self


class ServerOwnedResourceScope(_FrozenModel):
    organization_id: str = Field(pattern=r"^org_[0-9a-f]{32}$")
    workspace_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ApprovalRequestRecord(_FrozenModel):
    approval_request_id: str = Field(pattern=r"^apr_[0-9a-f]{32}$")
    organization_id: str = Field(pattern=r"^org_[0-9a-f]{32}$")
    workspace_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    requester_principal_id: str = Field(pattern=r"^prn_[0-9a-f]{32}$")
    approval_class: ApprovalClass
    request_generation: int = Field(ge=1)
    created_at: datetime

    @property
    def scope(self) -> ServerOwnedResourceScope:
        return ServerOwnedResourceScope(
            organization_id=self.organization_id,
            workspace_id=self.workspace_id,
        )


class AuthorizationDecision(_FrozenModel):
    decision_id: str
    allowed: bool
    reason_code: str
    action: EnterpriseAction
    principal_id: str
    principal_type: EnterprisePrincipalType
    authenticated_organization_id: str
    organization_id: str
    workspace_id: str
    identity_generation: int
    membership_generation: int
    session_id: str
    session_audit_id: str
    authentication_method: AuthenticationMethod
    recent_auth_at: datetime
    recent_auth_satisfied: bool
    policy_generation: int
    approval_request_id: str | None = None
    approval_request_generation: int | None = None
    effect_authority: Literal[False] = False

    def safe_audit_metadata(self) -> JsonObject:
        return {
            "decision_id": self.decision_id,
            "outcome": "allowed" if self.allowed else "denied",
            "reason_code": self.reason_code,
            "action": self.action.value,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "authenticated_organization_id": self.authenticated_organization_id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "identity_generation": self.identity_generation,
            "membership_generation": self.membership_generation,
            "session_audit_id": self.session_audit_id,
            "authentication_method": self.authentication_method.value,
            "recent_auth_satisfied": self.recent_auth_satisfied,
            "policy_generation": self.policy_generation,
            "approval_request_id": self.approval_request_id,
            "approval_request_generation": self.approval_request_generation,
            "effect_authority": self.effect_authority,
        }


class AuthorizedWorkspaceReference(_FrozenModel):
    organization_id: str
    workspace_id: str
    decision: AuthorizationDecision


class _SessionValidator(Protocol):
    def validate_session(self, handle: str) -> SessionContext: ...

    def validate_mutation(
        self,
        handle: str,
        *,
        allowed_origin: str,
        csrf_token: str,
    ) -> SessionContext: ...


class _IdentityAuthority(Protocol):
    def current_organization_authority(
        self,
        principal_id: str,
        organization_id: str,
    ) -> OrganizationAuthorityState: ...

    def current_authority_state(
        self,
        principal_id: str,
        organization_id: str,
        workspace_id: str,
    ) -> MembershipAuthorityState: ...

    def list_workspace_memberships(
        self,
        principal_id: str,
        organization_id: str,
    ) -> tuple[WorkspaceMembershipReference, ...]: ...


class _ApprovalRequestAuthority(Protocol):
    def require_pending_for_organization(
        self,
        approval_request_id: str,
        organization_id: str,
    ) -> ApprovalRequestRecord: ...


class EnterpriseApprovalRequestStore:
    """Authoritative pending-approval records resolved only by opaque ID."""

    def __init__(
        self,
        db_path: Path,
        *,
        clock: Callable[[], datetime],
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        verify_database_v2(db_path)
        self.db_path = db_path
        self._clock = clock
        self._id_factory = id_factory or _random_id

    def create_pending(
        self,
        *,
        scope: ServerOwnedResourceScope,
        requester_principal_id: str,
        approval_class: ApprovalClass,
    ) -> ApprovalRequestRecord:
        now = _require_aware_utc(self._clock())
        approval_request_id = self._id_factory("apr_")
        with closing(self._connection()) as connection, connection:
            authority = connection.execute(
                """
                SELECT p.principal_type, p.enabled, o.enabled, om.enabled,
                       w.enabled, wm.enabled
                FROM identity_principals AS p
                JOIN identity_organization_memberships AS om
                  ON om.principal_id = p.principal_id
                 AND om.organization_id = ?
                JOIN identity_organizations AS o
                  ON o.organization_id = om.organization_id
                JOIN identity_workspaces AS w
                  ON w.organization_id = om.organization_id
                 AND w.workspace_id = ?
                JOIN identity_workspace_memberships AS wm
                  ON wm.organization_id = w.organization_id
                 AND wm.workspace_id = w.workspace_id
                 AND wm.principal_id = p.principal_id
                WHERE p.principal_id = ?
                """,
                (
                    scope.organization_id,
                    scope.workspace_id,
                    requester_principal_id,
                ),
            ).fetchone()
            if authority is None or any(
                not bool(authority[index]) for index in (1, 2, 3, 4, 5)
            ):
                raise AuthorizationAuthorityUnavailableError(
                    "approval requester authority is unavailable"
                )
            if str(authority[0]) != EnterprisePrincipalType.HUMAN.value:
                raise AuthorizationAuthorityUnavailableError(
                    "approval requester must be human"
                )
            connection.execute(
                """
                INSERT INTO identity_approval_requests (
                    approval_request_id, organization_id, workspace_id,
                    requester_principal_id, approval_class,
                    request_generation, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, 'pending', ?, ?)
                """,
                (
                    approval_request_id,
                    scope.organization_id,
                    scope.workspace_id,
                    requester_principal_id,
                    approval_class.value,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return ApprovalRequestRecord(
            approval_request_id=approval_request_id,
            organization_id=scope.organization_id,
            workspace_id=scope.workspace_id,
            requester_principal_id=requester_principal_id,
            approval_class=approval_class,
            request_generation=1,
            created_at=now,
        )

    def require_pending_for_organization(
        self,
        approval_request_id: str,
        organization_id: str,
    ) -> ApprovalRequestRecord:
        if not _APPROVAL_REQUEST_ID_PATTERN.fullmatch(approval_request_id):
            raise AuthorizationAuthorityUnavailableError(
                "approval request is unavailable"
            )
        with closing(self._connection()) as connection, connection:
            row = connection.execute(
                """
                SELECT approval_request_id, organization_id, workspace_id,
                       requester_principal_id, approval_class,
                       request_generation, created_at
                FROM identity_approval_requests
                WHERE approval_request_id = ?
                  AND organization_id = ?
                  AND status = 'pending'
                """,
                (approval_request_id, organization_id),
            ).fetchone()
        if row is None:
            raise AuthorizationAuthorityUnavailableError(
                "approval request is unavailable"
            )
        try:
            return ApprovalRequestRecord(
                approval_request_id=str(row[0]),
                organization_id=str(row[1]),
                workspace_id=str(row[2]),
                requester_principal_id=str(row[3]),
                approval_class=ApprovalClass(str(row[4])),
                request_generation=int(row[5]),
                created_at=_parse_datetime(str(row[6])),
            )
        except (ValueError, TypeError) as exc:
            raise AuthorizationAuthorityUnavailableError(
                "approval request is unavailable"
            ) from exc

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class EnterpriseAuthorizationEngine:
    """Derive every decision from a validated session and current server state."""

    def __init__(
        self,
        *,
        sessions: _SessionValidator,
        identities: _IdentityAuthority,
        approval_requests: _ApprovalRequestAuthority,
        policy_provider: Callable[[], EnterpriseAuthorizationPolicy],
        clock: Callable[[], datetime],
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self._sessions = sessions
        self._identities = identities
        self._approval_requests = approval_requests
        self._policy_provider = policy_provider
        self._clock = clock
        self._id_factory = id_factory or _random_id

    @classmethod
    def from_stores(
        cls,
        *,
        sessions: EnterpriseSessionStore,
        identities: EnterpriseIdentityStore,
        approval_requests: EnterpriseApprovalRequestStore,
        policy_provider: Callable[[], EnterpriseAuthorizationPolicy],
        clock: Callable[[], datetime],
        id_factory: Callable[[str], str] | None = None,
    ) -> EnterpriseAuthorizationEngine:
        return cls(
            sessions=sessions,
            identities=identities,
            approval_requests=approval_requests,
            policy_provider=policy_provider,
            clock=clock,
            id_factory=id_factory,
        )

    def authorize(
        self,
        session_handle: str,
        *,
        scope: ServerOwnedResourceScope,
        action: EnterpriseAction,
    ) -> AuthorizationDecision:
        policy = self._current_policy()
        session = self._sessions.validate_session(session_handle)
        decision = self._authorize_core(
            session,
            scope=scope,
            action=action,
            approval_request_id=None,
            approval_request_generation=None,
            policy=policy,
        )
        if action in _MUTATING_ACTIONS:
            return decision.model_copy(
                update={
                    "allowed": False,
                    "reason_code": "mutation_origin_and_csrf_required",
                }
            )
        return decision

    def authorize_mutation(
        self,
        session_handle: str,
        *,
        allowed_origin: str,
        csrf_token: str,
        scope: ServerOwnedResourceScope,
        action: EnterpriseAction,
    ) -> AuthorizationDecision:
        if action not in _MUTATING_ACTIONS or action is EnterpriseAction.APPROVE:
            raise EnterpriseAuthorizationError(
                "mutation entry point requires a non-approval mutating action"
            )
        policy = self._current_policy()
        session = self._sessions.validate_mutation(
            session_handle,
            allowed_origin=allowed_origin,
            csrf_token=csrf_token,
        )
        return self._authorize_core(
            session,
            scope=scope,
            action=action,
            approval_request_id=None,
            approval_request_generation=None,
            policy=policy,
        )

    def authorize_approval(
        self,
        session_handle: str,
        *,
        approval_request_id: str,
        allowed_origin: str,
        csrf_token: str,
    ) -> AuthorizationDecision:
        policy = self._current_policy()
        session = self._sessions.validate_mutation(
            session_handle,
            allowed_origin=allowed_origin,
            csrf_token=csrf_token,
        )
        request = self._approval_requests.require_pending_for_organization(
            approval_request_id,
            session.organization_id,
        )
        decision = self._authorize_core(
            session,
            scope=request.scope,
            action=EnterpriseAction.APPROVE,
            approval_request_id=request.approval_request_id,
            approval_request_generation=request.request_generation,
            policy=policy,
        )
        if not decision.allowed:
            return decision
        if (
            request.approval_class in policy.self_approval_denied_for
            and request.requester_principal_id == decision.principal_id
        ):
            return decision.model_copy(
                update={
                    "allowed": False,
                    "reason_code": "self_approval_forbidden",
                }
            )
        return decision

    def authorize_bulk_read(
        self,
        session_handle: str,
        *,
        scope: ServerOwnedResourceScope,
        resource_scopes: Collection[ServerOwnedResourceScope],
    ) -> AuthorizationDecision:
        policy = self._current_policy()
        session = self._sessions.validate_session(session_handle)
        decision = self._authorize_core(
            session,
            scope=scope,
            action=EnterpriseAction.BULK_READ,
            approval_request_id=None,
            approval_request_generation=None,
            policy=policy,
        )
        if not decision.allowed:
            return decision
        if len(resource_scopes) > policy.maximum_bulk_items:
            return decision.model_copy(
                update={
                    "allowed": False,
                    "reason_code": "bulk_limit_exceeded",
                }
            )
        if any(resource_scope != scope for resource_scope in resource_scopes):
            return decision.model_copy(
                update={
                    "allowed": False,
                    "reason_code": "cross_scope_bulk_forbidden",
                }
            )
        return decision

    def list_authorized_workspaces(
        self,
        session_handle: str,
    ) -> tuple[AuthorizedWorkspaceReference, ...]:
        session = self._sessions.validate_session(session_handle)
        policy = self._current_policy()
        references = self._identities.list_workspace_memberships(
            session.principal_id,
            session.organization_id,
        )
        if any(
            reference.organization_id != session.organization_id
            or reference.membership_generation != session.membership_generation
            for reference in references
        ):
            raise AuthorizationAuthorityUnavailableError(
                "workspace listing authority changed concurrently"
            )
        authorized: list[AuthorizedWorkspaceReference] = []
        for reference in references:
            decision = self._authorize_core(
                session,
                scope=ServerOwnedResourceScope(
                    organization_id=reference.organization_id,
                    workspace_id=reference.workspace_id,
                ),
                action=EnterpriseAction.LIST,
                approval_request_id=None,
                approval_request_generation=None,
                policy=policy,
            )
            if decision.allowed:
                authorized.append(
                    AuthorizedWorkspaceReference(
                        organization_id=reference.organization_id,
                        workspace_id=reference.workspace_id,
                        decision=decision,
                    )
                )
        return tuple(authorized)

    def _authorize_core(
        self,
        session: SessionContext,
        *,
        scope: ServerOwnedResourceScope,
        action: EnterpriseAction,
        approval_request_id: str | None,
        approval_request_generation: int | None,
        policy: EnterpriseAuthorizationPolicy,
    ) -> AuthorizationDecision:
        organization = self._current_organization_authority(session)
        recent_auth_satisfied = session.has_recent_authentication(
            now=self._clock(),
            maximum_age=policy.recent_authentication_maximum_age,
            allowed_methods=policy.recent_authentication_methods,
        )
        if organization.principal_type is not EnterprisePrincipalType.HUMAN:
            return self._decision(
                session=session,
                principal_type=organization.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=recent_auth_satisfied,
                allowed=False,
                reason_code="human_principal_required",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        if scope.organization_id != session.organization_id:
            return self._decision(
                session=session,
                principal_type=organization.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=recent_auth_satisfied,
                allowed=False,
                reason_code="organization_scope_mismatch",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        try:
            authority = self._identities.current_authority_state(
                session.principal_id,
                session.organization_id,
                scope.workspace_id,
            )
        except EnterpriseIdentityError:
            return self._decision(
                session=session,
                principal_type=organization.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=recent_auth_satisfied,
                allowed=False,
                reason_code="workspace_authority_unavailable",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        if (
            authority.principal_id != session.principal_id
            or authority.organization_id != session.organization_id
            or authority.workspace_id != scope.workspace_id
            or authority.identity_generation != session.identity_generation
            or authority.membership_generation != session.membership_generation
        ):
            return self._decision(
                session=session,
                principal_type=authority.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=recent_auth_satisfied,
                allowed=False,
                reason_code="authority_generation_mismatch",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        if not _roles_allow(
            action,
            organization_roles=authority.organization_roles,
            workspace_roles=authority.workspace_roles,
        ):
            return self._decision(
                session=session,
                principal_type=authority.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=recent_auth_satisfied,
                allowed=False,
                reason_code="role_not_authorized",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        if (
            action in policy.recent_authentication_actions
            and not recent_auth_satisfied
        ):
            return self._decision(
                session=session,
                principal_type=authority.principal_type,
                scope=scope,
                action=action,
                policy=policy,
                recent_auth_satisfied=False,
                allowed=False,
                reason_code="recent_human_authentication_required",
                approval_request_id=approval_request_id,
                approval_request_generation=approval_request_generation,
            )
        return self._decision(
            session=session,
            principal_type=authority.principal_type,
            scope=scope,
            action=action,
            policy=policy,
            recent_auth_satisfied=recent_auth_satisfied,
            allowed=True,
            reason_code="authorized",
            approval_request_id=approval_request_id,
            approval_request_generation=approval_request_generation,
        )

    def _current_organization_authority(
        self,
        session: SessionContext,
    ) -> OrganizationAuthorityState:
        try:
            authority = self._identities.current_organization_authority(
                session.principal_id,
                session.organization_id,
            )
        except EnterpriseIdentityError as exc:
            raise AuthorizationAuthorityUnavailableError(
                "organization authority is unavailable"
            ) from exc
        if (
            authority.principal_id != session.principal_id
            or authority.organization_id != session.organization_id
            or authority.identity_generation != session.identity_generation
            or authority.membership_generation != session.membership_generation
        ):
            raise AuthorizationAuthorityUnavailableError(
                "organization authority generation changed concurrently"
            )
        return authority

    def _current_policy(self) -> EnterpriseAuthorizationPolicy:
        policy = self._policy_provider()
        if not isinstance(policy, EnterpriseAuthorizationPolicy):
            raise AuthorizationAuthorityUnavailableError(
                "authorization policy provider returned invalid state"
            )
        return policy

    def _decision(
        self,
        *,
        session: SessionContext,
        principal_type: EnterprisePrincipalType,
        scope: ServerOwnedResourceScope,
        action: EnterpriseAction,
        policy: EnterpriseAuthorizationPolicy,
        recent_auth_satisfied: bool,
        allowed: bool,
        reason_code: str,
        approval_request_id: str | None,
        approval_request_generation: int | None,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            decision_id=self._id_factory("adec_"),
            allowed=allowed,
            reason_code=reason_code,
            action=action,
            principal_id=session.principal_id,
            principal_type=principal_type,
            authenticated_organization_id=session.organization_id,
            organization_id=scope.organization_id,
            workspace_id=scope.workspace_id,
            identity_generation=session.identity_generation,
            membership_generation=session.membership_generation,
            session_id=session.session_id,
            session_audit_id=session.session_audit_id,
            authentication_method=session.authentication_method,
            recent_auth_at=session.recent_auth_at,
            recent_auth_satisfied=recent_auth_satisfied,
            policy_generation=policy.policy_generation,
            approval_request_id=approval_request_id,
            approval_request_generation=approval_request_generation,
        )


_MUTATING_ACTIONS = frozenset(
    {
        EnterpriseAction.CONTRIBUTE,
        EnterpriseAction.APPROVE,
        EnterpriseAction.MANAGE_MEMBERSHIP,
        EnterpriseAction.DESTRUCTIVE,
    }
)
_READ_ROLES = frozenset(
    {
        WorkspaceRole.READER,
        WorkspaceRole.CONTRIBUTOR,
        WorkspaceRole.APPROVER,
        WorkspaceRole.WORKSPACE_ADMIN,
        WorkspaceRole.AUDITOR,
    }
)
_CONTRIBUTE_ROLES = frozenset(
    {
        WorkspaceRole.CONTRIBUTOR,
        WorkspaceRole.WORKSPACE_ADMIN,
    }
)


def _roles_allow(
    action: EnterpriseAction,
    *,
    organization_roles: Collection[OrganizationRole],
    workspace_roles: Collection[WorkspaceRole],
) -> bool:
    organization = frozenset(organization_roles)
    workspace = frozenset(workspace_roles)
    if action in {
        EnterpriseAction.READ,
        EnterpriseAction.LIST,
        EnterpriseAction.BULK_READ,
    }:
        return bool(workspace & _READ_ROLES)
    if action is EnterpriseAction.CONTRIBUTE:
        return bool(workspace & _CONTRIBUTE_ROLES) or (
            OrganizationRole.ORGANIZATION_ADMIN in organization
        )
    if action is EnterpriseAction.APPROVE:
        return (
            WorkspaceRole.APPROVER in workspace
            or OrganizationRole.APPROVER in organization
        )
    if action is EnterpriseAction.MANAGE_MEMBERSHIP:
        return (
            WorkspaceRole.WORKSPACE_ADMIN in workspace
            or OrganizationRole.ORGANIZATION_ADMIN in organization
            or OrganizationRole.SECURITY_ADMIN in organization
        )
    if action is EnterpriseAction.AUDIT:
        return (
            WorkspaceRole.AUDITOR in workspace
            or OrganizationRole.AUDITOR in organization
            or OrganizationRole.SECURITY_ADMIN in organization
        )
    if action is EnterpriseAction.DESTRUCTIVE:
        return (
            WorkspaceRole.WORKSPACE_ADMIN in workspace
            or OrganizationRole.ORGANIZATION_ADMIN in organization
        )
    return False


def _parse_datetime(value: str) -> datetime:
    try:
        return _require_aware_utc(datetime.fromisoformat(value))
    except ValueError as exc:
        raise AuthorizationAuthorityUnavailableError(
            "stored authorization time is malformed"
        ) from exc


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise AuthorizationAuthorityUnavailableError(
            "trusted authorization clock is unavailable"
        )
    return value.astimezone(UTC)


def _random_id(prefix: str) -> str:
    return prefix + uuid4().hex
