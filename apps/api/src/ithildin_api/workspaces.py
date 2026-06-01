"""Trusted local workspace registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from ithildin_schemas import JsonObject
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError

from ithildin_api.yaml_utils import safe_load_no_duplicate_keys


class WorkspaceRegistryError(RuntimeError):
    """Raised when workspace configuration is invalid or unsafe."""


class WorkspaceRecord(StrictBaseModel):
    id: str
    root: str
    display_name: str
    enabled: bool = True
    metadata: JsonObject = Field(default_factory=dict)

    def safe_summary(self) -> JsonObject:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


class WorkspaceRegistryDocument(StrictBaseModel):
    version: str
    default_workspace_id: str
    workspaces: list[WorkspaceRecord]


class WorkspaceRegistry:
    def __init__(
        self,
        *,
        document: WorkspaceRegistryDocument,
        roots: dict[str, Path],
        path: Path,
        required: bool,
    ) -> None:
        self.document = document
        self.roots = roots
        self.path = path
        self.required = required
        self._records = {record.id: record for record in document.workspaces}

    @property
    def default_workspace_id(self) -> str:
        return self.document.default_workspace_id

    @classmethod
    def load(
        cls,
        registry_path: Path,
        *,
        require_registry: bool,
        fallback_root: Path,
        default_workspace_id: str,
    ) -> WorkspaceRegistry:
        if not registry_path.exists():
            if require_registry:
                raise WorkspaceRegistryError(f"workspace registry not found: {registry_path}")
            fallback = WorkspaceRecord(
                id=default_workspace_id,
                root=fallback_root.as_posix(),
                display_name="Default workspace",
            )
            document = WorkspaceRegistryDocument(
                version="generated-fallback",
                default_workspace_id=default_workspace_id,
                workspaces=[fallback],
            )
            return cls(
                document=document,
                roots={default_workspace_id: fallback_root.resolve(strict=False)},
                path=registry_path,
                required=require_registry,
            )

        try:
            raw_registry = safe_load_no_duplicate_keys(registry_path)
        except yaml.YAMLError as exc:
            raise WorkspaceRegistryError(
                f"invalid workspace registry YAML: {registry_path}: {exc}"
            ) from exc
        if not isinstance(raw_registry, dict):
            raise WorkspaceRegistryError(f"workspace registry must be a mapping: {registry_path}")
        try:
            document = WorkspaceRegistryDocument.model_validate(_json_object(raw_registry))
        except ValidationError as exc:
            raise WorkspaceRegistryError(
                f"invalid workspace registry schema: {registry_path}"
            ) from exc

        seen: set[str] = set()
        roots: dict[str, Path] = {}
        for record in document.workspaces:
            _validate_workspace_id(record.id)
            if record.id in seen:
                raise WorkspaceRegistryError(f"duplicate workspace id: {record.id}")
            seen.add(record.id)
            roots[record.id] = _resolve_root(record.root)

        if document.default_workspace_id not in seen:
            raise WorkspaceRegistryError(
                f"default workspace not found: {document.default_workspace_id}"
            )
        registry = cls(
            document=document,
            roots=roots,
            path=registry_path,
            required=require_registry,
        )
        if not registry.get(document.default_workspace_id).enabled:
            raise WorkspaceRegistryError("default workspace is disabled")

        return registry

    def get(self, workspace_id: str | None = None) -> WorkspaceRecord:
        resolved_id = workspace_id or self.default_workspace_id
        try:
            return self._records[resolved_id]
        except KeyError as exc:
            raise WorkspaceRegistryError(f"unknown workspace: {resolved_id}") from exc

    def resolve_active(self, workspace_id: str | None = None) -> tuple[WorkspaceRecord, Path]:
        record = self.get(workspace_id)
        if not record.enabled:
            raise WorkspaceRegistryError(f"workspace is disabled: {record.id}")
        return record, self.roots[record.id]

    def list_workspaces(self) -> list[WorkspaceRecord]:
        return list(self._records.values())

    def status(self) -> JsonObject:
        return {
            "required": self.required,
            "path": self.path.as_posix(),
            "default_workspace_id": self.default_workspace_id,
            "count": len(self._records),
            "enabled_count": sum(1 for record in self._records.values() if record.enabled),
        }


def _validate_workspace_id(workspace_id: str) -> None:
    if not workspace_id:
        raise WorkspaceRegistryError("workspace id must not be empty")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
    if any(char not in allowed for char in workspace_id):
        raise WorkspaceRegistryError(f"malformed workspace id: {workspace_id}")


def _resolve_root(root: str) -> Path:
    if not root:
        raise WorkspaceRegistryError("workspace root must not be empty")
    root_path = Path(root)
    if ".." in root_path.parts:
        raise WorkspaceRegistryError("workspace root must not contain traversal")
    return root_path.resolve(strict=False)


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise WorkspaceRegistryError("workspace registry keys must be strings")
        result[key] = item
    return result
