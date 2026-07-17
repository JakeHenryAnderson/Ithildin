from __future__ import annotations

import base64
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from ithildin_api.node_configuration import (
    NodeConfigurationSigner,
    NodeConfigurationTrust,
)
from ithildin_api.nodes import (
    NodeIdentityRotationRecord,
    canonical_identity_rotation_proof_message,
    canonical_signature_message,
    node_identity_key_id,
)
from ithildin_node.client import (
    NodeClient,
    NodeClientError,
    NodeState,
    StoredNodeConfiguration,
)
from ithildin_schemas import JsonObject, canonical_json, sha256_digest


class RecordingNodeClient(NodeClient):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:8000")
        self.requests: list[tuple[str, JsonObject, dict[str, str]]] = []
        self.configuration_private_key = Ed25519PrivateKey.generate()
        self.configuration_public_key = base64.b64encode(
            self.configuration_private_key.public_key().public_bytes_raw()
        ).decode()
        self.configuration_signer = NodeConfigurationSigner(
            private_key=self.configuration_private_key,
            trust=NodeConfigurationTrust(
                key_id=sha256_digest(self.configuration_public_key),
                public_key=self.configuration_public_key,
            ),
        )
        next_private_key = Ed25519PrivateKey.generate()
        next_public_key = base64.b64encode(
            next_private_key.public_key().public_bytes_raw()
        ).decode()
        self.next_configuration_signer = NodeConfigurationSigner(
            private_key=next_private_key,
            trust=NodeConfigurationTrust(
                key_id=sha256_digest(next_public_key),
                public_key=next_public_key,
            ),
        )
        self.response_configuration_signer = self.configuration_signer
        self.enrolled_identity_public_key: str | None = None
        self.activated_identity_key_id: str | None = None
        self.identity_rotation_challenge = "challenge-value-with-at-least-forty-characters-0001"
        self.identity_rotation_id = "nkr_" + ("4" * 32)
        self.identity_rotation_expires_at = "2026-07-16T13:00:00+00:00"

    def _post(
        self,
        path: str,
        payload: JsonObject,
        *,
        headers: dict[str, str] | None = None,
    ) -> JsonObject:
        self.requests.append((path, payload, headers or {}))
        if path == "/nodes/enroll":
            self.enrolled_identity_public_key = str(payload["public_key"])
            return {
                "node_id": "node_" + ("1" * 32),
                "principal_id": "agent:node.node_" + ("1" * 32),
                "workspace_id": "default",
                "enrolled_at": "2026-07-16T12:00:00+00:00",
                "configuration_trust": {
                    "key_id": sha256_digest(self.configuration_public_key),
                    "public_key": self.configuration_public_key,
                },
                "manifest_lock_digest": "sha256:" + ("a" * 64),
            }
        if path.endswith("/identity-key-rotation/challenges"):
            assert self.enrolled_identity_public_key is not None
            return {
                "rotation_id": self.identity_rotation_id,
                "node_id": "node_" + ("1" * 32),
                "principal_id": "agent:node.node_" + ("1" * 32),
                "workspace_id": "default",
                "current_key_id": node_identity_key_id(self.enrolled_identity_public_key),
                "next_key_id": None,
                "challenge": self.identity_rotation_challenge,
                "challenge_digest": sha256_digest(self.identity_rotation_challenge),
                "created_at": "2026-07-16T12:00:00+00:00",
                "expires_at": self.identity_rotation_expires_at,
                "activated_at": None,
                "status": "pending",
                "evidence_status": "complete",
            }
        if path.endswith("/identity-key-rotation/activations"):
            assert self.enrolled_identity_public_key is not None
            next_public_key = str(payload["next_public_key"])
            next_key_id = node_identity_key_id(next_public_key)
            rotation = NodeIdentityRotationRecord(
                rotation_id=self.identity_rotation_id,
                node_id="node_" + ("1" * 32),
                principal_id="agent:node.node_" + ("1" * 32),
                workspace_id="default",
                current_key_id=node_identity_key_id(self.enrolled_identity_public_key),
                challenge_digest=sha256_digest(self.identity_rotation_challenge),
                created_at="2026-07-16T12:00:00+00:00",
                expires_at=self.identity_rotation_expires_at,
                status="pending",
                evidence_status="complete",
                next_key_id=None,
                activated_at=None,
            )
            proof = canonical_identity_rotation_proof_message(
                rotation=rotation, next_key_id=next_key_id
            )
            Ed25519PublicKey.from_public_bytes(base64.b64decode(next_public_key)).verify(
                base64.b64decode(str(payload["next_key_proof"])), proof
            )
            self.activated_identity_key_id = next_key_id
            return _identity_rotation_activated_response(
                self.identity_rotation_id,
                node_identity_key_id(self.enrolled_identity_public_key),
                next_key_id,
            )
        if path.endswith("/identity-key-rotation/status"):
            assert self.activated_identity_key_id is not None
            assert self.enrolled_identity_public_key is not None
            return _identity_rotation_activated_response(
                self.identity_rotation_id,
                node_identity_key_id(self.enrolled_identity_public_key),
                self.activated_identity_key_id,
            )
        if path.endswith("/configuration-trust-transition"):
            transition: JsonObject = {
                "schema_version": "1",
                "current_key_id": self.configuration_signer.trust.key_id,
                "next_trust": self.next_configuration_signer.trust.summary(),
                "activation_mode": "explicit_gateway_restart",
                "acknowledgment_status": "staged_not_active",
            }
            unsigned: JsonObject = {
                "signature_type": "ithildin.node_configuration_trust_transition",
                "format_version": "1",
                "transition_id": "nct_" + ("3" * 32),
                "node_id": "node_" + ("1" * 32),
                "principal_id": "agent:node.node_" + ("1" * 32),
                "workspace_id": "default",
                "issued_at": "2026-07-16T12:00:00+00:00",
                "not_before": "2026-07-16T12:00:00+00:00",
                "expires_at": "2026-07-16T13:00:00+00:00",
                "transition_digest": sha256_digest(transition),
                "transition": transition,
            }
            message = (
                "ITHILDIN-NODE-CONFIG-TRUST-V1\n" + canonical_json(unsigned)
            ).encode()
            signature = self.configuration_private_key.sign(message)
            return {
                **unsigned,
                "signature": {
                    "algorithm": "ed25519",
                    "key_id": self.configuration_signer.trust.key_id,
                    "signature": base64.b64encode(signature).decode(),
                },
            }
        if path.endswith("/configuration-trust-transition/acknowledgments"):
            return {
                "acknowledgment_status": "staged_not_active",
                "acknowledgment_evidence_status": "complete",
            }
        if path.endswith("/configuration"):
            configuration: JsonObject = {
                "schema_version": "1",
                "policy_version": "test-policy-v1",
                "policy_digest": "sha256:" + ("b" * 64),
                "manifest_lock_digest": "sha256:" + ("a" * 64),
                "minimum_node_version": "0.1.0",
                "heartbeat_interval_seconds": 30,
                "offline_posture": "deny_governed_actions",
                "evidence_buffer_max_events": 1000,
                "enforcement_status": "stored_not_enforced",
            }
            envelope: JsonObject = {
                "signature_type": "ithildin.node_configuration",
                "format_version": "1",
                "configuration_id": "ncfg_" + ("2" * 32),
                "generation": 1,
                "node_id": "node_" + ("1" * 32),
                "principal_id": "agent:node.node_" + ("1" * 32),
                "workspace_id": "default",
                "issued_at": "2026-07-16T12:00:00+00:00",
                "not_before": "2026-07-16T12:00:00+00:00",
                "expires_at": "2026-07-16T13:00:00+00:00",
                "configuration_digest": sha256_digest(configuration),
                "configuration": configuration,
            }
            return self.response_configuration_signer.sign(envelope)
        if path.endswith("/configuration/acknowledgments"):
            return {
                "configuration_state": "stored_current_not_enforced",
                "configuration_acknowledgment_status": "stored_not_enforced",
            }
        return {"status": "enrolled", "observed_state": "observed_connected"}


def test_client_enrollment_state_is_exclusive_private_and_reloadable(tmp_path: Path) -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="secret-code-that-is-never-persisted",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    state_path = tmp_path / "node" / "state.json"

    state.write_new(state_path)

    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert NodeState.load(state_path) == state
    assert "private_key" not in state.safe_summary()
    assert "secret-code-that-is-never-persisted" not in state_path.read_text(encoding="utf-8")
    with pytest.raises(NodeClientError, match="already exists"):
        state.write_new(state_path)
    os.chmod(state_path, 0o644)
    with pytest.raises(NodeClientError, match="permissions must be 0600"):
        NodeState.load(state_path)

    link_path = tmp_path / "linked-state.json"
    link_path.symlink_to(state_path)
    with pytest.raises(NodeClientError, match="unavailable"):
        NodeState.load(link_path)


def test_client_heartbeat_signature_binds_path_timestamp_nonce_and_body() -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    nonce = "a" * 32

    result = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("2" * 64),
        mission_id="mission-synthetic-001",
        now=now,
        nonce=nonce,
    )

    assert result["observed_state"] == "observed_connected"
    path, payload, headers = client.requests[-1]
    timestamp = str(int(now.timestamp()))
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(payload),
    )
    public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(state.public_key))
    public_key.verify(base64.b64decode(headers["X-Ithildin-Signature"]), message)
    assert headers["X-Ithildin-Node"] == state.node_id
    assert headers["X-Ithildin-Timestamp"] == timestamp
    assert headers["X-Ithildin-Nonce"] == nonce


def test_client_verifies_stores_and_acknowledges_configuration(tmp_path: Path) -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    now = datetime(2026, 7, 16, 12, 5, tzinfo=UTC)

    configuration = client.pull_configuration(state, known_generation=0, now=now)
    output = tmp_path / "configuration" / "current.json"
    configuration.write_atomic(output)
    acknowledged = client.acknowledge_configuration(state, configuration, now=now)

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert StoredNodeConfiguration.load(output) == configuration
    assert configuration.safe_summary()["status"] == "stored_not_enforced"
    assert configuration.safe_summary()["enforcement_proven"] is False
    assert acknowledged["configuration_state"] == "stored_current_not_enforced"
    assert client.requests[-2][0].endswith("/configuration")
    assert client.requests[-1][0].endswith("/configuration/acknowledgments")


def test_client_stages_promotes_and_retains_bounded_previous_trust(tmp_path: Path) -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    now = datetime(2026, 7, 16, 12, 5, tzinfo=UTC)
    staged = client.stage_configuration_trust(state, now=now, nonce="c" * 32)
    state_path = tmp_path / "node" / "state.json"
    state.write_new(state_path)
    staged.state.write_atomic(state_path)
    reloaded = NodeState.load(state_path)

    assert reloaded.pending_configuration_key_id == client.next_configuration_signer.trust.key_id
    acknowledgment = client.acknowledge_configuration_trust(
        reloaded, now=now, nonce="d" * 32
    )
    assert acknowledgment["acknowledgment_status"] == "staged_not_active"

    client.response_configuration_signer = client.next_configuration_signer
    promoted = client.pull_configuration_with_state(
        reloaded, known_generation=0, now=now, nonce="e" * 32
    )
    assert promoted.trust_promoted is True
    assert promoted.verification_trust == "pending"
    assert (
        promoted.state.gateway_configuration_key_id
        == client.next_configuration_signer.trust.key_id
    )
    assert (
        promoted.state.previous_configuration_key_id
        == client.configuration_signer.trust.key_id
    )

    client.response_configuration_signer = client.configuration_signer
    recovered = client.pull_configuration_with_state(
        promoted.state, known_generation=0, now=now, nonce="f" * 32
    )
    assert recovered.verification_trust == "previous"
    assert recovered.trust_promoted is False
    assert (
        recovered.state.gateway_configuration_key_id
        == promoted.state.gateway_configuration_key_id
    )
    client.acknowledge_configuration(
        recovered.state, recovered.configuration, now=now, nonce="2" * 32
    )
    recovery_ack = client.requests[-1][1]
    assert recovery_ack["configuration_signing_key_id"] == client.configuration_signer.trust.key_id
    assert (
        recovery_ack["active_configuration_signing_key_id"]
        == client.next_configuration_signer.trust.key_id
    )
    with pytest.raises(NodeClientError, match="previous configuration trust expired"):
        client.pull_configuration_with_state(
            promoted.state,
            known_generation=0,
            now=datetime(2026, 7, 16, 13, 0, tzinfo=UTC),
            nonce="1" * 32,
        )


def test_client_identity_rotation_persists_pending_then_promotes_atomically(
    tmp_path: Path,
) -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    original_key_id = node_identity_key_id(state.public_key)
    state_path = tmp_path / "node" / "state.json"
    state.write_new(state_path)
    staged = client.stage_identity_key_rotation(
        state,
        now=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
        nonce="5" * 32,
    )
    staged.write_atomic(state_path)
    reloaded = NodeState.load(state_path)

    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert reloaded.pending_identity_rotation_id == client.identity_rotation_id
    assert reloaded.pending_identity_private_key is not None
    assert "pending_identity_private_key" not in reloaded.safe_summary()
    assert reloaded.safe_summary()["active_identity_key_id"] == original_key_id

    rotated = client.activate_identity_key_rotation(
        reloaded,
        now=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
        nonce="6" * 32,
    )
    rotated.write_atomic(state_path)
    final = NodeState.load(state_path)
    assert final.pending_identity_rotation_id is None
    assert final.pending_identity_private_key is None
    assert node_identity_key_id(final.public_key) != original_key_id
    assert final.safe_summary()["active_identity_key_id"] == client.activated_identity_key_id


def test_client_identity_rotation_recovers_after_gateway_activation_response_loss() -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    staged = client.stage_identity_key_rotation(
        state,
        now=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
        nonce="7" * 32,
    )
    assert staged.pending_identity_public_key is not None
    client.activated_identity_key_id = node_identity_key_id(
        staged.pending_identity_public_key
    )

    recovered = client.recover_identity_key_rotation(
        staged,
        now=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
        nonce="8" * 32,
    )

    assert recovered.pending_identity_rotation_id is None
    path, payload, headers = client.requests[-1]
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=headers["X-Ithildin-Timestamp"],
        nonce=headers["X-Ithildin-Nonce"],
        body_hash=sha256_digest(payload),
    )
    Ed25519PublicKey.from_public_bytes(base64.b64decode(recovered.public_key)).verify(
        base64.b64decode(headers["X-Ithildin-Signature"]), message
    )


def test_client_replaces_expired_pending_key_only_after_k1_challenge_succeeds() -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    staged = client.stage_identity_key_rotation(
        state,
        now=datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
        nonce="9" * 32,
    )
    previous_pending_key = staged.pending_identity_public_key

    refreshed = client.replace_expired_identity_key_rotation(
        staged,
        now=datetime(2026, 7, 16, 13, 1, tzinfo=UTC),
        nonce="a" * 32,
    )

    assert refreshed.pending_identity_public_key != previous_pending_key
    assert refreshed.public_key == state.public_key
    with pytest.raises(NodeClientError, match="is not expired"):
        client.replace_expired_identity_key_rotation(
            refreshed,
            now=datetime(2026, 7, 16, 12, 59, tzinfo=UTC),
            nonce="b" * 32,
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://example.com:8000",
        "http://user:password@127.0.0.1:8000",
        "http://127.0.0.1:8000/api",
    ],
)
def test_client_rejects_non_local_preview_api_urls(url: str) -> None:
    with pytest.raises(NodeClientError, match="Node API URL"):
        NodeClient(url)


def _identity_rotation_activated_response(
    rotation_id: str, current_key_id: str, key_id: str
) -> JsonObject:
    return {
        "rotation_id": rotation_id,
        "node_id": "node_" + ("1" * 32),
        "principal_id": "agent:node.node_" + ("1" * 32),
        "workspace_id": "default",
        "current_key_id": current_key_id,
        "next_key_id": key_id,
        "created_at": "2026-07-16T12:00:00+00:00",
        "expires_at": "2026-07-16T13:00:00+00:00",
        "activated_at": "2026-07-16T12:05:00+00:00",
        "status": "activated",
        "evidence_status": "complete",
        "active_identity_key_id": key_id,
    }
