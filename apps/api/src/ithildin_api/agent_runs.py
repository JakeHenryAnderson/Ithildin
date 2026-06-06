"""Read-only agent run correlation records."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ithildin_schemas import JsonObject, JsonValue


class AgentRunError(RuntimeError):
    """Raised when agent run records cannot be read safely."""


@dataclass(frozen=True)
class AgentRunRecord:
    run_id: str
    principal_id: str
    principal_type: str
    principal_roles: list[str]
    workspace_id: str
    session_id: str
    status: str
    tool_call_count: int
    created_at: str
    updated_at: str
    last_request_id: str | None
    policy_hash: str | None
    last_tool_name: str | None
    last_tool_manifest_hash: str | None
    metadata: JsonObject

    def summary(self) -> JsonObject:
        return {
            "run_id": self.run_id,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "principal_roles": cast(JsonValue, self.principal_roles),
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "status": self.status,
            "tool_call_count": self.tool_call_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_request_id": self.last_request_id,
            "policy_hash": self.policy_hash,
            "last_tool_name": self.last_tool_name,
            "last_tool_manifest_hash": self.last_tool_manifest_hash,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AgentRunContext:
    run_id: str
    session_id: str
    workspace_id: str
    principal_id: str

    def metadata(self) -> JsonObject:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "principal_id": self.principal_id,
        }


class AgentRunStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    principal_type TEXT NOT NULL,
                    principal_roles_json TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tool_call_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_request_id TEXT,
                    policy_hash TEXT,
                    last_tool_name TEXT,
                    last_tool_manifest_hash TEXT,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_runs_identity_session_workspace
                ON agent_runs(principal_id, session_id, workspace_id)
                """
            )
            connection.commit()

    def ensure_for_tool_call(
        self,
        *,
        principal: JsonObject,
        session_id: str,
        workspace_id: str,
        request_id: str,
        tool_name: str,
        policy_hash: str | None,
        tool_manifest_hash: str | None,
    ) -> tuple[AgentRunContext, bool]:
        principal_id = _string_or_default(principal.get("id"), "unknown")
        principal_type = _string_or_default(principal.get("type"), "unknown")
        principal_roles = _string_list(principal.get("roles"))
        now = datetime.now(UTC).isoformat()
        metadata: JsonObject = {"created_by": "governed_tool_call"}
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT run_id
                FROM agent_runs
                WHERE principal_id = ?
                  AND session_id = ?
                  AND workspace_id = ?
                """,
                (principal_id, session_id, workspace_id),
            ).fetchone()
            if row is None:
                run_id = _new_id("run")
                connection.execute(
                    """
                    INSERT INTO agent_runs (
                        run_id,
                        principal_id,
                        principal_type,
                        principal_roles_json,
                        workspace_id,
                        session_id,
                        status,
                        tool_call_count,
                        created_at,
                        updated_at,
                        last_request_id,
                        policy_hash,
                        last_tool_name,
                        last_tool_manifest_hash,
                        metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        principal_id,
                        principal_type,
                        json.dumps(principal_roles, sort_keys=True, separators=(",", ":")),
                        workspace_id,
                        session_id,
                        "active",
                        1,
                        now,
                        now,
                        request_id,
                        policy_hash,
                        tool_name,
                        tool_manifest_hash,
                        json.dumps(metadata, sort_keys=True, separators=(",", ":")),
                    ),
                )
                created = True
            else:
                run_id = str(row[0])
                connection.execute(
                    """
                    UPDATE agent_runs
                    SET updated_at = ?,
                        last_request_id = ?,
                        policy_hash = COALESCE(?, policy_hash),
                        last_tool_name = ?,
                        last_tool_manifest_hash = COALESCE(?, last_tool_manifest_hash),
                        tool_call_count = tool_call_count + 1
                    WHERE run_id = ?
                    """,
                    (
                        now,
                        request_id,
                        policy_hash,
                        tool_name,
                        tool_manifest_hash,
                        run_id,
                    ),
                )
                created = False
            connection.commit()
        return (
            AgentRunContext(
                run_id=run_id,
                session_id=session_id,
                workspace_id=workspace_id,
                principal_id=principal_id,
            ),
            created,
        )

    def list_runs(self, *, limit: int = 50) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 200))
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    principal_id,
                    principal_type,
                    principal_roles_json,
                    workspace_id,
                    session_id,
                    status,
                    tool_call_count,
                    created_at,
                    updated_at,
                    last_request_id,
                    policy_hash,
                    last_tool_name,
                    last_tool_manifest_hash,
                    metadata_json
                FROM agent_runs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()
        return [_record_from_row(row).summary() for row in rows]

    def get_run(self, run_id: str) -> JsonObject:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    run_id,
                    principal_id,
                    principal_type,
                    principal_roles_json,
                    workspace_id,
                    session_id,
                    status,
                    tool_call_count,
                    created_at,
                    updated_at,
                    last_request_id,
                    policy_hash,
                    last_tool_name,
                    last_tool_manifest_hash,
                    metadata_json
                FROM agent_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            raise AgentRunError(f"agent run not found: {run_id}")
        return _record_from_row(row).summary()

    def timeline(self, run_id: str, *, limit: int = 200) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 500))
        events: list[JsonObject] = []
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM audit_events
                ORDER BY rowid ASC
                """
            ).fetchall()
        for row in rows:
            try:
                payload = json.loads(str(row[0]))
            except json.JSONDecodeError as exc:
                raise AgentRunError("failed to decode audit event payload") from exc
            if not isinstance(payload, dict):
                raise AgentRunError("failed to decode audit event payload")
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict) or metadata.get("run_id") != run_id:
                continue
            events.append(_timeline_event(cast(JsonObject, payload)))
        return events[-bounded_limit:]

    def detail(self, run_id: str, *, timeline_limit: int = 200) -> JsonObject:
        return {
            "run": self.get_run(run_id),
            "timeline": cast(JsonValue, self.timeline(run_id, limit=timeline_limit)),
        }


def _record_from_row(row: tuple[object, ...]) -> AgentRunRecord:
    return AgentRunRecord(
        run_id=str(row[0]),
        principal_id=str(row[1]),
        principal_type=str(row[2]),
        principal_roles=_string_list(json.loads(str(row[3]))),
        workspace_id=str(row[4]),
        session_id=str(row[5]),
        status=str(row[6]),
        tool_call_count=int(str(row[7])),
        created_at=str(row[8]),
        updated_at=str(row[9]),
        last_request_id=_optional_string(row[10]),
        policy_hash=_optional_string(row[11]),
        last_tool_name=_optional_string(row[12]),
        last_tool_manifest_hash=_optional_string(row[13]),
        metadata=cast(JsonObject, json.loads(str(row[14]))),
    )


def _timeline_event(payload: JsonObject) -> JsonObject:
    metadata = payload.get("metadata")
    safe_metadata: JsonObject = metadata if isinstance(metadata, dict) else {}
    return {
        "event_id": payload.get("event_id"),
        "timestamp": payload.get("timestamp"),
        "event_type": payload.get("event_type"),
        "request_id": payload.get("request_id"),
        "tool_name": payload.get("tool_name"),
        "decision": payload.get("decision"),
        "event_hash": payload.get("event_hash"),
        "resource": payload.get("resource"),
        "metadata": safe_metadata,
    }


def _string_or_default(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
