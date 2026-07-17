from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.node_configuration import (
    NodeConfigurationSigner,
    generate_node_configuration_signing_keypair,
)
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionAcknowledgmentPayload,
    NodeConfigurationTrustTransitionAssignmentPayload,
    NodeConfigurationTrustTransitionConflictError,
    NodeConfigurationTrustTransitionStore,
    NodeConfigurationTrustTransitionVerificationError,
    transition_next_trust,
    verify_configuration_trust_transition,
)
from ithildin_api.nodes import EnrollmentCodeIssuePayload, NodeEnrollmentPayload, NodeStore
from ithildin_schemas import JsonObject, sha256_digest


def test_immutable_trust_transition_assignment_verification_and_acknowledgment(
    tmp_path: Path,
) -> None:
    node_store, transition_store, current_signer, next_signer, node_id = _stores(tmp_path)
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    pending = transition_store.assign(
        node_id=node_id,
        payload=_assignment(current_signer, next_signer),
        signer=current_signer,
        now=now,
    )

    assert pending.current_key_id == current_signer.trust.key_id
    assert pending.next_key_id == next_signer.trust.key_id
    assert pending.evidence_status == "pending"
    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="incomplete"):
        transition_store.desired(node_id, now=now)

    current = transition_store.mark_assignment_evidence_complete(
        node_id, pending.transition_id
    )
    verified = verify_configuration_trust_transition(
        json.loads(json.dumps(current.bundle)),
        current_trust=current_signer.trust,
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        now=now,
    )
    assert transition_next_trust(verified) == next_signer.trust

    acknowledgment = NodeConfigurationTrustTransitionAcknowledgmentPayload(
        protocol_version="1",
        transition_id=current.transition_id,
        transition_digest=current.transition_digest,
        status="staged_not_active",
    )
    transition_store.acknowledge_pending(
        node_id=node_id,
        payload=acknowledgment,
        now=now + timedelta(seconds=1),
    )
    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="state changed"):
        transition_store.acknowledge_pending(
            node_id=node_id,
            payload=acknowledgment,
            now=now + timedelta(seconds=2),
        )
    acknowledged = transition_store.mark_acknowledgment_evidence_complete(
        node_id, current.transition_id
    )
    assert acknowledged.acknowledgment_status == "staged_not_active"
    assert acknowledged.acknowledgment_evidence_status == "complete"

    restarted = NodeConfigurationTrustTransitionStore(transition_store.db_path)
    restarted.initialize()
    assert restarted.desired(node_id, now=now).transition_id == current.transition_id


def test_trust_transition_rejects_conflicts_tamper_wrong_target_and_expiry(
    tmp_path: Path,
) -> None:
    node_store, transition_store, current_signer, next_signer, node_id = _stores(tmp_path)
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    record = transition_store.assign(
        node_id=node_id,
        payload=_assignment(current_signer, next_signer),
        signer=current_signer,
        now=now,
    )
    transition_store.mark_assignment_evidence_complete(node_id, record.transition_id)

    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="active"):
        transition_store.assign(
            node_id=node_id,
            payload=_assignment(current_signer, next_signer),
            signer=current_signer,
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="changed"):
        transition_store.assign(
            node_id=node_id,
            payload=NodeConfigurationTrustTransitionAssignmentPayload(
                expected_current_key_id=next_signer.trust.key_id,
                next_public_key=current_signer.trust.public_key,
            ),
            signer=current_signer,
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="must differ"):
        transition_store.assign(
            node_id=node_id,
            payload=NodeConfigurationTrustTransitionAssignmentPayload(
                expected_current_key_id=current_signer.trust.key_id,
                next_public_key=current_signer.trust.public_key,
            ),
            signer=current_signer,
            now=now + timedelta(days=8),
        )

    for changed, reason in (
        ({"node_id": "node_" + ("f" * 32)}, "invalid trust transition signature"),
        ({"transition_digest": sha256_digest({"tampered": True})}, "invalid trust transition"),
    ):
        tampered: JsonObject = {**record.bundle, **changed}
        with pytest.raises(NodeConfigurationTrustTransitionVerificationError, match=reason):
            _verify(tampered, current_signer, node_id, now)
    signed_extra = _resign({**record.bundle, "unexpected_power": True}, current_signer)
    with pytest.raises(NodeConfigurationTrustTransitionVerificationError, match="envelope"):
        _verify(signed_extra, current_signer, node_id, now)
    with pytest.raises(NodeConfigurationTrustTransitionVerificationError, match="node_id mismatch"):
        _verify(record.bundle, current_signer, "node_" + ("f" * 32), now)
    with pytest.raises(NodeConfigurationTrustTransitionVerificationError, match="expired"):
        _verify(record.bundle, current_signer, node_id, now + timedelta(days=2))

    node_store.revoke(node_id, now=now + timedelta(days=8))
    node_store.mark_node_evidence_complete(node_id)
    with pytest.raises(NodeConfigurationTrustTransitionConflictError, match="revoked"):
        transition_store.assign(
            node_id=node_id,
            payload=_assignment(current_signer, next_signer),
            signer=current_signer,
            now=now + timedelta(days=8, seconds=1),
        )


def _stores(
    tmp_path: Path,
) -> tuple[
    NodeStore,
    NodeConfigurationTrustTransitionStore,
    NodeConfigurationSigner,
    NodeConfigurationSigner,
    str,
]:
    db_path = tmp_path / "ithildin.sqlite3"
    node_store = NodeStore(db_path)
    node_store.initialize()
    transition_store = NodeConfigurationTrustTransitionStore(db_path)
    transition_store.initialize()
    current_signer = _signer(tmp_path, "current")
    next_signer = _signer(tmp_path, "next")
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
    return node_store, transition_store, current_signer, next_signer, node.node_id


def _signer(tmp_path: Path, name: str) -> NodeConfigurationSigner:
    private_path = tmp_path / "keys" / f"{name}-private.pem"
    public_path = tmp_path / "keys" / f"{name}-public.pem"
    generate_node_configuration_signing_keypair(private_path, public_path)
    return NodeConfigurationSigner.load(private_path, public_path)


def _assignment(
    current_signer: NodeConfigurationSigner,
    next_signer: NodeConfigurationSigner,
) -> NodeConfigurationTrustTransitionAssignmentPayload:
    return NodeConfigurationTrustTransitionAssignmentPayload(
        expected_current_key_id=current_signer.trust.key_id,
        next_public_key=next_signer.trust.public_key,
        validity_seconds=86_400,
    )


def _verify(
    bundle: JsonObject,
    signer: NodeConfigurationSigner,
    node_id: str,
    now: datetime,
) -> None:
    verify_configuration_trust_transition(
        json.loads(json.dumps(bundle)),
        current_trust=signer.trust,
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        now=now,
    )


def _resign(bundle: JsonObject, signer: NodeConfigurationSigner) -> JsonObject:
    unsigned = {key: value for key, value in bundle.items() if key != "signature"}
    from ithildin_api.node_configuration_trust import _signature_message

    signature = signer.private_key.sign(_signature_message(unsigned))
    return {
        **unsigned,
        "signature": {
            "algorithm": "ed25519",
            "key_id": signer.trust.key_id,
            "signature": base64.b64encode(signature).decode(),
        },
    }
