"""Validate redacted evidence from the observed Node governed-access POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path
from typing import Any, cast

from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-governed-access-poc-20260717")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "configuration": root / "client/current-configuration.json",
        "enrollment": root / "evidence/enrollment-safe.json",
        "assignment": root / "evidence/assignment.json",
        "acknowledgment": root / "evidence/acknowledgment.json",
        "heartbeat": root / "evidence/heartbeat.json",
        "read_before": root / "evidence/governed-read-before-restart.json",
        "network_denial": root / "evidence/network-denial.json",
        "workspace_denial": root / "evidence/cross-workspace-denial.json",
        "partition": root / "evidence/partition-result.json",
        "replay": root / "evidence/replay-after-restart.json",
        "read_after": root / "evidence/governed-read-after-restart.json",
        "audit_verification": root / "evidence/audit-verification.json",
        "final_posture": root / "evidence/final-node-posture.json",
    }
    failures = [
        f"missing Node governed-access POC evidence: {name}"
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
        private_key = str(state.get("private_key", ""))
        evidence_text = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name not in {"database", "audit", "state", "configuration"}
        )
        audit_text = paths["audit"].read_text(encoding="utf-8")
        audit_events = [json.loads(line) for line in audit_text.splitlines() if line]
        with sqlite3.connect(paths["database"]) as connection:
            node_row = connection.execute(
                "SELECT node_id, principal_id, workspace_id, status, evidence_status, "
                "desired_configuration_generation, acknowledged_configuration_generation, "
                "configuration_acknowledgment_status FROM nodes"
            ).fetchone()
            replay_nonce_count = connection.execute(
                "SELECT COUNT(*) FROM node_nonces WHERE nonce = ?", ("a7" * 16,)
            ).fetchone()[0]
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "gateway_derived_identity_persisted": bool(node_row)
            and str(node_row[1]) == f"agent:node.{node_row[0]}"
            and node_row[2] == "default"
            and node_row[3] == "enrolled"
            and node_row[4] == "complete",
            "current_configuration_acknowledged_not_enforced": bool(node_row)
            and node_row[5] == 1
            and node_row[6] == 1
            and node_row[7] == "stored_not_enforced"
            and documents["final_posture"].get("configuration_state")
            == "stored_current_not_enforced",
            "governed_read_completed_before_restart": documents["read_before"].get("status")
            == "completed"
            and documents["read_before"].get("identity_source")
            == "gateway_derived_node"
            and documents["read_before"].get("workspace_id") == "default"
            and documents["read_before"].get("offline_fallback_used") is False,
            "network_denied_without_execution": documents["network_denial"].get("status")
            == "denied"
            and documents["network_denial"].get("is_error") is True,
            "cross_workspace_denied": documents["workspace_denial"].get("status")
            == "denied"
            and documents["workspace_denial"].get("is_error") is True,
            "partition_failed_closed_without_queue_or_retry": documents["partition"].get(
                "status"
            )
            == "failed_closed"
            and documents["partition"].get("error_category") == "Gateway is unavailable"
            and documents["partition"].get("local_execution_used") is False
            and documents["partition"].get("buffered_or_queued") is False
            and documents["partition"].get("automatic_retry_used") is False,
            "replay_denied_after_gateway_restart": documents["replay"].get(
                "replay_after_gateway_restart"
            )
            == "denied"
            and replay_nonce_count == 1,
            "fresh_read_completed_after_restart": documents["read_after"].get("status")
            == "completed",
            "audit_chain_valid": verification.valid
            and documents["audit_verification"].get("valid") is True,
            "derived_principal_and_configuration_bound_in_audit": bool(node_row)
            and str(node_row[1]) in audit_text
            and ":cfg:1:sha256:" in audit_text,
            "read_execution_and_ingress_denials_audited": sum(
                event.get("event_type") == "tool.execution.completed"
                for event in audit_events
            )
            == 2
            and sum(
                event.get("event_type") == "policy.evaluated"
                and event.get("decision") == "deny"
                for event in audit_events
            )
            >= 2,
            "private_files_mode_0600": all(
                stat.S_IMODE(paths[name].stat().st_mode) == 0o600
                for name in ("state", "configuration")
            ),
            "private_key_absent_from_evidence_and_audit": bool(private_key)
            and private_key not in evidence_text
            and private_key not in audit_text,
            "raw_read_content_not_persisted_in_evidence": "Governed external agent demo workspace"
            not in evidence_text,
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
        "claim_level": "node_authenticated_workspace_bound_governed_read_local_preview",
        "non_claims": [
            "node_write_or_network_authority",
            "runner_enforcement",
            "offline_execution",
            "remote_mcp",
            "production_identity",
            "arbitrary_host_control",
        ],
        "tool_count": tool_count,
        "checks": checks,
        "runtime": runtime,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node governed-access POC evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"claim_level: {report['claim_level']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{name}: {str(passed).lower()}" for name, passed in report["checks"].items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"invalid Node governed-access POC evidence: {path.name}")
    return cast(dict[str, Any], document)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve(), args.evidence_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
