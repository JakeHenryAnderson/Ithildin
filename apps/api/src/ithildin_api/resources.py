"""Shared policy resource construction helpers."""

from __future__ import annotations

from ithildin_schemas import JsonObject, ToolRisk

from ithildin_api.http_tools import HttpAllowlist, http_resource_from_url
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.sandbox_artifacts import (
    SANDBOX_ARTIFACT_WRITE_TEXT_TOOL,
    sandbox_artifact_resource_from_arguments,
)


def resource_from_arguments(
    arguments: JsonObject,
    risk: ToolRisk,
    *,
    tool_name: str | None = None,
    http_allowlist: HttpAllowlist | None = None,
    read_tool_executor: ReadToolExecutor | None = None,
) -> JsonObject:
    url = arguments.get("url")
    if risk == ToolRisk.NETWORK and isinstance(url, str):
        return http_resource_from_url(url, http_allowlist or HttpAllowlist(()))

    if tool_name == SANDBOX_ARTIFACT_WRITE_TEXT_TOOL:
        resource = sandbox_artifact_resource_from_arguments(arguments, read_tool_executor)
        resource["risk"] = risk.value
        return resource

    if risk in {ToolRisk.READ, ToolRisk.WRITE_PROPOSAL} and read_tool_executor is not None:
        path_resource = read_tool_executor.resource_from_arguments(arguments, tool_name=tool_name)
        path_resource["risk"] = risk.value
        return path_resource

    generic_resource: JsonObject = {
        "type": "tool_call",
        "in_scope": True,
        "risk": risk.value,
    }
    if "path" in arguments:
        generic_resource["path"] = arguments["path"]
        generic_resource["type"] = "file"
    if "workspace_id" in arguments:
        generic_resource["workspace_id"] = arguments["workspace_id"]
    return generic_resource
