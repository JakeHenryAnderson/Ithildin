"""Version-2 approval workflow storage and service."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional, cast
from uuid import uuid4

from ithildin_audit_core import AuditWriter
from ithildin_schemas import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEventType,
    JsonObject,
    canonical_json,
    sha256_digest,
)

from ithildin_api.promotion_authority import AdminPrincipalContext
from ithildin_api.trusted_host_promotion_v2_migration import (
    APPROVAL_CONTRACT_VERSION,
    TRUSTED_HOST_PROMOTION_TOOL,
    initialize_or_migrate_database,
)

MAX_DECISION_REASON_LENGTH = 500


class ApprovalError(RuntimeError):
    """Raised when an approval operation cannot be completed safely."""


@dataclass(frozen=True)
class CreateApprovalInput:
    principal: JsonObject
    tool_name: str
    resource: JsonObject
    summary: str
    one_time_scope: JsonObject
    request_id: Optional[str] = None
    request_hash: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[JsonObject] = None
    requester_context: AdminPrincipalContext | None = None
    promotion_authority_hash: str | None = None
    promotion_request_hash: str | None = None


_APPROVAL_COLUMNS = """
    approval_id, request_id, request_hash, principal_json, tool_name,
    resource_json, status, summary, expires_at, one_time_scope_json,
    metadata_json, approval_contract_version, requester_principal_id,
    requester_principal_generation, decided_at, deciding_principal_id,
    deciding_principal_generation, decision_reason_hash,
    decision_authority_snapshot_hash, decision_hash,
    executor_principal_id, executor_principal_generation
"""


class ApprovalStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        initialize_or_migrate_database(self.db_path)

    def create(
        self,
        approval: ApprovalRequest,
        *,
        promotion_authority_hash: str | None = None,
        promotion_request_hash: str | None = None,
    ) -> ApprovalRequest:
        if approval.approval_contract_version != APPROVAL_CONTRACT_VERSION:
            raise ApprovalError("new approvals must use the version-2 contract")
        now = datetime.now(UTC).isoformat()
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO approvals (
                        approval_id, request_id, request_hash, principal_json,
                        tool_name, resource_json, status, summary, expires_at,
                        one_time_scope_json, metadata_json, created_at, updated_at,
                        approval_contract_version, requester_principal_id,
                        requester_principal_generation, promotion_authority_hash,
                        promotion_request_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval.approval_id,
                        approval.request_id,
                        approval.request_hash,
                        canonical_json(approval.principal),
                        approval.tool_name,
                        canonical_json(approval.resource),
                        _v2_storage_status(approval.status),
                        approval.summary,
                        approval.expires_at.isoformat(),
                        canonical_json(approval.one_time_scope),
                        canonical_json(approval.metadata),
                        now,
                        now,
                        approval.approval_contract_version,
                        approval.requester_principal_id,
                        approval.requester_principal_generation,
                        promotion_authority_hash,
                        promotion_request_hash,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ApprovalError("approval version-2 authority binding is invalid") from exc
        return self.get(approval.approval_id)

    def get(self, approval_id: str) -> ApprovalRequest:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                f"SELECT {_APPROVAL_COLUMNS} FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise ApprovalError(f"approval not found: {approval_id}")
        return _approval_from_row(row)

    def list(self, status: Optional[ApprovalStatus] = None) -> list[ApprovalRequest]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                f"SELECT {_APPROVAL_COLUMNS} FROM approvals ORDER BY updated_at DESC"
            ).fetchall()
        approvals = [_approval_from_row(row) for row in rows]
        if status is not None:
            approvals = [approval for approval in approvals if approval.status is status]
        return approvals

    def compare_and_set_status(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        next_status: ApprovalStatus,
        expires_after: Optional[datetime] = None,
    ) -> ApprovalRequest:
        transition_time = datetime.now(UTC)
        query = """
            UPDATE approvals
            SET status = ?, updated_at = ?
            WHERE approval_id = ?
              AND approval_contract_version = '2'
              AND status = ?
        """
        parameters: list[str] = [
            _v2_storage_status(next_status),
            transition_time.isoformat(),
            approval_id,
            _v2_storage_status(expected_status),
        ]
        if expires_after is not None:
            query += " AND expires_at > ?"
            parameters.append(transition_time.isoformat())
        try:
            with sqlite3.connect(self.db_path) as connection:
                updated = connection.execute(query, parameters).rowcount
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ApprovalError("approval version-2 transition was rejected") from exc
        if updated != 1:
            current = self.get(approval_id)
            raise ApprovalError(f"approval is not {expected_status.value}: {current.status.value}")
        return self.get(approval_id)

    def decide(
        self,
        approval_id: str,
        *,
        next_status: ApprovalStatus,
        context: AdminPrincipalContext,
        reason: str | None,
    ) -> ApprovalRequest:
        if next_status not in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED}:
            raise ApprovalError("invalid approval decision transition")
        current = self.get(approval_id)
        if current.approval_contract_version != APPROVAL_CONTRACT_VERSION:
            raise ApprovalError("legacy approval is immutable")
        bounded_reason = _bounded_reason(reason)
        decided_at = datetime.now(UTC)
        authority_hash = self.promotion_authority_hash(approval_id)
        reason_hash = sha256_digest({"reason": bounded_reason or ""})
        decision_hash = sha256_digest(
            {
                "approval_id": approval_id,
                "approval_request_hash": current.request_hash,
                "decision_status": next_status.value,
                "decided_at": decided_at.isoformat(),
                "deciding_principal_id": context.principal_id,
                "deciding_principal_generation": context.identity_generation,
                "decision_reason_hash": reason_hash,
                "decision_authority_snapshot_hash": authority_hash,
            }
        )
        try:
            with sqlite3.connect(self.db_path) as connection:
                updated = connection.execute(
                    """
                    UPDATE approvals
                    SET status = ?, updated_at = ?, decided_at = ?,
                        deciding_principal_id = ?,
                        deciding_principal_generation = ?, decision_reason = ?,
                        decision_reason_hash = ?,
                        decision_authority_snapshot_hash = ?, decision_hash = ?
                    WHERE approval_id = ?
                      AND approval_contract_version = '2'
                      AND status = 'v2_pending'
                      AND expires_at > ?
                    """,
                    (
                        _v2_storage_status(next_status),
                        decided_at.isoformat(),
                        decided_at.isoformat(),
                        context.principal_id,
                        context.identity_generation,
                        bounded_reason,
                        reason_hash,
                        authority_hash,
                        decision_hash,
                        approval_id,
                        decided_at.isoformat(),
                    ),
                ).rowcount
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ApprovalError("approval version-2 decision was rejected") from exc
        if updated != 1:
            current = self.get(approval_id)
            if current.status is ApprovalStatus.PENDING and _is_expired(current):
                try:
                    self.compare_and_set_status(
                        approval_id,
                        expected_status=ApprovalStatus.PENDING,
                        next_status=ApprovalStatus.EXPIRED,
                    )
                except ApprovalError:
                    pass
                raise ApprovalError("approval is expired")
            raise ApprovalError(f"approval is not pending: {current.status.value}")
        return self.get(approval_id)

    def promotion_authority_hash(self, approval_id: str) -> str | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT tool_name, promotion_authority_hash FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise ApprovalError(f"approval not found: {approval_id}")
        if str(row[0]) != TRUSTED_HOST_PROMOTION_TOOL:
            return None
        value = row[1]
        if value is None:
            raise ApprovalError("trusted-host approval authority binding is unavailable")
        return str(value)


class ApprovalService:
    def __init__(
        self,
        store: ApprovalStore,
        audit_writer: AuditWriter,
        default_expiry: timedelta,
    ) -> None:
        self.store = store
        self.audit_writer = audit_writer
        self.default_expiry = default_expiry

    def create_pending(self, payload: CreateApprovalInput) -> ApprovalRequest:
        request_id = payload.request_id or _new_id("req")
        expires_at = payload.expires_at or datetime.now(UTC) + self.default_expiry
        request_hash = payload.request_hash or _request_hash(
            request_id=request_id,
            principal=payload.principal,
            tool_name=payload.tool_name,
            resource=payload.resource,
            one_time_scope=payload.one_time_scope,
        )
        requester_id, requester_generation = _requester_authority(payload)
        approval = ApprovalRequest(
            approval_id=_new_id("appr"),
            request_id=request_id,
            request_hash=request_hash,
            principal=payload.principal,
            tool_name=payload.tool_name,
            resource=payload.resource,
            status=ApprovalStatus.PENDING,
            summary=payload.summary,
            expires_at=expires_at,
            one_time_scope=payload.one_time_scope,
            metadata=payload.metadata or {},
            approval_contract_version=APPROVAL_CONTRACT_VERSION,
            requester_principal_id=requester_id,
            requester_principal_generation=requester_generation,
        )
        approval = self.store.create(
            approval,
            promotion_authority_hash=payload.promotion_authority_hash,
            promotion_request_hash=payload.promotion_request_hash,
        )
        self._audit(AuditEventType.APPROVAL_CREATED, approval)
        return approval

    def get(self, approval_id: str) -> ApprovalRequest:
        approval = self.store.get(approval_id)
        if approval.status == ApprovalStatus.PENDING and _is_expired(approval):
            try:
                approval = self.store.compare_and_set_status(
                    approval_id,
                    expected_status=ApprovalStatus.PENDING,
                    next_status=ApprovalStatus.EXPIRED,
                )
            except ApprovalError:
                approval = self.store.get(approval_id)
        return approval

    def list(self, status: Optional[ApprovalStatus] = None) -> list[ApprovalRequest]:
        approvals = self.store.list(status=status)
        return [self.get(approval.approval_id) for approval in approvals]

    def approve(
        self,
        approval_id: str,
        context: AdminPrincipalContext,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        approval = self.store.decide(
            approval_id,
            next_status=ApprovalStatus.APPROVED,
            context=context,
            reason=reason,
        )
        self._audit(AuditEventType.APPROVAL_APPROVED, approval)
        return approval

    def deny(
        self,
        approval_id: str,
        context: AdminPrincipalContext,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        approval = self.store.decide(
            approval_id,
            next_status=ApprovalStatus.DENIED,
            context=context,
            reason=reason,
        )
        self._audit(AuditEventType.APPROVAL_DENIED, approval)
        return approval

    def begin_execution(self, approval_id: str, request_hash: str) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.approval_contract_version != APPROVAL_CONTRACT_VERSION:
            raise ApprovalError("legacy approval is immutable")
        if approval.status != ApprovalStatus.APPROVED:
            raise ApprovalError(f"approval is not approved: {approval.status.value}")
        now = datetime.now(UTC)
        if _is_expired(approval, now=now):
            self.store.compare_and_set_status(
                approval_id,
                expected_status=ApprovalStatus.APPROVED,
                next_status=ApprovalStatus.EXPIRED,
            )
            raise ApprovalError("approval is expired")
        if approval.request_hash != request_hash:
            raise ApprovalError("approval request hash mismatch")
        try:
            return self.store.compare_and_set_status(
                approval_id,
                expected_status=ApprovalStatus.APPROVED,
                next_status=ApprovalStatus.EXECUTING,
                expires_after=now,
            )
        except ApprovalError:
            current = self.store.get(approval_id)
            if current.status == ApprovalStatus.APPROVED and _is_expired(current):
                self.store.compare_and_set_status(
                    approval_id,
                    expected_status=ApprovalStatus.APPROVED,
                    next_status=ApprovalStatus.EXPIRED,
                )
                raise ApprovalError("approval is expired") from None
            raise

    def complete_execution(self, approval_id: str, success: bool) -> ApprovalRequest:
        return self.store.compare_and_set_status(
            approval_id,
            expected_status=ApprovalStatus.EXECUTING,
            next_status=ApprovalStatus.EXECUTED if success else ApprovalStatus.FAILED,
        )

    def _audit(self, event_type: AuditEventType, approval: ApprovalRequest) -> None:
        run_metadata = {
            key: value
            for key, value in approval.metadata.items()
            if key in {"run_id", "session_id", "workspace_id", "principal_id"}
            and isinstance(value, str)
        }
        principal = approval.principal
        if approval.deciding_principal_id is not None:
            principal = cast(
                JsonObject,
                {
                    "id": approval.deciding_principal_id,
                    "identity_generation": approval.deciding_principal_generation,
                },
            )
        decision_metadata = {
            key: value
            for key, value in {
                "deciding_principal_id": approval.deciding_principal_id,
                "deciding_principal_generation": approval.deciding_principal_generation,
                "decided_at": (
                    approval.decided_at.isoformat() if approval.decided_at is not None else None
                ),
                "decision_reason_hash": approval.decision_reason_hash,
                "decision_authority_snapshot_hash": (
                    approval.decision_authority_snapshot_hash
                ),
                "decision_hash": approval.decision_hash,
            }.items()
            if value is not None
        }
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=event_type,
            request_id=approval.request_id,
            principal=principal,
            tool_name=approval.tool_name,
            resource=approval.resource,
            input_hash=approval.request_hash,
            metadata=cast(
                JsonObject,
                {
                    "approval_id": approval.approval_id,
                    "status": approval.status.value,
                    "approval_contract_version": approval.approval_contract_version,
                    "summary": approval.summary,
                    "one_time_scope_hash": sha256_digest(approval.one_time_scope),
                    "one_time_scope_keys": sorted(approval.one_time_scope.keys()),
                    **decision_metadata,
                    **run_metadata,
                },
            ),
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _approval_from_row(row: tuple[object, ...]) -> ApprovalRequest:
    contract_version = str(row[11])
    return ApprovalRequest(
        approval_id=str(row[0]),
        request_id=str(row[1]),
        request_hash=str(row[2]),
        principal=json.loads(str(row[3])),
        tool_name=str(row[4]),
        resource=json.loads(str(row[5])),
        status=_display_status(str(row[6])),
        summary=str(row[7]),
        expires_at=datetime.fromisoformat(str(row[8])),
        one_time_scope=json.loads(str(row[9])),
        metadata=json.loads(str(row[10])),
        approval_contract_version=contract_version,
        requester_principal_id=_optional_string(row[12]),
        requester_principal_generation=_optional_string(row[13]),
        decided_at=(datetime.fromisoformat(str(row[14])) if row[14] is not None else None),
        deciding_principal_id=_optional_string(row[15]),
        deciding_principal_generation=_optional_string(row[16]),
        decision_reason_hash=_optional_string(row[17]),
        decision_authority_snapshot_hash=_optional_string(row[18]),
        decision_hash=_optional_string(row[19]),
        executor_principal_id=_optional_string(row[20]),
        executor_principal_generation=_optional_string(row[21]),
    )


def _request_hash(
    *,
    request_id: str,
    principal: JsonObject,
    tool_name: str,
    resource: JsonObject,
    one_time_scope: JsonObject,
) -> str:
    return sha256_digest(
        {
            "request_id": request_id,
            "principal": principal,
            "tool_name": tool_name,
            "resource": resource,
            "one_time_scope": one_time_scope,
        }
    )


def _requester_authority(payload: CreateApprovalInput) -> tuple[str, str]:
    if payload.requester_context is not None:
        return (
            payload.requester_context.principal_id,
            payload.requester_context.identity_generation,
        )
    principal_id = payload.principal.get("id")
    if not isinstance(principal_id, str) or not principal_id:
        raise ApprovalError("approval requester principal id is unavailable")
    return principal_id, sha256_digest({"principal": payload.principal})


def _v2_storage_status(status: ApprovalStatus) -> str:
    if status is ApprovalStatus.LEGACY_UNBOUND:
        raise ApprovalError("legacy approval status is immutable")
    return f"v2_{status.value}"


def _display_status(storage_status: str) -> ApprovalStatus:
    if storage_status == "legacy_unbound":
        return ApprovalStatus.LEGACY_UNBOUND
    if storage_status.startswith("v2_"):
        return ApprovalStatus(storage_status.removeprefix("v2_"))
    if storage_status.startswith("legacy_"):
        return ApprovalStatus(storage_status.removeprefix("legacy_"))
    raise ApprovalError("approval storage status is unsupported")


def _bounded_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    if len(reason) > MAX_DECISION_REASON_LENGTH:
        raise ApprovalError("approval decision reason is too long")
    return reason


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _is_expired(approval: ApprovalRequest, *, now: Optional[datetime] = None) -> bool:
    return approval.expires_at <= (now or datetime.now(UTC))
