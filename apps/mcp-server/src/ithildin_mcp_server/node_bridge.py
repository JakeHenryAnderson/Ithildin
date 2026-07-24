"""No-argument MCP bridge for the reviewed fixed Ithildin Node mission profile."""

from __future__ import annotations

import json
import socket
from typing import Protocol, cast

from ithildin_schemas import JsonObject, canonical_json
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

PROTOCOL_VERSION = "1"
SOCKET_PATH = "/run/ithildin-node/mission.sock"
MAX_FRAME_BYTES = 16_384
OPERATION_TIMEOUT_SECONDS = 120
FIXED_PROFILE_DIGEST = "sha256:90b94d725640768f1a7d665e979bbe11f263a4ff264591a5348d0b5820db3e92"
AFFORDANCES = ("mission.step.1", "mission.step.2", "mission.complete")
_HANDOFF_KEYS = {
    "protocol_version",
    "mission_id",
    "claim_id",
    "envelope_digest",
    "handoff_nonce",
    "next_operation_index",
    "profile_digest",
}


class NodeBridgeError(RuntimeError):
    """Closed bridge error without runner output or credential material."""


class BridgeTransport(Protocol):
    def invoke(self, affordance: str) -> JsonObject: ...

    def close(self) -> None: ...


class UnixNodeBridgeTransport:
    """One process-memory-only mission handoff over the fixed local socket."""

    def __init__(
        self,
        *,
        socket_path: str = SOCKET_PATH,
        profile_digest: str = FIXED_PROFILE_DIGEST,
    ) -> None:
        self.socket_path = socket_path
        self.profile_digest = profile_digest
        self._connection: socket.socket | None = None
        self._handoff: JsonObject | None = None

    def invoke(self, affordance: str) -> JsonObject:
        if affordance not in AFFORDANCES:
            raise NodeBridgeError("unknown_affordance")
        self._ensure_connected()
        handoff = cast(JsonObject, self._handoff)
        request: JsonObject = {
            "protocol_version": PROTOCOL_VERSION,
            "affordance": affordance,
            "mission_id": handoff["mission_id"],
            "claim_id": handoff["claim_id"],
            "envelope_digest": handoff["envelope_digest"],
            "handoff_nonce": handoff["handoff_nonce"],
            "operation_index": handoff["next_operation_index"],
            "profile_digest": self.profile_digest,
        }
        connection = cast(socket.socket, self._connection)
        _send_frame(connection, request)
        response = _receive_frame(connection)
        for key in ("mission_id", "claim_id", "envelope_digest", "profile_digest"):
            if response.get(key) != request[key]:
                raise NodeBridgeError("response_binding_conflict")
        next_index = response.get("next_operation_index")
        if not isinstance(next_index, int) or isinstance(next_index, bool):
            raise NodeBridgeError("response_index_invalid")
        self._handoff = {**handoff, "next_operation_index": next_index}
        return response

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._handoff = None

    def _ensure_connected(self) -> None:
        if self._connection is not None:
            return
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(OPERATION_TIMEOUT_SECONDS)
        try:
            connection.connect(self.socket_path)
            handoff = _receive_frame(connection)
            _validate_handoff(handoff, self.profile_digest)
        except (OSError, NodeBridgeError):
            connection.close()
            raise
        self._connection = connection
        self._handoff = handoff


class FixedNodeBridgeAdapter:
    """Expose only the three reviewed no-argument affordances."""

    def __init__(self, transport: BridgeTransport) -> None:
        self.transport = transport

    async def list_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name=name,
                title=name,
                description="Fixed Ithildin mission affordance",
                inputSchema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                },
                annotations=types.ToolAnnotations(readOnlyHint=False),
            )
            for name in AFFORDANCES
        ]

    async def call_tool(
        self, name: str, arguments: dict[str, object] | None
    ) -> types.CallToolResult:
        if name not in AFFORDANCES:
            return _result(name, {"status": "denied", "reason_code": "unknown_affordance"}, True)
        if arguments:
            return _result(
                name,
                {"status": "denied", "reason_code": "arguments_not_allowed"},
                True,
            )
        try:
            response = self.transport.invoke(name)
        except (NodeBridgeError, OSError, TimeoutError):
            return _result(
                name,
                {"status": "denied", "reason_code": "node_bridge_unavailable"},
                True,
            )
        return _result(name, response, response.get("status") == "denied")


def create_node_bridge_server(adapter: FixedNodeBridgeAdapter) -> Server:
    server = Server("ithildin-fixed-node-bridge")

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        return await adapter.list_tools()

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, object] | None
    ) -> types.CallToolResult:
        return await adapter.call_tool(name, arguments)

    return server


async def run_stdio_node_bridge() -> None:
    transport = UnixNodeBridgeTransport()
    server = create_node_bridge_server(FixedNodeBridgeAdapter(transport))
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        transport.close()


def _validate_handoff(document: JsonObject, profile_digest: str) -> None:
    if set(document) != _HANDOFF_KEYS:
        raise NodeBridgeError("handoff_shape_invalid")
    if (
        document.get("protocol_version") != PROTOCOL_VERSION
        or document.get("profile_digest") != profile_digest
        or not isinstance(document.get("next_operation_index"), int)
        or isinstance(document.get("next_operation_index"), bool)
    ):
        raise NodeBridgeError("handoff_binding_invalid")


def _receive_frame(connection: socket.socket) -> JsonObject:
    frame = bytearray()
    while True:
        chunk = connection.recv(1)
        if not chunk:
            raise NodeBridgeError("node_bridge_disconnected")
        frame.extend(chunk)
        if len(frame) > MAX_FRAME_BYTES:
            raise NodeBridgeError("node_bridge_frame_too_large")
        if chunk == b"\n":
            break
    try:
        text = frame[:-1].decode("utf-8")
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, NodeBridgeError) as exc:
        raise NodeBridgeError("node_bridge_frame_invalid") from exc
    if not isinstance(raw, dict):
        raise NodeBridgeError("node_bridge_frame_invalid")
    document = cast(JsonObject, raw)
    if text != canonical_json(document):
        raise NodeBridgeError("node_bridge_frame_not_canonical")
    return document


def _send_frame(connection: socket.socket, document: JsonObject) -> None:
    payload = canonical_json(document).encode("utf-8") + b"\n"
    if len(payload) > MAX_FRAME_BYTES:
        raise NodeBridgeError("node_bridge_frame_too_large")
    connection.sendall(payload)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise NodeBridgeError("node_bridge_duplicate_key")
        document[key] = value
    return document


def _result(name: str, response: JsonObject, is_error: bool) -> types.CallToolResult:
    structured: JsonObject = {"tool_name": name, **response}
    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=json.dumps(structured, sort_keys=True),
            )
        ],
        structuredContent=structured,
        isError=is_error,
    )


if __name__ == "__main__":
    import anyio

    anyio.run(run_stdio_node_bridge)
