"""Audit writer with SQLite indexing and hash-chained JSONL evidence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, cast

from ithildin_schemas import (
    AuditEvent,
    AuditEventType,
    JsonObject,
    JsonValue,
    PolicyDecisionValue,
    sha256_digest,
)
from pydantic import ValidationError

GENESIS_HASH = "sha256:" + ("0" * 64)
REDACTED_VALUE = "[REDACTED]"


class AuditWriteError(RuntimeError):
    """Raised when audit evidence cannot be written safely."""


@dataclass(frozen=True)
class AuditVerificationFailure:
    row_number: int
    event_id: Optional[str]
    reason: str

    def as_dict(self) -> JsonObject:
        return {
            "row_number": self.row_number,
            "event_id": self.event_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AuditVerificationResult:
    valid: bool
    event_count: int
    first_timestamp: Optional[str]
    last_timestamp: Optional[str]
    head_hash: str
    failure: Optional[AuditVerificationFailure] = None

    def as_dict(self) -> JsonObject:
        return {
            "valid": self.valid,
            "event_count": self.event_count,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "head_hash": self.head_hash,
            "failure": self.failure.as_dict() if self.failure else None,
        }


class AuditWriter:
    def __init__(
        self,
        db_path: Path,
        jsonl_path: Path,
        redact_fields: Optional[set[str]] = None,
    ) -> None:
        self.db_path = db_path
        self.jsonl_path = jsonl_path
        self.redact_fields = redact_fields or set()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        request_id TEXT NOT NULL,
                        prev_event_hash TEXT NOT NULL,
                        event_hash TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise AuditWriteError("failed to initialize audit database") from exc

    def write_event(
        self,
        *,
        event_id: str,
        event_type: AuditEventType,
        request_id: str,
        principal: JsonObject,
        timestamp: Optional[datetime] = None,
        tool_name: Optional[str] = None,
        resource: Optional[JsonObject] = None,
        decision: Optional[PolicyDecisionValue] = None,
        policy_version: Optional[str] = None,
        matched_rules: Optional[list[str]] = None,
        input_hash: Optional[str] = None,
        redactions: Optional[list[str]] = None,
        metadata: Optional[JsonObject] = None,
    ) -> AuditEvent:
        effective_redactions = set(redactions or []) | self.redact_fields
        event_timestamp = timestamp or datetime.now(UTC)
        event_data: dict[str, object] = {
            "event_id": event_id,
            "timestamp": event_timestamp,
            "event_type": event_type,
            "request_id": request_id,
            "principal": _redact_json(principal, effective_redactions),
            "tool_name": tool_name,
            "resource": (
                _redact_json(resource, effective_redactions) if resource is not None else None
            ),
            "decision": decision,
            "policy_version": policy_version,
            "matched_rules": matched_rules or [],
            "input_hash": input_hash,
            "redactions": sorted(effective_redactions),
            "metadata": _redact_json(metadata or {}, effective_redactions),
        }
        connection: sqlite3.Connection | None = None
        try:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.db_path, isolation_level=None)
            connection.execute("BEGIN IMMEDIATE")
            self._require_clean_committed_lifecycle(connection)
            row = connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            prev_event_hash = GENESIS_HASH if row is None else str(row[0])
            chained_event_data = {**event_data, "prev_event_hash": prev_event_hash}
            event_hash = sha256_digest(_json_ready(chained_event_data))
            event = AuditEvent.model_validate(
                {**chained_event_data, "event_hash": event_hash}
            )
            self._persist_event(connection, event)
            connection.execute("COMMIT")
        except ValidationError as exc:
            if connection is not None and connection.in_transaction:
                connection.execute("ROLLBACK")
            raise AuditWriteError("invalid audit event") from exc
        except AuditWriteError:
            if connection is not None and connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except (OSError, sqlite3.Error) as exc:
            if connection is not None and connection.in_transaction:
                connection.execute("ROLLBACK")
            raise AuditWriteError("failed to write audit event") from exc
        finally:
            if connection is not None:
                connection.close()
        return event

    def list_events(
        self,
        *,
        limit: int = 100,
        event_type: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 500))
        filters: list[str] = []
        parameters: list[str | int] = []
        if event_type:
            filters.append("event_type = ?")
            parameters.append(event_type)
        if request_id:
            filters.append("request_id = ?")
            parameters.append(request_id)

        query = "SELECT payload_json FROM audit_events"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY rowid DESC LIMIT ?"
        parameters.append(bounded_limit)

        try:
            with sqlite3.connect(self.db_path) as connection:
                rows = connection.execute(query, tuple(parameters)).fetchall()
        except sqlite3.Error as exc:
            raise AuditWriteError("failed to read audit events") from exc

        events: list[JsonObject] = []
        for row in rows:
            try:
                payload = json.loads(str(row[0]))
            except json.JSONDecodeError as exc:
                raise AuditWriteError("failed to decode audit event payload") from exc
            if not isinstance(payload, dict):
                raise AuditWriteError("failed to decode audit event payload")
            events.append(cast(JsonObject, payload))
        return events

    def verify_chain(self) -> AuditVerificationResult:
        rows = self._payload_rows()
        if not rows:
            return AuditVerificationResult(
                valid=True,
                event_count=0,
                first_timestamp=None,
                last_timestamp=None,
                head_hash=GENESIS_HASH,
            )

        previous_hash = GENESIS_HASH
        first_timestamp: Optional[str] = None
        last_timestamp: Optional[str] = None
        head_hash = GENESIS_HASH

        for index, row in enumerate(rows, start=1):
            payload_json = _payload_json_from_row(row)
            try:
                payload = cast(JsonObject, json.loads(payload_json))
            except json.JSONDecodeError:
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="invalid audit payload JSON",
                )
            if not isinstance(payload, dict):
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="invalid audit event schema",
                )

            event_id = _optional_string(payload.get("event_id"))
            try:
                event = AuditEvent.model_validate(payload)
            except ValidationError:
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="invalid audit event schema",
                    event_id=event_id,
                )

            if not _indexed_columns_match_event(row, event):
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="indexed audit columns mismatch",
                    event_id=event.event_id,
                )

            if event.prev_event_hash != previous_hash:
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="previous event hash mismatch",
                    event_id=event.event_id,
                )

            expected_hash = _event_hash_from_event(event)
            if event.event_hash != expected_hash:
                return _failed_verification(
                    rows=rows,
                    row_number=index,
                    head_hash=head_hash,
                    reason="event hash mismatch",
                    event_id=event.event_id,
                )

            if first_timestamp is None:
                first_timestamp = event.timestamp.isoformat()
            last_timestamp = event.timestamp.isoformat()
            previous_hash = event.event_hash
            head_hash = event.event_hash

        return AuditVerificationResult(
            valid=True,
            event_count=len(rows),
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
            head_hash=head_hash,
        )

    def export_jsonl_bundle(self, *, require_clean_lifecycle: bool = False) -> str:
        verification = self.verify_chain()
        diagnostics = self.diagnostics()
        lifecycle = diagnostics.get("lifecycle")
        lifecycle_status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
        if require_clean_lifecycle and lifecycle_status != "clean":
            raise AuditWriteError("audit lifecycle is not clean for export")
        metadata = {
            "bundle_type": "ithildin.audit.export",
            "format_version": "1",
            "generated_at": datetime.now(UTC).isoformat(),
            "event_count": verification.event_count,
            "head_hash": verification.head_hash,
            "verification": verification.as_dict(),
            "diagnostics": {
                "category": diagnostics.get("category"),
                "lifecycle": lifecycle,
                "sqlite_event_count": diagnostics.get("sqlite_event_count"),
                "jsonl_line_count": diagnostics.get("jsonl_line_count"),
                "jsonl_head_hash": diagnostics.get("jsonl_head_hash"),
            },
        }
        lines = [
            json.dumps({"metadata": metadata}, sort_keys=True, separators=(",", ":")),
            *[_payload_json_from_row(row) for row in self._payload_rows()],
        ]
        return "\n".join(lines) + "\n"

    def exact_jsonl_match(self) -> bool:
        """Compare the mirror with the canonical LF-framed committed payload bytes."""

        payloads = [_payload_json_from_row(row) for row in self._payload_rows()]
        return self._jsonl_matches_payloads(payloads)

    def diagnostics(self) -> JsonObject:
        db_exists = self.db_path.exists()
        jsonl_exists = self.jsonl_path.exists()
        sqlite_event_count: Optional[int] = None
        jsonl_line_count: Optional[int] = None
        jsonl_head_hash: Optional[str] = None
        jsonl_error: Optional[str] = None
        sqlite_jsonl_payload_bytes_match: Optional[bool] = None
        if jsonl_exists:
            try:
                jsonl_lines = self.jsonl_path.read_text(encoding="utf-8").splitlines()
                jsonl_line_count = len(jsonl_lines)
                jsonl_head_hash = _jsonl_head_hash(jsonl_lines)
            except (OSError, UnicodeError) as exc:
                jsonl_error = str(exc)

        if not db_exists:
            verification: JsonObject = {
                "valid": True,
                "event_count": 0,
                "first_timestamp": None,
                "last_timestamp": None,
                "head_hash": GENESIS_HASH,
                "failure": None,
            }
            category = "not_initialized"
        else:
            try:
                sqlite_event_count = self._event_count()
                result = self.verify_chain()
            except AuditWriteError as exc:
                verification = {
                    "valid": False,
                    "event_count": 0,
                    "first_timestamp": None,
                    "last_timestamp": None,
                    "head_hash": GENESIS_HASH,
                    "failure": {
                        "row_number": 0,
                        "event_id": None,
                        "reason": str(exc),
                    },
                }
                category = "storage_read_failure"
            else:
                verification = result.as_dict()
                category = _diagnostic_category(result)
                try:
                    sqlite_jsonl_payload_bytes_match = self.exact_jsonl_match()
                except AuditWriteError as exc:
                    if jsonl_error is None:
                        jsonl_error = str(exc)

        lifecycle = _lifecycle_diagnostics(
            category=category,
            db_exists=db_exists,
            jsonl_exists=jsonl_exists,
            sqlite_event_count=sqlite_event_count,
            jsonl_line_count=jsonl_line_count,
            jsonl_head_hash=jsonl_head_hash,
            verification=verification,
            jsonl_error=jsonl_error,
            sqlite_jsonl_payload_bytes_match=sqlite_jsonl_payload_bytes_match,
        )

        return {
            "db_path": self.db_path.as_posix(),
            "log_path": self.jsonl_path.as_posix(),
            "db_exists": db_exists,
            "jsonl_exists": jsonl_exists,
            "db_size_bytes": _path_size(self.db_path),
            "jsonl_size_bytes": _path_size(self.jsonl_path),
            "sqlite_event_count": sqlite_event_count,
            "jsonl_line_count": jsonl_line_count,
            "jsonl_head_hash": jsonl_head_hash,
            "jsonl_error": jsonl_error,
            "sqlite_jsonl_payload_bytes_match": sqlite_jsonl_payload_bytes_match,
            "category": category,
            "lifecycle": lifecycle,
            "verification": verification,
        }

    def _payload_rows(self) -> list[tuple[object]]:
        try:
            with sqlite3.connect(self.db_path) as connection:
                return connection.execute(
                    """
                    SELECT
                        event_id,
                        timestamp,
                        event_type,
                        request_id,
                        prev_event_hash,
                        event_hash,
                        payload_json
                    FROM audit_events
                    ORDER BY rowid ASC
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise AuditWriteError("failed to read audit events") from exc

    def _event_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as connection:
                return int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
        except sqlite3.Error as exc:
            raise AuditWriteError("failed to count audit events") from exc

    def _persist_event(self, connection: sqlite3.Connection, event: AuditEvent) -> None:
        payload = event.model_dump(mode="json")
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id,
                timestamp,
                event_type,
                request_id,
                prev_event_hash,
                event_hash,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.request_id,
                event.prev_event_hash,
                event.event_hash,
                payload_json,
            ),
        )
        with self.jsonl_path.open("ab") as jsonl_file:
            jsonl_file.write(_canonical_jsonl_bytes([payload_json]))

    def _require_clean_committed_lifecycle(self, connection: sqlite3.Connection) -> None:
        """Refuse new evidence when committed SQLite and JSONL history diverge.

        The caller holds ``BEGIN IMMEDIATE``, which serializes all writers using
        this database while the committed JSONL mirror is compared byte-for-byte.
        An orphan append, missing line, partial line, or edited mirror therefore
        requires explicit operator recovery before the chain can advance.
        """

        sqlite_payloads = [
            str(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM audit_events ORDER BY rowid ASC"
            ).fetchall()
        ]
        if not self._jsonl_matches_payloads(sqlite_payloads):
            raise AuditWriteError("audit lifecycle recovery is required")

    def _jsonl_matches_payloads(self, payloads: list[str]) -> bool:
        try:
            actual = self.jsonl_path.read_bytes() if self.jsonl_path.exists() else b""
        except OSError as exc:
            raise AuditWriteError("audit lifecycle recovery is required") from exc
        return actual == _canonical_jsonl_bytes(payloads)


def _redact_json(value: JsonObject, redact_fields: set[str]) -> JsonObject:
    return {
        key: REDACTED_VALUE if key in redact_fields else _redact_value(item, redact_fields)
        for key, item in value.items()
    }


def _redact_value(value: object, redact_fields: set[str]) -> JsonValue:
    if isinstance(value, dict):
        return cast(JsonObject, {
            str(key): REDACTED_VALUE if key in redact_fields else _redact_value(item, redact_fields)
            for key, item in value.items()
        })
    if isinstance(value, list):
        return [_redact_value(item, redact_fields) for item in value]
    return cast(JsonValue, value)


def _json_ready(value: object) -> JsonValue:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, AuditEventType):
        return value.value
    if isinstance(value, PolicyDecisionValue):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return cast(JsonValue, value)


def _event_hash_from_event(event: AuditEvent) -> str:
    event_data = {
        "event_id": event.event_id,
        "timestamp": event.timestamp,
        "event_type": event.event_type,
        "request_id": event.request_id,
        "principal": event.principal,
        "tool_name": event.tool_name,
        "resource": event.resource,
        "decision": event.decision,
        "policy_version": event.policy_version,
        "matched_rules": event.matched_rules,
        "input_hash": event.input_hash,
        "redactions": event.redactions,
        "metadata": event.metadata,
        "prev_event_hash": event.prev_event_hash,
    }
    return sha256_digest(_json_ready(event_data))


def _payload_json_from_row(row: tuple[object, ...]) -> str:
    return str(row[-1])


def _indexed_columns_match_event(row: tuple[object, ...], event: AuditEvent) -> bool:
    return (
        str(row[0]) == event.event_id
        and str(row[1]) == event.timestamp.isoformat()
        and str(row[2]) == event.event_type.value
        and str(row[3]) == event.request_id
        and str(row[4]) == event.prev_event_hash
        and str(row[5]) == event.event_hash
    )


def _jsonl_head_hash(lines: list[str]) -> Optional[str]:
    if not lines:
        return GENESIS_HASH
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    event_hash = payload.get("event_hash")
    return event_hash if isinstance(event_hash, str) else None


def _canonical_jsonl_bytes(payloads: list[str]) -> bytes:
    return b"".join(payload.encode("utf-8") + b"\n" for payload in payloads)


def _path_size(path: Path) -> Optional[int]:
    try:
        return path.stat().st_size if path.exists() else None
    except OSError:
        return None


def _lifecycle_diagnostics(
    *,
    category: str,
    db_exists: bool,
    jsonl_exists: bool,
    sqlite_event_count: Optional[int],
    jsonl_line_count: Optional[int],
    jsonl_head_hash: Optional[str],
    verification: JsonObject,
    jsonl_error: Optional[str],
    sqlite_jsonl_payload_bytes_match: Optional[bool],
) -> JsonObject:
    verification_valid = verification.get("valid") is True
    verification_head_hash = _optional_string(verification.get("head_hash"))
    count_matches = (
        sqlite_event_count is not None
        and jsonl_line_count is not None
        and sqlite_event_count == jsonl_line_count
    )
    head_matches = (
        verification_head_hash is not None
        and jsonl_head_hash is not None
        and verification_head_hash == jsonl_head_hash
    )

    if not db_exists:
        lifecycle_status = "not_initialized"
    elif (
        verification_valid
        and verification.get("event_count") == 0
        and sqlite_event_count == 0
        and not jsonl_exists
    ):
        lifecycle_status = "clean"
    elif jsonl_error is not None or not jsonl_exists:
        lifecycle_status = "ambiguous"
    elif (
        verification_valid
        and count_matches
        and head_matches
        and sqlite_jsonl_payload_bytes_match is True
    ):
        lifecycle_status = "clean"
    elif not verification_valid:
        lifecycle_status = "verification_failed"
    else:
        lifecycle_status = "recovery_required"

    recommendations = {
        "clean": "No audit lifecycle action is required.",
        "not_initialized": "Initialize the API or audit writer before expecting audit evidence.",
        "verification_failed": "Inspect the first verification failure before exporting evidence.",
        "recovery_required": (
            "Compare SQLite and JSONL evidence before using exports; do not rewrite evidence "
            "without a separate review task."
        ),
        "ambiguous": (
            "Inspect local audit file availability and permissions before relying on exports."
        ),
    }

    return {
        "status": lifecycle_status,
        "retention_mode": "local_manual",
        "retention_mutation_supported": False,
        "repair_supported": False,
        "export_jsonl_available": db_exists,
        "sqlite_jsonl_event_count_match": count_matches if jsonl_line_count is not None else None,
        "sqlite_jsonl_head_hash_match": head_matches if jsonl_head_hash is not None else None,
        "sqlite_jsonl_payload_bytes_match": sqlite_jsonl_payload_bytes_match,
        "recommendation": recommendations[lifecycle_status],
        "category": category,
    }


def _failed_verification(
    *,
    rows: list[tuple[object]],
    row_number: int,
    head_hash: str,
    reason: str,
    event_id: Optional[str] = None,
) -> AuditVerificationResult:
    timestamps = _timestamps_from_rows(rows)
    return AuditVerificationResult(
        valid=False,
        event_count=len(rows),
        first_timestamp=timestamps[0],
        last_timestamp=timestamps[1],
        head_hash=head_hash,
        failure=AuditVerificationFailure(
            row_number=row_number,
            event_id=event_id,
            reason=reason,
        ),
    )


def _diagnostic_category(result: AuditVerificationResult) -> str:
    if result.valid and result.event_count == 0:
        return "empty_valid"
    if result.valid:
        return "valid"
    if result.failure is None:
        return "unknown_failure"
    if result.failure.reason == "invalid audit payload JSON":
        return "invalid_json"
    if result.failure.reason == "invalid audit event schema":
        return "invalid_schema"
    if result.failure.reason == "previous event hash mismatch":
        return "previous_hash_mismatch"
    if result.failure.reason == "event hash mismatch":
        return "event_hash_mismatch"
    if result.failure.reason == "indexed audit columns mismatch":
        return "index_mismatch"
    return "verification_failure"


def _timestamps_from_rows(rows: list[tuple[object]]) -> tuple[Optional[str], Optional[str]]:
    timestamps: list[str] = []
    for row in rows:
        try:
            payload = json.loads(_payload_json_from_row(row))
        except json.JSONDecodeError:
            continue
        timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
        if isinstance(timestamp, str):
            timestamps.append(timestamp)
    if not timestamps:
        return None, None
    return timestamps[0], timestamps[-1]


def _optional_string(value: object) -> Optional[str]:
    return value if isinstance(value, str) else None
