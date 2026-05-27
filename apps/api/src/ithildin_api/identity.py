"""Local trusted principal registry."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from ithildin_schemas import JsonObject
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError, field_validator


class PrincipalRegistryError(RuntimeError):
    """Raised when trusted principal configuration is invalid."""


class UnknownPrincipalError(PrincipalRegistryError):
    """Raised when a principal cannot be resolved from the trusted registry."""


class DisabledPrincipalError(PrincipalRegistryError):
    """Raised when a disabled principal is used for active work."""


class PrincipalType(StrEnum):
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"
    MODEL = "model"
    TOOL = "tool"
    ENDPOINT = "endpoint"
    TENANT = "tenant"


class PrincipalRole(StrEnum):
    OWNER = "Owner"
    ADMIN = "Admin"
    SECURITY_ADMIN = "SecurityAdmin"
    DEVELOPER = "Developer"
    APPROVER = "Approver"
    AUDITOR = "Auditor"
    AGENT_READ_ONLY = "AgentReadOnly"
    AGENT_DEVELOPER = "AgentDeveloper"


_PRINCIPAL_ID_PATTERN = re.compile(
    r"^(admin|user|agent|model|tool|endpoint|tenant):[A-Za-z0-9][A-Za-z0-9_.@/-]*$"
)


class PrincipalRecord(StrictBaseModel):
    id: str
    type: PrincipalType
    display_name: str
    roles: list[PrincipalRole] = Field(default_factory=list)
    enabled: bool = True
    metadata: JsonObject = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def id_must_have_known_prefix(cls, value: str) -> str:
        if not _PRINCIPAL_ID_PATTERN.match(value):
            raise ValueError("principal id must use a known prefix")
        return value

    def safe_summary(self) -> JsonObject:
        return {
            "id": self.id,
            "type": self.type.value,
            "display_name": self.display_name,
            "roles": [role.value for role in self.roles],
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    def trusted_principal(self) -> JsonObject:
        return {
            "id": self.id,
            "type": self.type.value,
            "roles": [role.value for role in self.roles],
        }


class PrincipalRegistryDocument(StrictBaseModel):
    principals: list[PrincipalRecord] = Field(default_factory=list)


class PrincipalRegistry:
    def __init__(self, principals: dict[str, PrincipalRecord], source_path: Path) -> None:
        self._principals = principals
        self.source_path = source_path

    @classmethod
    def load(cls, path: Path, *, require_registry: bool = True) -> PrincipalRegistry:
        if not path.exists():
            if require_registry:
                raise PrincipalRegistryError(f"principal registry not found: {path}")
            return cls({}, path)

        try:
            raw_document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise PrincipalRegistryError(f"invalid YAML principal registry: {path}") from exc

        if not isinstance(raw_document, dict):
            raise PrincipalRegistryError(f"principal registry must be a mapping: {path}")

        try:
            document = PrincipalRegistryDocument.model_validate(_json_object(raw_document))
        except ValidationError as exc:
            raise PrincipalRegistryError(f"invalid principal registry schema: {path}") from exc

        principals: dict[str, PrincipalRecord] = {}
        for principal in document.principals:
            if principal.id in principals:
                raise PrincipalRegistryError(f"duplicate principal id: {principal.id}")
            if principal.type.value != principal.id.split(":", 1)[0]:
                raise PrincipalRegistryError(
                    f"principal id/type mismatch for {principal.id}: {principal.type.value}"
                )
            principals[principal.id] = principal

        return cls(principals, path)

    @property
    def count(self) -> int:
        return len(self._principals)

    def status(self) -> JsonObject:
        enabled_count = sum(1 for principal in self._principals.values() if principal.enabled)
        return {
            "path": self.source_path.as_posix(),
            "count": self.count,
            "enabled_count": enabled_count,
        }

    def list_principals(self) -> list[PrincipalRecord]:
        return sorted(self._principals.values(), key=lambda principal: principal.id)

    def get(self, principal_id: str) -> PrincipalRecord:
        try:
            return self._principals[principal_id]
        except KeyError as exc:
            raise UnknownPrincipalError(f"unknown principal: {principal_id}") from exc

    def resolve_active(self, principal_id: str) -> PrincipalRecord:
        principal = self.get(principal_id)
        if not principal.enabled:
            raise DisabledPrincipalError(f"disabled principal: {principal_id}")
        return principal


def principal_id_from_json(principal: JsonObject) -> str | None:
    principal_id = principal.get("id")
    return principal_id if isinstance(principal_id, str) else None


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise PrincipalRegistryError("principal registry keys must be strings")
        result[key] = item
    return result
