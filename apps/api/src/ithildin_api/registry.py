"""Trusted tool manifest registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from ithildin_schemas import JsonObject, ToolManifest, sha256_digest
from pydantic import ValidationError


class ToolRegistryError(RuntimeError):
    """Base class for registry startup failures."""


class InvalidToolManifest(ToolRegistryError):
    """Raised when a trusted manifest cannot be parsed or validated."""


class DuplicateToolManifest(ToolRegistryError):
    """Raised when more than one manifest declares the same tool name."""


@dataclass(frozen=True)
class RegisteredTool:
    manifest: ToolManifest
    manifest_hash: str
    source_path: Path

    def summary(self) -> JsonObject:
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "title": self.manifest.title,
            "risk": self.manifest.risk.value,
            "category": self.manifest.category,
            "manifest_hash": self.manifest_hash,
            "mcp": self.manifest.mcp or {},
        }


@dataclass(frozen=True)
class UnknownToolDenied(Exception):
    tool_name: str
    reason: str = "unknown tool"

    @property
    def audit_metadata(self) -> JsonObject:
        return {
            "event_type": "tool.call.denied",
            "tool_name": self.tool_name,
            "decision": "deny",
            "reason": self.reason,
        }


class ToolRegistry:
    def __init__(self, tools: dict[str, RegisteredTool]) -> None:
        self._tools = tools

    @classmethod
    def load(cls, manifest_dir: Path) -> ToolRegistry:
        tools: dict[str, RegisteredTool] = {}

        if not manifest_dir.exists():
            return cls(tools)

        for manifest_path in sorted(manifest_dir.iterdir()):
            if manifest_path.suffix not in {".yaml", ".yml"}:
                continue

            registered_tool = _load_manifest(manifest_path)
            tool_name = registered_tool.manifest.name
            if tool_name in tools:
                raise DuplicateToolManifest(f"duplicate tool manifest for {tool_name}")
            tools[tool_name] = registered_tool

        return cls(tools)

    def list_tools(self, principal: Optional[str] = None) -> list[RegisteredTool]:
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> RegisteredTool:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise UnknownToolDenied(tool_name=tool_name) from exc


def _load_manifest(manifest_path: Path) -> RegisteredTool:
    try:
        raw_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise InvalidToolManifest(f"invalid YAML in {manifest_path}") from exc

    if not isinstance(raw_manifest, dict):
        raise InvalidToolManifest(f"manifest must be a mapping: {manifest_path}")

    manifest_data = _json_object(raw_manifest)
    try:
        manifest = ToolManifest.model_validate(manifest_data)
    except ValidationError as exc:
        raise InvalidToolManifest(f"invalid tool manifest schema: {manifest_path}") from exc

    return RegisteredTool(
        manifest=manifest,
        manifest_hash=sha256_digest(manifest_data),
        source_path=manifest_path,
    )


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise InvalidToolManifest("manifest keys must be strings")
        result[key] = item
    return result
