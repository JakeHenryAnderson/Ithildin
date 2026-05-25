"""Approval workflow storage and service."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional
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

    def approve(
        self, approval_id: str, decided_by: str, reason: Optional[str] = None
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        approval = self.store.set_status(
            approval_id,
            ApprovalStatus.APPROVED,
            decided_by=decided_by,
            reason=reason,
        )
        self._audit(AuditEventType.APPROVAL_APPROVED, approval)
        return approval

    def deny(
        self, approval_id: str, decided_by: str, reason: Optional[str] = None
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"approval is not pending: {approval.status.value}")
        approval = self.store.set_status(
            approval_id,
            ApprovalStatus.DENIED,
            decided_by=decided_by,
            reason=reason,
        )
        self._audit(AuditEventType.APPROVAL_DENIED, approval)
        return approval

    def begin_execution(self, approval_id: str, request_hash: str) -> ApprovalRequest:
        approval = self.get(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise ApprovalError(f"approval is not approved: {approval.status.value}")
        if approval.request_hash != request_hash:
            raise ApprovalError("approval request hash mismatch")
        return self.store.set_status(approval_id, ApprovalStatus.EXECUTING)

    def complete_execution(self, approval_id: str, success: bool) -> ApprovalRequest:
        approval = self.store.get(approval_id)
        if approval.status != ApprovalStatus.EXECUTING:
            raise ApprovalError(f"approval is not executing: {approval.status.value}")
        return self.store.set_status(
            approval_id,
            ApprovalStatus.EXECUTED if success else ApprovalStatus.FAILED,
        )

    def _audit(self, event_type: AuditEventType, approval: ApprovalRequest) -> None:
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=event_type,
            request_id=approval.request_id,
            principal=approval.principal,
            tool_name=approval.tool_name,
            resource=approval.resource,
            input_hash=approval.request_hash,
            metadata={
                "approval_id": approval.approval_id,
                "status": approval.status.value,
                "summary": approval.summary,
            },
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


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


def _is_expired(approval: ApprovalRequest) -> bool:
    return approval.expires_at <= datetime.now(UTC)
