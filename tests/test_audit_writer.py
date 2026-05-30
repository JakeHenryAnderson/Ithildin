from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_audit_core import (
    AuditSigningError,
    AuditWriteError,
    AuditWriter,
    generate_audit_signing_keypair,
    signed_audit_export_bundle,
    verify_signed_audit_export_bundle,
)
from ithildin_schemas import AuditEventType, JsonObject, PolicyDecisionValue

VALID_HASH = "sha256:" + ("a" * 64)
NOW = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)


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


def test_audit_writer_verifies_valid_multi_event_chain(tmp_path: Path) -> None:
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

    result = writer.verify_chain()

    assert result.valid is True
    assert result.event_count == 2
    assert result.first_timestamp == first.timestamp.isoformat()
    assert result.last_timestamp == second.timestamp.isoformat()
    assert result.head_hash == second.event_hash
    assert result.failure is None


def test_audit_writer_verifies_empty_chain(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    result = writer.verify_chain()

    assert result.as_dict() == {
        "valid": True,
        "event_count": 0,
        "first_timestamp": None,
        "last_timestamp": None,
        "head_hash": "sha256:" + ("0" * 64),
        "failure": None,
    }


def test_audit_writer_detects_tampered_payload(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        payload_json = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = 'evt_1'"
        ).fetchone()[0]
        payload = json.loads(str(payload_json))
        payload["tool_name"] = "fs.tampered"
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "event hash mismatch"
    assert result.failure.event_id == "evt_1"


def test_audit_writer_detects_broken_previous_hash(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_CALL_PROPOSED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    writer.write_event(
        event_id="evt_2",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_2",
        principal={"id": "agent:local-dev"},
    )
    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        payload_json = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = 'evt_2'"
        ).fetchone()[0]
        payload = json.loads(str(payload_json))
        payload["prev_event_hash"] = "sha256:" + ("1" * 64)
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_2'",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "previous event hash mismatch"
    assert result.failure.event_id == "evt_2"


def test_audit_writer_export_includes_metadata_and_jsonl_events(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    event = writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )

    bundle_lines = writer.export_jsonl_bundle().splitlines()

    metadata = json.loads(bundle_lines[0])["metadata"]
    event_payload = json.loads(bundle_lines[1])
    assert metadata["bundle_type"] == "ithildin.audit.export"
    assert metadata["format_version"] == "1"
    assert metadata["event_count"] == 1
    assert metadata["head_hash"] == event.event_hash
    assert metadata["verification"]["valid"] is True
    assert event_payload["event_id"] == "evt_1"


def test_audit_signing_key_generation_and_signed_export_verification(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    event = writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
    )
    private_key_path = tmp_path / "keys" / "audit-private.pem"
    public_key_path = tmp_path / "keys" / "audit-public.pem"

    key_id = generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    bundle = cast(
        dict[str, Any],
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )
    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert private_key_path.exists()
    assert public_key_path.exists()
    assert bundle["bundle_type"] == "ithildin.audit.signed_export"
    assert bundle["format_version"] == "1"
    assert bundle["events_sha256"].startswith("sha256:")
    assert bundle["metadata"]["head_hash"] == event.event_hash
    assert bundle["signature"]["algorithm"] == "ed25519"
    assert bundle["signature"]["key_id"] == key_id
    assert result.valid is True
    assert result.audit_verification.event_count == 1


def test_signed_audit_export_verifies_empty_chain(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )

    bundle = signed_audit_export_bundle(
        jsonl_bundle=writer.export_jsonl_bundle(),
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is True
    assert result.audit_verification.event_count == 0
    assert result.audit_verification.head_hash == "sha256:" + ("0" * 64)


@pytest.mark.parametrize(
    "tamper",
    ["metadata", "events", "events_sha256", "signature", "public_key"],
)
def test_signed_audit_export_detects_tampering(tmp_path: Path, tamper: str) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    bundle = cast(
        dict[str, Any],
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )

    if tamper == "metadata":
        bundle["metadata"]["event_count"] = 99
    elif tamper == "events":
        bundle["events_jsonl"] = str(bundle["events_jsonl"]).replace("fs.read", "fs.stat")
    elif tamper == "events_sha256":
        bundle["events_sha256"] = "sha256:" + ("b" * 64)
    elif tamper == "signature":
        bundle["signature"]["signature"] = "AA" + str(bundle["signature"]["signature"])[2:]
    else:
        bundle["signature"]["public_key"] = "AA" + str(bundle["signature"]["public_key"])[2:]

    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is False
    assert result.failure is not None


def test_signed_audit_export_rejects_wrong_trusted_public_key(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    wrong_private_key_path = tmp_path / "wrong-private.pem"
    wrong_public_key_path = tmp_path / "wrong-public.pem"
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    generate_audit_signing_keypair(
        private_key_path=wrong_private_key_path,
        public_key_path=wrong_public_key_path,
    )
    bundle = cast(
        JsonObject,
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )

    result = verify_signed_audit_export_bundle(bundle, public_key_path=wrong_public_key_path)

    assert result.valid is False
    assert result.failure == "signed bundle public key does not match trusted key"


def test_signed_audit_export_rejects_reordered_events_with_recomputed_digest(
    tmp_path: Path,
) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_CALL_PROPOSED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    writer.write_event(
        event_id="evt_2",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_2",
        principal={"id": "agent:local-dev"},
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    bundle = cast(
        JsonObject,
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )
    event_lines = str(bundle["events_jsonl"]).splitlines()
    reordered_events = "\n".join(reversed(event_lines)) + "\n"
    bundle["events_jsonl"] = reordered_events
    bundle["events_sha256"] = "sha256:" + hashlib.sha256(
        reordered_events.encode("utf-8")
    ).hexdigest()

    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is False
    assert result.failure == "signature verification failed"


def test_signed_audit_export_reflects_failed_chain_verification(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
    )
    with sqlite3.connect(writer.db_path) as connection:
        payload_json = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = 'evt_1'"
        ).fetchone()[0]
        payload = json.loads(str(payload_json))
        payload["tool_name"] = "fs.changed"
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
        )
        connection.commit()
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    generate_audit_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )

    bundle = cast(
        dict[str, Any],
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )
    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert bundle["metadata"]["verification"]["valid"] is False
    assert result.valid is True
    assert result.audit_verification.valid is False


def test_signed_audit_export_fails_for_missing_keys(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)

    with pytest.raises(AuditSigningError):
        signed_audit_export_bundle(
            jsonl_bundle=writer.export_jsonl_bundle(),
            private_key_path=tmp_path / "missing-private.pem",
            public_key_path=tmp_path / "missing-public.pem",
        )


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
