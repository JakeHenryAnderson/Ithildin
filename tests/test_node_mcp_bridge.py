from __future__ import annotations

import asyncio
import json
import socket

import pytest
from ithildin_mcp_server import node_bridge
from ithildin_mcp_server.node_bridge import (
    AFFORDANCE_DESCRIPTIONS,
    AFFORDANCES,
    FIXED_MISSION_INSTRUCTIONS,
    FIXED_PROFILE_DIGEST,
    FixedNodeBridgeAdapter,
    NodeBridgeError,
)
from ithildin_schemas import JsonObject, canonical_json


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.closed = False

    def invoke(self, affordance: str) -> JsonObject:
        self.calls.append(affordance)
        return {
            "status": "operation_closed",
            "mission_id": "mission_" + ("1" * 32),
            "claim_id": "mclaim_" + ("2" * 32),
            "envelope_digest": "sha256:" + ("3" * 64),
            "profile_digest": FIXED_PROFILE_DIGEST,
            "next_operation_index": len(self.calls) + 1,
            "handoff_nonce_digest": "sha256:" + ("4" * 64),
            "last_closed_status": f"operation_{len(self.calls)}_closed",
            "runner_state_authority": "runner_reported_only",
            "model_provider_state_known": False,
        }

    def close(self) -> None:
        self.closed = True


def test_mcp_bridge_lists_only_three_no_argument_affordances() -> None:
    adapter = FixedNodeBridgeAdapter(RecordingTransport())
    tools = asyncio.run(adapter.list_tools())

    assert [tool.name for tool in tools] == list(AFFORDANCES)
    assert [tool.description for tool in tools] == [
        AFFORDANCE_DESCRIPTIONS[name] for name in AFFORDANCES
    ]
    assert all(
        tool.inputSchema
        == {"type": "object", "additionalProperties": False, "properties": {}}
        for tool in tools
    )
    assert all(tool.annotations is not None for tool in tools)
    assert all(tool.annotations.readOnlyHint is False for tool in tools if tool.annotations)

    initialization = node_bridge.create_node_bridge_server(
        adapter
    ).create_initialization_options()
    assert initialization.instructions == FIXED_MISSION_INSTRUCTIONS


def test_mcp_bridge_invokes_closed_transport_and_denies_arguments() -> None:
    transport = RecordingTransport()
    adapter = FixedNodeBridgeAdapter(transport)

    result = asyncio.run(adapter.call_tool("mission.step.1", {}))
    denied_arguments = asyncio.run(adapter.call_tool("mission.step.2", {"path": "."}))
    denied_unknown = asyncio.run(adapter.call_tool("shell.run", {}))

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == "operation_closed"
    assert transport.calls == ["mission.step.1"]
    assert denied_arguments.isError is True
    assert denied_arguments.structuredContent is not None
    assert denied_arguments.structuredContent["reason_code"] == "arguments_not_allowed"
    assert denied_unknown.isError is True
    assert denied_unknown.structuredContent is not None
    assert denied_unknown.structuredContent["reason_code"] == "unknown_affordance"


def test_mcp_bridge_handoff_requires_exact_profile_and_shape() -> None:
    handoff: JsonObject = {
        "protocol_version": "1",
        "mission_id": "mission_" + ("1" * 32),
        "claim_id": "mclaim_" + ("2" * 32),
        "envelope_digest": "sha256:" + ("3" * 64),
        "handoff_nonce": "4" * 64,
        "next_operation_index": 1,
        "profile_digest": FIXED_PROFILE_DIGEST,
    }
    node_bridge._validate_handoff(handoff, FIXED_PROFILE_DIGEST)
    with pytest.raises(NodeBridgeError, match="handoff_binding_invalid"):
        node_bridge._validate_handoff(
            {**handoff, "profile_digest": "sha256:" + ("f" * 64)},
            FIXED_PROFILE_DIGEST,
        )
    with pytest.raises(NodeBridgeError, match="handoff_shape_invalid"):
        node_bridge._validate_handoff({**handoff, "mission": "free-form"}, FIXED_PROFILE_DIGEST)


def test_mcp_bridge_frames_are_canonical_bounded_and_duplicate_safe() -> None:
    document: JsonObject = {"a": 1, "b": "two"}
    left, right = socket.socketpair()
    try:
        node_bridge._send_frame(right, document)
        assert node_bridge._receive_frame(left) == document
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair()
    try:
        right.sendall(b'{"b":2,"a":1}\n')
        with pytest.raises(NodeBridgeError, match="not_canonical"):
            node_bridge._receive_frame(left)
    finally:
        left.close()
        right.close()

    left, right = socket.socketpair()
    try:
        right.sendall(b'{"a":1,"a":2}\n')
        with pytest.raises(NodeBridgeError, match="frame_invalid"):
            node_bridge._receive_frame(left)
    finally:
        left.close()
        right.close()

    assert len(canonical_json(document)) < node_bridge.MAX_FRAME_BYTES
    assert json.loads(canonical_json(document)) == document
