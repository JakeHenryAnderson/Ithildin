"""Read-only Manager-local trusted-host descriptor registry."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from ithildin_schemas import JsonObject, sha256_digest
from ithildin_schemas.models import StrictBaseModel
from pydantic import ConfigDict, Field, ValidationError, field_validator

from ithildin_api.promotion_authority import TrustedHostAuthorityRecord
from ithildin_api.yaml_utils import safe_load_no_duplicate_keys


class TrustedHostRegistryError(RuntimeError):
    """Raised when trusted-host configuration is invalid or cannot be resolved."""


TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST = sha256_digest(
    {
        "schema": "ithildin.trusted-host-registry",
        "version": "2",
        "permissions": {
            "staging_create_exclusive_allowed": True,
            "host_write_allowed": False,
            "broad_host_write_allowed": False,
        },
        "root_resolver_refs": ["manager_local_trusted_host_staging_root"],
    }
)

_ID_PATTERN = re.compile(r"^thd_[a-z0-9][a-z0-9_-]{0,63}$")
_WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_STAGING_LABEL_PATTERN = re.compile(r"^host-staging://[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class TrustedHostDescriptorConfig(StrictBaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    descriptor_schema_version: Literal["2"]
    descriptor_id: str
    enabled: bool = True
    os_family: Literal["darwin", "linux"]
    filesystem_posture: Literal["local_create_exclusive"]
    operator_review_status: Literal["reviewed"]
    evidence_timestamp: datetime
    workspace_id: str
    staging_label: str
    staging_root_resolver_ref: Literal["manager_local_trusted_host_staging_root"]
    staging_create_exclusive_allowed: Literal[True]
    host_write_allowed: Literal[False]
    broad_host_write_allowed: Literal[False]

    @field_validator("descriptor_id")
    @classmethod
    def _descriptor_id_is_safe(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError("invalid trusted-host descriptor id")
        return value

    @field_validator("workspace_id")
    @classmethod
    def _workspace_id_is_safe(cls, value: str) -> str:
        if not _WORKSPACE_PATTERN.fullmatch(value):
            raise ValueError("invalid trusted-host workspace id")
        return value

    @field_validator("staging_label")
    @classmethod
    def _staging_label_is_safe(cls, value: str) -> str:
        if not _STAGING_LABEL_PATTERN.fullmatch(value):
            raise ValueError("invalid trusted-host staging label")
        return value

    @field_validator("evidence_timestamp")
    @classmethod
    def _evidence_timestamp_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("trusted-host evidence timestamp must be timezone-aware")
        return value


class TrustedHostRegistryDocument(StrictBaseModel):
    version: Literal["2"]
    registry_schema_digest: str
    descriptors: list[TrustedHostDescriptorConfig] = Field(min_length=1)


class TrustedHostDescriptorRegistry:
    """Immutable process-lifetime descriptor registry with exact resolution."""

    def __init__(
        self,
        *,
        document: TrustedHostRegistryDocument,
        source_path: Path,
        source_digest: str,
    ) -> None:
        self.source_path = source_path
        self.source_digest = source_digest
        self._version = document.version
        self._registry_schema_digest = document.registry_schema_digest
        self.generation = sha256_digest(
            {
                "registry_schema_digest": document.registry_schema_digest,
                "source_digest": source_digest,
                "document": document.model_dump(mode="json"),
            }
        )
        self._records = tuple(document.descriptors)

    @classmethod
    def load(cls, path: Path) -> TrustedHostDescriptorRegistry:
        if not path.is_file():
            raise TrustedHostRegistryError(f"trusted-host registry not found: {path}")
        try:
            source_bytes = path.read_bytes()
            raw = safe_load_no_duplicate_keys(path)
        except (OSError, yaml.YAMLError) as exc:
            raise TrustedHostRegistryError(f"invalid trusted-host registry: {path}") from exc
        if not isinstance(raw, dict):
            raise TrustedHostRegistryError("trusted-host registry must be a mapping")
        try:
            document = TrustedHostRegistryDocument.model_validate(_json_object(raw))
        except ValidationError as exc:
            raise TrustedHostRegistryError("invalid trusted-host registry schema") from exc
        if document.registry_schema_digest != TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST:
            raise TrustedHostRegistryError("trusted-host registry schema digest mismatch")

        ids: set[str] = set()
        bindings: set[tuple[str, str]] = set()
        for descriptor in document.descriptors:
            if descriptor.descriptor_id in ids:
                raise TrustedHostRegistryError(
                    f"duplicate trusted-host descriptor id: {descriptor.descriptor_id}"
                )
            binding = (descriptor.workspace_id, descriptor.staging_label)
            if binding in bindings:
                raise TrustedHostRegistryError("duplicate trusted-host workspace/label binding")
            ids.add(descriptor.descriptor_id)
            bindings.add(binding)
        return cls(
            document=document,
            source_path=path,
            source_digest="sha256:" + hashlib.sha256(source_bytes).hexdigest(),
        )

    def resolve(self, *, workspace_id: str, staging_label: str) -> TrustedHostAuthorityRecord:
        matches = [
            record
            for record in self._records
            if record.enabled
            and record.workspace_id == workspace_id
            and record.staging_label == staging_label
        ]
        if len(matches) != 1:
            raise TrustedHostRegistryError("trusted-host destination does not resolve exactly once")
        record = matches[0]
        descriptor_hash = sha256_digest(
            {
                "registry_schema_digest": self._registry_schema_digest,
                "descriptor_generation": self.generation,
                "descriptor": record.model_dump(mode="json"),
            }
        )
        return TrustedHostAuthorityRecord(
            descriptor_id=record.descriptor_id,
            descriptor_hash=descriptor_hash,
            descriptor_generation=self.generation,
            registry_schema_digest=self._registry_schema_digest,
            workspace_id=record.workspace_id,
            staging_label=record.staging_label,
        )

    def status(self) -> JsonObject:
        return {
            "schema_version": self._version,
            "registry_schema_digest": self._registry_schema_digest,
            "generation": self.generation,
            "count": len(self._records),
            "enabled_count": sum(1 for record in self._records if record.enabled),
            "raw_paths_included": False,
        }


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TrustedHostRegistryError("trusted-host registry keys must be strings")
        result[key] = item
    return result
