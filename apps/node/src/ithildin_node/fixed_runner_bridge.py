"""Closed Unix-socket bridge for the reviewed fixed Hermes mission profile."""

from __future__ import annotations

import json
import os
import re
import secrets
import socket
import stat
import struct
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import cast

from ithildin_schemas import JsonObject, canonical_json, sha256_digest

from ithildin_node.client import (
    NodeClient,
    NodeClientError,
    NodeState,
    StoredNodeConfiguration,
)

PROTOCOL_VERSION = "1"
SOCKET_PATH = Path("/var/lib/ithildin-node/mission-socket/mission.sock")
RECEIPT_PATH = Path("/var/lib/ithildin-node/mission-receipt.json")
EXPECTED_PEER_UID = 10000
EXPECTED_SOCKET_GID = 20000
MAX_FRAME_BYTES = 16_384
OPERATION_TIMEOUT_SECONDS = 120
MISSION_WALL_TIME_SECONDS = 900
FIXED_RUNNER_ADAPTER = "hermes_fixed_node_bridge"
FIXED_DEPLOYMENT_TOPOLOGY = "docker_sidecar"
FIXED_PROFILE_DIGEST = "sha256:90b94d725640768f1a7d665e979bbe11f263a4ff264591a5348d0b5820db3e92"
FIXED_OPERATIONS = (
    ("mission.step.1", "project.structure.summary"),
    ("mission.step.2", "project.test.summary"),
)


class FixedBridgePhase(StrEnum):
    """Closed, non-authoritative markers for the last entered bridge phase."""

    FIXED_BRIDGE_ENTERED = "fixed_bridge_entered"
    PRECLAIM_VALIDATION_ENTERED = "preclaim_validation_entered"
    MISSION_CLAIM_ENTERED = "mission_claim_entered"
    SESSION_VALIDATION_ENTERED = "session_validation_entered"
    RECEIPT_PERSISTENCE_ENTERED = "receipt_persistence_entered"
    SOCKET_PARENT_VALIDATION_ENTERED = "socket_parent_validation_entered"
    SOCKET_BIND_ENTERED = "socket_bind_entered"
    SOCKET_PERMISSIONS_ENTERED = "socket_permissions_entered"
    LISTENER_ACCEPT_ENTERED = "listener_accept_entered"


FIXED_BRIDGE_PHASE_EXIT_CODES: Mapping[FixedBridgePhase, int] = MappingProxyType(
    {
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
)
FixedBridgePhaseHook = Callable[[FixedBridgePhase], None]

_MISSION_ID = re.compile(r"^mission_[0-9a-f]{32}$")
_CLAIM_ID = re.compile(r"^mclaim_[0-9a-f]{32}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUEST_KEYS = {
    "protocol_version",
    "affordance",
    "mission_id",
    "claim_id",
    "envelope_digest",
    "handoff_nonce",
    "operation_index",
    "profile_digest",
}
_RECEIPT_KEYS = {
    "mission_id",
    "claim_id",
    "envelope_digest",
    "next_operation_index",
    "handoff_nonce_digest",
    "last_closed_status",
    "last_closed_reason_code",
}


class FixedRunnerBridgeError(NodeClientError):
    """A fail-closed fixed bridge error using a stable reason code."""

    def __init__(self, reason_code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", reason_code):
            raise ValueError("unsafe fixed bridge reason code")
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class BridgeReceipt:
    """The complete and exclusive durable state allowed for one mission handoff."""

    mission_id: str
    claim_id: str
    envelope_digest: str
    next_operation_index: int
    handoff_nonce_digest: str
    last_closed_status: str
    last_closed_reason_code: str

    def document(self) -> JsonObject:
        return {
            "mission_id": self.mission_id,
            "claim_id": self.claim_id,
            "envelope_digest": self.envelope_digest,
            "next_operation_index": self.next_operation_index,
            "handoff_nonce_digest": self.handoff_nonce_digest,
            "last_closed_status": self.last_closed_status,
            "last_closed_reason_code": self.last_closed_reason_code,
        }

    @classmethod
    def create(
        cls,
        path: Path,
        *,
        mission_id: str,
        claim_id: str,
        envelope_digest: str,
        handoff_nonce: str,
    ) -> BridgeReceipt:
        receipt = cls(
            mission_id=mission_id,
            claim_id=claim_id,
            envelope_digest=envelope_digest,
            next_operation_index=1,
            handoff_nonce_digest=sha256_digest(handoff_nonce),
            last_closed_status="prepared",
            last_closed_reason_code="none",
        )
        _validate_receipt(receipt)
        _write_new_private(path, receipt.document())
        return receipt

    @classmethod
    def load(cls, path: Path) -> BridgeReceipt:
        document = _read_private_document(path)
        if set(document) != _RECEIPT_KEYS:
            raise FixedRunnerBridgeError("receipt_shape_invalid")
        mission_id = document["mission_id"]
        claim_id = document["claim_id"]
        envelope_digest = document["envelope_digest"]
        next_operation_index = document["next_operation_index"]
        handoff_nonce_digest = document["handoff_nonce_digest"]
        last_closed_status = document["last_closed_status"]
        last_closed_reason_code = document["last_closed_reason_code"]
        if (
            not isinstance(mission_id, str)
            or not isinstance(claim_id, str)
            or not isinstance(envelope_digest, str)
            or not isinstance(next_operation_index, int)
            or isinstance(next_operation_index, bool)
            or not isinstance(handoff_nonce_digest, str)
            or not isinstance(last_closed_status, str)
            or not isinstance(last_closed_reason_code, str)
        ):
            raise FixedRunnerBridgeError("receipt_shape_invalid")
        receipt = cls(
            mission_id=mission_id,
            claim_id=claim_id,
            envelope_digest=envelope_digest,
            next_operation_index=next_operation_index,
            handoff_nonce_digest=handoff_nonce_digest,
            last_closed_status=last_closed_status,
            last_closed_reason_code=last_closed_reason_code,
        )
        _validate_receipt(receipt)
        return receipt

    def advance(
        self,
        path: Path,
        *,
        status: str,
        reason_code: str = "none",
    ) -> BridgeReceipt:
        next_receipt = replace(
            self,
            next_operation_index=self.next_operation_index + 1,
            last_closed_status=status,
            last_closed_reason_code=reason_code,
        )
        _validate_receipt(next_receipt)
        _write_private_atomic(path, next_receipt.document())
        return next_receipt

    def close(
        self,
        path: Path,
        *,
        status: str,
        reason_code: str = "none",
    ) -> BridgeReceipt:
        next_receipt = replace(
            self,
            last_closed_status=status,
            last_closed_reason_code=reason_code,
        )
        _validate_receipt(next_receipt)
        _write_private_atomic(path, next_receipt.document())
        return next_receipt


@dataclass
class FixedMissionSession:
    """One prepared mission with exactly two governed operations and one completion."""

    client: NodeClient
    state: NodeState
    configuration: StoredNodeConfiguration
    node_version: str
    deployment_topology: str
    profile_digest: str
    handoff_nonce: str
    receipt_path: Path
    receipt: BridgeReceipt
    lifecycle_revision: int

    @classmethod
    def prepare(
        cls,
        *,
        client: NodeClient,
        state: NodeState,
        configuration: StoredNodeConfiguration,
        node_version: str,
        deployment_topology: str = FIXED_DEPLOYMENT_TOPOLOGY,
        profile_digest: str,
        receipt_path: Path,
        envelope: JsonObject,
        handoff_nonce: str | None = None,
        phase_hook: FixedBridgePhaseHook | None = None,
    ) -> FixedMissionSession:
        _validate_profile_digest(profile_digest)
        mission_id = _required_matching(envelope, "mission_id", _MISSION_ID)
        claim_id = _required_matching(envelope, "claim_id", _CLAIM_ID)
        envelope_digest = _required_matching(envelope, "envelope_digest", _DIGEST)
        revision = _required_integer(envelope, "claim_lifecycle_revision", minimum=2)
        _validate_closed_envelope(envelope, state)
        nonce = handoff_nonce or secrets.token_hex(32)
        if not re.fullmatch(r"[0-9a-f]{64}", nonce):
            raise FixedRunnerBridgeError("handoff_nonce_invalid")
        _emit_phase(phase_hook, FixedBridgePhase.RECEIPT_PERSISTENCE_ENTERED)
        _preflight_receipt_path(receipt_path)
        receipt = BridgeReceipt.create(
            receipt_path,
            mission_id=mission_id,
            claim_id=claim_id,
            envelope_digest=envelope_digest,
            handoff_nonce=nonce,
        )
        return cls(
            client=client,
            state=state,
            configuration=configuration,
            node_version=node_version,
            deployment_topology=deployment_topology,
            profile_digest=profile_digest,
            handoff_nonce=nonce,
            receipt_path=receipt_path,
            receipt=receipt,
            lifecycle_revision=revision,
        )

    @property
    def terminal(self) -> bool:
        return self.receipt.last_closed_status in {
            "runner_reported_succeeded",
            "cancel_observed",
            "failed_closed",
        }

    def handoff_document(self) -> JsonObject:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "mission_id": self.receipt.mission_id,
            "claim_id": self.receipt.claim_id,
            "envelope_digest": self.receipt.envelope_digest,
            "handoff_nonce": self.handoff_nonce,
            "next_operation_index": self.receipt.next_operation_index,
            "profile_digest": self.profile_digest,
        }

    def report_running(self) -> JsonObject:
        try:
            self._refresh_heartbeat()
            response = self.client.report_mission(
                self.state,
                mission_id=self.receipt.mission_id,
                claim_id=self.receipt.claim_id,
                envelope_digest=self.receipt.envelope_digest,
                expected_lifecycle_revision=self.lifecycle_revision,
                report_id=_report_id(),
                report_kind="runner_running",
                outcome_code="started",
            )
            revision = _gateway_report_revision(
                response,
                expected_state="runner_reported_running",
            )
        except FixedRunnerBridgeError as exc:
            self._fail_closed(exc.reason_code)
            raise
        except NodeClientError as exc:
            self._fail_closed("gateway_ambiguity")
            raise FixedRunnerBridgeError("gateway_ambiguity") from exc
        self.lifecycle_revision = revision
        self.receipt = self.receipt.close(
            self.receipt_path, status="runner_reported_running"
        )
        return _closed_status(self, "runner_reported_running")

    def handle_request(self, document: JsonObject) -> JsonObject:
        try:
            if self.terminal:
                raise FixedRunnerBridgeError("mission_already_closed")
            self._validate_request(document)
            operation_index = cast(int, document["operation_index"])
            if operation_index in (1, 2):
                return self._run_step(operation_index)
            if operation_index == 3:
                return self._complete()
            raise FixedRunnerBridgeError("operation_index_invalid")
        except FixedRunnerBridgeError as exc:
            if not self.terminal:
                self._fail_closed(exc.reason_code)
            raise
        except NodeClientError as exc:
            self._fail_closed("gateway_ambiguity")
            raise FixedRunnerBridgeError("gateway_ambiguity") from exc

    def _validate_request(self, document: JsonObject) -> None:
        if set(document) != _REQUEST_KEYS:
            raise FixedRunnerBridgeError("request_shape_invalid")
        bindings = {
            "protocol_version": PROTOCOL_VERSION,
            "mission_id": self.receipt.mission_id,
            "claim_id": self.receipt.claim_id,
            "envelope_digest": self.receipt.envelope_digest,
            "handoff_nonce": self.handoff_nonce,
            "operation_index": self.receipt.next_operation_index,
            "profile_digest": self.profile_digest,
        }
        if any(document.get(key) != value for key, value in bindings.items()):
            raise FixedRunnerBridgeError("request_binding_conflict")
        expected_affordance = {
            1: "mission.step.1",
            2: "mission.step.2",
            3: "mission.complete",
        }.get(self.receipt.next_operation_index)
        if expected_affordance is None or document.get("affordance") != expected_affordance:
            raise FixedRunnerBridgeError("operation_order_conflict")

    def _poll_control(self) -> JsonObject:
        self._refresh_heartbeat()
        control = self.client.poll_mission_control(
            self.state,
            mission_id=self.receipt.mission_id,
            claim_id=self.receipt.claim_id,
            envelope_digest=self.receipt.envelope_digest,
            observed_lifecycle_revision=self.lifecycle_revision,
        )
        decision = control.get("control_decision")
        revision = _required_integer(control, "decision_revision", minimum=2)
        self.lifecycle_revision = revision
        if decision == "continue":
            return control
        if decision == "cancel_requested":
            self._refresh_heartbeat()
            self.client.report_mission(
                self.state,
                mission_id=self.receipt.mission_id,
                claim_id=self.receipt.claim_id,
                envelope_digest=self.receipt.envelope_digest,
                expected_lifecycle_revision=revision,
                report_id=_report_id(),
                report_kind="cancel_observed",
                outcome_code="cancellation_observed",
            )
            self.receipt = self.receipt.close(
                self.receipt_path,
                status="cancel_observed",
                reason_code="cancel_requested",
            )
            raise FixedRunnerBridgeError("cancel_requested")
        raise FixedRunnerBridgeError("control_decision_invalid")

    def _run_step(self, operation_index: int) -> JsonObject:
        self._poll_control()
        affordance, tool_name = FIXED_OPERATIONS[operation_index - 1]
        result = self.client.governed_tool_call(
            self.state,
            self.configuration,
            node_version=self.node_version,
            session_id=_mission_session_id(self.receipt),
            tool_name=tool_name,
            arguments={},
        )
        if (
            result.get("status") != "completed"
            or result.get("is_error") is not False
            or result.get("tool_name") != tool_name
            or not isinstance(result.get("content"), dict)
        ):
            self._fail_closed("governed_result_invalid")
            raise FixedRunnerBridgeError("governed_result_invalid")
        self.receipt = self.receipt.advance(
            self.receipt_path, status=f"operation_{operation_index}_closed"
        )
        return {
            **_closed_status(self, "operation_closed"),
            "affordance": affordance,
            "operation_index": operation_index,
            "tool_name": tool_name,
            "governed_result": cast(JsonObject, result["content"]),
        }

    def _complete(self) -> JsonObject:
        self._poll_control()
        self._refresh_heartbeat()
        response = self.client.report_mission(
            self.state,
            mission_id=self.receipt.mission_id,
            claim_id=self.receipt.claim_id,
            envelope_digest=self.receipt.envelope_digest,
            expected_lifecycle_revision=self.lifecycle_revision,
            report_id=_report_id(),
            report_kind="runner_succeeded",
            outcome_code="succeeded",
            artifact_digest=None,
        )
        try:
            revision = _gateway_report_revision(
                response,
                expected_state="runner_reported_succeeded",
            )
        except FixedRunnerBridgeError as exc:
            self._fail_closed(exc.reason_code)
            raise
        self.lifecycle_revision = revision
        self.receipt = self.receipt.advance(
            self.receipt_path, status="runner_reported_succeeded"
        )
        return _closed_status(self, "runner_reported_succeeded")

    def _refresh_heartbeat(self) -> None:
        try:
            heartbeat = self.client.heartbeat(
                self.state,
                node_version=self.node_version,
                runner_adapter=FIXED_RUNNER_ADAPTER,
                deployment_topology=self.deployment_topology,
                configuration_digest=self.configuration.configuration_digest,
                mission_id=self.receipt.mission_id,
            )
        except NodeClientError as exc:
            raise FixedRunnerBridgeError("gateway_heartbeat_unavailable") from exc
        if (
            heartbeat.get("observed_state") != "observed_connected"
            or heartbeat.get("last_configuration_digest")
            != self.configuration.configuration_digest
            or heartbeat.get("last_mission_id") != self.receipt.mission_id
        ):
            raise FixedRunnerBridgeError("gateway_heartbeat_invalid")

    def _fail_closed(self, reason_code: str) -> None:
        self.receipt = self.receipt.close(
            self.receipt_path,
            status="failed_closed",
            reason_code=reason_code,
        )


def run_fixed_mission_cycle(
    *,
    client: NodeClient,
    state: NodeState,
    configuration: StoredNodeConfiguration,
    node_version: str,
    deployment_topology: str = FIXED_DEPLOYMENT_TOPOLOGY,
    socket_path: Path = SOCKET_PATH,
    receipt_path: Path = RECEIPT_PATH,
    profile_digest: str = FIXED_PROFILE_DIGEST,
    expected_peer_uid: int = EXPECTED_PEER_UID,
    expected_socket_gid: int | None = None,
    wall_time_seconds: int = MISSION_WALL_TIME_SECONDS,
    phase_hook: FixedBridgePhaseHook | None = None,
) -> JsonObject:
    """Claim and serve one fixed mission; never start, stop, or inspect a runner."""

    _emit_phase(phase_hook, FixedBridgePhase.FIXED_BRIDGE_ENTERED)
    _emit_phase(phase_hook, FixedBridgePhase.PRECLAIM_VALIDATION_ENTERED)
    _preflight_receipt_path(receipt_path)
    _preflight_socket_path(
        socket_path,
        expected_gid=(
            EXPECTED_SOCKET_GID
            if expected_socket_gid is None and socket_path == SOCKET_PATH
            else os.getegid()
            if expected_socket_gid is None
            else expected_socket_gid
        ),
    )
    _emit_phase(phase_hook, FixedBridgePhase.MISSION_CLAIM_ENTERED)
    envelope = client.claim_mission(state)
    if envelope is None:
        return {
            "status": "no_queued_mission",
            "profile_digest": profile_digest,
            "runner_state_authority": "runner_reported_only",
            "model_provider_state_known": False,
        }
    _emit_phase(phase_hook, FixedBridgePhase.SESSION_VALIDATION_ENTERED)
    session = FixedMissionSession.prepare(
        client=client,
        state=state,
        configuration=configuration,
        node_version=node_version,
        deployment_topology=deployment_topology,
        profile_digest=profile_digest,
        receipt_path=receipt_path,
        envelope=envelope,
        phase_hook=phase_hook,
    )
    try:
        _serve_session(
            session,
            socket_path=socket_path,
            expected_peer_uid=expected_peer_uid,
            expected_socket_gid=(
                EXPECTED_SOCKET_GID
                if expected_socket_gid is None and socket_path == SOCKET_PATH
                else os.getegid()
                if expected_socket_gid is None
                else expected_socket_gid
            ),
            wall_time_seconds=wall_time_seconds,
            phase_hook=phase_hook,
        )
    except FixedRunnerBridgeError as exc:
        if not session.terminal:
            session._fail_closed(exc.reason_code)
        raise
    return _closed_status(session, session.receipt.last_closed_status)


def _serve_session(
    session: FixedMissionSession,
    *,
    socket_path: Path,
    expected_peer_uid: int,
    expected_socket_gid: int,
    wall_time_seconds: int,
    phase_hook: FixedBridgePhaseHook | None = None,
) -> None:
    listener, parent_descriptor = _open_listener(
        socket_path,
        wall_time_seconds,
        expected_gid=expected_socket_gid,
        phase_hook=phase_hook,
    )
    connection: socket.socket | None = None
    deadline = time.monotonic() + wall_time_seconds
    try:
        _emit_phase(phase_hook, FixedBridgePhase.LISTENER_ACCEPT_ENTERED)
        connection, _address = listener.accept()
        if _peer_uid(connection) != expected_peer_uid:
            raise FixedRunnerBridgeError("peer_identity_denied")
        connection.settimeout(OPERATION_TIMEOUT_SECONDS)
        session.report_running()
        _send_frame(connection, session.handoff_document())
        while not session.terminal:
            if time.monotonic() >= deadline:
                raise FixedRunnerBridgeError("mission_wall_time_exceeded")
            request = _receive_frame(connection)
            try:
                response = session.handle_request(request)
            except FixedRunnerBridgeError as exc:
                _send_frame(connection, _denied_status(session, exc.reason_code))
                raise
            _send_frame(connection, response)
    except FixedRunnerBridgeError as exc:
        if not session.terminal:
            session._fail_closed(exc.reason_code)
        raise
    except NodeClientError as exc:
        session._fail_closed("gateway_ambiguity")
        raise FixedRunnerBridgeError("gateway_ambiguity") from exc
    except TimeoutError as exc:
        session._fail_closed("bridge_timeout")
        raise FixedRunnerBridgeError("bridge_timeout") from exc
    finally:
        if connection is not None:
            connection.close()
        listener.close()
        try:
            os.unlink(socket_path.name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            pass
        finally:
            os.close(parent_descriptor)


def _open_listener(
    path: Path,
    timeout_seconds: int,
    *,
    expected_gid: int,
    phase_hook: FixedBridgePhaseHook | None = None,
) -> tuple[socket.socket, int]:
    _emit_phase(phase_hook, FixedBridgePhase.SOCKET_PARENT_VALIDATION_ENTERED)
    parent_descriptor = _open_owned_directory(
        path.parent,
        expected_uid=os.geteuid(),
        expected_gid=expected_gid,
        allowed_modes={0o770},
        reason_code="socket_parent_unsafe",
    )
    _require_leaf_absent(parent_descriptor, path.name, reason_code="socket_path_unsafe")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    descriptor_path = f"/proc/self/fd/{parent_descriptor}/{path.name}"
    old_umask = os.umask(0o117)
    _emit_phase(phase_hook, FixedBridgePhase.SOCKET_BIND_ENTERED)
    try:
        listener.bind(descriptor_path)
    except OSError as exc:
        listener.close()
        os.close(parent_descriptor)
        raise FixedRunnerBridgeError("socket_bind_failed") from exc
    finally:
        os.umask(old_umask)
    _emit_phase(phase_hook, FixedBridgePhase.SOCKET_PERMISSIONS_ENTERED)
    try:
        os.chown(
            path.name,
            -1,
            expected_gid,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        os.chmod(path.name, 0o660, dir_fd=parent_descriptor, follow_symlinks=False)
        details = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as exc:
        listener.close()
        os.close(parent_descriptor)
        raise FixedRunnerBridgeError("socket_permissions_invalid") from exc
    if (
        not stat.S_ISSOCK(details.st_mode)
        or stat.S_IMODE(details.st_mode) != 0o660
        or details.st_uid != os.geteuid()
        or details.st_gid != expected_gid
    ):
        listener.close()
        os.close(parent_descriptor)
        raise FixedRunnerBridgeError("socket_permissions_invalid")
    listener.listen(1)
    listener.settimeout(timeout_seconds)
    return listener, parent_descriptor


def _emit_phase(
    phase_hook: FixedBridgePhaseHook | None,
    phase: FixedBridgePhase,
) -> None:
    if phase_hook is None:
        return
    try:
        phase_hook(phase)
    except BaseException:
        # Diagnostic observers are non-authoritative and cannot alter bridge behavior.
        pass


def _peer_uid(connection: socket.socket) -> int:
    peer_credential = getattr(socket, "SO_PEERCRED", None)
    if peer_credential is None:
        raise FixedRunnerBridgeError("peer_identity_unavailable")
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, peer_credential, struct.calcsize("3i"))
        _pid, uid, _gid = struct.unpack("3i", raw)
    except (OSError, struct.error) as exc:
        raise FixedRunnerBridgeError("peer_identity_unavailable") from exc
    return cast(int, uid)


def _receive_frame(connection: socket.socket) -> JsonObject:
    frame = bytearray()
    while True:
        chunk = connection.recv(1)
        if not chunk:
            raise FixedRunnerBridgeError("bridge_disconnected")
        frame.extend(chunk)
        if len(frame) > MAX_FRAME_BYTES:
            raise FixedRunnerBridgeError("frame_too_large")
        if chunk == b"\n":
            break
    try:
        text = frame[:-1].decode("utf-8")
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, FixedRunnerBridgeError) as exc:
        raise FixedRunnerBridgeError("frame_invalid") from exc
    if not isinstance(document, dict):
        raise FixedRunnerBridgeError("frame_invalid")
    result = cast(JsonObject, document)
    if text != canonical_json(result):
        raise FixedRunnerBridgeError("frame_not_canonical")
    return result


def _send_frame(connection: socket.socket, document: JsonObject) -> None:
    payload = canonical_json(document).encode("utf-8") + b"\n"
    if len(payload) > MAX_FRAME_BYTES:
        raise FixedRunnerBridgeError("frame_too_large")
    connection.sendall(payload)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise FixedRunnerBridgeError("duplicate_frame_key")
        document[key] = value
    return document


def _validate_closed_envelope(envelope: JsonObject, state: NodeState) -> None:
    if (
        envelope.get("delivery_schema_version") != "1"
        or envelope.get("workspace_id") != state.workspace_id
        or envelope.get("mission_template_id") != "synthetic_read_review_v1"
        or envelope.get("gateway_lifecycle_state") != "claimed"
        or envelope.get("gateway_delivery_recorded") is not True
        or envelope.get("runner_state_authority") != "runner_reported_only"
        or envelope.get("model_provider_state_known") is not False
    ):
        raise FixedRunnerBridgeError("envelope_authority_invalid")
    payload = envelope.get("template_payload")
    if not isinstance(payload, dict):
        raise FixedRunnerBridgeError("template_payload_invalid")
    expected: JsonObject = {
        "operations": [
            {"sequence": 1, "tool_name": FIXED_OPERATIONS[0][1]},
            {"sequence": 2, "tool_name": FIXED_OPERATIONS[1][1]},
        ]
    }
    if payload.get("operations") != expected["operations"]:
        raise FixedRunnerBridgeError("template_operations_invalid")
    digest = envelope.get("template_payload_digest")
    if digest != sha256_digest(payload):
        raise FixedRunnerBridgeError("template_digest_invalid")


def _closed_status(session: FixedMissionSession, status: str) -> JsonObject:
    next_required_affordance = (
        "none"
        if session.terminal
        else {
            1: "mission.step.1",
            2: "mission.step.2",
            3: "mission.complete",
            4: "none",
        }[session.receipt.next_operation_index]
    )
    return {
        "status": status,
        "mission_id": session.receipt.mission_id,
        "claim_id": session.receipt.claim_id,
        "envelope_digest": session.receipt.envelope_digest,
        "profile_digest": session.profile_digest,
        "next_operation_index": session.receipt.next_operation_index,
        "next_required_affordance": next_required_affordance,
        "handoff_nonce_digest": session.receipt.handoff_nonce_digest,
        "last_closed_status": session.receipt.last_closed_status,
        "runner_state_authority": "runner_reported_only",
        "model_provider_state_known": False,
    }


def _denied_status(
    session: FixedMissionSession,
    reason_code: str,
) -> JsonObject:
    if not session.terminal:
        session.receipt = session.receipt.close(
            session.receipt_path,
            status="failed_closed",
            reason_code=reason_code,
        )
    return {
        **_closed_status(session, "denied"),
        "reason_code": reason_code,
    }


def _mission_session_id(receipt: BridgeReceipt) -> str:
    envelope_prefix = receipt.envelope_digest.removeprefix("sha256:")[:16]
    return f"mission:{receipt.mission_id}:{receipt.claim_id}:{envelope_prefix}"


def _gateway_report_revision(
    document: JsonObject,
    *,
    expected_state: str,
) -> int:
    if document.get("gateway_lifecycle_state") != expected_state:
        raise FixedRunnerBridgeError("gateway_report_not_advanced")
    return _required_integer(document, "gateway_lifecycle_revision", minimum=2)


def _report_id() -> str:
    return f"mreport_{secrets.token_hex(16)}"


def _validate_receipt(receipt: BridgeReceipt) -> None:
    if (
        not _MISSION_ID.fullmatch(receipt.mission_id)
        or not _CLAIM_ID.fullmatch(receipt.claim_id)
        or not _DIGEST.fullmatch(receipt.envelope_digest)
        or not _DIGEST.fullmatch(receipt.handoff_nonce_digest)
        or receipt.next_operation_index not in {1, 2, 3, 4}
        or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", receipt.last_closed_status)
        or not re.fullmatch(
            r"[a-z][a-z0-9_]{2,63}",
            receipt.last_closed_reason_code,
        )
    ):
        raise FixedRunnerBridgeError("receipt_invalid")


def _validate_profile_digest(value: str) -> None:
    if not _DIGEST.fullmatch(value):
        raise FixedRunnerBridgeError("profile_digest_invalid")


def _required_matching(document: JsonObject, key: str, pattern: re.Pattern[str]) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise FixedRunnerBridgeError(f"{key}_invalid")
    return value


def _required_integer(document: JsonObject, key: str, *, minimum: int) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise FixedRunnerBridgeError(f"{key}_invalid")
    return value


def _preflight_receipt_path(path: Path) -> None:
    parent_descriptor = _open_owned_directory(
        path.parent,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        allowed_modes=None,
        reason_code="receipt_parent_unsafe",
    )
    try:
        _require_leaf_absent(
            parent_descriptor,
            path.name,
            reason_code="restart_ambiguity",
        )
    finally:
        os.close(parent_descriptor)


def _preflight_socket_path(path: Path, *, expected_gid: int) -> None:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise FixedRunnerBridgeError("socket_path_invalid")
    parent = path.parent
    if parent == Path("/"):
        raise FixedRunnerBridgeError("socket_parent_unsafe")
    try:
        parent_descriptor = _open_owned_directory(
            parent,
            expected_uid=os.geteuid(),
            expected_gid=expected_gid,
            allowed_modes={0o770},
            reason_code="socket_parent_unsafe",
        )
    except FixedRunnerBridgeError:
        grandparent_descriptor = _open_owned_directory(
            parent.parent,
            expected_uid=os.geteuid(),
            expected_gid=os.getegid(),
            allowed_modes=None,
            reason_code="socket_parent_unsafe",
        )
        try:
            _require_leaf_absent(
                grandparent_descriptor,
                parent.name,
                reason_code="socket_parent_unsafe",
            )
            os.mkdir(parent.name, mode=0o770, dir_fd=grandparent_descriptor)
            parent_descriptor = os.open(
                parent.name,
                _directory_flags(),
                dir_fd=grandparent_descriptor,
            )
            os.fchown(parent_descriptor, os.geteuid(), expected_gid)
            os.fchmod(parent_descriptor, 0o770)
            os.fsync(grandparent_descriptor)
        except OSError as exc:
            raise FixedRunnerBridgeError("socket_parent_unavailable") from exc
        finally:
            os.close(grandparent_descriptor)
        details = os.fstat(parent_descriptor)
        if (
            not stat.S_ISDIR(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o770
            or details.st_uid != os.geteuid()
            or details.st_gid != expected_gid
        ):
            os.close(parent_descriptor)
            raise FixedRunnerBridgeError("socket_parent_unsafe") from None
    try:
        _require_leaf_absent(
            parent_descriptor,
            path.name,
            reason_code="socket_path_unsafe",
        )
    finally:
        os.close(parent_descriptor)


def _read_private_document(path: Path) -> JsonObject:
    parent_descriptor = _open_owned_directory(
        path.parent,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        allowed_modes=None,
        reason_code="receipt_parent_unsafe",
    )
    try:
        descriptor = os.open(
            path.name,
            _file_flags(os.O_RDONLY),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        os.close(parent_descriptor)
        raise FixedRunnerBridgeError("receipt_unavailable") from exc
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
        ):
            raise FixedRunnerBridgeError("receipt_permissions_invalid")
        raw = os.read(descriptor, MAX_FRAME_BYTES + 1)
    finally:
        os.close(descriptor)
        os.close(parent_descriptor)
    if len(raw) > MAX_FRAME_BYTES:
        raise FixedRunnerBridgeError("receipt_too_large")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, FixedRunnerBridgeError) as exc:
        raise FixedRunnerBridgeError("receipt_invalid") from exc
    if not isinstance(document, dict):
        raise FixedRunnerBridgeError("receipt_invalid")
    result = cast(JsonObject, document)
    if raw.decode("utf-8") != canonical_json(result):
        raise FixedRunnerBridgeError("receipt_not_canonical")
    return result


def _write_new_private(path: Path, document: JsonObject) -> None:
    parent_descriptor = _open_owned_directory(
        path.parent,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        allowed_modes=None,
        reason_code="receipt_parent_unsafe",
    )
    try:
        descriptor = os.open(
            path.name,
            _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
            dir_fd=parent_descriptor,
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json(document).encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent_descriptor)
    except FileExistsError as exc:
        raise FixedRunnerBridgeError("restart_ambiguity") from exc
    except OSError as exc:
        raise FixedRunnerBridgeError("receipt_write_failed") from exc
    finally:
        os.close(parent_descriptor)


def _write_private_atomic(path: Path, document: JsonObject) -> None:
    parent_descriptor = _open_owned_directory(
        path.parent,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
        allowed_modes=None,
        reason_code="receipt_parent_unsafe",
    )
    temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
    temporary_descriptor = -1
    try:
        current_descriptor = os.open(
            path.name,
            _file_flags(os.O_RDONLY),
            dir_fd=parent_descriptor,
        )
        try:
            current = os.fstat(current_descriptor)
            if (
                not stat.S_ISREG(current.st_mode)
                or stat.S_IMODE(current.st_mode) != 0o600
                or current.st_uid != os.geteuid()
                or current.st_gid != os.getegid()
            ):
                raise FixedRunnerBridgeError("receipt_path_unsafe")
        finally:
            os.close(current_descriptor)
        temporary_descriptor = os.open(
            temporary_name,
            _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
            dir_fd=parent_descriptor,
        )
        payload = canonical_json(document).encode("utf-8")
        written = os.write(temporary_descriptor, payload)
        if written != len(payload):
            raise OSError("short receipt write")
        os.fsync(temporary_descriptor)
        os.close(temporary_descriptor)
        temporary_descriptor = -1
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        os.fsync(parent_descriptor)
    except OSError as exc:
        try:
            os.unlink(temporary_name, dir_fd=parent_descriptor)
        except OSError:
            pass
        raise FixedRunnerBridgeError("receipt_write_failed") from exc
    finally:
        if temporary_descriptor >= 0:
            os.close(temporary_descriptor)
        os.close(parent_descriptor)


def _open_owned_directory(
    path: Path,
    *,
    expected_uid: int,
    expected_gid: int,
    allowed_modes: set[int] | None,
    reason_code: str,
) -> int:
    if not path.is_absolute():
        raise FixedRunnerBridgeError(reason_code)
    try:
        descriptor = os.open(path, _directory_flags())
    except OSError as exc:
        raise FixedRunnerBridgeError(reason_code) from exc
    details = os.fstat(descriptor)
    mode = stat.S_IMODE(details.st_mode)
    mode_is_allowed = (
        mode in allowed_modes if allowed_modes is not None else mode & 0o022 == 0
    )
    if (
        not stat.S_ISDIR(details.st_mode)
        or details.st_uid != expected_uid
        or details.st_gid != expected_gid
        or not mode_is_allowed
    ):
        os.close(descriptor)
        raise FixedRunnerBridgeError(reason_code)
    return descriptor


def _require_leaf_absent(parent_descriptor: int, name: str, *, reason_code: str) -> None:
    if name in {"", ".", ".."} or "/" in name:
        raise FixedRunnerBridgeError(reason_code)
    try:
        os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise FixedRunnerBridgeError(reason_code) from exc
    raise FixedRunnerBridgeError(reason_code)


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _file_flags(base: int) -> int:
    flags = base
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags
