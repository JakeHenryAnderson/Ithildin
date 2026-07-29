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
    NodeIdentityRotationActivationPayload,
    NodeStore,
    canonical_identity_rotation_proof_message,
    canonical_signature_message,
    node_identity_key_id,
)
from ithildin_schemas import JsonObject, sha256_digest
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


def test_node_identity_rejects_noncanonical_base64_without_changing_canonical_ids(
    tmp_path: Path,
) -> None:
    store = NodeStore(tmp_path / "ithildin.sqlite3")
    store.initialize()
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    private_key, canonical_public_key = _keypair()
    variants = _noncanonical_public_key_variants(canonical_public_key)

    legacy_public_key = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
    legacy_key_id = "sha256:c13217bb5694185919fa9b0bb7d18759c8dd4006aa0de169d29e9480d38f7bcd"
    assert base64.b64decode(legacy_public_key, validate=True) == bytes(range(32))
    assert node_identity_key_id(legacy_public_key) == legacy_key_id
    assert node_identity_key_id(canonical_public_key) == sha256_digest(canonical_public_key)
    assert variants
    for variant in variants:
        assert base64.b64decode(variant, validate=True) == base64.b64decode(
            canonical_public_key,
            validate=True,
        )
        with pytest.raises(ValidationError, match="invalid Ed25519 public key"):
            _enrollment(issued.enrollment_code, variant)
        with pytest.raises(ValidationError, match="invalid Ed25519 public key"):
            NodeIdentityRotationActivationPayload(
                protocol_version="1",
                rotation_id="nkr_" + ("a" * 32),
                challenge="c" * 40,
                next_public_key=variant,
                next_key_proof=base64.b64encode(private_key.sign(b"same-key")).decode(),
            )
        with pytest.raises(ValueError, match="invalid Ed25519 public key"):
            node_identity_key_id(variant)


def test_identity_rotation_store_rejects_noncanonical_alias_of_current_key(
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
    current_private, current_public = _keypair()
    node = store.enroll(_enrollment(issued.enrollment_code, current_public), now=now)
    node = store.mark_node_evidence_complete(node.node_id)
    challenge = store.issue_identity_rotation_challenge(node.node_id, now=now)
    rotation = store.mark_identity_rotation_challenge_evidence_complete(
        challenge.record.rotation_id
    )
    aliased_public_key = _noncanonical_public_key_variants(current_public)[0]
    payload = NodeIdentityRotationActivationPayload.model_construct(
        protocol_version="1",
        rotation_id=rotation.rotation_id,
        challenge=challenge.challenge,
        next_public_key=aliased_public_key,
        next_key_proof=base64.b64encode(current_private.sign(b"same-key")).decode(),
    )

    with pytest.raises(
        NodeConflictError,
        match="identity-key rotation must change the key",
    ):
        store.activate_identity_rotation(node.node_id, payload, now=now)


def test_node_store_fails_closed_on_persisted_noncanonical_public_key(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    store = NodeStore(db_path)
    store.initialize()
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    _, canonical_public_key = _keypair()
    record = store.enroll(_enrollment(issued.enrollment_code, canonical_public_key))
    noncanonical_public_key = _noncanonical_public_key_variants(canonical_public_key)[0]
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO node_identity_key_rotations (
                rotation_id, node_id, principal_id, workspace_id, current_key_id,
                current_public_key, challenge_digest, created_at, expires_at, status,
                evidence_status, next_public_key, next_key_id, activated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'expired', 'complete', ?, ?, NULL)
            """,
            (
                "nkr_" + ("f" * 32),
                record.node_id,
                record.principal_id,
                record.workspace_id,
                node_identity_key_id(canonical_public_key),
                noncanonical_public_key,
                sha256_digest("historical challenge"),
                datetime(2026, 7, 16, tzinfo=UTC).isoformat(),
                datetime(2026, 7, 16, tzinfo=UTC).isoformat(),
                noncanonical_public_key,
                "sha256:" + ("f" * 64),
            ),
        )
        connection.commit()

    # Historical terminal transition material is evidence, not current authority.
    NodeStore(db_path).initialize()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE nodes SET public_key = ? WHERE node_id = ?",
            (noncanonical_public_key, record.node_id),
        )
        connection.commit()

    with pytest.raises(
        NodeConflictError,
        match=(
            "stored Node identity key is non-canonical; explicit offline "
            "reconciliation is required and no rewrite occurred"
        ),
    ):
        NodeStore(db_path).initialize()
    with sqlite3.connect(db_path) as connection:
        persisted_public_key = connection.execute(
            "SELECT public_key FROM nodes WHERE node_id = ?",
            (record.node_id,),
        ).fetchone()
    assert persisted_public_key is not None
    assert persisted_public_key[0] == noncanonical_public_key


@pytest.mark.parametrize(
    ("status", "evidence_status", "authority_column"),
    [
        ("pending", "complete", "current_public_key"),
        ("activated", "pending", "current_public_key"),
        ("activated", "pending", "next_public_key"),
    ],
)
def test_node_store_checks_recoverable_rotation_key_material(
    tmp_path: Path,
    status: str,
    evidence_status: str,
    authority_column: str,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    store = NodeStore(db_path)
    store.initialize()
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    _, current_public_key = _keypair()
    record = store.enroll(_enrollment(issued.enrollment_code, current_public_key))
    record = store.mark_node_evidence_complete(record.node_id)
    _, next_public_key = _keypair()
    current_stored_key = current_public_key
    next_stored_key: str | None = next_public_key if status == "activated" else None
    if authority_column == "current_public_key":
        current_stored_key = _noncanonical_public_key_variants(current_public_key)[0]
    else:
        next_stored_key = _noncanonical_public_key_variants(next_public_key)[0]

    with sqlite3.connect(db_path) as connection:
        if status == "activated":
            connection.execute(
                "UPDATE nodes SET public_key = ?, evidence_status = 'pending' "
                "WHERE node_id = ?",
                (next_public_key, record.node_id),
            )
        connection.execute(
            """
            INSERT INTO node_identity_key_rotations (
                rotation_id, node_id, principal_id, workspace_id, current_key_id,
                current_public_key, challenge_digest, created_at, expires_at, status,
                evidence_status, next_public_key, next_key_id, activated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "nkr_" + ("e" * 32),
                record.node_id,
                record.principal_id,
                record.workspace_id,
                node_identity_key_id(current_public_key),
                current_stored_key,
                sha256_digest("recoverable challenge"),
                datetime(2026, 7, 16, tzinfo=UTC).isoformat(),
                datetime(2026, 7, 16, 1, tzinfo=UTC).isoformat(),
                status,
                evidence_status,
                next_stored_key,
                (
                    node_identity_key_id(next_public_key)
                    if next_stored_key is not None
                    else None
                ),
                (
                    datetime(2026, 7, 16, tzinfo=UTC).isoformat()
                    if status == "activated"
                    else None
                ),
            ),
        )
        connection.commit()

    with pytest.raises(
        NodeConflictError,
        match="stored Node identity key is non-canonical",
    ):
        NodeStore(db_path).initialize()
    with sqlite3.connect(db_path) as connection:
        persisted_keys = connection.execute(
            "SELECT current_public_key, next_public_key "
            "FROM node_identity_key_rotations WHERE rotation_id = ?",
            ("nkr_" + ("e" * 32),),
        ).fetchone()
    assert persisted_keys is not None
    expected = (
        current_stored_key
        if authority_column == "current_public_key"
        else next_stored_key
    )
    observed_index = 0 if authority_column == "current_public_key" else 1
    assert persisted_keys[observed_index] == expected


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
    assert "last_node_version" in node_columns
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
    assert accepted.last_node_version == heartbeat.node_version
    assert accepted.last_configuration_digest == heartbeat.configuration_digest
    assert accepted.last_heartbeat_hash is not None
    restarted = NodeStore(db_path)
    restarted.initialize()
    assert restarted.get(record.node_id).last_node_version == heartbeat.node_version
    tampered = heartbeat.model_copy(update={"node_version": "0.0.1"})
    tamper_nonce = "d" * 32
    with pytest.raises(NodeAuthenticationError, match="invalid Node signature"):
        restarted.accept_heartbeat(
            node_id=record.node_id,
            timestamp=timestamp,
            nonce=tamper_nonce,
            signature=_sign(
                private_key,
                node_id=record.node_id,
                timestamp=timestamp,
                nonce=tamper_nonce,
                heartbeat=heartbeat,
            ),
            payload=tampered,
            path=f"/nodes/{record.node_id}/heartbeat",
            max_clock_skew_seconds=120,
            now=now,
        )
    assert restarted.get(record.node_id).last_node_version == heartbeat.node_version
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


def test_identity_key_rotation_requires_both_keys_retires_old_key_and_survives_restart(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    store = NodeStore(db_path)
    store.initialize()
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    issued = store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
        now=now,
    )
    store.mark_enrollment_code_evidence_complete(issued.code_id)
    current_private, current_public = _keypair()
    node = store.enroll(_enrollment(issued.enrollment_code, current_public), now=now)
    node = store.mark_node_evidence_complete(node.node_id)
    challenge_path = f"/nodes/{node.node_id}/identity-key-rotation/challenges"
    challenge_body: JsonObject = {"protocol_version": "1"}
    store.authenticate_request(
        node_id=node.node_id,
        timestamp=str(int(now.timestamp())),
        nonce="1" * 32,
        signature=_sign_request(
            current_private,
            path=challenge_path,
            timestamp=str(int(now.timestamp())),
            nonce="1" * 32,
            body=challenge_body,
        ),
        body=challenge_body,
        path=challenge_path,
        max_clock_skew_seconds=120,
        now=now,
    )
    challenge = store.issue_identity_rotation_challenge(node.node_id, now=now)
    rotation = store.mark_identity_rotation_challenge_evidence_complete(
        challenge.record.rotation_id
    )
    next_private, next_public = _keypair()
    next_key_id = node_identity_key_id(next_public)
    proof = canonical_identity_rotation_proof_message(
        rotation=rotation, next_key_id=next_key_id
    )
    activation = NodeIdentityRotationActivationPayload(
        protocol_version="1",
        rotation_id=rotation.rotation_id,
        challenge=challenge.challenge,
        next_public_key=next_public,
        next_key_proof=base64.b64encode(next_private.sign(proof)).decode(),
    )
    activation_body = activation.model_dump(mode="json")
    activation_path = f"/nodes/{node.node_id}/identity-key-rotation/activations"
    store.authenticate_request(
        node_id=node.node_id,
        timestamp=str(int(now.timestamp())),
        nonce="2" * 32,
        signature=_sign_request(
            current_private,
            path=activation_path,
            timestamp=str(int(now.timestamp())),
            nonce="2" * 32,
            body=activation_body,
        ),
        body=activation_body,
        path=activation_path,
        max_clock_skew_seconds=120,
        now=now,
    )
    pending_node, pending_rotation = store.activate_identity_rotation(
        node.node_id, activation, now=now
    )
    assert pending_node.evidence_status == "pending"
    assert pending_rotation.evidence_status == "pending"
    rotated_node, rotated = store.mark_identity_rotation_activation_evidence_complete(
        rotation.rotation_id
    )
    assert node_identity_key_id(rotated_node.public_key) == next_key_id
    assert rotated.summary(now=now)["retired_key_request_authority"] is False

    status_path = f"/nodes/{node.node_id}/identity-key-rotation/status"
    status_body: JsonObject = {
        "protocol_version": "1",
        "rotation_id": rotation.rotation_id,
    }
    with pytest.raises(NodeAuthenticationError, match="invalid Node signature"):
        store.authenticate_request(
            node_id=node.node_id,
            timestamp=str(int(now.timestamp())),
            nonce="3" * 32,
            signature=_sign_request(
                current_private,
                path=status_path,
                timestamp=str(int(now.timestamp())),
                nonce="3" * 32,
                body=status_body,
            ),
            body=status_body,
            path=status_path,
            max_clock_skew_seconds=120,
            now=now,
        )
    restarted = NodeStore(db_path)
    restarted.initialize()
    restarted.authenticate_request(
        node_id=node.node_id,
        timestamp=str(int(now.timestamp())),
        nonce="4" * 32,
        signature=_sign_request(
            next_private,
            path=status_path,
            timestamp=str(int(now.timestamp())),
            nonce="4" * 32,
            body=status_body,
        ),
        body=status_body,
        path=status_path,
        max_clock_skew_seconds=120,
        now=now,
    )
    assert restarted.latest_identity_rotation(node.node_id) == rotated


def test_identity_key_rotation_rejects_incomplete_expired_same_key_and_bad_proof(
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
    current_private, current_public = _keypair()
    node = store.enroll(_enrollment(issued.enrollment_code, current_public), now=now)
    store.mark_node_evidence_complete(node.node_id)
    challenge = store.issue_identity_rotation_challenge(
        node.node_id, expires_in_seconds=60, now=now
    )
    same_key_activation = NodeIdentityRotationActivationPayload(
        protocol_version="1",
        rotation_id=challenge.record.rotation_id,
        challenge=challenge.challenge,
        next_public_key=current_public,
        next_key_proof=base64.b64encode(current_private.sign(b"wrong-domain")).decode(),
    )
    with pytest.raises(NodeAuthenticationError, match="evidence is incomplete"):
        store.activate_identity_rotation(node.node_id, same_key_activation, now=now)
    rotation = store.mark_identity_rotation_challenge_evidence_complete(
        challenge.record.rotation_id
    )
    with pytest.raises(NodeConflictError, match="must change the key"):
        store.activate_identity_rotation(node.node_id, same_key_activation, now=now)
    next_private, next_public = _keypair()
    bad_proof = NodeIdentityRotationActivationPayload(
        protocol_version="1",
        rotation_id=rotation.rotation_id,
        challenge=challenge.challenge,
        next_public_key=next_public,
        next_key_proof=base64.b64encode(next_private.sign(b"wrong-domain")).decode(),
    )
    with pytest.raises(NodeAuthenticationError, match="invalid Node signature"):
        store.activate_identity_rotation(node.node_id, bad_proof, now=now)
    valid_proof = canonical_identity_rotation_proof_message(
        rotation=rotation, next_key_id=node_identity_key_id(next_public)
    )
    expired = bad_proof.model_copy(
        update={"next_key_proof": base64.b64encode(next_private.sign(valid_proof)).decode()}
    )
    with pytest.raises(NodeAuthenticationError, match="expired"):
        store.activate_identity_rotation(
            node.node_id, expired, now=now + timedelta(seconds=61)
        )
    replacement = store.issue_identity_rotation_challenge(
        node.node_id, expires_in_seconds=60, now=now + timedelta(seconds=61)
    )
    assert replacement.record.rotation_id != rotation.rotation_id
    assert store.get_identity_rotation(rotation.rotation_id).summary(
        now=now + timedelta(seconds=61)
    )["status"] == "expired"
def _keypair() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, base64.b64encode(public_bytes).decode()


def _noncanonical_public_key_variants(canonical_public_key: str) -> list[str]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    final_index = alphabet.index(canonical_public_key[-2])
    variants = [
        canonical_public_key[:-2] + alphabet[(final_index & 0b111100) | pad_bits] + "="
        for pad_bits in range(4)
    ]
    return [variant for variant in variants if variant != canonical_public_key]


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


def _sign_request(
    private_key: Ed25519PrivateKey,
    *,
    path: str,
    timestamp: str,
    nonce: str,
    body: JsonObject,
) -> str:
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(body),
    )
    return base64.b64encode(private_key.sign(message)).decode()
