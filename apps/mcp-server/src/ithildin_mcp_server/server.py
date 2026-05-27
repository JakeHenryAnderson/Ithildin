"""MCP adapter for Ithildin governed tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.config import Settings, load_settings
from ithildin_api.database import initialize_database
from ithildin_api.http_tools import HttpFetchExecutor
from ithildin_api.identity import (
    PrincipalRegistry,
    PrincipalRegistryError,
    filter_tools_for_principal,
)
from ithildin_api.patches import PatchProposalService, PatchProposalStore
from ithildin_api.policy import load_policy_engine
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.redaction import RedactionService
from ithildin_api.registry import ToolRegistry
from ithildin_api.storage import validate_storage_settings
from ithildin_api.telemetry import configure_telemetry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
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
    principal_registry: PrincipalRegistry | None = None

    async def list_tools(self) -> list[types.Tool]:
        tools: list[types.Tool] = []
        if self.principal_registry is None:
            registered_tools = self.registry.list_tools()
        else:
            try:
                principal = self.principal_registry.resolve_active("agent:mcp-local")
            except PrincipalRegistryError:
                registered_tools = []
            else:
                registered_tools = filter_tools_for_principal(
                    self.registry.list_tools(),
                    principal,
                    lambda tool: tool.manifest.risk,
                )
        for registered_tool in registered_tools:
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
    validate_storage_settings(resolved_settings)
    telemetry = configure_telemetry(resolved_settings)
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
    registry = ToolRegistry.load(
        resolved_settings.manifest_dir,
        lock_path=resolved_settings.manifest_lock_path,
        require_lock=resolved_settings.require_manifest_lock,
    )
    principal_registry = PrincipalRegistry.load(
        resolved_settings.principal_registry_path,
        require_registry=resolved_settings.require_known_principals,
    )
    policy_evaluator = load_policy_engine(resolved_settings)
    http_fetch_executor = HttpFetchExecutor.from_settings(
        http_allowlist=resolved_settings.http_allowlist,
        timeout_seconds=resolved_settings.http_timeout_seconds,
        max_response_bytes=resolved_settings.http_max_response_bytes,
        max_redirects=resolved_settings.http_max_redirects,
    )
    redaction_service = RedactionService.from_settings(
        extra_keys=resolved_settings.redaction_extra_keys,
        extra_patterns=resolved_settings.redaction_extra_patterns,
    )
    read_tool_executor = ReadToolExecutor.from_settings(
        workspace_root=resolved_settings.workspace_root,
        max_read_bytes=resolved_settings.max_read_bytes,
        search_result_limit=resolved_settings.search_result_limit,
        git_log_limit=resolved_settings.git_log_limit,
    )
    patch_store = PatchProposalStore(resolved_settings.db_path)
    patch_store.initialize()
    patch_proposal_service = PatchProposalService(
        patch_store,
        read_tool_executor.filesystem,
        resolved_settings.max_patch_bytes,
    )
    tool_call_service = GovernedToolCallService(
        registry,
        policy_evaluator,
        approval_service,
        audit_writer,
        read_tool_executor,
        patch_proposal_service,
        http_fetch_executor,
        redaction_service,
        principal_registry,
        telemetry,
    )
    return IthildinMcpAdapter(
        registry=registry,
        tool_call_service=tool_call_service,
        principal_registry=principal_registry,
    )


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
