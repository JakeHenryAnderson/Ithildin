"""Validate safe evidence from the observed Node identity-key rotation POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path
from typing import Any, cast

from ithildin_api.nodes import node_identity_key_id
from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-identity-key-rotation-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "enrollment": root / "evidence/enrollment-safe.json",
        "staged": root / "evidence/staged-safe.json",
        "activation": root / "evidence/gateway-activation-safe.json",
        "retired": root / "evidence/retired-key-result.json",
        "pre_restart": root / "evidence/pre-restart-inventory.json",
        "recovered": root / "evidence/recovered-safe.json",
        "heartbeat": root / "evidence/new-key-heartbeat.json",
        "post_restart": root / "evidence/post-restart-inventory.json",
        "revocation": root / "evidence/revocation.json",
        "post_revocation": root / "evidence/post-revocation-result.json",
    }
    failures = [
        f"missing identity-rotation POC evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, bool] = {}
    if not failures:
        documents = {
            name: _json(path) for name, path in paths.items() if name not in {"database", "audit"}
        }
        state = documents["state"]
        public_key = str(state.get("public_key", ""))
        private_key = str(state.get("private_key", ""))
        active_key_id = node_identity_key_id(public_key) if public_key else ""
        with sqlite3.connect(paths["database"]) as connection:
            node = connection.execute(
                "SELECT status, evidence_status, public_key FROM nodes"
            ).fetchone()
            rotation = connection.execute(
                """
                SELECT status, evidence_status, current_key_id, next_key_id
                FROM node_identity_key_rotations ORDER BY created_at DESC LIMIT 1
                """
            ).fetchone()
        audit_text = paths["audit"].read_text(encoding="utf-8")
        event_types = [
            json.loads(line).get("event_type") for line in audit_text.splitlines() if line
        ]
        safe_outputs = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name not in {"database", "audit", "state"}
        )
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "pending_k2_persisted_before_activation": documents["staged"].get(
                "pending_identity_rotation_id"
            )
            is not None
            and documents["staged"].get("pending_identity_key_id") is not None,
            "gateway_activated_k2_before_local_promotion": documents["pre_restart"]
            .get("identity_key_rotation", {})
            .get("status")
            == "activated"
            and documents["staged"].get("pending_identity_rotation_id") is not None,
            "retired_k1_denied": documents["retired"].get("retired_key_heartbeat") == "denied",
            "restart_recovery_promoted_k2": documents["recovered"].get(
                "pending_identity_rotation_id"
            )
            is None
            and documents["recovered"].get("active_identity_key_id") == active_key_id,
            "new_k2_heartbeat_accepted": documents["heartbeat"].get("observed_state")
            == "observed_connected"
            and documents["post_restart"].get("active_identity_key_id") == active_key_id,
            "gateway_and_node_key_match": bool(node) and node[2] == public_key,
            "rotation_evidence_complete": bool(rotation)
            and rotation[0] == "activated"
            and rotation[1] == "complete"
            and rotation[3] == active_key_id
            and rotation[2] != rotation[3],
            "revocation_denied_k2": bool(node)
            and node[0] == "revoked"
            and node[1] == "complete"
            and documents["post_revocation"].get("post_revocation_heartbeat") == "denied",
            "rotation_audit_events_present": event_types.count(
                "node.identity_key_rotation.challenge_issued"
            )
            == 1
            and event_types.count("node.identity_key.rotated") == 1,
            "audit_chain_valid": verification.valid,
            "state_file_mode_0600": stat.S_IMODE(paths["state"].stat().st_mode) == 0o600,
            "private_and_public_key_absent_from_safe_evidence_and_audit": bool(private_key)
            and private_key not in safe_outputs
            and private_key not in audit_text
            and public_key not in safe_outputs
            and public_key not in audit_text,
        }
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    checks = {"tool_count_unchanged": tool_count == 24, **runtime}
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "two_proof_node_identity_key_rotation_and_crash_recovery",
        "non_claims": [
            "private_key_custody_or_hardware_attestation",
            "production_pki_or_remote_transport",
            "fleet_rollout_or_automatic_scheduling",
            "runner_or_model_provider_health",
            "production_readiness_or_uat_approval",
        ],
        "tool_count": tool_count,
        "checks": checks,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node identity-key rotation POC evidence check",
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
        raise ValueError(f"invalid identity-rotation evidence: {path.name}")
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
