"""Shared policy resource construction helpers."""

from __future__ import annotations

from ithildin_schemas import JsonObject, ToolRisk

from ithildin_api.http_tools import HttpAllowlist, http_resource_from_url


def resource_from_arguments(
    arguments: JsonObject,
    risk: ToolRisk,
    *,
    http_allowlist: HttpAllowlist | None = None,
) -> JsonObject:
    url = arguments.get("url")
    if risk == ToolRisk.NETWORK and isinstance(url, str):
        return http_resource_from_url(url, http_allowlist or HttpAllowlist(()))

    resource: JsonObject = {
        "type": "tool_call",
        "in_scope": True,
        "risk": risk.value,
    }
    if "path" in arguments:
        resource["path"] = arguments["path"]
        resource["type"] = "file"
    if "workspace_id" in arguments:
        resource["workspace_id"] = arguments["workspace_id"]
    return resource
