"""Approval workflow storage and service."""

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


class ApprovalStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    principal_json TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    resource_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    one_time_scope_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    decided_by TEXT,
                    decision_reason TEXT
                )
                """
            )
            connection.commit()

    def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id,
                    request_id,
                    request_hash,
                    principal_json,
                    tool_name,
                    resource_json,
                    status,
                    summary,
                    expires_at,
                    one_time_scope_json,
                    metadata_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.approval_id,
                    approval.request_id,
                    approval.request_hash,
                    canonical_json(approval.principal),
                    approval.tool_name,
                    canonical_json(approval.resource),
                    approval.status.value,
                    approval.summary,
                    approval.expires_at.isoformat(),
                    canonical_json(approval.one_time_scope),
                    canonical_json(approval.metadata),
                    now,
                    now,
                ),
            )
            connection.commit()
        return approval

    def get(self, approval_id: str) -> ApprovalRequest:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    approval_id,
                    request_id,
                    request_hash,
                    principal_json,
                    tool_name,
                    resource_json,
                    status,
                    summary,
                    expires_at,
                    one_time_scope_json,
                    metadata_json
                FROM approvals
                WHERE approval_id = ?
                """,
                (approval_id,),
            ).fetchone()

        if row is None:
            raise ApprovalError(f"approval not found: {approval_id}")

        return _approval_from_row(row)

    def list(self, status: Optional[ApprovalStatus] = None) -> list[ApprovalRequest]:
        query = """
            SELECT
                approval_id,
                request_id,
                request_hash,
                principal_json,
                tool_name,
                resource_json,
                status,
                summary,
                expires_at,
                one_time_scope_json,
                metadata_json
            FROM approvals
        """
        parameters: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status.value,)
        query += " ORDER BY updated_at DESC"

        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [_approval_from_row(row) for row in rows]

    def set_status(
        self,
        approval_id: str,
        status: ApprovalStatus,
        *,
        decided_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE approvals
                SET status = ?,
                    updated_at = ?,
                    decided_by = COALESCE(?, decided_by),
                    decision_reason = COALESCE(?, decision_reason)
                WHERE approval_id = ?
                """,
                (status.value, datetime.now(UTC).isoformat(), decided_by, reason, approval_id),
            ).rowcount
            connection.commit()

        if updated != 1:
            raise ApprovalError(f"approval not found: {approval_id}")
        return self.get(approval_id)

    def compare_and_set_status(
        self,
        approval_id: str,
        *,
        expected_status: ApprovalStatus,
        next_status: ApprovalStatus,
        expires_after: Optional[datetime] = None,
        decided_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> ApprovalRequest:
        transition_time = datetime.now(UTC)
        query = """
            UPDATE approvals
            SET status = ?,
                updated_at = ?,
                decided_by = COALESCE(?, decided_by),
                decision_reason = COALESCE(?, decision_reason)
            WHERE approval_id = ?
              AND status = ?
        """
        parameters: list[str | None] = [
            next_status.value,
            transition_time.isoformat(),
            decided_by,
            reason,
            approval_id,
            expected_status.value,
        ]
        if expires_after is not None:
            query += " AND expires_at > ?"
            parameters.append(transition_time.isoformat())
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(query, parameters).rowcount
            connection.commit()

        if updated != 1:
            current = self.get(approval_id)
            raise ApprovalError(f"approval is not {expected_status.value}: {current.status.value}")
        return self.get(approval_id)


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
        )
        self.store.create(approval)
        self._audit(AuditEventType.APPROVAL_CREATED, approval)
        return approval

    def get(self, approval_id: str) -> ApprovalRequest:
        approval = self.store.get(approval_id)
        if approval.status == ApprovalStatus.PENDING and _is_expired(approval):
            approval = self.store.set_status(approval_id, ApprovalStatus.EXPIRED)
        return approval

    def list(self, status: Optional[ApprovalStatus] = None) -> list[ApprovalRequest]:
        approvals = self.store.list(status=status)
        return [self.get(approval.approval_id) for approval in approvals]

    def approve(
        self, approval_id: str, decided_by: str, reason: Optional[str] = None
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        try:
            approval = self.store.compare_and_set_status(
                approval_id,
                expected_status=ApprovalStatus.PENDING,
                next_status=ApprovalStatus.APPROVED,
                expires_after=datetime.now(UTC),
                decided_by=decided_by,
                reason=reason,
            )
        except ApprovalError:
            current = self.get(approval_id)
            raise ApprovalError(f"approval is not pending: {current.status.value}") from None
        self._audit(AuditEventType.APPROVAL_APPROVED, approval)
        return approval

    def deny(
        self, approval_id: str, decided_by: str, reason: Optional[str] = None
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        try:
            approval = self.store.compare_and_set_status(
                approval_id,
                expected_status=ApprovalStatus.PENDING,
                next_status=ApprovalStatus.DENIED,
                expires_after=datetime.now(UTC),
                decided_by=decided_by,
                reason=reason,
            )
        except ApprovalError:
            current = self.get(approval_id)
            raise ApprovalError(f"approval is not pending: {current.status.value}") from None
        self._audit(AuditEventType.APPROVAL_DENIED, approval)
        return approval

    def begin_execution(self, approval_id: str, request_hash: str) -> ApprovalRequest:
        approval = self.get(approval_id)
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
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=event_type,
            request_id=approval.request_id,
            principal=approval.principal,
            tool_name=approval.tool_name,
            resource=approval.resource,
            input_hash=approval.request_hash,
            metadata=cast(
                JsonObject,
                {
                    "approval_id": approval.approval_id,
                    "status": approval.status.value,
                    "summary": approval.summary,
                    "one_time_scope_hash": sha256_digest(approval.one_time_scope),
                    "one_time_scope_keys": sorted(approval.one_time_scope.keys()),
                    **run_metadata,
                },
            ),
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _approval_from_row(row: tuple[object, ...]) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=str(row[0]),
        request_id=str(row[1]),
        request_hash=str(row[2]),
        principal=json.loads(str(row[3])),
        tool_name=str(row[4]),
        resource=json.loads(str(row[5])),
        status=ApprovalStatus(str(row[6])),
        summary=str(row[7]),
        expires_at=datetime.fromisoformat(str(row[8])),
        one_time_scope=json.loads(str(row[9])),
        metadata=json.loads(str(row[10])),
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


def _is_expired(approval: ApprovalRequest, *, now: Optional[datetime] = None) -> bool:
    return approval.expires_at <= (now or datetime.now(UTC))
