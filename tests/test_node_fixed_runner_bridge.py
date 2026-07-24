from __future__ import annotations

import hashlib
import json
import socket
import stat
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from ithildin_node import fixed_runner_bridge as bridge_module
from ithildin_node.client import NodeClientError, NodeState, StoredNodeConfiguration
from ithildin_node.fixed_runner_bridge import (
    FIXED_PROFILE_DIGEST,
    BridgeReceipt,
    FixedMissionSession,
    FixedRunnerBridgeError,
    run_fixed_mission_cycle,
)
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from test_node_client import RecordingNodeClient


class MissionRecordingNodeClient(RecordingNodeClient):
    def governed_tool_call(
        self,
        state: NodeState,
        configuration: StoredNodeConfiguration,
        *,
        node_version: str,
        session_id: str,
        tool_name: str,
        arguments: JsonObject,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        return super().governed_tool_call(
            state,
            configuration,
            node_version=node_version,
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            now=now or datetime(2026, 7, 16, 12, 5, tzinfo=UTC),
            nonce=nonce,
        )


def _prepared(tmp_path: Path) -> tuple[FixedMissionSession, MissionRecordingNodeClient]:
    client = MissionRecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes_fixed_node_bridge",
        deployment_topology="docker_sidecar",
    )
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    configuration = client.pull_configuration(state, known_generation=0, now=now)
    envelope = client.claim_mission(state, now=now, nonce="91" * 16)
    assert envelope is not None
    session = FixedMissionSession.prepare(
        client=client,
        state=state,
        configuration=configuration,
        node_version="0.1.0",
        profile_digest=FIXED_PROFILE_DIGEST,
        receipt_path=tmp_path / "mission-receipt.json",
        envelope=envelope,
        handoff_nonce="8" * 64,
    )
    session.report_running()
    return session, client


def _request(session: FixedMissionSession, affordance: str) -> JsonObject:
    handoff = session.handoff_document()
    return {
        "protocol_version": "1",
        "affordance": affordance,
        "mission_id": handoff["mission_id"],
        "claim_id": handoff["claim_id"],
        "envelope_digest": handoff["envelope_digest"],
        "handoff_nonce": handoff["handoff_nonce"],
        "operation_index": handoff["next_operation_index"],
        "profile_digest": handoff["profile_digest"],
    }


def test_fixed_session_runs_only_two_envelope_operations_then_reports_completion(
    tmp_path: Path,
) -> None:
    session, client = _prepared(tmp_path)

    first = session.handle_request(_request(session, "mission.step.1"))
    second = session.handle_request(_request(session, "mission.step.2"))
    completed = session.handle_request(_request(session, "mission.complete"))

    assert first["tool_name"] == "project.structure.summary"
    assert second["tool_name"] == "project.test.summary"
    assert completed["status"] == "runner_reported_succeeded"
    assert session.terminal is True
    assert session.receipt.next_operation_index == 4
    assert session.receipt.last_closed_status == "runner_reported_succeeded"
    receipt_text = session.receipt_path.read_text(encoding="utf-8")
    assert stat.S_IMODE(session.receipt_path.stat().st_mode) == 0o600
    assert "88888888" not in receipt_text
    assert "README.md" not in receipt_text
    assert set(BridgeReceipt.load(session.receipt_path).document()) == {
        "mission_id",
        "claim_id",
        "envelope_digest",
        "next_operation_index",
        "handoff_nonce_digest",
        "last_closed_status",
    }
    mission_requests = [
        (path.rsplit("/", 1)[-1], payload)
        for path, payload, _headers in client.requests
        if "/mission-" in path or path.endswith("/governed-tool-calls")
    ]
    assert [name for name, _payload in mission_requests] == [
        "mission-claims",
        "mission-reports",
        "mission-control",
        "governed-tool-calls",
        "mission-control",
        "governed-tool-calls",
        "mission-control",
        "mission-reports",
    ]
    governed = [
        payload for name, payload in mission_requests if name == "governed-tool-calls"
    ]
    assert [payload["tool_name"] for payload in governed] == [
        "project.structure.summary",
        "project.test.summary",
    ]
    expected_session = (
        f"mission:{session.receipt.mission_id}:{session.receipt.claim_id}:"
        f"{session.receipt.envelope_digest.removeprefix('sha256:')[:16]}"
    )
    assert all(payload["session_id"] == expected_session for payload in governed)
    with pytest.raises(FixedRunnerBridgeError, match="mission_already_closed"):
        session.handle_request(_request(session, "mission.complete"))


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ({"affordance": "mission.step.2"}, "operation_order_conflict"),
        ({"claim_id": "mclaim_" + ("f" * 32)}, "request_binding_conflict"),
        ({"profile_digest": "sha256:" + ("f" * 64)}, "request_binding_conflict"),
        ({"operation_index": 2}, "request_binding_conflict"),
        ({"unknown": "value"}, "request_shape_invalid"),
    ],
)
def test_fixed_session_denies_reordered_cross_bound_profile_drift_and_unknown_fields(
    tmp_path: Path,
    mutation: JsonObject,
    reason: str,
) -> None:
    session, _client = _prepared(tmp_path)
    request = {**_request(session, "mission.step.1"), **mutation}
    with pytest.raises(FixedRunnerBridgeError, match=reason):
        session.handle_request(request)
    assert session.receipt.next_operation_index == 1


def test_fixed_session_restart_receipt_blocks_new_handoff(tmp_path: Path) -> None:
    session, client = _prepared(tmp_path)
    envelope = client.claim_mission(session.state)
    assert envelope is not None
    with pytest.raises(FixedRunnerBridgeError, match="restart_ambiguity"):
        FixedMissionSession.prepare(
            client=client,
            state=session.state,
            configuration=session.configuration,
            node_version="0.1.0",
            profile_digest=FIXED_PROFILE_DIGEST,
            receipt_path=session.receipt_path,
            envelope=envelope,
        )


@pytest.mark.parametrize(
    "closed_status",
    ["prepared", "runner_reported_succeeded", "failed_closed"],
)
def test_existing_receipt_blocks_before_gateway_claim(
    tmp_path: Path,
    closed_status: str,
) -> None:
    session, client = _prepared(tmp_path)
    session.receipt = session.receipt.close(
        session.receipt_path,
        status=closed_status,
    )
    claim_count = sum(
        path.endswith("/mission-claims") for path, _payload, _headers in client.requests
    )

    with pytest.raises(FixedRunnerBridgeError, match="restart_ambiguity"):
        run_fixed_mission_cycle(
            client=client,
            state=session.state,
            configuration=session.configuration,
            node_version="0.1.0",
            socket_path=tmp_path / "socket" / "mission.sock",
            receipt_path=session.receipt_path,
        )

    assert (
        sum(path.endswith("/mission-claims") for path, _payload, _headers in client.requests)
        == claim_count
    )


def test_receipt_parent_and_leaf_ownership_or_mode_ambiguity_blocks_preclaim(
    tmp_path: Path,
) -> None:
    session, client = _prepared(tmp_path)
    session.receipt_path.chmod(0o640)
    claim_count = sum(
        path.endswith("/mission-claims") for path, _payload, _headers in client.requests
    )

    with pytest.raises(FixedRunnerBridgeError, match="restart_ambiguity"):
        run_fixed_mission_cycle(
            client=client,
            state=session.state,
            configuration=session.configuration,
            node_version="0.1.0",
            socket_path=tmp_path / "socket" / "mission.sock",
            receipt_path=session.receipt_path,
        )

    assert (
        sum(path.endswith("/mission-claims") for path, _payload, _headers in client.requests)
        == claim_count
    )


def test_fixed_session_gateway_ambiguity_closes_without_operation_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session, client = _prepared(tmp_path)

    def unavailable(*_args: object, **_kwargs: object) -> JsonObject:
        raise NodeClientError("Gateway is unavailable")

    monkeypatch.setattr(client, "governed_tool_call", unavailable)
    with pytest.raises(FixedRunnerBridgeError, match="gateway_ambiguity"):
        session.handle_request(_request(session, "mission.step.1"))
    assert session.receipt.last_closed_status == "failed_closed"
    assert session.receipt.next_operation_index == 1


def test_fixed_session_cancel_observation_does_not_claim_runner_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session, client = _prepared(tmp_path)
    original_post = client._post

    def canceling_post(
        path: str,
        payload: JsonObject,
        *,
        headers: dict[str, str] | None = None,
    ) -> JsonObject:
        if path.endswith("/mission-control"):
            return {"control_decision": "cancel_requested", "decision_revision": 4}
        return original_post(path, payload, headers=headers)

    monkeypatch.setattr(client, "_post", canceling_post)
    with pytest.raises(FixedRunnerBridgeError, match="cancel_requested"):
        session.handle_request(_request(session, "mission.step.1"))
    assert session.receipt.last_closed_status == "cancel_observed"
    reports = [
        payload
        for path, payload, _headers in client.requests
        if path.endswith("/mission-reports")
    ]
    assert reports[-1]["report_kind"] == "cancel_observed"
    assert all(payload["report_kind"] != "runner_canceled" for payload in reports)


def test_canonical_frame_rejects_duplicate_reordered_and_oversized_input() -> None:
    left, right = socket.socketpair()
    try:
        right.sendall(b'{"a":1,"a":1}\n')
        with pytest.raises(FixedRunnerBridgeError, match="frame_invalid"):
            bridge_module._receive_frame(left)
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair()
    try:
        right.sendall(b'{"z":1,"a":2}\n')
        with pytest.raises(FixedRunnerBridgeError, match="frame_not_canonical"):
            bridge_module._receive_frame(left)
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair()
    try:
        sender = threading.Thread(
            target=right.sendall,
            args=(b"x" * (bridge_module.MAX_FRAME_BYTES + 1),),
            daemon=True,
        )
        sender.start()
        with pytest.raises(FixedRunnerBridgeError, match="frame_too_large"):
            bridge_module._receive_frame(left)
        sender.join(timeout=1)
    finally:
        left.close()
        right.close()


def test_profile_digest_matches_immutable_profile_document() -> None:
    profile_path = Path("deploy/hermes-node-bridge/profile.json")
    document = json.loads(profile_path.read_text(encoding="utf-8"))
    assert FIXED_PROFILE_DIGEST == sha256_digest(document)
    assert canonical_json(document).encode("utf-8")
    config_path = Path("deploy/hermes-node-bridge/config.yaml")
    assert document["hermes_config_digest"] == (
        "sha256:" + hashlib.sha256(config_path.read_bytes()).hexdigest()
    )


def test_operator_profile_fixes_runner_without_lifecycle_or_host_control() -> None:
    base = yaml.safe_load(Path("deploy/docker-compose.yml").read_text(encoding="utf-8"))
    compose = yaml.safe_load(
        Path("deploy/hermes-node-bridge/compose.yaml").read_text(encoding="utf-8")
    )
    assert base["name"] == "ithildin-demo"
    assert "ithildin-api" in base["services"]
    assert base["services"]["ithildin-node"]["user"] == "10002:10002"
    assert "ithildin-node-state" in base["volumes"]
    node = compose["services"]["ithildin-node"]
    runner = compose["services"]["hermes"]
    assert runner["build"] == {
        "context": "..",
        "dockerfile": "deploy/hermes-node-bridge/Dockerfile",
    }
    merged_context = (
        Path("deploy/docker-compose.yml").parent / runner["build"]["context"]
    ).resolve()
    assert merged_context == Path(".").resolve()
    assert (
        merged_context / runner["build"]["dockerfile"]
    ) == Path("deploy/hermes-node-bridge/Dockerfile").resolve()
    assert (merged_context / runner["build"]["dockerfile"]).is_file()
    assert node["user"] == "10002:10002"
    assert node["group_add"] == ["20000"]
    assert node["command"][-2:] == ["--max-cycles", "1"]
    assert node["healthcheck"]["test"][:3] == ["CMD", "python", "-c"]
    assert "stat.S_ISSOCK" in node["healthcheck"]["test"][3]
    assert runner["user"] == "10000:10000"
    assert runner["group_add"] == ["20000"]
    assert runner["entrypoint"] == [
        "/usr/bin/timeout",
        "--foreground",
        "--signal=TERM",
        "--kill-after=10s",
        "900s",
        "/opt/hermes/.venv/bin/hermes",
    ]
    assert runner["command"][:3] == ["chat", "--quiet", "--query"]
    assert runner["environment"] == []
    assert runner["read_only"] is True
    assert runner["cap_drop"] == ["ALL"]
    assert runner["security_opt"] == ["no-new-privileges:true"]
    assert runner["pids_limit"] == 256
    assert runner["mem_limit"] == "4096m"
    assert runner["cpus"] == 2
    assert runner["logging"] == {"driver": "none"}
    assert runner["ulimits"] == {"fsize": 16777216}
    assert runner["tmpfs"] == [
        "/opt/data/scratch:size=128m,mode=0700,uid=10000,gid=10000",
        "/tmp:size=128m,mode=0700,uid=10000,gid=10000",
    ]
    assert [volume["target"] for volume in runner["volumes"]] == [
        "/run/ithildin-node"
    ]
    assert runner["volumes"][0]["source"] == "ithildin-node-state"
    assert runner["volumes"][0]["volume"]["subpath"] == "mission-socket"
    assert runner["volumes"][0]["read_only"] is True
    assert "name" not in compose
    assert "volumes" not in compose
    dockerfile = Path("deploy/hermes-node-bridge/Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert (
        "import ithildin_mcp_server.node_bridge, ithildin_schemas" in dockerfile
    )
    assert dockerfile.index("USER 10000:10000") < dockerfile.index(
        "import ithildin_mcp_server.node_bridge, ithildin_schemas"
    )
    serialized = canonical_json(compose)
    for forbidden in (
        "/var/run/docker.sock",
        "privileged",
        "pid: host",
        "network_mode: host",
        "SSH",
        "KUBECONFIG",
    ):
        assert forbidden not in serialized
