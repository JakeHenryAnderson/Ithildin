from __future__ import annotations

from pathlib import Path

import pytest
from ithildin_api.registry import (
    DuplicateToolManifest,
    InvalidToolManifest,
    ToolRegistry,
    UnknownToolDenied,
)


def write_manifest(path: Path, name: str = "fs.read") -> None:
    path.write_text(
        f"""
name: {name}
version: 1.0.0
title: Read file
risk: read
category: filesystem
mcp:
  exposed: true
input_schema:
  type: object
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )


def test_empty_manifest_directory_loads_empty_registry(tmp_path: Path) -> None:
    registry = ToolRegistry.load(tmp_path)

    assert registry.list_tools() == []


def test_valid_yaml_manifest_loads_tool(tmp_path: Path) -> None:
    write_manifest(tmp_path / "fs-read.yaml")

    registry = ToolRegistry.load(tmp_path)
    tools = registry.list_tools()

    assert len(tools) == 1
    assert tools[0].manifest.name == "fs.read"
    assert tools[0].manifest.version == "1.0.0"
    assert tools[0].manifest_hash.startswith("sha256:")


def test_manifest_hash_is_stable(tmp_path: Path) -> None:
    write_manifest(tmp_path / "fs-read.yaml")

    first_registry = ToolRegistry.load(tmp_path)
    second_registry = ToolRegistry.load(tmp_path)

    assert first_registry.get_tool("fs.read").manifest_hash == second_registry.get_tool(
        "fs.read"
    ).manifest_hash


def test_invalid_yaml_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("name: [", encoding="utf-8")

    with pytest.raises(InvalidToolManifest):
        ToolRegistry.load(tmp_path)


def test_invalid_manifest_schema_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "invalid.yaml").write_text("name: fs.read\n", encoding="utf-8")

    with pytest.raises(InvalidToolManifest):
        ToolRegistry.load(tmp_path)


def test_duplicate_tool_names_fail_closed(tmp_path: Path) -> None:
    write_manifest(tmp_path / "one.yaml", name="fs.read")
    write_manifest(tmp_path / "two.yml", name="fs.read")

    with pytest.raises(DuplicateToolManifest):
        ToolRegistry.load(tmp_path)


def test_non_manifest_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")

    registry = ToolRegistry.load(tmp_path)

    assert registry.list_tools() == []


def test_unknown_tool_lookup_has_audit_ready_denial_metadata(tmp_path: Path) -> None:
    registry = ToolRegistry.load(tmp_path)

    with pytest.raises(UnknownToolDenied) as exc_info:
        registry.get_tool("fs.missing")

    assert exc_info.value.audit_metadata == {
        "event_type": "tool.call.denied",
        "tool_name": "fs.missing",
        "decision": "deny",
        "reason": "unknown tool",
    }


def test_committed_read_tool_manifests_load() -> None:
    registry = ToolRegistry.load(Path("tool-manifests"))

    assert [tool.manifest.name for tool in registry.list_tools()] == [
        "fs.list",
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "fs.search",
        "fs.stat",
        "git.diff",
        "git.log",
        "git.status",
        "http.fetch",
    ]
