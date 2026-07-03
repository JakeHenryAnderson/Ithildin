"""Operator-attested sandbox/VM descriptor records."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, field_validator


class SandboxDescriptorError(RuntimeError):
    """Raised when sandbox descriptor evidence is unsafe or missing."""


_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,127}$")
_STATUS_VALUES = {"accepted"}


class SandboxDescriptorPayload(StrictBaseModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    principal_id: str = Field(min_length=1, max_length=128)
    run_id: str | None = Field(default=None, max_length=128)
    sandbox_id: str = Field(min_length=1, max_length=128)
    sandbox_profile_id: str = Field(min_length=1, max_length=128)
    vm_profile_hash: str
    isolation_label: str = Field(min_length=1, max_length=128)
    network_posture_label: str = Field(min_length=1, max_length=128)
    mount_root_label: str = Field(min_length=1, max_length=128)
    model_client_label: str = Field(min_length=1, max_length=128)
    descriptor_source: Literal["operator_supplied"]
    vm_lifecycle_source: Literal["operator_managed"]
    isolation_claim_source: Literal["operator_attested"]
    network_posture_source: Literal["operator_attested"]
    mount_posture_source: Literal["operator_attested"]
    model_client_source: Literal["operator_attested"]
    ithildin_live_inspection_performed: Literal[False]
    ithildin_lifecycle_control_performed: Literal[False]
    mission_control_runtime_authority_used: Literal[False]
    trusted_host_promotion_performed: Literal[False]
    approval_id: str | None = Field(default=None, max_length=128)
    audit_event_id: str | None = Field(default=None, max_length=128)
    signed_export_id: str | None = Field(default=None, max_length=128)
    failure_transcript_hash: str | None = None
    packet_hash: str | None = None
    operator_notes_label: str | None = Field(default=None, max_length=128)

    @field_validator(
        "workspace_id",
        "principal_id",
        "run_id",
        "sandbox_id",
        "sandbox_profile_id",
        "isolation_label",
        "network_posture_label",
        "mount_root_label",
        "model_client_label",
        "approval_id",
        "audit_event_id",
        "signed_export_id",
        "operator_notes_label",
    )
    @classmethod
    def _labels_are_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _LABEL_PATTERN.fullmatch(value):
            raise ValueError("unsafe label")
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError("raw paths are not allowed")
        if any(ord(character) < 32 for character in value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("vm_profile_hash", "failure_transcript_hash", "packet_hash")
    @classmethod
    def _hashes_are_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise ValueError("expected sha256 digest")
        return value

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json", exclude_none=True))


@dataclass(frozen=True)
class SandboxDescriptorRecord:
    descriptor_id: str
    status: str
    created_at: str
    updated_at: str
    payload_hash: str
    payload: JsonObject

    def summary(self) -> JsonObject:
        return {
            "descriptor_id": self.descriptor_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload_hash": self.payload_hash,
            "workspace_id": self.payload.get("workspace_id"),
            "principal_id": self.payload.get("principal_id"),
            "run_id": self.payload.get("run_id"),
            "sandbox_id": self.payload.get("sandbox_id"),
            "sandbox_profile_id": self.payload.get("sandbox_profile_id"),
            "descriptor_source": self.payload.get("descriptor_source"),
            "vm_lifecycle_source": self.payload.get("vm_lifecycle_source"),
            "isolation_claim_source": self.payload.get("isolation_claim_source"),
            "network_posture_source": self.payload.get("network_posture_source"),
            "mount_posture_source": self.payload.get("mount_posture_source"),
            "model_client_source": self.payload.get("model_client_source"),
            "ithildin_live_inspection_performed": self.payload.get(
                "ithildin_live_inspection_performed"
            ),
            "ithildin_lifecycle_control_performed": self.payload.get(
                "ithildin_lifecycle_control_performed"
            ),
            "mission_control_runtime_authority_used": self.payload.get(
                "mission_control_runtime_authority_used"
            ),
            "trusted_host_promotion_performed": self.payload.get(
                "trusted_host_promotion_performed"
            ),
            "correlation": {
                "approval_id": self.payload.get("approval_id"),
                "audit_event_id": self.payload.get("audit_event_id"),
                "signed_export_id": self.payload.get("signed_export_id"),
            },
            "output_policy": _output_policy(),
        }

    def detail(self) -> JsonObject:
        return {
            **self.summary(),
            "safe_payload": self.payload,
        }


class SandboxDescriptorStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sandbox_descriptors (
                    descriptor_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sandbox_descriptors_created_at
                ON sandbox_descriptors(created_at)
                """
            )
            connection.commit()

    def create(self, payload: SandboxDescriptorPayload) -> SandboxDescriptorRecord:
        safe_payload = payload.safe_payload()
        payload_hash = sha256_digest(safe_payload)
        now = datetime.now(UTC).isoformat()
        descriptor_id = f"sdesc_{uuid4().hex}"
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO sandbox_descriptors (
                    descriptor_id,
                    status,
                    created_at,
                    updated_at,
                    payload_hash,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    descriptor_id,
                    "accepted",
                    now,
                    now,
                    payload_hash,
                    canonical_json(safe_payload),
                ),
            )
            connection.commit()
        return SandboxDescriptorRecord(
            descriptor_id=descriptor_id,
            status="accepted",
            created_at=now,
            updated_at=now,
            payload_hash=payload_hash,
            payload=safe_payload,
        )

    def list(self, *, limit: int = 50) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT descriptor_id, status, created_at, updated_at, payload_hash, payload_json
                FROM sandbox_descriptors
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [record.summary() for record in (_record_from_row(row) for row in rows)]

    def get(self, descriptor_id: str) -> JsonObject:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT descriptor_id, status, created_at, updated_at, payload_hash, payload_json
                FROM sandbox_descriptors
                WHERE descriptor_id = ?
                """,
                (descriptor_id,),
            ).fetchone()
        if row is None:
            raise SandboxDescriptorError("sandbox descriptor not found")
        return _record_from_row(row).detail()

    def status(self) -> JsonObject:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT status, COUNT(*)
                FROM sandbox_descriptors
                GROUP BY status
                """
            ).fetchall()
        counts = {
            str(status): int(count)
            for status, count in rows
            if str(status) in _STATUS_VALUES
        }
        return {
            "enabled": True,
            "mode": "operator_attested_descriptor_only",
            "count": sum(counts.values()),
            "statuses": cast(JsonValue, counts),
            "runtime_controls": {
                "live_vm_inspection": False,
                "vm_container_lifecycle": False,
                "sandbox_orchestration": False,
                "mission_control_runtime_authority": False,
                "trusted_host_promotion": False,
                "host_writes": False,
                "network_expansion": False,
            },
        }


def safe_audit_metadata(record: SandboxDescriptorRecord) -> JsonObject:
    payload = record.payload
    return {
        "descriptor_id": record.descriptor_id,
        "descriptor_status": record.status,
        "descriptor_payload_hash": record.payload_hash,
        "descriptor_source": payload.get("descriptor_source"),
        "vm_lifecycle_source": payload.get("vm_lifecycle_source"),
        "isolation_claim_source": payload.get("isolation_claim_source"),
        "network_posture_source": payload.get("network_posture_source"),
        "mount_posture_source": payload.get("mount_posture_source"),
        "model_client_source": payload.get("model_client_source"),
        "workspace_id": payload.get("workspace_id"),
        "principal_id": payload.get("principal_id"),
        "run_id": payload.get("run_id"),
        "sandbox_id": payload.get("sandbox_id"),
        "sandbox_profile_id": payload.get("sandbox_profile_id"),
        "ithildin_live_inspection_performed": payload.get(
            "ithildin_live_inspection_performed"
        ),
        "ithildin_lifecycle_control_performed": payload.get(
            "ithildin_lifecycle_control_performed"
        ),
        "mission_control_runtime_authority_used": payload.get(
            "mission_control_runtime_authority_used"
        ),
        "trusted_host_promotion_performed": payload.get(
            "trusted_host_promotion_performed"
        ),
        "output_policy": _output_policy(),
    }


def _record_from_row(row: tuple[object, ...]) -> SandboxDescriptorRecord:
    try:
        payload = json.loads(str(row[5]))
    except json.JSONDecodeError as exc:
        raise SandboxDescriptorError("failed to decode sandbox descriptor") from exc
    if not isinstance(payload, dict):
        raise SandboxDescriptorError("failed to decode sandbox descriptor")
    return SandboxDescriptorRecord(
        descriptor_id=str(row[0]),
        status=str(row[1]),
        created_at=str(row[2]),
        updated_at=str(row[3]),
        payload_hash=str(row[4]),
        payload=cast(JsonObject, payload),
    )


def _output_policy() -> JsonObject:
    return {
        "descriptor_only": True,
        "operator_attested": True,
        "no_live_vm_inspection": True,
        "no_lifecycle_control": True,
        "no_mission_control_runtime_authority": True,
        "no_trusted_host_promotion": True,
        "no_host_writes": True,
        "no_network_expansion": True,
        "excluded_categories": [
            "prompts",
            "model_responses",
            "file_contents",
            "diffs",
            "transcripts",
            "raw_paths",
            "directory_listings",
            "command_lines",
            "shell_output",
            "environment_values",
            "registry_urls",
            "dependency_names",
            "package_scripts",
            "secrets",
        ],
    }
