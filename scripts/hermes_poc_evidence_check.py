"""Validate observed Track A Hermes POC evidence without promoting its claims."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from ithildin_audit_core import AuditWriter
from ithildin_schemas.hashing import sha256_digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path("var/hermes-poc/db/ithildin.sqlite3")
DEFAULT_AUDIT = Path("var/hermes-poc/logs/audit.jsonl")
DEFAULT_ARTIFACT = Path("deploy/hermes-poc/workspace/output/case-001-artifact.txt")
EXPECTED_PRINCIPAL = "agent:mcp-local"
EXPECTED_SESSION = "mcp-stdio"
EXPECTED_ARTIFACT_LABEL = "sandbox://local-demo-sandbox/output/case-001-artifact.txt"
EXPECTED_SOAK_PATHS = {f"soak/case-{index:03d}.md" for index in range(1, 26)}

JsonObject = dict[str, Any]


def load_events(path: Path) -> list[JsonObject]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def evaluate_runtime_evidence(
    events: list[JsonObject],
    *,
    approval_statuses: dict[str, str],
    artifact_content: str,
) -> dict[str, Any]:
    completed = _events(events, event_type="tool.execution.completed")
    failed = _events(events, event_type="tool.execution.failed")
    policies = _events(events, event_type="policy.evaluated")
    approvals = _events(events, event_type="approval.created")

    allowed_list = _has_policy(policies, "fs.list", "allow") and _has_tool(completed, "fs.list")
    allowed_read = _has_policy(policies, "fs.read", "allow") and _has_tool(completed, "fs.read")
    traversal_denials = [
        event
        for event in policies
        if event.get("tool_name") == "fs.read"
        and event.get("decision") == "deny"
        and "outside the workspace scope" in _reason(event)
    ]
    http_denials = [
        event
        for event in policies
        if event.get("tool_name") == "http.fetch" and event.get("decision") == "deny"
    ]
    http_denied_without_execution = bool(http_denials) and all(
        not _has_request(completed, str(event.get("request_id", ""))) for event in http_denials
    )

    approval_required = _has_policy(
        policies, "sandbox.artifact.write_text", "require_approval"
    ) and bool(approvals)
    created_approval_ids = {
        str(_metadata(event).get("approval_id", "")) for event in approvals
    }
    executed_approval_ids = {
        approval_id
        for approval_id, status in approval_statuses.items()
        if status == "executed" and approval_id in created_approval_ids
    }
    completed_writes = [
        event
        for event in completed
        if event.get("tool_name") == "sandbox.artifact.write_text"
        and _metadata(event).get("approval_binding_verified") is True
        and _metadata(event).get("approval_id") in executed_approval_ids
    ]
    replay_denied = any(
        event.get("tool_name") == "sandbox.artifact.write_text"
        and "approval is not approved: executed" in _reason(event)
        for event in failed
    )

    expected_content_hash = sha256_digest(artifact_content)
    artifact_hash_bound = any(
        _metadata(event).get("artifact_label") == EXPECTED_ARTIFACT_LABEL
        and _metadata(event).get("content_sha256") == expected_content_hash
        for event in completed_writes
    )
    completed_soak_paths = {
        str(event.get("resource", {}).get("path", ""))
        for event in completed
        if event.get("tool_name") == "fs.read" and isinstance(event.get("resource"), dict)
    }
    soak_completed = completed_soak_paths.issuperset(EXPECTED_SOAK_PATHS)

    governed_events = [
        event
        for event in events
        if event.get("tool_name")
        and event.get("event_type")
        in {
            "agent.session.started",
            "policy.evaluated",
            "tool.execution.started",
            "tool.execution.completed",
            "tool.execution.failed",
            "approval.created",
            "approval.approved",
        }
    ]
    fixed_identity = bool(governed_events) and all(
        _metadata(event).get("principal_id") == EXPECTED_PRINCIPAL
        and _metadata(event).get("session_id") == EXPECTED_SESSION
        for event in governed_events
    )

    return {
        "allowed_list_observed": allowed_list,
        "allowed_read_observed": allowed_read,
        "out_of_root_read_denied": bool(traversal_denials),
        "unapproved_http_denied_without_execution": http_denied_without_execution,
        "approval_required_observed": approval_required,
        "approval_executed_once": bool(completed_writes),
        "approval_replay_denied": replay_denied,
        "artifact_content_hash_bound": artifact_hash_bound,
        "soak_25_unique_reads_completed": soak_completed,
        "fixed_stdio_identity_observed": fixed_identity,
        "approval_ids": sorted(executed_approval_ids),
        "soak_unique_read_count": len(completed_soak_paths & EXPECTED_SOAK_PATHS),
        "event_count": len(events),
    }


def build_report(
    repo_root: Path,
    *,
    db_path: Path = DEFAULT_DB,
    audit_path: Path = DEFAULT_AUDIT,
    artifact_path: Path = DEFAULT_ARTIFACT,
) -> dict[str, Any]:
    db_path = _under(repo_root, db_path)
    audit_path = _under(repo_root, audit_path)
    artifact_path = _under(repo_root, artifact_path)
    failures: list[str] = []
    for label, path in (
        ("database", db_path),
        ("audit log", audit_path),
        ("synthetic artifact", artifact_path),
    ):
        if not path.is_file():
            failures.append(f"missing Hermes POC {label}")

    lock_path = repo_root / "tool-manifests.lock.json"
    tool_names: list[str] = []
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        tool_names = sorted(str(item["name"]) for item in lock.get("manifests", []))
    else:
        failures.append("missing manifest lock")

    runtime: dict[str, Any] = {}
    chain: dict[str, Any] = {"valid": False, "event_count": 0, "head_hash": None}
    if not failures:
        events = load_events(audit_path)
        approval_statuses = _approval_statuses(db_path)
        artifact_content = artifact_path.read_text(encoding="utf-8")
        runtime = evaluate_runtime_evidence(
            events,
            approval_statuses=approval_statuses,
            artifact_content=artifact_content,
        )
        verification = AuditWriter(db_path, audit_path).verify_chain()
        chain = {
            "valid": verification.valid,
            "event_count": verification.event_count,
            "head_hash": verification.head_hash,
            "failure": verification.failure,
        }

    checks = {
        "tool_count_unchanged": len(tool_names) == 24,
        "delete_tool_absent": not any("delete" in name for name in tool_names),
        "audit_chain_valid": chain["valid"],
        **{key: value for key, value in runtime.items() if isinstance(value, bool)},
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "governed_surface_enforced",
        "non_claims": [
            "fixture_access_path_constrained",
            "agent_fully_non_bypassable",
            "ithildin_managed_runner_lifecycle",
            "dynamic_agent_identity",
        ],
        "tool_count": len(tool_names),
        "checks": checks,
        "runtime": runtime,
        "audit_chain": chain,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Hermes POC evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"claim_level: {report['claim_level']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(
        f"{name}: {str(passed).lower()}" for name, passed in report["checks"].items()
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _approval_statuses(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT approval_id, status FROM approvals").fetchall()
    return {str(approval_id): str(status) for approval_id, status in rows}


def _events(events: list[JsonObject], *, event_type: str) -> list[JsonObject]:
    return [event for event in events if event.get("event_type") == event_type]


def _has_policy(events: list[JsonObject], tool_name: str, decision: str) -> bool:
    return any(
        event.get("tool_name") == tool_name and event.get("decision") == decision
        for event in events
    )


def _has_tool(events: list[JsonObject], tool_name: str) -> bool:
    return any(event.get("tool_name") == tool_name for event in events)


def _has_request(events: list[JsonObject], request_id: str) -> bool:
    return any(event.get("request_id") == request_id for event in events)


def _metadata(event: JsonObject) -> JsonObject:
    value = event.get("metadata")
    return value if isinstance(value, dict) else {}


def _reason(event: JsonObject) -> str:
    return str(_metadata(event).get("reason", ""))


def _under(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--artifact-path", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(
        args.repo_root.resolve(),
        db_path=args.db_path,
        audit_path=args.audit_path,
        artifact_path=args.artifact_path,
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
