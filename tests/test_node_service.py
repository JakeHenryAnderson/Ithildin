from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ithildin_node import service as service_module
from ithildin_node.client import NodeClientError
from ithildin_node.service import retry_delay_seconds, run_service, synchronize_once
from test_node_client import RecordingNodeClient


def test_service_cycle_persists_verified_configuration_and_reports_without_runner_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = RecordingNodeClient()
    state = client.enroll(
        enrollment_code="one-time-code",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )
    state_path = tmp_path / "node" / "state.json"
    configuration_path = tmp_path / "node" / "configuration.json"
    state.write_new(state_path)
    original_pull = client.pull_configuration_with_state
    original_acknowledge = client.acknowledge_configuration
    original_heartbeat = client.heartbeat
    fixed_now = datetime(2026, 7, 16, 12, 5, tzinfo=UTC)
    monkeypatch.setattr(service_module, "NodeClient", lambda _url: client)
    monkeypatch.setattr(
        client,
        "pull_configuration_with_state",
        lambda state, known_generation=None: original_pull(
            state,
            known_generation=known_generation,
            now=fixed_now,
            nonce="1" * 32,
        ),
    )
    monkeypatch.setattr(
        client,
        "acknowledge_configuration",
        lambda state, configuration: original_acknowledge(
            state, configuration, now=fixed_now, nonce="2" * 32
        ),
    )
    monkeypatch.setattr(
        client,
        "heartbeat",
        lambda state, **values: original_heartbeat(
            state, **values, now=fixed_now, nonce="3" * 32
        ),
    )

    result = synchronize_once(
        state_path=state_path,
        configuration_path=configuration_path,
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
    )

    assert result.generation == 1
    assert result.heartbeat_interval_seconds == 30
    assert result.configuration_state == "stored_current_not_enforced"
    assert result.safe_summary()["runner_execution_authority"] is False
    assert result.safe_summary()["self_update_authority"] is False
    assert stat.S_IMODE(configuration_path.stat().st_mode) == 0o600


def test_service_one_cycle_emits_safe_posture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    emitted: list[str] = []
    monkeypatch.setattr(
        service_module,
        "synchronize_once",
        lambda **_values: service_module.NodeServiceCycle(
            node_id="node_" + ("1" * 32),
            generation=2,
            configuration_digest="sha256:" + ("a" * 64),
            configuration_state="stored_current_not_enforced",
            observed_state="observed_connected",
            heartbeat_interval_seconds=30,
            trust_promoted=False,
            verification_trust="active",
        ),
    )

    result = run_service(
        state_path=tmp_path / "state.json",
        configuration_path=tmp_path / "configuration.json",
        node_version="0.1.0",
        runner_adapter="hermes",
        deployment_topology="docker_sidecar",
        max_cycles=1,
        emit=emitted.append,
    )

    assert result == 0
    assert len(emitted) == 1
    assert '"status": "synchronized"' in emitted[0]
    assert '"runner_execution_authority": false' in emitted[0]


def test_retry_delay_is_exponential_and_bounded() -> None:
    assert [
        retry_delay_seconds(value, initial_seconds=5, maximum_seconds=60)
        for value in range(1, 7)
    ] == [5, 10, 20, 40, 60, 60]
    with pytest.raises(NodeClientError, match="at least 1"):
        retry_delay_seconds(0, initial_seconds=5, maximum_seconds=60)


def test_service_lease_denies_concurrent_use_and_remains_private(tmp_path: Path) -> None:
    lease_path = tmp_path / ".service.lock"
    descriptor = service_module._acquire_service_lease(lease_path)
    try:
        assert stat.S_IMODE(lease_path.stat().st_mode) == 0o600
        with pytest.raises(NodeClientError, match="already in use"):
            service_module._acquire_service_lease(lease_path)
    finally:
        os.close(descriptor)
