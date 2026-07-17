"""Exercise operator-managed Node version posture against a live local Gateway."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from ithildin_node.client import NodeClient, NodeClientError, NodeState
from ithildin_schemas import JsonObject


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before-restart", "after-restart"))
    parser.add_argument("--api-url", default="http://127.0.0.1:8014")
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    (root / "client").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    if args.phase == "before-restart":
        _before_restart(args.api_url, args.admin_token, root)
    else:
        _after_restart(args.api_url, args.admin_token, root)
    return 0


def _before_restart(api_url: str, token: str, root: Path) -> None:
    issued = _request(
        api_url,
        "/nodes/enrollment-codes",
        token,
        {"workspace_id": "default", "display_name": "Hermes version-posture POC"},
    )
    client = NodeClient(api_url)
    state = client.enroll(
        enrollment_code=_required(issued, "enrollment_code"),
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    state.write_new(root / "client/state.json")
    _write(root / "evidence/enrollment-safe.json", state.safe_summary())

    assignment = _request(
        api_url,
        f"/nodes/{state.node_id}/configurations",
        token,
        {
            "minimum_node_version": "0.2.0",
            "heartbeat_interval_seconds": 30,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
            "validity_seconds": 86400,
        },
    )
    _write(root / "evidence/minimum-assignment.json", assignment)
    invalid_status = _request_error_status(
        api_url,
        f"/nodes/{state.node_id}/configurations",
        token,
        {"minimum_node_version": "latest"},
    )
    _write(root / "evidence/invalid-version-result.json", {"status": invalid_status})

    below = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("0" * 64),
        mission_id="mission-node-version-poc",
    )
    _write(root / "evidence/below-minimum-heartbeat.json", below)
    upgraded = client.heartbeat(
        state,
        node_version="0.2.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("0" * 64),
        mission_id="mission-node-version-poc",
    )
    _write(root / "evidence/operator-upgrade-heartbeat.json", upgraded)
    _write(root / "evidence/operator-upgrade-inventory.json", _inventory(api_url, token, state))


def _after_restart(api_url: str, token: str, root: Path) -> None:
    state = NodeState.load(root / "client/state.json")
    client = NodeClient(api_url)
    _write(root / "evidence/restart-inventory.json", _inventory(api_url, token, state))
    rolled_back = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("0" * 64),
        mission_id="mission-node-version-rollback-poc",
    )
    _write(root / "evidence/operator-rollback-heartbeat.json", rolled_back)
    _write(root / "evidence/operator-rollback-inventory.json", _inventory(api_url, token, state))
    revoked = _request(api_url, f"/nodes/{state.node_id}/revoke", token, {})
    _write(root / "evidence/revocation.json", revoked)
    try:
        client.heartbeat(
            state,
            node_version="0.3.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
            configuration_digest="sha256:" + ("0" * 64),
        )
    except NodeClientError:
        outcome: JsonObject = {"post_revocation_heartbeat": "denied"}
    else:
        outcome = {"post_revocation_heartbeat": "accepted"}
    _write(root / "evidence/post-revocation-result.json", outcome)


def _inventory(api_url: str, token: str, state: NodeState) -> JsonObject:
    return _request(api_url, f"/nodes/{state.node_id}", token)


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


def _request_error_status(api_url: str, path: str, token: str, payload: JsonObject) -> int:
    request = urllib.request.Request(
        f"{api_url}{path}",
        data=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as exc:
        return exc.code
    raise RuntimeError("Gateway unexpectedly accepted an invalid Node version")


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
