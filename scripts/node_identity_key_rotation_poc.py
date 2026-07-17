"""Exercise crash-safe Node identity-key rotation against a live local Gateway."""

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
    parser.add_argument("--api-url", default="http://127.0.0.1:8015")
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
        {"workspace_id": "default", "display_name": "Hermes identity-rotation POC"},
    )
    client = NodeClient(api_url)
    original = client.enroll(
        enrollment_code=_required(issued, "enrollment_code"),
        node_version="0.2.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    original.write_new(root / "client/state.json")
    _write(root / "evidence/enrollment-safe.json", original.safe_summary())
    staged = client.stage_identity_key_rotation(original)
    staged.write_atomic(root / "client/state.json")
    _write(root / "evidence/staged-safe.json", staged.safe_summary())

    # Deliberately do not persist the returned promoted state. This models a lost response or a
    # client exit after Gateway activation while preserving K2 in the pending mode-0600 state.
    activated = client.activate_identity_key_rotation(staged)
    _write(root / "evidence/gateway-activation-safe.json", activated.safe_summary())
    try:
        client.heartbeat(
            original,
            node_version="0.2.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
            configuration_digest="sha256:" + ("0" * 64),
        )
    except NodeClientError:
        old_key_result: JsonObject = {"retired_key_heartbeat": "denied"}
    else:
        old_key_result = {"retired_key_heartbeat": "accepted"}
    _write(root / "evidence/retired-key-result.json", old_key_result)
    _write(root / "evidence/pre-restart-inventory.json", _inventory(api_url, token, staged))


def _after_restart(api_url: str, token: str, root: Path) -> None:
    staged = NodeState.load(root / "client/state.json")
    client = NodeClient(api_url)
    recovered = client.recover_identity_key_rotation(staged)
    recovered.write_atomic(root / "client/state.json")
    _write(root / "evidence/recovered-safe.json", recovered.safe_summary())
    heartbeat = client.heartbeat(
        recovered,
        node_version="0.2.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest="sha256:" + ("0" * 64),
        mission_id="mission-node-identity-rotation-poc",
    )
    _write(root / "evidence/new-key-heartbeat.json", heartbeat)
    _write(root / "evidence/post-restart-inventory.json", _inventory(api_url, token, recovered))
    revoked = _request(api_url, f"/nodes/{recovered.node_id}/revoke", token, {})
    _write(root / "evidence/revocation.json", revoked)
    try:
        client.heartbeat(
            recovered,
            node_version="0.2.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
            configuration_digest="sha256:" + ("0" * 64),
        )
    except NodeClientError:
        result: JsonObject = {"post_revocation_heartbeat": "denied"}
    else:
        result = {"post_revocation_heartbeat": "accepted"}
    _write(root / "evidence/post-revocation-result.json", result)


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
