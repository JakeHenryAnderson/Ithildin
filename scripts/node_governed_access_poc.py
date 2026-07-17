"""Exercise bounded Node-governed reads against a restartable local Gateway."""

from __future__ import annotations

import argparse
import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.nodes import canonical_signature_message
from ithildin_node.client import NodeClient, NodeClientError, NodeState, StoredNodeConfiguration
from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest

REPLAY_NONCE = "a7" * 16


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before-restart", "partition", "after-restart"))
    parser.add_argument("--api-url", default="http://127.0.0.1:8013")
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    (root / "client").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    if args.phase == "before-restart":
        _before_restart(args.api_url, args.admin_token, root)
    elif args.phase == "partition":
        _partition(args.api_url, root)
    else:
        _after_restart(args.api_url, args.admin_token, root)
    return 0


def _before_restart(api_url: str, token: str, root: Path) -> None:
    issued = _request(
        api_url,
        "/nodes/enrollment-codes",
        token,
        {"workspace_id": "default", "display_name": "Hermes governed-access POC"},
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
    assigned = _request(
        api_url,
        f"/nodes/{state.node_id}/configurations",
        token,
        {
            "minimum_node_version": "0.1.0",
            "heartbeat_interval_seconds": 30,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
        },
    )
    _write(root / "evidence/assignment.json", _configuration_summary(assigned))
    configuration = client.pull_configuration(state, known_generation=0)
    configuration.write_atomic(root / "client/current-configuration.json")
    acknowledgment = client.acknowledge_configuration(state, configuration)
    _write(root / "evidence/acknowledgment.json", acknowledgment)
    heartbeat = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        configuration_digest=configuration.configuration_digest,
        mission_id="mission-node-governed-access-poc",
    )
    _write(root / "evidence/heartbeat.json", heartbeat)
    governed = client.governed_tool_call(
        state,
        configuration,
        node_version="0.1.0",
        session_id="hermes-read-before-restart",
        tool_name="fs.read",
        arguments={"path": "demo/README.md"},
        nonce=REPLAY_NONCE,
    )
    _write(root / "evidence/governed-read-before-restart.json", _result_summary(governed))
    network = client.governed_tool_call(
        state,
        configuration,
        node_version="0.1.0",
        session_id="hermes-network-denial",
        tool_name="http.fetch",
        arguments={"url": "https://example.com"},
        nonce="a8" * 16,
    )
    _write(root / "evidence/network-denial.json", _result_summary(network))
    cross_workspace_payload: JsonObject = {
        "protocol_version": "1",
        "configuration_generation": configuration.generation,
        "configuration_digest": configuration.configuration_digest,
        "node_version": "0.1.0",
        "session_id": "hermes-cross-workspace-denial",
        "tool_name": "fs.read",
        "arguments": {"path": "README.md", "workspace_id": "demo"},
    }
    cross_workspace = _signed_request(
        api_url,
        state,
        f"/nodes/{state.node_id}/governed-tool-calls",
        cross_workspace_payload,
        nonce="a9" * 16,
    )
    _write(
        root / "evidence/cross-workspace-denial.json",
        _result_summary(cross_workspace),
    )


def _partition(api_url: str, root: Path) -> None:
    state = NodeState.load(root / "client/state.json")
    configuration = StoredNodeConfiguration.load(root / "client/current-configuration.json")
    try:
        NodeClient(api_url, timeout_seconds=0.25).governed_tool_call(
            state,
            configuration,
            node_version="0.1.0",
            session_id="hermes-partition-denial",
            tool_name="fs.read",
            arguments={"path": "demo/README.md"},
            nonce="aa" * 16,
        )
    except NodeClientError as exc:
        outcome: JsonObject = {
            "status": "failed_closed",
            "error_category": str(exc),
            "local_execution_used": False,
            "buffered_or_queued": False,
            "automatic_retry_used": False,
        }
    else:
        outcome = {"status": "unexpectedly_accepted"}
    _write(root / "evidence/partition-result.json", outcome)


def _after_restart(api_url: str, token: str, root: Path) -> None:
    state = NodeState.load(root / "client/state.json")
    configuration = StoredNodeConfiguration.load(root / "client/current-configuration.json")
    client = NodeClient(api_url)
    try:
        client.governed_tool_call(
            state,
            configuration,
            node_version="0.1.0",
            session_id="hermes-read-before-restart",
            tool_name="fs.read",
            arguments={"path": "demo/README.md"},
            nonce=REPLAY_NONCE,
        )
    except NodeClientError:
        replay: JsonObject = {"replay_after_gateway_restart": "denied"}
    else:
        replay = {"replay_after_gateway_restart": "accepted"}
    _write(root / "evidence/replay-after-restart.json", replay)
    fresh = client.governed_tool_call(
        state,
        configuration,
        node_version="0.1.0",
        session_id="hermes-read-after-restart",
        tool_name="fs.read",
        arguments={"path": "demo/README.md"},
        nonce="ab" * 16,
    )
    _write(root / "evidence/governed-read-after-restart.json", _result_summary(fresh))
    verification = _request(api_url, "/audit-events/verify", token)
    _write(root / "evidence/audit-verification.json", verification)
    inventory = _request(api_url, f"/nodes/{state.node_id}", token)
    _write(root / "evidence/final-node-posture.json", inventory)
    query = urllib.parse.urlencode(
        {
            "limit": 25,
            "principal_id": state.principal_id,
            "workspace_id": state.workspace_id,
        }
    )
    listed = _request(api_url, f"/runs?{query}", token)
    runs = listed.get("runs")
    if not isinstance(runs, list):
        raise RuntimeError("Gateway run response is invalid")
    correlated: list[JsonObject] = []
    for item in runs:
        if not isinstance(item, dict):
            raise RuntimeError("Gateway run record is invalid")
        run_id = _required(item, "run_id")
        exported = _request(api_url, f"/runs/{run_id}/evidence-export", token)
        exported_run = exported.get("run")
        if not isinstance(exported_run, dict):
            raise RuntimeError("Gateway run evidence response is invalid")
        correlated.append(
            {
                "run_id": run_id,
                "session_id": item.get("session_id"),
                "metadata": _run_origin_summary(item.get("metadata")),
                "export_origin": _run_origin_summary(exported_run.get("origin")),
            }
        )
    summary = listed.get("summary")
    returned = summary.get("returned") if isinstance(summary, dict) else None
    _write(
        root / "evidence/governed-run-correlation.json",
        {
            "principal_id": state.principal_id,
            "workspace_id": state.workspace_id,
            "returned": returned,
            "runs": cast(list[JsonValue], correlated),
        },
    )


def _signed_request(
    api_url: str,
    state: NodeState,
    path: str,
    payload: JsonObject,
    *,
    nonce: str,
) -> JsonObject:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(payload),
    )
    private_key = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(state.private_key, validate=True)
    )
    return _request_raw(
        api_url,
        path,
        payload,
        headers={
            "X-Ithildin-Node": state.node_id,
            "X-Ithildin-Timestamp": timestamp,
            "X-Ithildin-Nonce": nonce,
            "X-Ithildin-Signature": base64.b64encode(private_key.sign(message)).decode(),
        },
    )


def _request(
    api_url: str,
    path: str,
    token: str,
    payload: JsonObject | None = None,
) -> JsonObject:
    headers = {"Authorization": f"Bearer {token}"}
    if payload is None:
        return _request_raw(api_url, path, None, headers=headers)
    return _request_raw(api_url, path, payload, headers=headers)


def _request_raw(
    api_url: str,
    path: str,
    payload: JsonObject | None,
    *,
    headers: dict[str, str],
) -> JsonObject:
    data = None
    method = "GET"
    if payload is not None:
        data = canonical_json(payload).encode()
        method = "POST"
        headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(
        f"{api_url}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            document = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gateway request failed with HTTP {exc.code}: {path}") from exc
    if not isinstance(document, dict):
        raise RuntimeError("Gateway response is invalid")
    return cast(JsonObject, document)


def _result_summary(document: JsonObject) -> JsonObject:
    return {
        "status": document.get("status"),
        "request_id": document.get("request_id"),
        "tool_name": document.get("tool_name"),
        "is_error": document.get("is_error"),
        "identity_source": document.get("identity_source"),
        "workspace_id": document.get("workspace_id"),
        "configuration_generation": document.get("configuration_generation"),
        "configuration_digest": document.get("configuration_digest"),
        "offline_fallback_used": document.get("offline_fallback_used"),
        "redacted_content_digest": sha256_digest(document.get("content")),
    }


def _configuration_summary(document: JsonObject) -> JsonObject:
    return {
        "configuration_id": document.get("configuration_id"),
        "generation": document.get("generation"),
        "configuration_digest": document.get("configuration_digest"),
        "evidence_status": document.get("evidence_status"),
    }


def _run_origin_summary(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise RuntimeError("Gateway run origin is invalid")
    return {
        key: value.get(key)
        for key in (
            "ingress_kind",
            "identity_source",
            "node_id",
            "node_display_name",
            "authorization_profile",
            "configuration_generation",
            "configuration_digest",
            "offline_fallback_allowed",
            "runner_enforcement_proven",
        )
    }


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
