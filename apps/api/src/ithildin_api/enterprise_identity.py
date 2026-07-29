"""Provider-neutral, local-only PIS-004A identity and membership domain."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable, Collection, Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import uuid4

from ithildin_schemas import JsonObject
from pydantic import BaseModel, ConfigDict

from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

_WORKSPACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
CALLER_AUTHORITY_FIELDS = frozenset(
    {
        "principal",
        "principal_id",
        "organization",
        "organization_id",
        "workspace",
        "workspace_id",
        "role",
        "roles",
        "identity_generation",
        "membership_generation",
        "policy_generation",
    }
)


class EnterpriseIdentityError(RuntimeError):
    """Base class for fail-closed identity-domain errors."""


class EnterpriseIdentityNotFoundError(EnterpriseIdentityError):
    """Raised when server-owned identity state cannot be resolved."""


class EnterpriseIdentityConflictError(EnterpriseIdentityError):
    """Raised when immutable identity state would be remapped."""


class EnterpriseIdentityDisabledError(EnterpriseIdentityError):
    """Raised when disabled identity state is presented for active authority."""


class CallerAuthorityRejectedError(EnterpriseIdentityError):
    """Raised when untrusted input attempts to supply authority fields."""


class EnterprisePrincipalType(StrEnum):
    HUMAN = "human"
    NODE = "node"
    SERVICE = "service"


class OrganizationRole(StrEnum):
    MEMBER = "member"
    ORGANIZATION_ADMIN = "organization_admin"
    SECURITY_ADMIN = "security_admin"
    APPROVER = "approver"
    AUDITOR = "auditor"
    NODE_OPERATOR = "node_operator"
    SERVICE_OPERATOR = "service_operator"


class WorkspaceRole(StrEnum):
    READER = "reader"
    CONTRIBUTOR = "contributor"
    APPROVER = "approver"
    WORKSPACE_ADMIN = "workspace_admin"
    AUDITOR = "auditor"
    NODE = "node"
    SERVICE = "service"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OrganizationRecord(_FrozenModel):
    organization_id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ProviderConfigurationRecord(_FrozenModel):
    provider_configuration_id: str
    organization_id: str
    exact_issuer: str
    enabled: bool
    generation: int
    created_at: datetime
    updated_at: datetime


class PrincipalRecord(_FrozenModel):
    principal_id: str
    principal_type: EnterprisePrincipalType
    enabled: bool
    identity_generation: int
    created_at: datetime
    updated_at: datetime


class IdentityResolution(_FrozenModel):
    identity_audit_id: str
    principal_id: str
    principal_type: EnterprisePrincipalType
    organization_id: str
    provider_configuration_id: str
    identity_generation: int

    def safe_audit_metadata(self, *, outcome: str, reason_code: str) -> JsonObject:
        return {
            "identity_audit_id": self.identity_audit_id,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "organization_id": self.organization_id,
            "provider_configuration_id": self.provider_configuration_id,
            "identity_generation": self.identity_generation,
            "outcome": outcome,
            "reason_code": reason_code,
        }


class MembershipAuthorityState(_FrozenModel):
    principal_id: str
    principal_type: EnterprisePrincipalType
    organization_id: str
    workspace_id: str
    identity_generation: int
    membership_generation: int
    organization_roles: tuple[OrganizationRole, ...]
    workspace_roles: tuple[WorkspaceRole, ...]

    def safe_audit_metadata(self, *, outcome: str, reason_code: str) -> JsonObject:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "identity_generation": self.identity_generation,
            "membership_generation": self.membership_generation,
            "outcome": outcome,
            "reason_code": reason_code,
        }


class WorkspaceMembershipReference(_FrozenModel):
    organization_id: str
    workspace_id: str
    membership_generation: int


def reject_caller_authority_fields(payload: Mapping[str, object]) -> None:
    """Reject authority-looking keys at any depth in untrusted input."""

    _reject_authority_value(payload)


def _reject_authority_value(value: object) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).strip().lower().replace("-", "_")
            if key in CALLER_AUTHORITY_FIELDS:
                raise CallerAuthorityRejectedError(
                    f"caller-supplied authority field is forbidden: {key}"
                )
            _reject_authority_value(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _reject_authority_value(child)


class EnterpriseIdentityStore:
    """SQLite-backed server authority for PIS-004A identity and memberships."""

    def __init__(
        self,
        db_path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        verify_database_v2(db_path)
        self.db_path = db_path
        self._clock = clock or _utc_now
        self._id_factory = id_factory or _random_id

    def create_organization(self) -> OrganizationRecord:
        now = _require_aware_utc(self._clock())
        organization_id = self._id_factory("org_")
        with closing(self._connection()) as connection, connection:
            connection.execute(
                """
                INSERT INTO identity_organizations (
                    organization_id, enabled, created_at, updated_at
                ) VALUES (?, 1, ?, ?)
                """,
                (organization_id, now.isoformat(), now.isoformat()),
            )
        return OrganizationRecord(
            organization_id=organization_id,
            enabled=True,
            created_at=now,
            updated_at=now,
        )

    def add_provider_configuration(
        self,
        organization_id: str,
        *,
        exact_issuer: str,
    ) -> ProviderConfigurationRecord:
        _validate_exact_issuer(exact_issuer)
        now = _require_aware_utc(self._clock())
        provider_configuration_id = self._id_factory("idpc_")
        with closing(self._connection()) as connection, connection:
            self._require_active_organization(connection, organization_id)
            connection.execute(
                """
                INSERT INTO identity_provider_configurations (
                    provider_configuration_id, organization_id, exact_issuer,
                    enabled, generation, created_at, updated_at
                ) VALUES (?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    provider_configuration_id,
                    organization_id,
                    exact_issuer,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return ProviderConfigurationRecord(
            provider_configuration_id=provider_configuration_id,
            organization_id=organization_id,
            exact_issuer=exact_issuer,
            enabled=True,
            generation=1,
            created_at=now,
            updated_at=now,
        )

    def provision_human_identity(
        self,
        organization_id: str,
        provider_configuration_id: str,
        *,
        exact_issuer: str,
        subject: str,
    ) -> IdentityResolution:
        _validate_exact_issuer(exact_issuer)
        _validate_subject(subject)
        now = _require_aware_utc(self._clock())
        principal_id = self._id_factory("prn_")
        identity_audit_id = self._id_factory("iaud_")
        with self._transaction() as connection:
            provider = self._require_active_provider(
                connection,
                organization_id,
                provider_configuration_id,
            )
            if provider["exact_issuer"] != exact_issuer:
                raise EnterpriseIdentityConflictError("configured issuer mismatch")
            existing = connection.execute(
                """
                SELECT principal_id FROM identity_bindings
                WHERE organization_id = ?
                  AND provider_configuration_id = ?
                  AND exact_issuer = ?
                  AND subject = ?
                """,
                (
                    organization_id,
                    provider_configuration_id,
                    exact_issuer,
                    subject,
                ),
            ).fetchone()
            if existing is not None:
                raise EnterpriseIdentityConflictError("immutable identity key already exists")
            connection.execute(
                """
                INSERT INTO identity_principals (
                    principal_id, principal_type, enabled, identity_generation,
                    created_at, updated_at
                ) VALUES (?, 'human', 1, 1, ?, ?)
                """,
                (principal_id, now.isoformat(), now.isoformat()),
            )
            connection.execute(
                """
                INSERT INTO identity_bindings (
                    organization_id, provider_configuration_id, exact_issuer,
                    subject, principal_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    provider_configuration_id,
                    exact_issuer,
                    subject,
                    principal_id,
                    now.isoformat(),
                ),
            )
        return IdentityResolution(
            identity_audit_id=identity_audit_id,
            principal_id=principal_id,
            principal_type=EnterprisePrincipalType.HUMAN,
            organization_id=organization_id,
            provider_configuration_id=provider_configuration_id,
            identity_generation=1,
        )

    def create_nonhuman_principal(
        self,
        principal_type: EnterprisePrincipalType,
    ) -> PrincipalRecord:
        if principal_type is EnterprisePrincipalType.HUMAN:
            raise EnterpriseIdentityError(
                "human principals require an exact external identity binding"
            )
        now = _require_aware_utc(self._clock())
        principal_id = self._id_factory("prn_")
        with closing(self._connection()) as connection, connection:
            connection.execute(
                """
                INSERT INTO identity_principals (
                    principal_id, principal_type, enabled, identity_generation,
                    created_at, updated_at
                ) VALUES (?, ?, 1, 1, ?, ?)
                """,
                (
                    principal_id,
                    principal_type.value,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return PrincipalRecord(
            principal_id=principal_id,
            principal_type=principal_type,
            enabled=True,
            identity_generation=1,
            created_at=now,
            updated_at=now,
        )

    def resolve_identity(
        self,
        organization_id: str,
        provider_configuration_id: str,
        *,
        exact_issuer: str,
        subject: str,
    ) -> IdentityResolution:
        _validate_exact_issuer(exact_issuer)
        _validate_subject(subject)
        with closing(self._connection()) as connection, connection:
            row = connection.execute(
                """
                SELECT p.principal_id, p.principal_type, p.enabled,
                       p.identity_generation, o.enabled, pc.enabled
                FROM identity_bindings AS b
                JOIN identity_principals AS p ON p.principal_id = b.principal_id
                JOIN identity_organizations AS o
                  ON o.organization_id = b.organization_id
                JOIN identity_provider_configurations AS pc
                  ON pc.provider_configuration_id = b.provider_configuration_id
                 AND pc.organization_id = b.organization_id
                 AND pc.exact_issuer = b.exact_issuer
                WHERE b.organization_id = ?
                  AND b.provider_configuration_id = ?
                  AND b.exact_issuer = ?
                  AND b.subject = ?
                """,
                (
                    organization_id,
                    provider_configuration_id,
                    exact_issuer,
                    subject,
                ),
            ).fetchone()
        if row is None:
            raise EnterpriseIdentityNotFoundError("identity mapping not found")
        if not bool(row[2]) or not bool(row[4]) or not bool(row[5]):
            raise EnterpriseIdentityDisabledError("identity mapping is disabled")
        return IdentityResolution(
            identity_audit_id=self._id_factory("iaud_"),
            principal_id=str(row[0]),
            principal_type=EnterprisePrincipalType(str(row[1])),
            organization_id=organization_id,
            provider_configuration_id=provider_configuration_id,
            identity_generation=int(row[3]),
        )

    def set_organization_membership(
        self,
        organization_id: str,
        principal_id: str,
        *,
        roles: Collection[OrganizationRole],
        enabled: bool = True,
    ) -> int:
        roles_json = _roles_json(roles)
        now = _require_aware_utc(self._clock())
        with self._transaction() as connection:
            self._require_active_organization(connection, organization_id)
            principal = self._require_principal(connection, principal_id)
            if not bool(principal["enabled"]):
                raise EnterpriseIdentityDisabledError("principal is disabled")
            if principal["principal_type"] == EnterprisePrincipalType.HUMAN.value:
                binding = connection.execute(
                    """
                    SELECT organization_id FROM identity_bindings
                    WHERE principal_id = ?
                    """,
                    (principal_id,),
                ).fetchone()
                if binding is None or str(binding[0]) != organization_id:
                    raise EnterpriseIdentityConflictError(
                        "human membership organization does not match identity binding"
                    )
            existing = connection.execute(
                """
                SELECT membership_generation, created_at
                FROM identity_organization_memberships
                WHERE organization_id = ? AND principal_id = ?
                """,
                (organization_id, principal_id),
            ).fetchone()
            if existing is None:
                generation = 1
                connection.execute(
                    """
                    INSERT INTO identity_organization_memberships (
                        organization_id, principal_id, enabled,
                        membership_generation, roles_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        organization_id,
                        principal_id,
                        int(enabled),
                        generation,
                        roles_json,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            else:
                generation = int(existing[0]) + 1
                connection.execute(
                    """
                    UPDATE identity_organization_memberships
                    SET enabled = ?, membership_generation = ?,
                        roles_json = ?, updated_at = ?
                    WHERE organization_id = ? AND principal_id = ?
                    """,
                    (
                        int(enabled),
                        generation,
                        roles_json,
                        now.isoformat(),
                        organization_id,
                        principal_id,
                    ),
                )
        return generation

    def create_workspace(self, organization_id: str, workspace_id: str) -> None:
        _validate_workspace_id(workspace_id)
        now = _require_aware_utc(self._clock())
        with closing(self._connection()) as connection, connection:
            self._require_active_organization(connection, organization_id)
            connection.execute(
                """
                INSERT INTO identity_workspaces (
                    organization_id, workspace_id, enabled, generation,
                    created_at, updated_at
                ) VALUES (?, ?, 1, 1, ?, ?)
                """,
                (organization_id, workspace_id, now.isoformat(), now.isoformat()),
            )

    def set_workspace_membership(
        self,
        organization_id: str,
        workspace_id: str,
        principal_id: str,
        *,
        roles: Collection[WorkspaceRole],
        enabled: bool = True,
    ) -> int:
        _validate_workspace_id(workspace_id)
        roles_json = _roles_json(roles)
        now = _require_aware_utc(self._clock())
        with self._transaction() as connection:
            workspace = connection.execute(
                """
                SELECT enabled FROM identity_workspaces
                WHERE organization_id = ? AND workspace_id = ?
                """,
                (organization_id, workspace_id),
            ).fetchone()
            if workspace is None:
                raise EnterpriseIdentityNotFoundError("workspace not found")
            if not bool(workspace[0]):
                raise EnterpriseIdentityDisabledError("workspace is disabled")
            membership = connection.execute(
                """
                SELECT enabled, membership_generation
                FROM identity_organization_memberships
                WHERE organization_id = ? AND principal_id = ?
                """,
                (organization_id, principal_id),
            ).fetchone()
            if membership is None:
                raise EnterpriseIdentityNotFoundError("organization membership not found")
            if not bool(membership[0]):
                raise EnterpriseIdentityDisabledError("organization membership is disabled")
            generation = int(membership[1]) + 1
            connection.execute(
                """
                UPDATE identity_organization_memberships
                SET membership_generation = ?, updated_at = ?
                WHERE organization_id = ? AND principal_id = ?
                """,
                (generation, now.isoformat(), organization_id, principal_id),
            )
            existing = connection.execute(
                """
                SELECT 1 FROM identity_workspace_memberships
                WHERE organization_id = ? AND workspace_id = ? AND principal_id = ?
                """,
                (organization_id, workspace_id, principal_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO identity_workspace_memberships (
                        organization_id, workspace_id, principal_id,
                        enabled, roles_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        organization_id,
                        workspace_id,
                        principal_id,
                        int(enabled),
                        roles_json,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE identity_workspace_memberships
                    SET enabled = ?, roles_json = ?, updated_at = ?
                    WHERE organization_id = ? AND workspace_id = ? AND principal_id = ?
                    """,
                    (
                        int(enabled),
                        roles_json,
                        now.isoformat(),
                        organization_id,
                        workspace_id,
                        principal_id,
                    ),
                )
        return generation

    def current_authority_state(
        self,
        principal_id: str,
        organization_id: str,
        workspace_id: str,
    ) -> MembershipAuthorityState:
        _validate_workspace_id(workspace_id)
        with closing(self._connection()) as connection, connection:
            row = connection.execute(
                """
                SELECT p.principal_type, p.enabled, p.identity_generation,
                       o.enabled, om.enabled, om.membership_generation,
                       om.roles_json, w.enabled, wm.enabled, wm.roles_json
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
                (organization_id, workspace_id, principal_id),
            ).fetchone()
        if row is None:
            raise EnterpriseIdentityNotFoundError("membership authority not found")
        if any(not bool(row[index]) for index in (1, 3, 4, 7, 8)):
            raise EnterpriseIdentityDisabledError("membership authority is disabled")
        return MembershipAuthorityState(
            principal_id=principal_id,
            principal_type=EnterprisePrincipalType(str(row[0])),
            organization_id=organization_id,
            workspace_id=workspace_id,
            identity_generation=int(row[2]),
            membership_generation=int(row[5]),
            organization_roles=_parse_roles(str(row[6]), OrganizationRole),
            workspace_roles=_parse_roles(str(row[9]), WorkspaceRole),
        )

    def list_workspace_memberships(
        self,
        principal_id: str,
        organization_id: str,
    ) -> tuple[WorkspaceMembershipReference, ...]:
        with closing(self._connection()) as connection, connection:
            membership = connection.execute(
                """
                SELECT p.enabled, o.enabled, om.enabled, om.membership_generation
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
            if membership is None:
                raise EnterpriseIdentityNotFoundError("organization membership not found")
            if any(not bool(membership[index]) for index in (0, 1, 2)):
                raise EnterpriseIdentityDisabledError("organization membership is disabled")
            generation = int(membership[3])
            rows = connection.execute(
                """
                SELECT wm.organization_id, wm.workspace_id
                FROM identity_workspace_memberships AS wm
                JOIN identity_workspaces AS w
                  ON w.organization_id = wm.organization_id
                 AND w.workspace_id = wm.workspace_id
                WHERE wm.principal_id = ?
                  AND wm.organization_id = ?
                  AND wm.enabled = 1
                  AND w.enabled = 1
                ORDER BY wm.workspace_id
                """,
                (principal_id, organization_id),
            ).fetchall()
        return tuple(
            WorkspaceMembershipReference(
                organization_id=str(row[0]),
                workspace_id=str(row[1]),
                membership_generation=generation,
            )
            for row in rows
        )

    def set_principal_enabled(self, principal_id: str, *, enabled: bool) -> int:
        now = _require_aware_utc(self._clock())
        with self._transaction() as connection:
            principal = self._require_principal(connection, principal_id)
            generation = int(principal["identity_generation"]) + 1
            updated = connection.execute(
                """
                UPDATE identity_principals
                SET enabled = ?, identity_generation = ?, updated_at = ?
                WHERE principal_id = ?
                  AND identity_generation = ?
                """,
                (
                    int(enabled),
                    generation,
                    now.isoformat(),
                    principal_id,
                    int(principal["identity_generation"]),
                ),
            )
            if updated.rowcount != 1:
                raise EnterpriseIdentityConflictError("identity generation changed concurrently")
        return generation

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _transaction(self) -> _ImmediateTransaction:
        return _ImmediateTransaction(self._connection())

    @staticmethod
    def _require_active_organization(
        connection: sqlite3.Connection,
        organization_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT organization_id, enabled FROM identity_organizations
            WHERE organization_id = ?
            """,
            (organization_id,),
        ).fetchone()
        if row is None:
            raise EnterpriseIdentityNotFoundError("organization not found")
        if not bool(row["enabled"]):
            raise EnterpriseIdentityDisabledError("organization is disabled")
        return cast(sqlite3.Row, row)

    @staticmethod
    def _require_active_provider(
        connection: sqlite3.Connection,
        organization_id: str,
        provider_configuration_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT provider_configuration_id, organization_id, exact_issuer,
                   enabled, generation
            FROM identity_provider_configurations
            WHERE organization_id = ? AND provider_configuration_id = ?
            """,
            (organization_id, provider_configuration_id),
        ).fetchone()
        if row is None:
            raise EnterpriseIdentityNotFoundError("provider configuration not found")
        if not bool(row["enabled"]):
            raise EnterpriseIdentityDisabledError("provider configuration is disabled")
        return cast(sqlite3.Row, row)

    @staticmethod
    def _require_principal(
        connection: sqlite3.Connection,
        principal_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT principal_id, principal_type, enabled, identity_generation
            FROM identity_principals WHERE principal_id = ?
            """,
            (principal_id,),
        ).fetchone()
        if row is None:
            raise EnterpriseIdentityNotFoundError("principal not found")
        return cast(sqlite3.Row, row)


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


def _roles_json(roles: Collection[StrEnum]) -> str:
    values = sorted({role.value for role in roles})
    if not values:
        raise EnterpriseIdentityError("at least one server-owned role is required")
    return json.dumps(values, separators=(",", ":"))


def _parse_roles[RoleT: StrEnum](
    payload: str,
    role_type: type[RoleT],
) -> tuple[RoleT, ...]:
    try:
        values = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise EnterpriseIdentityError("stored membership roles are invalid") from exc
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise EnterpriseIdentityError("stored membership roles are invalid")
    try:
        return tuple(role_type(value) for value in values)
    except ValueError as exc:
        raise EnterpriseIdentityError("stored membership role is unknown") from exc


def _validate_exact_issuer(value: str) -> None:
    if value != value.strip() or len(value) > 2048:
        raise EnterpriseIdentityError("exact issuer is malformed")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
    ):
        raise EnterpriseIdentityError("exact issuer is malformed")


def _validate_subject(value: str) -> None:
    if not 1 <= len(value) <= 512 or any(ord(character) < 0x20 for character in value):
        raise EnterpriseIdentityError("external subject is malformed")


def _validate_workspace_id(value: str) -> None:
    if not _WORKSPACE_ID_PATTERN.fullmatch(value):
        raise EnterpriseIdentityError("workspace identifier is malformed")


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise EnterpriseIdentityError("trusted clock is unavailable")
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _random_id(prefix: str) -> str:
    return prefix + uuid4().hex
