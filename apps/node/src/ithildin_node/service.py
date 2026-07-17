"""Supervised local-preview Ithildin Node control-plane service loop."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from ithildin_schemas import JsonObject

from ithildin_node.client import NodeClient, NodeClientError, NodeState, StoredNodeConfiguration


@dataclass(frozen=True)
class NodeServiceCycle:
    """Safe result of one configuration and heartbeat synchronization cycle."""

    node_id: str
    generation: int
    configuration_digest: str
    configuration_state: str
    observed_state: str
    heartbeat_interval_seconds: int
    trust_promoted: bool
    verification_trust: str

    def safe_summary(self) -> JsonObject:
        return {
            "status": "synchronized",
            "node_id": self.node_id,
            "generation": self.generation,
            "configuration_digest": self.configuration_digest,
            "configuration_state": self.configuration_state,
            "observed_state": self.observed_state,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "configuration_trust_promoted": self.trust_promoted,
            "configuration_verification_trust": self.verification_trust,
            "runner_execution_authority": False,
            "self_update_authority": False,
        }


def synchronize_once(
    *,
    state_path: Path,
    configuration_path: Path,
    node_version: str,
    runner_adapter: str,
    deployment_topology: str,
) -> NodeServiceCycle:
    """Pull, verify, durably store, acknowledge, and report one Node cycle."""

    state = NodeState.load(state_path)
    client = NodeClient(state.api_url)
    known_generation = None
    if configuration_path.exists():
        known_generation = StoredNodeConfiguration.load(configuration_path).generation
    pulled = client.pull_configuration_with_state(
        state,
        known_generation=known_generation,
    )
    if pulled.state != state:
        # Persist promoted signing trust before accepting configuration under it locally.
        pulled.state.write_atomic(state_path)
    pulled.configuration.write_atomic(configuration_path)
    acknowledgment = client.acknowledge_configuration(
        pulled.state,
        pulled.configuration,
    )
    heartbeat = client.heartbeat(
        pulled.state,
        node_version=node_version,
        runner_adapter=runner_adapter,
        deployment_topology=deployment_topology,
        configuration_digest=pulled.configuration.configuration_digest,
    )
    return NodeServiceCycle(
        node_id=pulled.state.node_id,
        generation=pulled.configuration.generation,
        configuration_digest=pulled.configuration.configuration_digest,
        configuration_state=_response_string(
            acknowledgment, "configuration_state", "unknown"
        ),
        observed_state=_response_string(heartbeat, "observed_state", "unknown"),
        heartbeat_interval_seconds=_heartbeat_interval(pulled.configuration),
        trust_promoted=pulled.trust_promoted,
        verification_trust=pulled.verification_trust,
    )


def run_service(
    *,
    state_path: Path,
    configuration_path: Path,
    node_version: str,
    runner_adapter: str,
    deployment_topology: str,
    max_cycles: int | None = None,
    retry_initial_seconds: int = 5,
    retry_max_seconds: int = 60,
    stop_event: Event | None = None,
    emit: Callable[[str], None] = print,
) -> int:
    """Run the bounded Node synchronization loop until signaled or cycle-limited."""

    if max_cycles is not None and max_cycles < 1:
        raise NodeClientError("max cycles must be at least 1")
    if retry_initial_seconds < 1 or retry_max_seconds < retry_initial_seconds:
        raise NodeClientError("retry bounds are invalid")
    effective_stop = stop_event or Event()
    attempts = 0
    consecutive_failures = 0
    lease_descriptor = _acquire_service_lease(state_path.parent / ".service.lock")
    try:
        while not effective_stop.is_set():
            attempts += 1
            try:
                cycle = synchronize_once(
                    state_path=state_path,
                    configuration_path=configuration_path,
                    node_version=node_version,
                    runner_adapter=runner_adapter,
                    deployment_topology=deployment_topology,
                )
                consecutive_failures = 0
                delay = cycle.heartbeat_interval_seconds
                emit(json.dumps(cycle.safe_summary(), sort_keys=True))
            except NodeClientError as exc:
                consecutive_failures += 1
                delay = retry_delay_seconds(
                    consecutive_failures,
                    initial_seconds=retry_initial_seconds,
                    maximum_seconds=retry_max_seconds,
                )
                emit(
                    json.dumps(
                        {
                            "status": "degraded_retrying",
                            "error": str(exc),
                            "consecutive_failures": consecutive_failures,
                            "retry_in_seconds": delay,
                            "runner_execution_authority": False,
                            "self_update_authority": False,
                        },
                        sort_keys=True,
                    )
                )
            if max_cycles is not None and attempts >= max_cycles:
                return 0 if consecutive_failures == 0 else 1
            effective_stop.wait(delay)
        emit(
            json.dumps(
                {
                    "status": "stopped",
                    "runner_execution_authority": False,
                    "self_update_authority": False,
                },
                sort_keys=True,
            )
        )
        return 0
    finally:
        os.close(lease_descriptor)


def install_signal_handlers(stop_event: Event) -> None:
    """Translate normal service-manager termination into a graceful loop stop."""

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)


def retry_delay_seconds(
    consecutive_failures: int, *, initial_seconds: int, maximum_seconds: int
) -> int:
    if consecutive_failures < 1:
        raise NodeClientError("consecutive failures must be at least 1")
    exponent = min(consecutive_failures - 1, 30)
    return min(maximum_seconds, initial_seconds * (1 << exponent))


def _acquire_service_lease(path: Path) -> int:
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise NodeClientError("Node service lease is unavailable") from exc
    try:
        file_status = os.fstat(descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise NodeClientError("Node service lease must be a regular file")
        if stat.S_IMODE(file_status.st_mode) & 0o077:
            raise NodeClientError("Node service lease permissions must be 0600")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise NodeClientError("Node service identity is already in use") from exc
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _heartbeat_interval(configuration: StoredNodeConfiguration) -> int:
    closed_configuration = configuration.bundle.get("configuration")
    if not isinstance(closed_configuration, dict):
        raise NodeClientError("stored configuration payload is invalid")
    value = closed_configuration.get("heartbeat_interval_seconds")
    if not isinstance(value, int) or isinstance(value, bool) or not 15 <= value <= 300:
        raise NodeClientError("stored heartbeat interval is invalid")
    return value


def _response_string(document: JsonObject, key: str, fallback: str) -> str:
    value = document.get(key)
    return value if isinstance(value, str) and value else fallback
