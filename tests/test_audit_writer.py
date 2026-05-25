from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import AuditEventType, PolicyDecisionValue

VALID_HASH = "sha256:" + ("a" * 64)
NOW = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)


def make_writer(tmp_path: Path, redact_fields: set[str] | None = None) -> AuditWriter:
    writer = AuditWriter(
        db_path=tmp_path / "audit.sqlite3",
        jsonl_path=tmp_path / "audit.jsonl",
        redact_fields=redact_fields,
    )
    writer.initialize()
    return writer


def test_audit_writer_persists_sqlite_and_jsonl(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    event = writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
        resource={"path": "/workspace/README.md"},
        decision=PolicyDecisionValue.ALLOW,
        policy_version=VALID_HASH,
        input_hash=VALID_HASH,
    )

    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        row = connection.execute(
            "SELECT event_id, event_hash FROM audit_events WHERE event_id = 'evt_1'"
        ).fetchone()

    jsonl_payload = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8"))
    assert row == ("evt_1", event.event_hash)
    assert jsonl_payload["event_id"] == "evt_1"
    assert jsonl_payload["event_hash"] == event.event_hash


def test_audit_writer_hash_chain_links_events(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    first = writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_CALL_PROPOSED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    second = writer.write_event(
        event_id="evt_2",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_2",
        principal={"id": "agent:local-dev"},
    )

    assert first.prev_event_hash == "sha256:" + ("0" * 64)
    assert second.prev_event_hash == first.event_hash


def test_audit_writer_redacts_configured_fields(tmp_path: Path) -> None:
    writer = make_writer(tmp_path, redact_fields={"token"})

    event = writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_CALL_PROPOSED,
        request_id="req_1",
        principal={"id": "agent:local-dev", "token": "secret"},
        metadata={"nested": {"token": "secret"}, "safe": "value"},
    )

    assert event.principal["token"] == "[REDACTED]"
    assert event.metadata == {"nested": {"token": "[REDACTED]"}, "safe": "value"}
    assert event.redactions == ["token"]


def test_audit_writer_rejects_invalid_event_data(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    with pytest.raises(AuditWriteError):
        writer.write_event(
            event_id="evt_1",
            timestamp=datetime(2026, 5, 25, 12, 0),
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
        )


def test_audit_writer_blocks_when_jsonl_cannot_be_written(tmp_path: Path) -> None:
    blocked_path = tmp_path / "blocked"
    blocked_path.write_text("not a directory", encoding="utf-8")
    writer = AuditWriter(
        db_path=tmp_path / "audit.sqlite3",
        jsonl_path=blocked_path / "audit.jsonl",
    )
    writer.initialize()

    with pytest.raises(AuditWriteError):
        writer.write_event(
            event_id="evt_1",
            timestamp=NOW,
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
        )

    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

    assert row_count == 0
