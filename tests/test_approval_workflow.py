from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_audit_core import AuditWriter
from ithildin_schemas import ApprovalStatus


def make_service(tmp_path: Path, expiry: timedelta = timedelta(minutes=15)) -> ApprovalService:
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    store = ApprovalStore(db_path)
    store.initialize()
    return ApprovalService(store, audit_writer, expiry)


def create_input(expires_at: datetime | None = None) -> CreateApprovalInput:
    return CreateApprovalInput(
        principal={"id": "agent:local-dev"},
        tool_name="fs.apply_patch",
        resource={"path": "/workspace/app.py"},
        summary="Modify app.py",
        one_time_scope={"tool_name": "fs.apply_patch", "arguments": {"path": "app.py"}},
        expires_at=expires_at,
    )


def test_create_pending_approval_writes_audit_event(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    approval = service.create_pending(create_input())

    assert approval.approval_id.startswith("appr_")
    assert approval.request_id.startswith("req_")
    assert approval.request_hash.startswith("sha256:")
    assert approval.status == ApprovalStatus.PENDING
    audit_lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in audit_lines]
    assert payloads[0]["event_type"] == "approval.created"
    assert payloads[0]["metadata"]["approval_id"] == approval.approval_id


def test_approve_once_and_prevent_replay(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())

    approved = service.approve(approval.approval_id, decided_by="user:alice")
    executing = service.begin_execution(approved.approval_id, approved.request_hash)
    executed = service.complete_execution(executing.approval_id, success=True)

    assert approved.status == ApprovalStatus.APPROVED
    assert executing.status == ApprovalStatus.EXECUTING
    assert executed.status == ApprovalStatus.EXECUTED
    with pytest.raises(ApprovalError):
        service.begin_execution(approved.approval_id, approved.request_hash)


def test_request_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    approved = service.approve(approval.approval_id, decided_by="user:alice")

    with pytest.raises(ApprovalError, match="hash mismatch"):
        service.begin_execution(approved.approval_id, "sha256:" + ("f" * 64))


def test_begin_execution_uses_expiry_guard_in_atomic_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    approved = service.approve(approval.approval_id, decided_by="user:alice")
    original_compare_and_set = service.store.compare_and_set_status
    observed_expiry_guards: list[datetime | None] = []

    def record_expiry_guard(*args: object, **kwargs: object) -> object:
        if kwargs.get("next_status") == ApprovalStatus.EXECUTING:
            guard = kwargs.get("expires_after")
            assert guard is None or isinstance(guard, datetime)
            observed_expiry_guards.append(guard)
        return original_compare_and_set(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(service.store, "compare_and_set_status", record_expiry_guard)

    service.begin_execution(approved.approval_id, approved.request_hash)

    assert observed_expiry_guards
    assert observed_expiry_guards[0] is not None


def test_denied_approval_cannot_execute(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    denied = service.deny(approval.approval_id, decided_by="user:alice", reason="no")

    assert denied.status == ApprovalStatus.DENIED
    with pytest.raises(ApprovalError):
        service.begin_execution(denied.approval_id, denied.request_hash)


def test_expired_approval_cannot_be_approved_or_executed(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(
        create_input(expires_at=datetime(2026, 5, 25, 12, 0, tzinfo=UTC))
    )

    expired = service.get(approval.approval_id)

    assert expired.status == ApprovalStatus.EXPIRED
    with pytest.raises(ApprovalError):
        service.approve(expired.approval_id, decided_by="user:alice")
    with pytest.raises(ApprovalError):
        service.begin_execution(expired.approval_id, expired.request_hash)


def test_approval_store_persists_records(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())

    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        row = connection.execute(
            "SELECT approval_id, status FROM approvals WHERE approval_id = ?",
            (approval.approval_id,),
        ).fetchone()

    assert row == (approval.approval_id, "pending")
