from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_audit_core import AuditWriter
from ithildin_schemas import AuditEventType


def test_audit_diagnostics_reports_empty_and_valid_chains(tmp_path: Path) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()

    empty = cast(dict[str, Any], writer.diagnostics())
    assert empty["category"] == "empty_valid"
    assert empty["verification"]["valid"] is True
    assert empty["verification"]["event_count"] == 0
    assert empty["lifecycle"]["status"] == "clean"
    assert empty["lifecycle"]["retention_mode"] == "local_manual"
    assert empty["lifecycle"]["repair_supported"] is False

    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )

    populated = cast(dict[str, Any], writer.diagnostics())
    assert populated["category"] == "valid"
    assert populated["verification"]["valid"] is True
    assert populated["verification"]["event_count"] == 1
    assert populated["sqlite_event_count"] == 1
    assert populated["jsonl_line_count"] == 1
    assert populated["jsonl_head_hash"] == populated["verification"]["head_hash"]
    assert populated["lifecycle"]["status"] == "clean"
    assert populated["lifecycle"]["sqlite_jsonl_event_count_match"] is True
    assert populated["lifecycle"]["sqlite_jsonl_head_hash_match"] is True


def test_audit_diagnostics_classifies_tampered_payload(tmp_path: Path) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()
    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )

    with sqlite3.connect(writer.db_path) as connection:
        payload_json = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = 'evt_1'"
        ).fetchone()[0]
        payload = json.loads(str(payload_json))
        payload["metadata"] = {"tampered": True}
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
        )
        connection.commit()

    diagnostics = cast(dict[str, Any], writer.diagnostics())
    assert diagnostics["category"] == "event_hash_mismatch"
    assert diagnostics["lifecycle"]["status"] == "verification_failed"
    assert diagnostics["verification"]["valid"] is False
    assert diagnostics["verification"]["failure"]["event_id"] == "evt_1"


def test_audit_diagnostics_classifies_invalid_json(tmp_path: Path) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()
    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )

    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            ("{",),
        )
        connection.commit()

    diagnostics = cast(dict[str, Any], writer.diagnostics())
    assert diagnostics["category"] == "invalid_json"
    assert diagnostics["lifecycle"]["status"] == "verification_failed"
    assert diagnostics["verification"]["valid"] is False
    assert diagnostics["verification"]["failure"]["reason"] == "invalid audit payload JSON"


def test_audit_diagnostics_reports_jsonl_lifecycle_drift(tmp_path: Path) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()
    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )
    writer.jsonl_path.write_text("", encoding="utf-8")

    diagnostics = cast(dict[str, Any], writer.diagnostics())

    assert diagnostics["category"] == "valid"
    assert diagnostics["verification"]["valid"] is True
    assert diagnostics["sqlite_event_count"] == 1
    assert diagnostics["jsonl_line_count"] == 0
    assert diagnostics["lifecycle"]["status"] == "recovery_required"
    assert diagnostics["lifecycle"]["sqlite_jsonl_event_count_match"] is False
    assert diagnostics["lifecycle"]["sqlite_jsonl_head_hash_match"] is False


@pytest.mark.parametrize("drift", ["content_edit_same_head", "missing_terminal_newline"])
def test_audit_diagnostics_requires_exact_lf_framed_payload_parity(
    tmp_path: Path,
    drift: str,
) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()
    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )
    if drift == "content_edit_same_head":
        payload = json.loads(writer.jsonl_path.read_text(encoding="utf-8"))
        payload["principal"]["id"] = "agent:edited"
        writer.jsonl_path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    else:
        writer.jsonl_path.write_bytes(
            writer.jsonl_path.read_bytes().removesuffix(b"\n")
        )

    diagnostics = cast(dict[str, Any], writer.diagnostics())

    assert diagnostics["verification"]["valid"] is True
    assert diagnostics["lifecycle"]["sqlite_jsonl_event_count_match"] is True
    assert diagnostics["lifecycle"]["sqlite_jsonl_head_hash_match"] is True
    assert diagnostics["lifecycle"]["sqlite_jsonl_payload_bytes_match"] is False
    assert diagnostics["lifecycle"]["status"] == "recovery_required"


def test_audit_diagnostics_cli_json_and_fail_on_invalid(tmp_path: Path) -> None:
    writer = AuditWriter(tmp_path / "audit.sqlite3", tmp_path / "audit.jsonl")
    writer.initialize()

    valid = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/audit_diagnostics.py",
            "--db-path",
            str(writer.db_path),
            "--log-path",
            str(writer.jsonl_path),
            "--json",
            "--fail-on-invalid",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(valid.stdout)["category"] == "empty_valid"

    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            ("{",),
        )
        connection.commit()

    invalid = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/audit_diagnostics.py",
            "--db-path",
            str(writer.db_path),
            "--log-path",
            str(writer.jsonl_path),
            "--json",
            "--fail-on-invalid",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["category"] == "invalid_json"
