from __future__ import annotations

import base64
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ithildin_api.nodes import canonical_signature_message
from ithildin_node.client import NodeClient, NodeClientError, NodeState
from ithildin_schemas import JsonObject, sha256_digest


class RecordingNodeClient(NodeClient):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:8000")
        self.requests: list[tuple[str, JsonObject, dict[str, str]]] = []

    def _post(
        self,
        path: str,
        payload: JsonObject,
        *,
        headers: dict[str, str] | None = None,
    ) -> JsonObject:
        self.requests.append((path, payload, headers or {}))
        if path == "/nodes/enroll":
            return {
                "node_id": "node_" + ("1" * 32),
                "principal_id": "agent:node.node_" + ("1" * 32),
                "workspace_id": "default",
                "enrolled_at": "2026-07-16T12:00:00+00:00",
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
