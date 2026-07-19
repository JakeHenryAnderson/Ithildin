"""Read-only agent run correlation records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest

if TYPE_CHECKING:
    from ithildin_schemas import ApprovalRequest


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


@dataclass(frozen=True)
class AgentRunFilters:
    principal_id: str | None = None
    workspace_id: str | None = None
    status: str | None = None
    tool_name: str | None = None
    session_id: str | None = None

    def applied(self) -> JsonObject:
        return {
            key: value
            for key, value in {
                "principal_id": self.principal_id,
                "workspace_id": self.workspace_id,
                "status": self.status,
                "tool_name": self.tool_name,
                "session_id": self.session_id,
            }.items()
            if value is not None
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
        run_metadata: JsonObject | None = None,
    ) -> tuple[AgentRunContext, bool]:
        principal_id = _string_or_default(principal.get("id"), "unknown")
        principal_type = _string_or_default(principal.get("type"), "unknown")
        principal_roles = _string_list(principal.get("roles"))
        now = datetime.now(UTC).isoformat()
        requested_metadata: JsonObject = {
            "created_by": "governed_tool_call",
            **(run_metadata or {}),
        }
        if requested_metadata.get("created_by") != "governed_tool_call":
            raise AgentRunError("agent run creation source cannot be overridden")
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT run_id, metadata_json
                FROM agent_runs
                WHERE principal_id = ?
                  AND session_id = ?
                  AND workspace_id = ?
                """,
                (principal_id, session_id, workspace_id),
            ).fetchone()
            if row is None:
                run_id = _new_id("run")
                metadata = requested_metadata
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
                        canonical_json(metadata),
                    ),
                )
                created = True
            else:
                run_id = str(row[0])
                metadata = _merge_run_metadata(row[1], requested_metadata)
                connection.execute(
                    """
                    UPDATE agent_runs
                    SET updated_at = ?,
                        last_request_id = ?,
                        policy_hash = COALESCE(?, policy_hash),
                        last_tool_name = ?,
                        last_tool_manifest_hash = COALESCE(?, last_tool_manifest_hash),
                        metadata_json = ?,
                        tool_call_count = tool_call_count + 1
                    WHERE run_id = ?
                    """,
                    (
                        now,
                        request_id,
                        policy_hash,
                        tool_name,
                        tool_manifest_hash,
                        canonical_json(metadata),
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
        return cast(list[JsonObject], self.query_runs(limit=limit)["runs"])

    def query_runs(
        self,
        *,
        limit: int = 50,
        filters: AgentRunFilters | None = None,
    ) -> JsonObject:
        bounded_limit = max(1, min(limit, 200))
        filters = filters or AgentRunFilters()
        where_clauses: list[str] = []
        params: list[str | int] = []
        for column, value in [
            ("principal_id", filters.principal_id),
            ("workspace_id", filters.workspace_id),
            ("status", filters.status),
            ("last_tool_name", filters.tool_name),
            ("session_id", filters.session_id),
        ]:
            if value is None:
                continue
            where_clauses.append(f"{column} = ?")
            params.append(value)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        params.append(bounded_limit)
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                f"""
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
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        runs = [_record_from_row(row).summary() for row in rows]
        return {
            "runs": cast(JsonValue, runs),
            "summary": _runs_summary(runs, filters),
        }

    def mission_candidates(self, mission_id: str) -> list[JsonObject]:
        """Return every run carrying one exact server-written mission binding."""

        if (
            len(mission_id) != 40
            or not mission_id.startswith("mission_")
            or any(character not in "0123456789abcdef" for character in mission_id[8:])
        ):
            raise AgentRunError("invalid mission correlation ID")
        with sqlite3.connect(self.db_path) as connection:
            invalid = connection.execute(
                "SELECT 1 FROM agent_runs WHERE json_valid(metadata_json) = 0 LIMIT 1"
            ).fetchone()
            if invalid is not None:
                raise AgentRunError("failed to decode agent run metadata")
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
                WHERE json_extract(metadata_json, '$.mission_id') = ?
                ORDER BY updated_at DESC, run_id ASC
                """,
                (mission_id,),
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

    def evidence_export(
        self,
        run_id: str,
        *,
        approvals: list[ApprovalRequest],
        patch_diagnostics: JsonObject,
        timeline_limit: int = 200,
    ) -> JsonObject:
        run = self.get_run(run_id)
        timeline = [
            _export_timeline_event(event)
            for event in self.timeline(run_id, limit=timeline_limit)
        ]
        correlated_request_ids = {
            str(event["request_id"])
            for event in timeline
            if isinstance(event.get("request_id"), str) and event.get("request_id")
        }
        correlated_approval_ids = {
            str(event["approval_id"])
            for event in timeline
            if isinstance(event.get("approval_id"), str) and event.get("approval_id")
        }
        approval_summaries = [
            _export_approval(approval)
            for approval in approvals
            if _approval_correlates_with_run(
                approval,
                run_id=run_id,
                request_ids=correlated_request_ids,
            )
        ]
        correlated_approval_ids.update(
            str(approval["approval_id"])
            for approval in approval_summaries
            if isinstance(approval.get("approval_id"), str)
        )
        patch_summaries = _export_patch_diagnostics(
            patch_diagnostics,
            workspace_id=str(run["workspace_id"]),
            approval_ids=correlated_approval_ids,
        )
        exported_at = datetime.now(UTC).isoformat()
        warnings = _export_warnings(
            run=run,
            timeline=timeline,
            approvals=approval_summaries,
            patch_diagnostics=patch_summaries,
            original_timeline_count=len(self.timeline(run_id, limit=500)),
            timeline_limit=timeline_limit,
        )
        bundle: JsonObject = {
            "schema_version": "1",
            "export_id": _new_id("runev"),
            "exported_at": exported_at,
            "run": _export_run_summary(run),
            "summary": _export_human_summary(
                run=run,
                timeline=timeline,
                approvals=approval_summaries,
                patch_diagnostics=patch_summaries,
                warnings=warnings,
            ),
            "timeline": cast(JsonValue, timeline),
            "approvals": cast(JsonValue, approval_summaries),
            "patch_diagnostics": cast(JsonValue, patch_summaries),
            "signed_export_references": [],
            "evidence_hashes": {},
            "redaction_summary": {
                "excluded_categories": [
                    "prompts",
                    "model_output",
                    "raw_tool_arguments",
                    "file_contents",
                    "diffs",
                    "response_bodies",
                    "secrets",
                    "raw_sensitive_paths",
                ]
            },
            "warnings": cast(JsonValue, warnings),
        }
        bundle["evidence_hashes"] = _section_hashes(bundle)
        return bundle


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


def _merge_run_metadata(raw: object, requested: JsonObject) -> JsonObject:
    try:
        existing = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise AgentRunError("failed to decode agent run metadata") from exc
    if not isinstance(existing, dict):
        raise AgentRunError("failed to decode agent run metadata")
    for key, value in requested.items():
        if key in existing and existing[key] != value:
            raise AgentRunError("agent run authority provenance conflicts")
    return {**cast(JsonObject, existing), **requested}


def _runs_summary(runs: list[JsonObject], filters: AgentRunFilters) -> JsonObject:
    latest_update = None
    for run in runs:
        updated_at = run.get("updated_at")
        if isinstance(updated_at, str) and (latest_update is None or updated_at > latest_update):
            latest_update = updated_at
    return {
        "returned": len(runs),
        "filters": filters.applied(),
        "workspaces": _count_by_key(runs, "workspace_id"),
        "principals": _count_by_key(runs, "principal_id"),
        "statuses": _count_by_key(runs, "status"),
        "tools": _count_by_key(runs, "last_tool_name"),
        "latest_updated_at": latest_update,
    }


def _count_by_key(runs: list[JsonObject], key: str) -> JsonObject:
    counts: dict[str, int] = {}
    for run in runs:
        value = run.get(key)
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    return cast(JsonObject, counts)


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


def _export_run_summary(run: JsonObject) -> JsonObject:
    metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
    model_client_label = metadata.get("model_client_label") if isinstance(metadata, dict) else None
    sandbox_id = metadata.get("sandbox_id") if isinstance(metadata, dict) else None
    return {
        "run_id": run.get("run_id"),
        "principal_id": run.get("principal_id"),
        "workspace_id": run.get("workspace_id"),
        "sandbox_id": sandbox_id if isinstance(sandbox_id, str) else None,
        "session_id": run.get("session_id"),
        "model_client_label": model_client_label if isinstance(model_client_label, str) else None,
        "status": run.get("status"),
        "policy_hash": run.get("policy_hash"),
        "manifest_lock_hash": run.get("last_tool_manifest_hash"),
        "tool_call_count": run.get("tool_call_count"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "origin": _export_run_origin(cast(JsonObject, metadata)),
    }


def _export_run_origin(metadata: JsonObject) -> JsonObject | None:
    node_id = metadata.get("node_id")
    if (
        metadata.get("ingress_kind") != "node_governed_access"
        or metadata.get("identity_source") != "gateway_derived_node"
        or not isinstance(node_id, str)
        or not node_id
    ):
        return None
    return {
        "ingress_kind": "node_governed_access",
        "identity_source": "gateway_derived_node",
        "node_id": node_id,
        "node_display_name": metadata.get("node_display_name"),
        "authorization_profile": metadata.get("authorization_profile"),
        "configuration_generation": metadata.get("configuration_generation"),
        "configuration_digest": metadata.get("configuration_digest"),
        "offline_fallback_allowed": metadata.get("offline_fallback_allowed"),
        "runner_enforcement_proven": metadata.get("runner_enforcement_proven"),
    }


def _export_timeline_event(event: JsonObject) -> JsonObject:
    metadata = _json_object_or_empty(event.get("metadata"))
    approval_id = _metadata_string(metadata, "approval_id")
    return {
        "event_id": event.get("event_id"),
        "run_id": _metadata_string(metadata, "run_id"),
        "timestamp": event.get("timestamp"),
        "category": event.get("event_type"),
        "status": _timeline_status(event),
        "correlation_id": event.get("request_id"),
        "request_id": event.get("request_id"),
        "tool_name": event.get("tool_name"),
        "approval_id": approval_id,
        "audit_event_id": event.get("event_id"),
        "policy_hash": _metadata_string(metadata, "policy_hash"),
        "manifest_hash": _metadata_string(metadata, "manifest_hash"),
        "metadata": _safe_timeline_metadata(metadata),
    }


def _export_human_summary(
    *,
    run: JsonObject,
    timeline: list[JsonObject],
    approvals: list[JsonObject],
    patch_diagnostics: list[JsonObject],
    warnings: list[JsonObject],
) -> JsonObject:
    tools_used = sorted(
        {
            tool
            for event in timeline
            if isinstance((tool := event.get("tool_name")), str) and tool
        }
    )
    decisions = _count_values(_timeline_decision(event) for event in timeline)
    decisions.update(
        _count_values(
            event.get("status")
            for event in timeline
            if event.get("category") == "policy.evaluated"
        )
    )
    return {
        "principal_id": run.get("principal_id"),
        "workspace_id": run.get("workspace_id"),
        "session_id": run.get("session_id"),
        "status": run.get("status"),
        "tool_call_count": run.get("tool_call_count"),
        "tools_used": cast(JsonValue, tools_used),
        "decision_counts": cast(JsonValue, decisions),
        "approval_count": len(approvals),
        "patch_diagnostic_count": len(patch_diagnostics),
        "audit_event_count": len(timeline),
        "warning_count": len(warnings),
        "latest_policy_hash": run.get("policy_hash"),
        "manifest_lock_hash": run.get("last_tool_manifest_hash"),
    }


def _count_values(values: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _timeline_decision(event: JsonObject) -> str | None:
    metadata = event.get("metadata")
    if isinstance(metadata, dict):
        decision = metadata.get("decision")
        if isinstance(decision, str) and decision:
            return decision
    return None


def _timeline_status(event: JsonObject) -> str:
    event_type = event.get("event_type")
    if isinstance(event_type, str):
        if event_type.endswith(".completed"):
            return "completed"
        if event_type.endswith(".failed"):
            return "failed"
        if event_type.endswith(".started"):
            return "started"
        if event_type == "policy.evaluated":
            decision = event.get("decision")
            return decision if isinstance(decision, str) else "evaluated"
    return "recorded"


def _safe_timeline_metadata(metadata: JsonObject) -> JsonObject:
    allowed = {
        "run_id",
        "session_id",
        "workspace_id",
        "principal_id",
        "executor",
        "approval_id",
        "approval_binding_verified",
        "proposal_id",
        "proposal_hash",
        "base_file_hash",
        "policy_hash",
        "policy_version",
        "policy_engine",
        "manifest_hash",
        "manifest_version",
        "redaction_count",
        "redaction_categories",
    }
    return {key: value for key, value in metadata.items() if key in allowed}


def _export_approval(approval: ApprovalRequest) -> JsonObject:
    scope = approval.one_time_scope
    return {
        "approval_id": approval.approval_id,
        "request_id": approval.request_id,
        "request_hash": approval.request_hash,
        "tool_name": approval.tool_name,
        "status": approval.status.value,
        "expires_at": approval.expires_at.isoformat(),
        "summary_hash": sha256_digest(approval.summary),
        "principal_id": _json_object_string(approval.principal, "id"),
        "resource_type": _json_object_string(approval.resource, "type"),
        "resource_hash": sha256_digest(_safe_resource_reference(approval.resource)),
        "one_time_scope": _safe_approval_scope(scope),
        "metadata": _safe_approval_metadata(approval.metadata),
    }


def _approval_correlates_with_run(
    approval: ApprovalRequest,
    *,
    run_id: str,
    request_ids: set[str],
) -> bool:
    metadata_run_id = _json_object_string(approval.metadata, "run_id")
    return metadata_run_id == run_id or approval.request_id in request_ids


def _safe_approval_scope(scope: JsonObject) -> JsonObject:
    allowed = {
        "proposal_id",
        "proposal_hash",
        "base_file_hash",
        "expected_post_apply_file_hash",
        "manifest_hash",
        "manifest_version",
        "policy_hash",
        "policy_version",
        "policy_engine",
        "policy_document_version",
        "request_hash",
        "tool_input_schema_hash",
        "workspace_id",
    }
    result = {key: value for key, value in scope.items() if key in allowed}
    path = _json_object_string(scope, "path")
    if path is not None:
        result["path_hash"] = sha256_digest(path)
    return result


def _safe_approval_metadata(metadata: JsonObject) -> JsonObject:
    allowed = {
        "policy_engine",
        "policy_hash",
        "policy_version",
        "policy_document_version",
        "matched_rules",
        "manifest_hash",
        "manifest_version",
        "tool_input_schema_hash",
        "approval_scope_hash",
        "proposal_id",
        "proposal_hash",
        "base_file_hash",
        "run_id",
        "session_id",
        "workspace_id",
        "principal_id",
    }
    return {key: value for key, value in metadata.items() if key in allowed}


def _export_patch_diagnostics(
    patch_diagnostics: JsonObject,
    *,
    workspace_id: str,
    approval_ids: set[str],
) -> list[JsonObject]:
    attempts = patch_diagnostics.get("attempts")
    if not isinstance(attempts, list):
        return []
    exported: list[JsonObject] = []
    for item in attempts:
        if not isinstance(item, dict):
            continue
        attempt: JsonObject = item
        approval_id = _json_object_string(attempt, "approval_id")
        attempt_workspace_id = _json_object_string(attempt, "workspace_id")
        if approval_id not in approval_ids and attempt_workspace_id != workspace_id:
            continue
        exported.append(_safe_patch_attempt(attempt))
    return exported


def _safe_patch_attempt(attempt: JsonObject) -> JsonObject:
    result = {
        key: attempt.get(key)
        for key in [
            "attempt_id",
            "approval_id",
            "proposal_id",
            "request_id",
            "workspace_id",
            "proposal_hash",
            "base_file_hash",
            "expected_post_apply_hash",
            "status",
            "failure_reason",
            "created_at",
            "updated_at",
            "current_target_hash",
            "current_matches_expected_post_apply_hash",
            "current_matches_base_file_hash",
            "diagnostic_status",
            "diagnostic_reason",
        ]
    }
    path = _json_object_string(attempt, "path")
    if path is not None:
        result["path_hash"] = sha256_digest(path)
    return result


def _export_warnings(
    *,
    run: JsonObject,
    timeline: list[JsonObject],
    approvals: list[JsonObject],
    patch_diagnostics: list[JsonObject],
    original_timeline_count: int,
    timeline_limit: int,
) -> list[JsonObject]:
    warnings: list[JsonObject] = []
    if original_timeline_count > len(timeline) or original_timeline_count > timeline_limit:
        warnings.append(
            {
                "type": "timeline_truncated",
                "message": "Timeline was bounded by the requested limit.",
                "limit": timeline_limit,
            }
        )
    if not timeline:
        warnings.append(
            {
                "type": "missing_audit_correlation",
                "message": "No correlated audit timeline events were found for this run.",
            }
        )
    if run.get("tool_call_count") and not approvals:
        warnings.append(
            {
                "type": "approval_correlation_unavailable",
                "message": "No approval records correlated to this run.",
            }
        )
    if not patch_diagnostics:
        warnings.append(
            {
                "type": "patch_diagnostics_unavailable",
                "message": "No incomplete patch apply diagnostics correlated to this run.",
            }
        )
    warnings.append(
        {
            "type": "signed_evidence_unavailable",
            "message": "No signed audit export reference is attached to this run export.",
        }
    )
    return warnings


def _section_hashes(bundle: JsonObject) -> JsonObject:
    return {
        "run_sha256": sha256_digest(bundle["run"]),
        "timeline_sha256": sha256_digest(bundle["timeline"]),
        "approvals_sha256": sha256_digest(bundle["approvals"]),
        "patch_diagnostics_sha256": sha256_digest(bundle["patch_diagnostics"]),
    }


def _metadata_string(metadata: object, key: str) -> str | None:
    if isinstance(metadata, dict):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _json_object_or_empty(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _json_object_string(payload: JsonObject, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _safe_resource_reference(resource: JsonObject) -> str:
    safe: JsonObject = {}
    resource_type = _json_object_string(resource, "type")
    workspace_id = _json_object_string(resource, "workspace_id")
    if resource_type is not None:
        safe["type"] = resource_type
    if workspace_id is not None:
        safe["workspace_id"] = workspace_id
    return canonical_json(safe)


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
