from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

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


def test_begin_execution_rejects_approval_expiring_during_atomic_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    approved = service.approve(approval.approval_id, decided_by="user:alice")
    original_compare_and_set = service.store.compare_and_set_status
    expired_during_transition = False

    def expire_before_executing_update(*args: object, **kwargs: object) -> object:
        nonlocal expired_during_transition
        if kwargs.get("next_status") == ApprovalStatus.EXECUTING and not expired_during_transition:
            expired_during_transition = True
            with sqlite3.connect(service.store.db_path) as connection:
                connection.execute(
                    "UPDATE approvals SET expires_at = ? WHERE approval_id = ?",
                    (
                        (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                        approved.approval_id,
                    ),
                )
                connection.commit()
        return original_compare_and_set(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(service.store, "compare_and_set_status", expire_before_executing_update)

    with pytest.raises(ApprovalError, match="expired"):
        service.begin_execution(approved.approval_id, approved.request_hash)

    current = service.store.get(approved.approval_id)
    assert expired_during_transition
    assert current.status == ApprovalStatus.EXPIRED


def test_denied_approval_cannot_execute(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    denied = service.deny(approval.approval_id, decided_by="user:alice", reason="no")

    assert denied.status == ApprovalStatus.DENIED
    with pytest.raises(ApprovalError):
        service.begin_execution(denied.approval_id, denied.request_hash)


def test_terminal_decision_is_atomic_and_preserves_first_decision_metadata(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())

    denied = service.deny(
        approval.approval_id,
        decided_by="user:alice",
        reason="scope is not authorized",
    )

    with pytest.raises(ApprovalError, match="not pending"):
        service.approve(approval.approval_id, decided_by="user:bob")

    with sqlite3.connect(service.store.db_path) as connection:
        stored = connection.execute(
            "SELECT status, decided_by, decision_reason FROM approvals WHERE approval_id = ?",
            (approval.approval_id,),
        ).fetchone()
    events = [
        json.loads(line)["event_type"]
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert denied.status == ApprovalStatus.DENIED
    assert stored == ("denied", "user:alice", "scope is not authorized")
    assert events.count("approval.denied") == 1
    assert "approval.approved" not in events


def test_conflicting_terminal_decisions_have_one_atomic_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    original_compare_and_set = service.store.compare_and_set_status
    both_ready = Barrier(2)

    def coordinated_transition(*args: object, **kwargs: object) -> object:
        if kwargs.get("next_status") in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED}:
            both_ready.wait(timeout=5)
        return original_compare_and_set(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(service.store, "compare_and_set_status", coordinated_transition)

    def decide(action: str) -> str:
        try:
            if action == "approve":
                approved = service.approve(approval.approval_id, decided_by="user:approver")
                return approved.status.value
            return service.deny(approval.approval_id, decided_by="user:denier").status.value
        except ApprovalError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(decide, ["approve", "deny"]))

    current = service.store.get(approval.approval_id)
    events = [
        json.loads(line)["event_type"]
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    terminal_events = [
        event for event in events if event in {"approval.approved", "approval.denied"}
    ]

    assert current.status in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED}
    assert sum(outcome in {"approved", "denied"} for outcome in outcomes) == 1
    assert sum("approval is not pending" in outcome for outcome in outcomes) == 1
    assert len(terminal_events) == 1


def test_terminal_decision_rejects_expiry_during_atomic_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = make_service(tmp_path)
    approval = service.create_pending(create_input())
    original_compare_and_set = service.store.compare_and_set_status

    def expire_before_decision(*args: object, **kwargs: object) -> object:
        with sqlite3.connect(service.store.db_path) as connection:
            connection.execute(
                "UPDATE approvals SET expires_at = ? WHERE approval_id = ?",
                (
                    (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                    approval.approval_id,
                ),
            )
            connection.commit()
        return original_compare_and_set(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(service.store, "compare_and_set_status", expire_before_decision)

    with pytest.raises(ApprovalError, match="expired"):
        service.approve(approval.approval_id, decided_by="user:alice")

    assert service.store.get(approval.approval_id).status == ApprovalStatus.EXPIRED


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
