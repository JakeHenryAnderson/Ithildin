from __future__ import annotations

import base64
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.nodes import (
    EnrollmentCodeIssuePayload,
    NodeAuthenticationError,
    NodeConflictError,
    NodeEnrollmentPayload,
    NodeHeartbeatPayload,
    NodeStore,
    canonical_signature_message,
)
from ithildin_schemas import sha256_digest
from pydantic import ValidationError


def test_enrollment_is_one_time_digest_only_and_gateway_derived(tmp_path: Path) -> None:
    store = NodeStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Hermes workstation"),
        expires_in_seconds=600,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    private_key, public_key = _keypair()
    payload = _enrollment(issued.enrollment_code, public_key)

    record = store.enroll(payload)

    assert record.node_id.startswith("node_")
    assert record.principal_id == f"agent:node.{record.node_id}"
    assert record.workspace_id == "default"
    assert record.summary()["observed_state"] == "evidence_incomplete"
    record = store.mark_node_evidence_complete(record.node_id)
    assert record.summary()["observed_state"] == "never_observed"
    with sqlite3.connect(store.db_path) as connection:
        row = connection.execute(
            "SELECT code_hash, consumed_at, consumed_node_id FROM node_enrollment_codes"
        ).fetchone()
    assert row is not None
    assert issued.enrollment_code not in str(row[0])
    assert str(row[0]).startswith("sha256:")
    assert row[1] is not None
    assert row[2] == record.node_id
    with pytest.raises(NodeConflictError, match="already consumed"):
        store.enroll(payload)
    assert private_key is not None


def test_expired_or_unknown_enrollment_code_fails_closed(tmp_path: Path) -> None:
    store = NodeStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    now = datetime(2026, 7, 16, tzinfo=UTC)
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=60,
        now=now,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    _, public_key = _keypair()
    with pytest.raises(NodeAuthenticationError, match="expired"):
        store.enroll(
            _enrollment(issued.enrollment_code, public_key),
            now=now + timedelta(seconds=61),
        )
    with pytest.raises(NodeAuthenticationError, match="invalid enrollment code"):
        store.enroll(_enrollment("x" * 48, public_key), now=now)


def test_incomplete_audit_evidence_blocks_node_transitions(tmp_path: Path) -> None:
    store = NodeStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
    )
    _, public_key = _keypair()
    payload = _enrollment(issued.enrollment_code, public_key)

    with pytest.raises(NodeAuthenticationError, match="evidence is incomplete"):
        store.enroll(payload)

    store.mark_enrollment_code_evidence_complete(issued.code_id)
    record = store.enroll(payload)
    with pytest.raises(NodeAuthenticationError, match="evidence is incomplete"):
        store.accept_heartbeat(
            node_id=record.node_id,
            timestamp=str(int(datetime.now(UTC).timestamp())),
            nonce="9" * 32,
            signature="not-reached",
            payload=_heartbeat(),
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
        )
    with pytest.raises(NodeConflictError, match="evidence is incomplete"):
        store.revoke(record.node_id)


def test_node_store_migrates_existing_schemas_with_evidence_state(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE node_enrollment_codes (
                code_id TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE,
                workspace_id TEXT NOT NULL, display_name TEXT NOT NULL,
                created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                consumed_at TEXT, consumed_node_id TEXT
            );
            CREATE TABLE nodes (
                node_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL UNIQUE,
                workspace_id TEXT NOT NULL, display_name TEXT NOT NULL,
                status TEXT NOT NULL, public_key TEXT NOT NULL,
                descriptor_hash TEXT NOT NULL, descriptor_json TEXT NOT NULL,
                enrolled_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                last_seen_at TEXT, revoked_at TEXT, last_heartbeat_hash TEXT,
                last_configuration_digest TEXT, last_mission_id TEXT
            );
            """
        )
    store = NodeStore(db_path)

    store.initialize()

    with sqlite3.connect(db_path) as connection:
        node_columns = {row[1] for row in connection.execute("PRAGMA table_info(nodes)")}
        code_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(node_enrollment_codes)")
        }
    assert "evidence_status" in node_columns
    assert "evidence_status" in code_columns


def test_signed_heartbeat_replay_restart_and_revocation(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    store = NodeStore(db_path)
    store.initialize()
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Hermes Node"),
        expires_in_seconds=600,
        now=now,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    private_key, public_key = _keypair()
    record = store.enroll(_enrollment(issued.enrollment_code, public_key), now=now)
    record = store.mark_node_evidence_complete(record.node_id)
    heartbeat = _heartbeat()
    timestamp = str(int(now.timestamp()))
    nonce = "a" * 32
    signature = _sign(
        private_key,
        node_id=record.node_id,
        timestamp=timestamp,
        nonce=nonce,
        heartbeat=heartbeat,
    )

    accepted = store.accept_heartbeat(
        node_id=record.node_id,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
        payload=heartbeat,
        path=f"/nodes/{record.node_id}/heartbeat",
        max_clock_skew_seconds=120,
        now=now,
    )

    assert accepted.summary(now=now)["observed_state"] == "evidence_incomplete"
    accepted = store.mark_node_evidence_complete(record.node_id)
    assert accepted.summary(now=now)["observed_state"] == "observed_connected"
    assert accepted.last_configuration_digest == heartbeat.configuration_digest
    assert accepted.last_heartbeat_hash is not None
    restarted = NodeStore(db_path)
    restarted.initialize()
    with pytest.raises(NodeAuthenticationError, match="replayed Node nonce"):
        restarted.accept_heartbeat(
            node_id=record.node_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
            payload=heartbeat,
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
            now=now,
        )
    restarted.revoke(record.node_id, now=now + timedelta(seconds=1))
    restarted.mark_node_evidence_complete(record.node_id)
    nonce_two = "b" * 32
    with pytest.raises(NodeAuthenticationError, match="revoked"):
        restarted.accept_heartbeat(
            node_id=record.node_id,
            timestamp=timestamp,
            nonce=nonce_two,
            signature=_sign(
                private_key,
                node_id=record.node_id,
                timestamp=timestamp,
                nonce=nonce_two,
                heartbeat=heartbeat,
            ),
            payload=heartbeat,
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
            now=now,
        )


def test_invalid_signature_stale_timestamp_and_unsafe_metadata_are_rejected(
    tmp_path: Path,
) -> None:
    store = NodeStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
        now=now,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    _, public_key = _keypair()
    record = store.enroll(_enrollment(issued.enrollment_code, public_key), now=now)
    record = store.mark_node_evidence_complete(record.node_id)
    wrong_private_key, _ = _keypair()
    heartbeat = _heartbeat()
    timestamp = str(int(now.timestamp()))
    nonce = "c" * 32
    with pytest.raises(NodeAuthenticationError, match="invalid Node signature"):
        store.accept_heartbeat(
            node_id=record.node_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=_sign(
                wrong_private_key,
                node_id=record.node_id,
                timestamp=timestamp,
                nonce=nonce,
                heartbeat=heartbeat,
            ),
            payload=heartbeat,
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
            now=now,
        )
    with pytest.raises(NodeAuthenticationError, match="stale Node timestamp"):
        store.accept_heartbeat(
            node_id=record.node_id,
            timestamp=str(int((now - timedelta(minutes=5)).timestamp())),
            nonce="d" * 32,
            signature="not-valid",
            payload=heartbeat,
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
            now=now,
        )
    with pytest.raises(ValidationError):
        NodeHeartbeatPayload.model_validate(
            {**heartbeat.model_dump(), "runner_adapter": "../../unsafe"}
        )


def _keypair() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, base64.b64encode(public_bytes).decode()


def _enrollment(code: str, public_key: str) -> NodeEnrollmentPayload:
    return NodeEnrollmentPayload(
        enrollment_code=code,
        public_key=public_key,
        protocol_version="1",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )


def _heartbeat() -> NodeHeartbeatPayload:
    return NodeHeartbeatPayload(
        protocol_version="1",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("1" * 64),
        mission_id="mission-synthetic-001",
    )


def _sign(
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    timestamp: str,
    nonce: str,
    heartbeat: NodeHeartbeatPayload,
) -> str:
    message = canonical_signature_message(
        method="POST",
        path=f"/nodes/{node_id}/heartbeat",
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(heartbeat.safe_payload()),
    )
    return base64.b64encode(private_key.sign(message)).decode()
