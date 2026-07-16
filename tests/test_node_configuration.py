from __future__ import annotations

import base64
import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.node_configuration import (
    NodeConfigurationAcknowledgmentPayload,
    NodeConfigurationAssignmentPayload,
    NodeConfigurationConflictError,
    NodeConfigurationRollbackPayload,
    NodeConfigurationSigner,
    NodeConfigurationSigningError,
    NodeConfigurationStore,
    NodeConfigurationVerificationError,
    generate_node_configuration_signing_keypair,
    verify_configuration_bundle,
)
from ithildin_api.nodes import (
    EnrollmentCodeIssuePayload,
    NodeEnrollmentPayload,
    NodeStore,
)
from ithildin_schemas import JsonObject, sha256_digest


def test_configuration_signing_keypair_is_distinct_private_and_loadable(
    tmp_path: Path,
) -> None:
    private_path = tmp_path / "keys" / "configuration-private.pem"
    public_path = tmp_path / "keys" / "configuration-public.pem"

    trust = generate_node_configuration_signing_keypair(private_path, public_path)
    signer = NodeConfigurationSigner.load(private_path, public_path)

    assert signer.trust == trust
    assert stat.S_IMODE(private_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_path.stat().st_mode) == 0o644
    with pytest.raises(NodeConfigurationSigningError, match="already exists"):
        generate_node_configuration_signing_keypair(private_path, public_path)
    os.chmod(private_path, 0o644)
    with pytest.raises(NodeConfigurationSigningError, match="permissions are unsafe"):
        NodeConfigurationSigner.load(private_path, public_path)
    os.chmod(private_path, 0o600)
    private_path.write_text("not a private key", encoding="utf-8")
    with pytest.raises(NodeConfigurationSigningError, match="private key is invalid"):
        NodeConfigurationSigner.load(private_path, public_path)


def test_immutable_configuration_assignment_verification_acknowledgment_and_drift(
    tmp_path: Path,
) -> None:
    node_store, configuration_store, signer, node_id = _stores(tmp_path)
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    assignment = NodeConfigurationAssignmentPayload(
        minimum_node_version="0.1.0",
        heartbeat_interval_seconds=30,
        offline_posture="deny_governed_actions",
        evidence_buffer_max_events=1000,
        validity_seconds=3600,
    )

    pending = configuration_store.assign(
        node_id=node_id,
        payload=assignment,
        signer=signer,
        policy_version="test-policy-v1",
        policy_digest="sha256:" + ("1" * 64),
        manifest_lock_digest="sha256:" + ("2" * 64),
        now=now,
    )

    assert pending.generation == 1
    with pytest.raises(NodeConfigurationConflictError, match="evidence is incomplete"):
        configuration_store.desired(node_id, now=now)
    current = configuration_store.mark_assignment_evidence_complete(node_id, 1)
    verified = verify_configuration_bundle(
        current.bundle,
        trust=signer.trust,
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        minimum_generation=1,
        expected_manifest_lock_digest="sha256:" + ("2" * 64),
        now=now,
    )
    assert verified["configuration_digest"] == current.configuration_digest
    verified_configuration = verified["configuration"]
    assert isinstance(verified_configuration, dict)
    assert verified_configuration["enforcement_status"] == "stored_not_enforced"

    acknowledgment = NodeConfigurationAcknowledgmentPayload(
        protocol_version="1",
        generation=1,
        configuration_digest=current.configuration_digest,
        status="stored_not_enforced",
    )
    configuration_store.acknowledge_pending(
        node_id=node_id,
        payload=acknowledgment,
        now=now + timedelta(seconds=1),
    )
    assert node_store.get(node_id).summary()["configuration_state"] == "evidence_incomplete"
    node_store.mark_node_evidence_complete(node_id)
    assert (
        node_store.get(node_id).summary()["configuration_state"]
        == "stored_current_not_enforced"
    )

    second = configuration_store.assign(
        node_id=node_id,
        payload=assignment,
        signer=signer,
        policy_version="test-policy-v2",
        policy_digest="sha256:" + ("3" * 64),
        manifest_lock_digest="sha256:" + ("2" * 64),
        now=now + timedelta(seconds=2),
    )
    assert second.generation == 2
    configuration_store.mark_assignment_evidence_complete(node_id, 2)
    assert node_store.get(node_id).summary()["configuration_state"] == "configuration_drift"


def test_configuration_verification_rejects_target_tamper_expiry_and_manifest_drift(
    tmp_path: Path,
) -> None:
    _, configuration_store, signer, node_id = _stores(tmp_path)
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    record = configuration_store.assign(
        node_id=node_id,
        payload=NodeConfigurationAssignmentPayload(minimum_node_version="0.1.0"),
        signer=signer,
        policy_version="test-policy-v1",
        policy_digest="sha256:" + ("4" * 64),
        manifest_lock_digest="sha256:" + ("5" * 64),
        now=now,
    )
    configuration_store.mark_assignment_evidence_complete(node_id, 1)

    for overrides, reason in (
        ({"node_id": "node_" + ("f" * 32)}, "invalid configuration signature"),
        ({"configuration_digest": "sha256:" + ("0" * 64)}, "invalid configuration signature"),
    ):
        tampered: JsonObject = {**record.bundle, **overrides}
        with pytest.raises(NodeConfigurationVerificationError, match=reason):
            _verify(tampered, signer, node_id, now)
    with pytest.raises(NodeConfigurationVerificationError, match="manifest-lock digest mismatch"):
        verify_configuration_bundle(
            record.bundle,
            trust=signer.trust,
            node_id=node_id,
            principal_id=f"agent:node.{node_id}",
            workspace_id="default",
            minimum_generation=1,
            expected_manifest_lock_digest="sha256:" + ("6" * 64),
            now=now,
        )
    with pytest.raises(NodeConfigurationVerificationError, match="expired"):
        _verify(record.bundle, signer, node_id, now + timedelta(hours=2))
    unsigned = {key: value for key, value in record.bundle.items() if key != "signature"}
    signed_configuration = unsigned["configuration"]
    assert isinstance(signed_configuration, dict)
    signed_configuration["unexpected_power"] = True
    unsigned["configuration_digest"] = sha256_digest(signed_configuration)
    with pytest.raises(NodeConfigurationVerificationError, match="payload is invalid"):
        _verify(signer.sign(unsigned), signer, node_id, now)


def test_manual_rollback_creates_fresh_signed_generation_and_checks_current_state(
    tmp_path: Path,
) -> None:
    node_store, configuration_store, signer, node_id = _stores(tmp_path)
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    first = configuration_store.assign(
        node_id=node_id,
        payload=NodeConfigurationAssignmentPayload(minimum_node_version="0.1.0"),
        signer=signer,
        policy_version="test-policy-v1",
        policy_digest="sha256:" + ("1" * 64),
        manifest_lock_digest="sha256:" + ("2" * 64),
        now=now,
    )
    configuration_store.mark_assignment_evidence_complete(node_id, first.generation)
    second = configuration_store.assign(
        node_id=node_id,
        payload=NodeConfigurationAssignmentPayload(minimum_node_version="0.2.0"),
        signer=signer,
        policy_version="test-policy-v2",
        policy_digest="sha256:" + ("3" * 64),
        manifest_lock_digest="sha256:" + ("2" * 64),
        now=now + timedelta(seconds=1),
    )
    configuration_store.mark_assignment_evidence_complete(node_id, second.generation)

    rollback = configuration_store.rollback(
        node_id=node_id,
        payload=NodeConfigurationRollbackPayload(
            source_generation=1,
            expected_current_generation=2,
        ),
        signer=signer,
        now=now + timedelta(seconds=2),
    )

    assert rollback.generation == 3
    assert rollback.assignment_kind == "manual_rollback"
    assert rollback.rollback_source_generation == 1
    assert rollback.configuration_id != first.configuration_id
    assert rollback.bundle["signature"] != first.bundle["signature"]
    assert rollback.configuration_digest == first.configuration_digest
    assert rollback.bundle["configuration"] == first.bundle["configuration"]
    with pytest.raises(NodeConfigurationConflictError, match="evidence is incomplete"):
        configuration_store.desired(node_id, now=now + timedelta(seconds=2))
    configuration_store.mark_assignment_evidence_complete(node_id, rollback.generation)
    assert node_store.get(node_id).summary()["configuration_state"] == "awaiting_node_storage"
    history = configuration_store.list(node_id)
    assert [record.generation for record in history] == [3, 2, 1]
    verify_configuration_bundle(
        rollback.bundle,
        trust=signer.trust,
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        minimum_generation=3,
        expected_manifest_lock_digest="sha256:" + ("2" * 64),
        now=now + timedelta(seconds=2),
    )
    with pytest.raises(NodeConfigurationVerificationError, match="generation regressed"):
        verify_configuration_bundle(
            first.bundle,
            trust=signer.trust,
            node_id=node_id,
            principal_id=f"agent:node.{node_id}",
            workspace_id="default",
            minimum_generation=3,
            expected_manifest_lock_digest="sha256:" + ("2" * 64),
            now=now + timedelta(seconds=2),
        )

    restarted_store = NodeConfigurationStore(configuration_store.db_path)
    restarted_store.initialize()
    restarted = restarted_store.desired(node_id, now=now + timedelta(seconds=2))
    assert restarted.generation == 3
    assert restarted.rollback_source_generation == 1

    with pytest.raises(NodeConfigurationConflictError, match="desired configuration changed"):
        configuration_store.rollback(
            node_id=node_id,
            payload=NodeConfigurationRollbackPayload(
                source_generation=1,
                expected_current_generation=2,
            ),
            signer=signer,
            now=now + timedelta(seconds=3),
        )

    node_store.revoke(node_id, now=now + timedelta(seconds=4))
    node_store.mark_node_evidence_complete(node_id)
    with pytest.raises(NodeConfigurationConflictError, match="Node is revoked"):
        restarted_store.rollback(
            node_id=node_id,
            payload=NodeConfigurationRollbackPayload(
                source_generation=1,
                expected_current_generation=3,
            ),
            signer=signer,
            now=now + timedelta(seconds=5),
        )


def _stores(
    tmp_path: Path,
) -> tuple[NodeStore, NodeConfigurationStore, NodeConfigurationSigner, str]:
    db_path = tmp_path / "ithildin.sqlite3"
    node_store = NodeStore(db_path)
    node_store.initialize()
    configuration_store = NodeConfigurationStore(db_path)
    configuration_store.initialize()
    private_path = tmp_path / "keys" / "config-private.pem"
    public_path = tmp_path / "keys" / "config-public.pem"
    generate_node_configuration_signing_keypair(private_path, public_path)
    signer = NodeConfigurationSigner.load(private_path, public_path)
    issued = node_store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(workspace_id="default", display_name="Node"),
        expires_in_seconds=600,
    )
    node_store.mark_enrollment_code_evidence_complete(issued.code_id)
    node_private = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        node_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    node = node_store.enroll(
        NodeEnrollmentPayload(
            enrollment_code=issued.enrollment_code,
            public_key=public_key,
            protocol_version="1",
            node_version="0.1.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
        )
    )
    node_store.mark_node_evidence_complete(node.node_id)
    return node_store, configuration_store, signer, node.node_id


def _verify(
    bundle: JsonObject,
    signer: NodeConfigurationSigner,
    node_id: str,
    now: datetime,
) -> None:
    verify_configuration_bundle(
        json.loads(json.dumps(bundle)),
        trust=signer.trust,
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        minimum_generation=1,
        expected_manifest_lock_digest="sha256:" + ("5" * 64),
        now=now,
    )
