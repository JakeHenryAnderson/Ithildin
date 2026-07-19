from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_audit_core import (
    AuditSigningError,
    AuditWriteError,
    AuditWriter,
    generate_audit_signing_keypair,
    signed_audit_export_bundle,
    verify_exported_events_jsonl,
    verify_signed_audit_export_bundle,
)
from ithildin_audit_core.signing import _signature_payload
from ithildin_schemas import (
    AuditEventType,
    JsonObject,
    PolicyDecisionValue,
    canonical_json,
    sha256_digest,
)

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


def tamper_text(value: str) -> str:
    replacement = "A" if value[-1] != "A" else "B"
    return f"{value[:-1]}{replacement}"


def event_hash_from_payload(payload: JsonObject) -> str:
    return sha256_digest(
        {
            "event_id": payload["event_id"],
            "timestamp": payload["timestamp"],
            "event_type": payload["event_type"],
            "request_id": payload["request_id"],
            "principal": payload["principal"],
            "tool_name": payload.get("tool_name"),
            "resource": payload.get("resource"),
            "decision": payload.get("decision"),
            "policy_version": payload.get("policy_version"),
            "matched_rules": payload.get("matched_rules", []),
            "input_hash": payload.get("input_hash"),
            "redactions": payload.get("redactions", []),
            "metadata": payload.get("metadata", {}),
            "prev_event_hash": payload["prev_event_hash"],
        }
    )


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


def test_audit_writer_serializes_concurrent_chain_appends(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer_count = 16
    barrier = Barrier(writer_count)

    def write_one(index: int) -> str:
        barrier.wait()
        event = writer.write_event(
            event_id=f"evt_{index}",
            timestamp=NOW,
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            request_id=f"req_{index}",
            principal={"id": f"agent:{index}"},
        )
        return event.event_hash

    with ThreadPoolExecutor(max_workers=writer_count) as executor:
        hashes = list(executor.map(write_one, range(writer_count)))

    verification = writer.verify_chain()
    diagnostics = writer.diagnostics()

    assert len(set(hashes)) == writer_count
    assert verification.valid is True
    assert verification.event_count == writer_count
    assert diagnostics["sqlite_event_count"] == writer_count
    assert diagnostics["jsonl_line_count"] == writer_count
    assert diagnostics["jsonl_head_hash"] == verification.head_hash


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
            """
            UPDATE audit_events
            SET payload_json = ?, prev_event_hash = ?
            WHERE event_id = 'evt_2'
            """,
            (
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                payload["prev_event_hash"],
            ),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "previous event hash mismatch"
    assert result.failure.event_id == "evt_2"


def test_audit_writer_detects_invalid_payload_json(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id, timestamp, event_type, request_id,
                prev_event_hash, event_hash, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt_bad",
                NOW.isoformat(),
                AuditEventType.POLICY_EVALUATED.value,
                "req_bad",
                "sha256:" + ("0" * 64),
                VALID_HASH,
                "{",
            ),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "invalid audit payload JSON"
    assert result.failure.row_number == 1


def test_audit_writer_detects_non_object_payload_json(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id, timestamp, event_type, request_id,
                prev_event_hash, event_hash, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt_bad",
                NOW.isoformat(),
                AuditEventType.POLICY_EVALUATED.value,
                "req_bad",
                "sha256:" + ("0" * 64),
                VALID_HASH,
                "[]",
            ),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "invalid audit event schema"
    assert result.failure.row_number == 1


def test_audit_writer_detects_invalid_event_schema(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    payload = {
        "event_id": "evt_bad",
        "timestamp": NOW.isoformat(),
        "event_type": AuditEventType.POLICY_EVALUATED.value,
        "request_id": "req_bad",
        "principal": {"id": "agent:local-dev"},
        "prev_event_hash": "sha256:" + ("0" * 64),
    }
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id, timestamp, event_type, request_id,
                prev_event_hash, event_hash, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt_bad",
                NOW.isoformat(),
                AuditEventType.POLICY_EVALUATED.value,
                "req_bad",
                "sha256:" + ("0" * 64),
                VALID_HASH,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ),
        )
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "invalid audit event schema"
    assert result.failure.event_id == "evt_bad"


def test_audit_writer_detects_missing_middle_row(tmp_path: Path) -> None:
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
    writer.write_event(
        event_id="evt_3",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
        request_id="req_3",
        principal={"id": "agent:local-dev"},
    )
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute("DELETE FROM audit_events WHERE event_id = 'evt_2'")
        connection.commit()

    result = writer.verify_chain()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "previous event hash mismatch"
    assert result.failure.event_id == "evt_3"
    assert result.event_count == 2


def test_audit_writer_detects_index_payload_mismatch(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    with sqlite3.connect(writer.db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET event_hash = ? WHERE event_id = 'evt_1'",
            ("sha256:" + ("b" * 64),),
        )
        connection.commit()

    result = writer.verify_chain()
    diagnostics = writer.diagnostics()

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "indexed audit columns mismatch"
    assert diagnostics["category"] == "index_mismatch"


def test_audit_diagnostics_categorize_corruption(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    with sqlite3.connect(writer.db_path) as connection:
        payload_json = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = 'evt_1'"
        ).fetchone()[0]
        payload = json.loads(str(payload_json))
        payload["principal"] = {"id": "agent:tampered"}
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
        )
        connection.commit()

    diagnostics = writer.diagnostics()
    verification = cast(dict[str, Any], diagnostics["verification"])

    assert diagnostics["category"] == "event_hash_mismatch"
    assert verification["valid"] is False


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
    assert metadata["diagnostics"]["lifecycle"]["status"] == "clean"
    assert event_payload["event_id"] == "evt_1"


def test_audit_writer_export_can_require_clean_lifecycle(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    writer.jsonl_path.write_text("", encoding="utf-8")

    bundle_lines = writer.export_jsonl_bundle().splitlines()
    metadata = json.loads(bundle_lines[0])["metadata"]

    assert metadata["diagnostics"]["lifecycle"]["status"] == "recovery_required"
    with pytest.raises(AuditWriteError, match="audit lifecycle is not clean"):
        writer.export_jsonl_bundle(require_clean_lifecycle=True)


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
        bundle["signature"]["signature"] = tamper_text(str(bundle["signature"]["signature"]))
    else:
        bundle["signature"]["public_key"] = tamper_text(str(bundle["signature"]["public_key"]))

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
    bundle = signed_audit_export_bundle(
        jsonl_bundle=writer.export_jsonl_bundle(),
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )

    result = verify_signed_audit_export_bundle(bundle, public_key_path=wrong_public_key_path)

    assert result.valid is False
    assert result.failure == "signed bundle public key does not match trusted key"


def test_signed_audit_export_requires_trusted_public_key(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
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

    result = verify_signed_audit_export_bundle(bundle)

    assert result.valid is False
    assert result.failure == "trusted public key is required"


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
    bundle = signed_audit_export_bundle(
        jsonl_bundle=writer.export_jsonl_bundle(),
        private_key_path=private_key_path,
        public_key_path=public_key_path,
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


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("bundle_type", "wrong.bundle", "bundle_type has unsupported value"),
        ("format_version", "999", "format_version has unsupported value"),
        ("events_sha256", "sha256:bad", "events_sha256 must be a sha256 digest"),
    ],
)
def test_signed_audit_export_rejects_malformed_top_level_fields(
    tmp_path: Path,
    field: str,
    value: str,
    failure: str,
) -> None:
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
    bundle[field] = value

    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is False
    assert result.failure == failure


def test_signed_audit_export_rejects_resigned_malformed_nested_metadata(
    tmp_path: Path,
) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
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
    metadata = cast(dict[str, Any], bundle["metadata"])
    metadata["bundle_type"] = "wrong.bundle"
    signature = cast(dict[str, Any], bundle["signature"])
    signature_metadata: JsonObject = {
        "algorithm": cast(str, signature["algorithm"]),
        "key_id": cast(str, signature["key_id"]),
        "public_key": cast(str, signature["public_key"]),
        "created_at": cast(str, signature["created_at"]),
    }
    private_key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    payload = _signature_payload(
        metadata=cast(JsonObject, metadata),
        events_sha256=cast(str, bundle["events_sha256"]),
        signature_metadata=signature_metadata,
    )
    signature["signature"] = base64.b64encode(
        private_key.sign(canonical_json(payload).encode("utf-8"))
    ).decode("ascii")

    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is False
    assert result.failure == "metadata verification does not match exported events"


def test_signed_audit_export_rejects_non_object_bundle() -> None:
    result = verify_signed_audit_export_bundle([])

    assert result.valid is False
    assert result.failure == "bundle must be an object"


def test_signed_audit_export_rejects_manifest_signature_bundle_confusion(
    tmp_path: Path,
) -> None:
    bundle = cast(
        JsonObject,
        {
            "signature_type": "ithildin.manifest_lock.signature",
            "format_version": "1",
        },
    )

    result = verify_signed_audit_export_bundle(
        bundle,
        public_key_path=tmp_path / "missing-public.pem",
    )

    assert result.valid is False
    assert result.failure == "bundle_type must be a string"


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("algorithm", "ed448", "unsupported signature algorithm"),
        ("key_id", "sha256:bad", "signature.key_id must be a sha256 digest"),
        ("signature", "not base64!", "Only base64 data is allowed"),
    ],
)
def test_signed_audit_export_rejects_malformed_signature_fields(
    tmp_path: Path,
    field: str,
    value: str,
    failure: str,
) -> None:
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
    signature = cast(dict[str, Any], bundle["signature"])
    signature[field] = value

    result = verify_signed_audit_export_bundle(bundle, public_key_path=public_key_path)

    assert result.valid is False
    assert result.failure == failure


def test_exported_events_jsonl_rejects_duplicate_event_lines(tmp_path: Path) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    event_line = writer.export_jsonl_bundle().splitlines()[1]

    result = verify_exported_events_jsonl(f"{event_line}\n{event_line}\n")

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "duplicate audit event id"
    assert result.failure.event_id == "evt_1"


def test_exported_events_jsonl_rejects_duplicate_event_ids_with_valid_hash(
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
    event_lines = writer.export_jsonl_bundle().splitlines()[1:]
    second_payload = cast(JsonObject, json.loads(event_lines[1]))
    second_payload["event_id"] = "evt_1"
    second_payload["event_hash"] = event_hash_from_payload(second_payload)
    adversarial_jsonl = "\n".join(
        [
            event_lines[0],
            json.dumps(second_payload, sort_keys=True, separators=(",", ":")),
        ]
    )

    result = verify_exported_events_jsonl(f"{adversarial_jsonl}\n")

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "duplicate audit event id"
    assert result.failure.event_id == "evt_1"


def test_exported_events_jsonl_rejects_non_object_payload() -> None:
    result = verify_exported_events_jsonl("[]\n")

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "invalid audit event schema"


def test_exported_events_jsonl_rejects_missing_middle_event(tmp_path: Path) -> None:
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
    writer.write_event(
        event_id="evt_3",
        timestamp=NOW,
        event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
        request_id="req_3",
        principal={"id": "agent:local-dev"},
    )
    event_lines = writer.export_jsonl_bundle().splitlines()[1:]

    result = verify_exported_events_jsonl("\n".join([event_lines[0], event_lines[2]]) + "\n")

    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "previous event hash mismatch"
    assert result.failure.event_id == "evt_3"


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
    assert result.valid is False
    assert result.failure == "audit verification failed"
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


@pytest.mark.parametrize("drift", ["orphan", "missing", "tampered", "invalid_utf8"])
def test_audit_writer_blocks_new_events_when_committed_jsonl_lifecycle_drifts(
    tmp_path: Path,
    drift: str,
) -> None:
    writer = make_writer(tmp_path)
    writer.write_event(
        event_id="evt_1",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:local-dev"},
    )
    original = writer.jsonl_path.read_text(encoding="utf-8")
    if drift == "orphan":
        writer.jsonl_path.write_text(original + "{}\n", encoding="utf-8")
    elif drift == "missing":
        writer.jsonl_path.write_text("", encoding="utf-8")
    elif drift == "tampered":
        writer.jsonl_path.write_text(
            original.replace("policy.evaluated", "policy.tampered"),
            encoding="utf-8",
        )
    else:
        writer.jsonl_path.write_bytes(b"\xff\n")
    drifted = writer.jsonl_path.read_bytes()

    with pytest.raises(AuditWriteError, match="lifecycle recovery is required"):
        writer.write_event(
            event_id="evt_2",
            timestamp=NOW,
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_2",
            principal={"id": "agent:local-dev"},
        )

    with sqlite3.connect(writer.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone() == (1,)
    assert writer.jsonl_path.read_bytes() == drifted
