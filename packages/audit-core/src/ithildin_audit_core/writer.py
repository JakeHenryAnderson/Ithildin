"""Audit writer with SQLite indexing and hash-chained JSONL evidence."""

from __future__ import annotations

import json
import sqlite3
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
        prev_event_hash = self._latest_event_hash()
        event_timestamp = timestamp or datetime.now(UTC)
        event_data = {
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
            "prev_event_hash": prev_event_hash,
        }
        event_hash = sha256_digest(_json_ready(event_data))

        try:
            event = AuditEvent.model_validate({**event_data, "event_hash": event_hash})
        except ValidationError as exc:
            raise AuditWriteError("invalid audit event") from exc

        self._persist_event(event)
        return event

    def _latest_event_hash(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as connection:
                row = connection.execute(
                    "SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
        except sqlite3.Error as exc:
            raise AuditWriteError("failed to read audit hash chain") from exc

        if row is None:
            return GENESIS_HASH
        return str(row[0])

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

        return [cast(JsonObject, json.loads(str(row[0]))) for row in rows]

    def _persist_event(self, event: AuditEvent) -> None:
        payload = event.model_dump(mode="json")
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        try:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as connection:
                connection.execute("BEGIN")
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
                with self.jsonl_path.open("a", encoding="utf-8") as jsonl_file:
                    jsonl_file.write(payload_json + "\n")
                connection.commit()
        except (OSError, sqlite3.Error) as exc:
            raise AuditWriteError("failed to write audit event") from exc


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
