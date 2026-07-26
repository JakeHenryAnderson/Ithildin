from __future__ import annotations

import hashlib
import json
import os
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
    FIXED_BRIDGE_PHASE_EXIT_CODES,
    FIXED_PROFILE_DIGEST,
    BridgeReceipt,
    FixedBridgePhase,
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


def _cycle_inputs() -> tuple[
    MissionRecordingNodeClient,
    NodeState,
    StoredNodeConfiguration,
]:
    client = MissionRecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes_fixed_node_bridge",
        deployment_topology="docker_sidecar",
    )
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
    configuration = client.pull_configuration(state, known_generation=0, now=now)
    return client, state, configuration


def _prepared(tmp_path: Path) -> tuple[FixedMissionSession, MissionRecordingNodeClient]:
    client, state, configuration = _cycle_inputs()
    now = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
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


def test_fixed_bridge_phase_exit_mapping_is_closed_unique_and_subsignal() -> None:
    assert FIXED_BRIDGE_PHASE_EXIT_CODES == {
        FixedBridgePhase.FIXED_BRIDGE_ENTERED: 80,
        FixedBridgePhase.PRECLAIM_VALIDATION_ENTERED: 81,
        FixedBridgePhase.MISSION_CLAIM_ENTERED: 82,
        FixedBridgePhase.SESSION_VALIDATION_ENTERED: 83,
        FixedBridgePhase.RECEIPT_PERSISTENCE_ENTERED: 84,
        FixedBridgePhase.SOCKET_PARENT_VALIDATION_ENTERED: 85,
        FixedBridgePhase.SOCKET_BIND_ENTERED: 86,
        FixedBridgePhase.SOCKET_PERMISSIONS_ENTERED: 87,
        FixedBridgePhase.LISTENER_ACCEPT_ENTERED: 88,
    }
    assert set(FIXED_BRIDGE_PHASE_EXIT_CODES) == set(FixedBridgePhase)
    assert len(set(FIXED_BRIDGE_PHASE_EXIT_CODES.values())) == 9
    assert all(0 < code < 128 for code in FIXED_BRIDGE_PHASE_EXIT_CODES.values())


def test_fixed_bridge_top_level_phase_boundaries_are_ordered_and_last_entered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state, configuration = _cycle_inputs()
    observed: list[FixedBridgePhase] = []

    def stop_before_listener(*_args: object, **_kwargs: object) -> None:
        raise FixedRunnerBridgeError("synthetic_listener_stop")

    monkeypatch.setattr(bridge_module, "_serve_session", stop_before_listener)

    with pytest.raises(FixedRunnerBridgeError, match="synthetic_listener_stop"):
        run_fixed_mission_cycle(
            client=client,
            state=state,
            configuration=configuration,
            node_version="0.1.0",
            socket_path=tmp_path / "socket" / "mission.sock",
            receipt_path=tmp_path / "mission-receipt.json",
            expected_socket_gid=tmp_path.stat().st_gid,
            phase_hook=observed.append,
        )

    assert observed == list(FixedBridgePhase)[:5]


def test_fixed_bridge_listener_setup_phase_boundaries_precede_their_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    parent_descriptor = os.open(tmp_path, os.O_RDONLY)

    class FakeSocket:
        def bind(self, _path: str) -> None:
            events.append("bind")

        def listen(self, backlog: int) -> None:
            assert backlog == 1
            events.append("listen")

        def settimeout(self, timeout: int) -> None:
            assert timeout == 9
            events.append("settimeout")

        def close(self) -> None:
            events.append("close")

    details = type(
        "SocketDetails",
        (),
        {
            "st_mode": stat.S_IFSOCK | 0o660,
            "st_uid": os.geteuid(),
            "st_gid": os.getegid(),
        },
    )()
    monkeypatch.setattr(
        bridge_module,
        "_open_owned_directory",
        lambda *_args, **_kwargs: os.dup(parent_descriptor),
    )
    monkeypatch.setattr(
        bridge_module,
        "_require_leaf_absent",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(bridge_module.socket, "socket", lambda *_args: FakeSocket())
    monkeypatch.setattr(
        bridge_module.os,
        "chown",
        lambda *_args, **_kwargs: events.append("chown"),
    )
    monkeypatch.setattr(
        bridge_module.os,
        "chmod",
        lambda *_args, **_kwargs: events.append("chmod"),
    )
    monkeypatch.setattr(bridge_module.os, "stat", lambda *_args, **_kwargs: details)

    listener, returned_parent = bridge_module._open_listener(
        tmp_path / "mission.sock",
        9,
        expected_gid=os.getegid(),
        phase_hook=lambda phase: events.append(phase.value),
    )
    try:
        assert events == [
            "socket_parent_validation_entered",
            "socket_bind_entered",
            "bind",
            "socket_permissions_entered",
            "chown",
            "chmod",
            "listen",
            "settimeout",
        ]
    finally:
        listener.close()
        os.close(returned_parent)
        os.close(parent_descriptor)


def test_listener_accept_phase_is_emitted_immediately_before_accept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, _client = _prepared(tmp_path)
    parent_descriptor = os.open(tmp_path, os.O_RDONLY)
    events: list[str] = []

    class TimeoutListener:
        def accept(self) -> tuple[socket.socket, object]:
            events.append("accept")
            raise TimeoutError

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        bridge_module,
        "_open_listener",
        lambda *_args, **_kwargs: (TimeoutListener(), os.dup(parent_descriptor)),
    )

    with pytest.raises(FixedRunnerBridgeError, match="bridge_timeout"):
        bridge_module._serve_session(
            session,
            socket_path=tmp_path / "mission.sock",
            expected_peer_uid=os.geteuid(),
            expected_socket_gid=os.getegid(),
            wall_time_seconds=9,
            phase_hook=lambda phase: events.append(phase.value),
        )

    os.close(parent_descriptor)
    assert events[:2] == ["listener_accept_entered", "accept"]


def test_phase_hook_is_default_noop_and_failures_cannot_change_bridge_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, state, configuration = _cycle_inputs()
    monkeypatch.setattr(client, "claim_mission", lambda _state: None)

    def arguments(base: Path) -> dict[str, object]:
        base.mkdir()
        return {
            "client": client,
            "state": state,
            "configuration": configuration,
            "node_version": "0.1.0",
            "socket_path": base / "socket" / "mission.sock",
            "receipt_path": base / "mission-receipt.json",
            "expected_socket_gid": base.stat().st_gid,
        }

    without_hook = run_fixed_mission_cycle(**arguments(tmp_path / "without"))

    def failing_hook(_phase: FixedBridgePhase) -> None:
        raise RuntimeError("non-authoritative observer failed")

    with_failing_hook = run_fixed_mission_cycle(
        **arguments(tmp_path / "with"),
        phase_hook=failing_hook,
    )

    assert with_failing_hook == without_hook
    assert with_failing_hook["status"] == "no_queued_mission"


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
    assert base["services"]["ithildin-node"]["tmpfs"] == [
        "/tmp:size=16m,mode=0700,uid=10002,gid=10002"
    ]
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
    assert "tmpfs" not in node
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
    pinned = (
        "nousresearch/hermes-agent@sha256:"
        "6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
    )
    assert dockerfile.count(f"FROM {pinned}") == 2
    assert "ghcr.io/astral-sh/uv:" not in dockerfile
    assert "/src/.venv" not in dockerfile
    assert "ENV UV_PROJECT_ENVIRONMENT=/opt/ithildin/.venv" in dockerfile
    assert (
        "uv sync --frozen --no-dev --no-editable --python /usr/bin/python3"
        in dockerfile
    )
    assert dockerfile.count("sys.version_info >= (3, 12)") == 2
    assert dockerfile.count("sys.prefix == '/opt/ithildin/.venv'") == 2
    assert (
        'COPY --from=bridge-build /opt/ithildin/.venv '
        "/opt/ithildin/.venv"
    ) in dockerfile
    assert (
        dockerfile.count(
            "import ithildin_mcp_server.node_bridge, ithildin_schemas"
        )
        == 2
    )
    assert dockerfile.index("USER 10000:10000") < dockerfile.rindex(
        "import ithildin_mcp_server.node_bridge, ithildin_schemas"
    )
    assert 'ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]' in dockerfile
    assert "COPY --from=bridge-build /opt/hermes" not in dockerfile
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


def _validate_runtime_native_bridge_dockerfile(dockerfile: str) -> None:
    pinned = (
        "nousresearch/hermes-agent@sha256:"
        "6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
    )
    assert dockerfile.count(f"FROM {pinned}") == 2
    assert "ghcr.io/astral-sh/uv:" not in dockerfile
    assert "/src/.venv" not in dockerfile
    assert dockerfile.count("/opt/ithildin/.venv") >= 8
    assert "ENV UV_PROJECT_ENVIRONMENT=/opt/ithildin/.venv" in dockerfile
    assert (
        "uv sync --frozen --no-dev --no-editable --python /usr/bin/python3"
        in dockerfile
    )
    assert dockerfile.count("sys.version_info >= (3, 12)") == 2
    assert dockerfile.count("sys.prefix == '/opt/ithildin/.venv'") == 2
    assert dockerfile.count("readlink -f /usr/bin/python3") == 1
    assert (
        'COPY --from=bridge-build /opt/ithildin/.venv '
        "/opt/ithildin/.venv"
    ) in dockerfile
    assert 'ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]' in dockerfile
    assert "COPY --from=bridge-build /opt/hermes" not in dockerfile


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        (
            "FROM nousresearch/hermes-agent@sha256:"
            "6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc "
            "AS bridge-build",
            "FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS bridge-build",
        ),
        (
            "ENV UV_PROJECT_ENVIRONMENT=/opt/ithildin/.venv",
            "ENV UV_PROJECT_ENVIRONMENT=/src/.venv",
        ),
        ("--python /usr/bin/python3", "--python python3"),
        (
            "sys.prefix == '/opt/ithildin/.venv'",
            "sys.prefix == '/src/.venv'",
        ),
        (
            "COPY --from=bridge-build /opt/ithildin/.venv "
            "/opt/ithildin/.venv",
            "COPY --from=bridge-build /opt/ithildin/.venv /tmp/.venv",
        ),
        (
            'ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]',
            "COPY --from=bridge-build /opt/hermes /opt/hermes\n"
            'ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]',
        ),
    ],
)
def test_runtime_native_bridge_dockerfile_hostile_drift_fails_static_contract(
    original: str,
    replacement: str,
) -> None:
    dockerfile = Path("deploy/hermes-node-bridge/Dockerfile").read_text(
        encoding="utf-8"
    )
    _validate_runtime_native_bridge_dockerfile(dockerfile)
    assert original in dockerfile

    with pytest.raises(AssertionError):
        _validate_runtime_native_bridge_dockerfile(
            dockerfile.replace(original, replacement, 1)
        )
