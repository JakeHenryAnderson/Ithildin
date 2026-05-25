"""MCP adapter for Ithildin governed tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.config import Settings, load_settings
from ithildin_api.database import initialize_database
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import JsonObject
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

DEFAULT_AGENT_PRINCIPAL: JsonObject = {
    "id": "agent:mcp-local",
    "type": "agent",
    "roles": ["AgentDeveloper"],
}


@dataclass(frozen=True)
class IthildinMcpAdapter:
    registry: ToolRegistry
    tool_call_service: GovernedToolCallService

    async def list_tools(self) -> list[types.Tool]:
        tools: list[types.Tool] = []
        for registered_tool in self.registry.list_tools():
            manifest = registered_tool.manifest
            mcp_metadata = manifest.mcp or {}
            if mcp_metadata.get("exposed") is not True:
                continue
            annotations_data = mcp_metadata.get("annotations")
            annotations = (
                types.ToolAnnotations(**cast(dict[str, Any], annotations_data))
                if isinstance(annotations_data, dict)
                else None
            )
            tools.append(
                types.Tool(
                    name=manifest.name,
                    title=manifest.title,
                    description=manifest.title,
                    inputSchema=manifest.input_schema,
                    annotations=annotations,
                    _meta={"manifest_hash": registered_tool.manifest_hash},
                )
            )
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, object]) -> types.CallToolResult:
        result = self.tool_call_service.call_tool(
            tool_name=tool_name,
            arguments=_json_object(arguments),
            principal=DEFAULT_AGENT_PRINCIPAL,
            session_id="mcp-stdio",
        )
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=json.dumps(result.content, sort_keys=True),
                )
            ],
            structuredContent={
                "status": result.status,
                "request_id": result.request_id,
                "tool_name": result.tool_name,
                **result.content,
            },
            isError=result.is_error,
        )


def create_mcp_server(adapter: IthildinMcpAdapter) -> Server:
    server = Server("ithildin-mcp")

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        return await adapter.list_tools()

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, object]) -> types.CallToolResult:
        return await adapter.call_tool(name, arguments)

    return server


def create_adapter(settings: Settings | None = None) -> IthildinMcpAdapter:
    resolved_settings = settings or load_settings()
    initialize_database(resolved_settings.db_path)
    audit_writer = AuditWriter(resolved_settings.db_path, resolved_settings.audit_log_path)
    audit_writer.initialize()
    approval_store = ApprovalStore(resolved_settings.db_path)
    approval_store.initialize()
    approval_service = ApprovalService(
        approval_store,
        audit_writer,
        default_expiry=timedelta(seconds=resolved_settings.approval_expiry_seconds),
    )
    registry = ToolRegistry.load(resolved_settings.manifest_dir)
    policy_evaluator = PolicyEvaluator.load(resolved_settings.policy_path)
    tool_call_service = GovernedToolCallService(
        registry,
        policy_evaluator,
        approval_service,
        audit_writer,
    )
    return IthildinMcpAdapter(registry=registry, tool_call_service=tool_call_service)


async def run_stdio_server(settings: Settings | None = None) -> None:
    server = create_mcp_server(create_adapter(settings))
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _json_object(value: dict[str, object]) -> JsonObject:
    return cast(JsonObject, value)
