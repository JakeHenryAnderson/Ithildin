"""Exercise the bounded signed Node configuration POC against a live local Gateway."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path

from ithildin_api.node_configuration import (
    NodeConfigurationTrust,
    NodeConfigurationVerificationError,
    verify_configuration_bundle,
)
from ithildin_node.client import NodeClient, NodeClientError, NodeState, StoredNodeConfiguration
from ithildin_schemas import JsonObject


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before-restart", "after-restart"))
    parser.add_argument("--api-url", default="http://127.0.0.1:8012")
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_root.resolve()
    (evidence / "client").mkdir(parents=True, exist_ok=True)
    (evidence / "evidence").mkdir(parents=True, exist_ok=True)
    if args.phase == "before-restart":
        _before_restart(args.api_url, args.admin_token, evidence)
    else:
        _after_restart(args.api_url, args.admin_token, evidence)
    return 0


def _before_restart(api_url: str, token: str, root: Path) -> None:
    issued = _request(
        api_url,
        "/nodes/enrollment-codes",
        token,
        {
            "workspace_id": "default",
            "display_name": "Hermes configuration POC",
        },
    )
    client = NodeClient(api_url)
    state = client.enroll(
        enrollment_code=_required(issued, "enrollment_code"),
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    state_path = root / "client/state.json"
    state.write_new(state_path)
    _write(root / "evidence/enrollment-safe.json", state.safe_summary())

    first = _assign(api_url, token, state.node_id, heartbeat_interval=30)
    _write(root / "evidence/assignment-generation-1.json", first)
    stored = client.pull_configuration(state, known_generation=0)
    stored_path = root / "client/current-configuration.json"
    stored.write_atomic(stored_path)
    acknowledged = client.acknowledge_configuration(state, stored)
    _write(root / "evidence/generation-1-acknowledgment.json", acknowledged)
    heartbeat = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest=stored.configuration_digest,
        mission_id="mission-node-config-poc",
    )
    _write(root / "evidence/generation-1-heartbeat.json", heartbeat)

    tampered = deepcopy(stored.bundle)
    configuration = tampered.get("configuration")
    if not isinstance(configuration, dict):
        raise RuntimeError("verified configuration body is unavailable")
    configuration["heartbeat_interval_seconds"] = 31
    try:
        verify_configuration_bundle(
            tampered,
            trust=NodeConfigurationTrust(
                key_id=state.gateway_configuration_key_id,
                public_key=state.gateway_configuration_public_key,
            ),
            node_id=state.node_id,
            principal_id=state.principal_id,
            workspace_id=state.workspace_id,
            minimum_generation=0,
            expected_manifest_lock_digest=state.gateway_manifest_lock_digest,
        )
    except NodeConfigurationVerificationError:
        tamper_result: JsonObject = {"tampered_bundle_outcome": "denied"}
    else:
        tamper_result = {"tampered_bundle_outcome": "accepted"}
    _write(root / "evidence/tamper-result.json", tamper_result)

    second = _assign(api_url, token, state.node_id, heartbeat_interval=45)
    _write(root / "evidence/assignment-generation-2.json", second)
    inventory = _inventory(api_url, token, state.node_id)
    _write(root / "evidence/pre-restart-drift-inventory.json", inventory)


def _after_restart(api_url: str, token: str, root: Path) -> None:
    state = NodeState.load(root / "client/state.json")
    client = NodeClient(api_url)
    previous = StoredNodeConfiguration.load(root / "client/current-configuration.json")
    stored = client.pull_configuration(state, known_generation=previous.generation)
    stored.write_atomic(root / "client/current-configuration.json")
    acknowledged = client.acknowledge_configuration(state, stored)
    _write(root / "evidence/post-restart-generation-2-acknowledgment.json", acknowledged)
    heartbeat = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest=stored.configuration_digest,
        mission_id="mission-node-config-poc",
    )
    _write(root / "evidence/post-restart-heartbeat.json", heartbeat)
    inventory = _inventory(api_url, token, state.node_id)
    _write(root / "evidence/post-restart-current-inventory.json", inventory)
    revoked = _request(api_url, f"/nodes/{state.node_id}/revoke", token, {})
    _write(root / "evidence/revocation.json", revoked)
    try:
        client.pull_configuration(state, known_generation=stored.generation)
    except NodeClientError:
        outcome: JsonObject = {"post_revocation_configuration_retrieval": "denied"}
    else:
        outcome = {"post_revocation_configuration_retrieval": "accepted"}
    _write(root / "evidence/post-revocation-result.json", outcome)


def _assign(
    api_url: str, token: str, node_id: str, *, heartbeat_interval: int
) -> JsonObject:
    return _request(
        api_url,
        f"/nodes/{node_id}/configurations",
        token,
        {
            "minimum_node_version": "0.1.0",
            "heartbeat_interval_seconds": heartbeat_interval,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
        },
    )


def _inventory(api_url: str, token: str, node_id: str) -> JsonObject:
    response = _request(api_url, "/nodes", token)
    nodes = response.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("Node inventory is invalid")
    for node in nodes:
        if isinstance(node, dict) and node.get("node_id") == node_id:
            return node
    raise RuntimeError("POC Node is absent from inventory")


def _request(
    api_url: str,
    path: str,
    token: str,
    payload: JsonObject | None = None,
) -> JsonObject:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        method = "POST"
    request = urllib.request.Request(f"{api_url}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            document = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gateway request failed with HTTP {exc.code}: {path}") from exc
    if not isinstance(document, dict):
        raise RuntimeError("Gateway response is invalid")
    return document


def _required(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Gateway response is missing {key}")
    return value


def _write(path: Path, document: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
