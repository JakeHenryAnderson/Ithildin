"""Validate observed local-preview Ithildin Node POC evidence without exposing secrets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path
from typing import Any, cast

from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "enrollment": root / "evidence/enrollment-response.json",
        "enroll_result": root / "evidence/enroll-result.json",
        "heartbeat": root / "evidence/heartbeat-result.json",
        "replay": root / "evidence/replay-result.json",
        "restart_heartbeat": root / "evidence/restart-heartbeat-result.json",
        "revoke": root / "evidence/revoke-result.json",
        "post_revoke": root / "evidence/post-revoke-result.json",
        "inventory": root / "evidence/node-inventory.json",
        "audit_verify": root / "evidence/audit-verify.json",
    }
    failures = [
        f"missing Node POC evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, Any] = {}
    if not failures:
        documents = {
            name: _json(path)
            for name, path in paths.items()
            if name not in {"database", "audit"}
        }
        state = documents["state"]
        enrollment = documents["enrollment"]
        inventory = documents["inventory"]
        node_rows, nonce_count, code_rows = _database_state(paths["database"])
        audit_text = paths["audit"].read_text(encoding="utf-8")
        audit_events = [json.loads(line) for line in audit_text.splitlines() if line]
        event_types = [str(event.get("event_type", "")) for event in audit_events]
        secret = str(enrollment.get("enrollment_code", ""))
        private_key = str(state.get("private_key", ""))
        safe_outputs = "\n".join(
            paths[name].read_text(encoding="utf-8")
            for name in (
                "enroll_result",
                "heartbeat",
                "replay",
                "restart_heartbeat",
                "revoke",
                "post_revoke",
                "inventory",
                "audit_verify",
            )
        )
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "enrollment_code_consumed_once": len(code_rows) == 1
            and code_rows[0][0] is not None
            and code_rows[0][1] is not None,
            "enrollment_evidence_complete": bool(code_rows)
            and all(row[2] == "complete" for row in code_rows),
            "gateway_derived_identity": bool(node_rows)
            and str(node_rows[0][1]) == f"agent:node.{node_rows[0][0]}",
            "node_evidence_complete": bool(node_rows)
            and all(row[3] == "complete" for row in node_rows),
            "signed_heartbeat_observed": documents["heartbeat"].get("observed_state")
            == "observed_connected",
            "replay_denied": documents["replay"].get("replay_outcome") == "denied",
            "restart_heartbeat_observed": documents["restart_heartbeat"].get("observed_state")
            == "observed_connected",
            "revocation_persisted": bool(node_rows)
            and node_rows[0][2] == "revoked"
            and documents["revoke"].get("status") == "revoked",
            "post_revocation_denied": documents["post_revoke"].get("post_revoke_outcome")
            == "denied",
            "durable_nonce_count_sufficient": nonce_count >= 3,
            "state_file_mode_0600": stat.S_IMODE(paths["state"].stat().st_mode) == 0o600,
            "enrollment_secret_absent_from_audit": bool(secret) and secret not in audit_text,
            "private_key_absent_from_safe_outputs": bool(private_key)
            and private_key not in safe_outputs
            and private_key not in audit_text,
            "node_lifecycle_audit_present": all(
                event_type in event_types
                for event_type in (
                    "node.enrollment_code.issued",
                    "node.enrolled",
                    "node.heartbeat.accepted",
                    "node.revoked",
                )
            ),
            "audit_chain_valid": verification.valid,
            "api_audit_verification_valid": documents["audit_verify"].get("valid") is True,
            "inventory_denies_runner_health_claim": inventory.get("runner_health_known") is False,
            "node_count": len(node_rows),
            "nonce_count": nonce_count,
            "audit_event_count": verification.event_count,
            "audit_head_hash": verification.head_hash,
        }

    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    checks = {
        "tool_count_unchanged": tool_count == 24,
        **{key: value for key, value in runtime.items() if isinstance(value, bool)},
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "authenticated_node_identity_and_connectivity",
        "non_claims": [
            "filesystem_non_bypass",
            "runner_health",
            "model_health",
            "node_tool_execution",
            "remote_mcp",
            "production_identity",
        ],
        "tool_count": tool_count,
        "checks": checks,
        "runtime": runtime,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node POC evidence check",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve(), args.evidence_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def _json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"invalid Node POC evidence document: {path.name}")
    return cast(dict[str, Any], document)


def _database_state(
    db_path: Path,
) -> tuple[list[tuple[str, str, str, str]], int, list[tuple[object, object, str]]]:
    with sqlite3.connect(db_path) as connection:
        node_rows = cast(
            list[tuple[str, str, str, str]],
            connection.execute(
                "SELECT node_id, principal_id, status, evidence_status FROM nodes"
            ).fetchall(),
        )
        nonce_count = int(connection.execute("SELECT COUNT(*) FROM node_nonces").fetchone()[0])
        code_rows = cast(
            list[tuple[object, object, str]],
            connection.execute(
                "SELECT consumed_at, consumed_node_id, evidence_status "
                "FROM node_enrollment_codes"
            ).fetchall(),
        )
    return node_rows, nonce_count, code_rows


if __name__ == "__main__":
    raise SystemExit(main())
