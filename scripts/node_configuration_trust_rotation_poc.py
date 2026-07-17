"""Exercise restart-based Node configuration trust rotation against a live Gateway."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from ithildin_api.node_configuration import NodeConfigurationSigner
from ithildin_node.client import NodeClient, NodeState, StoredNodeConfiguration
from ithildin_schemas import JsonObject


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("stage-k2", "activate-k2", "recover-k1"))
    parser.add_argument("--api-url", default="http://127.0.0.1:8013")
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--next-private-key", type=Path)
    parser.add_argument("--next-public-key", type=Path)
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    (root / "client").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    if args.phase == "stage-k2":
        if args.next_private_key is None or args.next_public_key is None:
            parser.error("stage-k2 requires the next signing key paths")
        next_signer = NodeConfigurationSigner.load(
            args.next_private_key.resolve(), args.next_public_key.resolve()
        )
        _stage(args.api_url, args.admin_token, root, next_signer)
    elif args.phase == "activate-k2":
        _activate(args.api_url, args.admin_token, root)
    else:
        _recover(args.api_url, args.admin_token, root)
    return 0


def _stage(api_url: str, token: str, root: Path, next_signer: NodeConfigurationSigner) -> None:
    issued = _request(
        api_url,
        "/nodes/enrollment-codes",
        token,
        {"workspace_id": "default", "display_name": "Hermes trust-rotation POC"},
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
    first = _assign(api_url, token, state.node_id, heartbeat_interval=30)
    _write(root / "evidence/k1-generation-1-assignment.json", first)
    configuration = client.pull_configuration(state, known_generation=0)
    configuration.write_atomic(root / "client/current-configuration.json")
    first_ack = client.acknowledge_configuration(state, configuration)
    _write(root / "evidence/k1-generation-1-ack.json", first_ack)
    transition = _request(
        api_url,
        f"/nodes/{state.node_id}/configuration-trust-transitions",
        token,
        {
            "expected_current_key_id": state.gateway_configuration_key_id,
            "next_public_key": next_signer.trust.public_key,
            "validity_seconds": 86_400,
        },
    )
    _write(root / "evidence/k1-transition-assignment.json", transition)
    staged = client.stage_configuration_trust(state)
    staged.state.write_atomic(state_path)
    staged_ack = client.acknowledge_configuration_trust(staged.state)
    _write(root / "evidence/k1-transition-stage-ack.json", staged_ack)
    _write(root / "evidence/k1-staged-inventory.json", _inventory(api_url, token, state.node_id))
    _write(root / "evidence/k1-staged-state-safe.json", staged.state.safe_summary())


def _activate(api_url: str, token: str, root: Path) -> None:
    state_path = root / "client/state.json"
    state = NodeState.load(state_path)
    client = NodeClient(api_url)
    second = _assign(api_url, token, state.node_id, heartbeat_interval=45)
    _write(root / "evidence/k2-generation-2-assignment.json", second)
    previous = StoredNodeConfiguration.load(root / "client/current-configuration.json")
    pulled = client.pull_configuration_with_state(
        state, known_generation=previous.generation
    )
    if not pulled.trust_promoted or pulled.verification_trust != "pending":
        raise RuntimeError("Node did not promote staged K2 trust")
    pulled.configuration.write_atomic(root / "client/current-configuration.json")
    pulled.state.write_atomic(state_path)
    acknowledgment = client.acknowledge_configuration(
        pulled.state, pulled.configuration
    )
    _write(root / "evidence/k2-generation-2-ack.json", acknowledgment)
    _write(
        root / "evidence/k2-active-inventory.json",
        _inventory(api_url, token, state.node_id),
    )
    _write(root / "evidence/k2-active-state-safe.json", pulled.state.safe_summary())


def _recover(api_url: str, token: str, root: Path) -> None:
    state_path = root / "client/state.json"
    state = NodeState.load(state_path)
    client = NodeClient(api_url)
    third = _assign(api_url, token, state.node_id, heartbeat_interval=60)
    _write(root / "evidence/k1-recovery-generation-3-assignment.json", third)
    previous = StoredNodeConfiguration.load(root / "client/current-configuration.json")
    pulled = client.pull_configuration_with_state(
        state, known_generation=previous.generation
    )
    if pulled.trust_promoted or pulled.verification_trust != "previous":
        raise RuntimeError("Node did not use bounded previous K1 recovery trust")
    if pulled.state.gateway_configuration_key_id != state.gateway_configuration_key_id:
        raise RuntimeError("Node silently demoted active configuration trust")
    pulled.configuration.write_atomic(root / "client/current-configuration.json")
    acknowledgment = client.acknowledge_configuration(state, pulled.configuration)
    _write(root / "evidence/k1-recovery-generation-3-ack.json", acknowledgment)
    _write(
        root / "evidence/k1-recovery-inventory.json",
        _inventory(api_url, token, state.node_id),
    )
    _write(root / "evidence/k1-recovery-state-safe.json", state.safe_summary())


def _assign(api_url: str, token: str, node_id: str, *, heartbeat_interval: int) -> JsonObject:
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
    response = _request(api_url, f"/nodes/{node_id}", token)
    if response.get("node_id") != node_id:
        raise RuntimeError("POC Node inventory binding is invalid")
    return response


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
