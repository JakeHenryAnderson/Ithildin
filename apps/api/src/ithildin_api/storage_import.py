"""Offline PIS-003 descriptor snapshot validation and caller-owned import contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest
from sqlalchemy import func, insert, select
from sqlalchemy.engine import Connection

from ithildin_api.sandbox_descriptors import SandboxDescriptorPayload
from ithildin_api.storage_schema import sandbox_descriptors

_DESCRIPTOR_ID = re.compile(r"^sdesc_[0-9a-f]{32}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SOURCE_KEYS = {
    "descriptor_id",
    "status",
    "created_at",
    "updated_at",
    "payload_hash",
    "payload_json",
}
_ROLLBACK_DISPOSITION = "revert_exact_candidate_and_discard_isolated_target_before_activation"


class StorageImportError(RuntimeError):
    """Raised when offline source or target evidence is unsafe or inconsistent."""


@dataclass(frozen=True)
class DescriptorImportRow:
    descriptor_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    payload_hash: str
    payload: JsonObject

    def database_values(self) -> dict[str, object]:
        return {
            "descriptor_id": self.descriptor_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload_hash": self.payload_hash,
            "payload_json": self.payload,
        }

    def semantic_evidence(self) -> JsonObject:
        return {
            "descriptor_id": self.descriptor_id,
            "status": self.status,
            "created_at": _utc_text(self.created_at),
            "updated_at": _utc_text(self.updated_at),
            "payload_hash": self.payload_hash,
            "canonical_payload_sha256": _canonical_bytes_digest(self.payload),
        }


@dataclass(frozen=True)
class ValidatedDescriptorSnapshot:
    records: tuple[DescriptorImportRow, ...]
    descriptor_ids: tuple[str, ...]
    records_digest: str

    @property
    def record_count(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class PreconnectionRollbackReceipt:
    candidate_commit: str
    target_label: str
    disposition: str = _ROLLBACK_DISPOSITION
    bound_before_connection: bool = True
    source_sqlite_modified: bool = False
    activation_allowed: bool = False
    credentials_included: bool = False

    def document(self) -> JsonObject:
        self.validate()
        return {
            "candidate_commit": self.candidate_commit,
            "target_label": self.target_label,
            "disposition": self.disposition,
            "bound_before_connection": self.bound_before_connection,
            "source_sqlite_modified": self.source_sqlite_modified,
            "activation_allowed": self.activation_allowed,
            "credentials_included": self.credentials_included,
        }

    def digest(self) -> str:
        return sha256_digest(self.document())

    def validate(self) -> None:
        if not _COMMIT.fullmatch(self.candidate_commit):
            raise StorageImportError("rollback candidate commit is invalid")
        if not _safe_label(self.target_label):
            raise StorageImportError("rollback target label is invalid")
        if self.disposition != _ROLLBACK_DISPOSITION:
            raise StorageImportError("rollback disposition is invalid")
        if not self.bound_before_connection:
            raise StorageImportError("rollback receipt was not bound before connection")
        if self.source_sqlite_modified or self.activation_allowed or self.credentials_included:
            raise StorageImportError("rollback receipt crosses the offline authority boundary")


@dataclass(frozen=True)
class DescriptorImportContext:
    candidate_commit: str
    target_label: str
    rollback_receipt_digest: str

    @classmethod
    def bind(cls, receipt: PreconnectionRollbackReceipt) -> DescriptorImportContext:
        receipt.validate()
        return cls(
            candidate_commit=receipt.candidate_commit,
            target_label=receipt.target_label,
            rollback_receipt_digest=receipt.digest(),
        )

    def validate(self, receipt: PreconnectionRollbackReceipt) -> None:
        receipt.validate()
        if not _COMMIT.fullmatch(self.candidate_commit):
            raise StorageImportError("import candidate commit is invalid")
        if not _safe_label(self.target_label):
            raise StorageImportError("import target label is invalid")
        if not _SHA256.fullmatch(self.rollback_receipt_digest):
            raise StorageImportError("rollback receipt digest is invalid")
        if (
            self.candidate_commit != receipt.candidate_commit
            or self.target_label != receipt.target_label
            or self.rollback_receipt_digest != receipt.digest()
        ):
            raise StorageImportError("import context does not match the rollback receipt")


@dataclass(frozen=True)
class DescriptorImportReceipt:
    candidate_commit: str
    target_label: str
    rollback_receipt_digest: str
    record_count: int
    descriptor_ids: tuple[str, ...]
    created_at_utc: tuple[str, ...]
    updated_at_utc: tuple[str, ...]
    source_records_digest: str
    target_records_digest: str
    verified_at: str
    receipt_version: str = "1"
    slice_id: str = "PIS-003-SD-PG-001"
    aggregate: str = "sandbox_descriptors"
    schema_revision: str = "0001_sandbox_descriptors"
    transaction_owner: str = "caller"
    transaction_state: str = "outer_transaction_open"
    target_state: str = "quarantined_discard_required"
    database_commit_performed: bool = False
    verification_status: str = "semantic_round_trip_verified_uncommitted"

    def document(self) -> JsonObject:
        return {
            "receipt_version": self.receipt_version,
            "slice_id": self.slice_id,
            "aggregate": self.aggregate,
            "schema_revision": self.schema_revision,
            "candidate_commit": self.candidate_commit,
            "target_label": self.target_label,
            "rollback_receipt_digest": self.rollback_receipt_digest,
            "record_count": self.record_count,
            "descriptor_ids": list(self.descriptor_ids),
            "created_at_utc": list(self.created_at_utc),
            "updated_at_utc": list(self.updated_at_utc),
            "source_records_digest": self.source_records_digest,
            "target_records_digest": self.target_records_digest,
            "verified_at": self.verified_at,
            "transaction_owner": self.transaction_owner,
            "transaction_state": self.transaction_state,
            "target_state": self.target_state,
            "database_commit_performed": self.database_commit_performed,
            "verification_status": self.verification_status,
            "credentials_included": False,
            "dsn_included": False,
            "activation_allowed": False,
        }

    def digest(self) -> str:
        return sha256_digest(self.document())


def validate_descriptor_snapshot(
    rows: Iterable[Mapping[str, object]],
) -> ValidatedDescriptorSnapshot:
    """Validate and canonicalize exported rows without touching a database connection."""

    normalized = tuple(_normalize_source_row(row) for row in rows)
    ids = [row.descriptor_id for row in normalized]
    if len(ids) != len(set(ids)):
        raise StorageImportError("duplicate descriptor_id in source rows")
    records = tuple(sorted(normalized, key=lambda row: row.descriptor_id))
    evidence = [row.semantic_evidence() for row in records]
    return ValidatedDescriptorSnapshot(
        records=records,
        descriptor_ids=tuple(row.descriptor_id for row in records),
        records_digest=sha256_digest(cast(JsonValue, evidence)),
    )


def import_validated_descriptor_snapshot(
    connection: Connection,
    snapshot: ValidatedDescriptorSnapshot,
    context: DescriptorImportContext,
    rollback_receipt: PreconnectionRollbackReceipt,
    *,
    verified_at: datetime,
) -> DescriptorImportReceipt:
    """Import and verify a snapshot inside a caller-owned explicit outer transaction."""

    context.validate(rollback_receipt)
    _validate_snapshot_integrity(snapshot)
    verified_at_text = _utc_text(_require_utc_datetime(verified_at, "verified_at"))
    if connection.dialect.name != "postgresql":
        raise StorageImportError("caller-owned connection must use the PostgreSQL dialect")
    if not connection.in_transaction() or connection.in_nested_transaction():
        raise StorageImportError("caller-owned non-nested outer transaction is required")

    existing = connection.execute(
        select(func.count()).select_from(sandbox_descriptors)
    ).scalar_one()
    if type(existing) is not int or existing != 0:
        raise StorageImportError("isolated target must be empty")

    if snapshot.records:
        connection.execute(
            insert(sandbox_descriptors),
            [row.database_values() for row in snapshot.records],
        )

    target_result = connection.execute(
        select(
            sandbox_descriptors.c.descriptor_id,
            sandbox_descriptors.c.status,
            sandbox_descriptors.c.created_at,
            sandbox_descriptors.c.updated_at,
            sandbox_descriptors.c.payload_hash,
            sandbox_descriptors.c.payload_json,
        ).order_by(sandbox_descriptors.c.descriptor_id)
    )
    target_records = tuple(
        _normalize_target_row(cast(Mapping[str, Any], row))
        for row in target_result.mappings().all()
    )
    target_evidence = [row.semantic_evidence() for row in target_records]
    target_digest = sha256_digest(cast(JsonValue, target_evidence))
    if (
        len(target_records) != snapshot.record_count
        or tuple(row.descriptor_id for row in target_records) != snapshot.descriptor_ids
        or target_digest != snapshot.records_digest
    ):
        raise StorageImportError("target semantic verification failed; discard target")

    return DescriptorImportReceipt(
        candidate_commit=context.candidate_commit,
        target_label=context.target_label,
        rollback_receipt_digest=context.rollback_receipt_digest,
        record_count=snapshot.record_count,
        descriptor_ids=snapshot.descriptor_ids,
        created_at_utc=tuple(_utc_text(row.created_at) for row in snapshot.records),
        updated_at_utc=tuple(_utc_text(row.updated_at) for row in snapshot.records),
        source_records_digest=snapshot.records_digest,
        target_records_digest=target_digest,
        verified_at=verified_at_text,
    )


def _validate_snapshot_integrity(snapshot: ValidatedDescriptorSnapshot) -> None:
    revalidated = validate_descriptor_snapshot(
        {
            "descriptor_id": row.descriptor_id,
            "status": row.status,
            "created_at": _utc_text(row.created_at),
            "updated_at": _utc_text(row.updated_at),
            "payload_hash": row.payload_hash,
            "payload_json": canonical_json(row.payload),
        }
        for row in snapshot.records
    )
    if revalidated != snapshot:
        raise StorageImportError("validated snapshot integrity is invalid")


def _normalize_source_row(row: Mapping[str, object]) -> DescriptorImportRow:
    if set(row) != _SOURCE_KEYS:
        raise StorageImportError("source row fields are not exact")
    descriptor_id = _exact_string(row["descriptor_id"], "descriptor_id")
    if not _DESCRIPTOR_ID.fullmatch(descriptor_id):
        raise StorageImportError("descriptor_id is invalid")
    status = _exact_string(row["status"], "status")
    if status != "accepted":
        raise StorageImportError("descriptor status is not accepted")
    created_at = _strict_utc_source_text(row["created_at"], "created_at")
    updated_at = _strict_utc_source_text(row["updated_at"], "updated_at")
    if updated_at < created_at:
        raise StorageImportError("updated_at precedes created_at")
    payload_hash = _exact_string(row["payload_hash"], "payload_hash")
    if not _SHA256.fullmatch(payload_hash):
        raise StorageImportError("payload_hash is invalid")
    payload = _parse_source_payload(row["payload_json"])
    if sha256_digest(payload) != payload_hash:
        raise StorageImportError("payload_hash does not match canonical payload")
    return DescriptorImportRow(
        descriptor_id=descriptor_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        payload_hash=payload_hash,
        payload=payload,
    )


def _normalize_target_row(row: Mapping[str, Any]) -> DescriptorImportRow:
    descriptor_id = _exact_string(row.get("descriptor_id"), "target descriptor_id")
    if not _DESCRIPTOR_ID.fullmatch(descriptor_id):
        raise StorageImportError("target descriptor_id is invalid")
    status = _exact_string(row.get("status"), "target status")
    if status != "accepted":
        raise StorageImportError("target descriptor status is not accepted")
    created_at = _require_utc_datetime(row.get("created_at"), "target created_at")
    updated_at = _require_utc_datetime(row.get("updated_at"), "target updated_at")
    if updated_at < created_at:
        raise StorageImportError("target updated_at precedes created_at")
    payload_hash = _exact_string(row.get("payload_hash"), "target payload_hash")
    if not _SHA256.fullmatch(payload_hash):
        raise StorageImportError("target payload_hash is invalid")
    payload = _validate_payload_object(row.get("payload_json"), source_text=None)
    if sha256_digest(payload) != payload_hash:
        raise StorageImportError("target payload_hash does not match canonical payload")
    return DescriptorImportRow(
        descriptor_id=descriptor_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        payload_hash=payload_hash,
        payload=payload,
    )


def _parse_source_payload(value: object) -> JsonObject:
    if not isinstance(value, str):
        raise StorageImportError("payload_json must be canonical JSON text")
    try:
        parsed = json.loads(
            value,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError):
        raise StorageImportError("payload_json is malformed or duplicated") from None
    return _validate_payload_object(parsed, source_text=value)


def _validate_payload_object(value: object, *, source_text: str | None) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise StorageImportError("payload_json must be an object")
    try:
        payload = SandboxDescriptorPayload.model_validate(value).safe_payload()
    except ValueError:
        raise StorageImportError("payload_json violates the descriptor contract") from None
    canonical = canonical_json(payload)
    if source_text is not None and source_text != canonical:
        raise StorageImportError("payload_json is not canonical Ithildin JSON")
    return payload


def _strict_utc_source_text(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise StorageImportError(f"{field} is not a canonical ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise StorageImportError(f"{field} is not a canonical ISO-8601 timestamp") from None
    normalized = _require_utc_datetime(parsed, field)
    if value != _utc_text(normalized):
        raise StorageImportError(f"{field} is not canonical UTC text")
    return normalized


def _require_utc_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise StorageImportError(f"{field} must be timezone-aware UTC")
    offset = value.utcoffset()
    if offset is None:
        raise StorageImportError(f"{field} must be timezone-aware UTC")
    if offset.total_seconds() != 0:
        raise StorageImportError(f"{field} must be UTC")
    return value.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _canonical_bytes_digest(payload: JsonObject) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _exact_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise StorageImportError(f"{field} must be a string")
    return value


def _closed_object(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _safe_label(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value))
