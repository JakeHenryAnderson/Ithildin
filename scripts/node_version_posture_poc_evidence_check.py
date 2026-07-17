"""Validate safe evidence from the observed Node version-posture POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path
from typing import Any, cast

from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-version-posture-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "enrollment": root / "evidence/enrollment-safe.json",
        "assignment": root / "evidence/minimum-assignment.json",
        "invalid": root / "evidence/invalid-version-result.json",
        "below": root / "evidence/below-minimum-heartbeat.json",
        "upgrade": root / "evidence/operator-upgrade-heartbeat.json",
        "upgrade_inventory": root / "evidence/operator-upgrade-inventory.json",
        "restart": root / "evidence/restart-inventory.json",
        "rollback": root / "evidence/operator-rollback-heartbeat.json",
        "rollback_inventory": root / "evidence/operator-rollback-inventory.json",
        "revocation": root / "evidence/revocation.json",
        "post_revocation": root / "evidence/post-revocation-result.json",
    }
    failures = [
        f"missing version-posture POC evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, bool] = {}
    if not failures:
        documents = {
            name: _json(path) for name, path in paths.items() if name not in {"database", "audit"}
        }
        with sqlite3.connect(paths["database"]) as connection:
            node_row = connection.execute(
                "SELECT status, evidence_status, last_node_version, "
                "desired_configuration_generation FROM nodes"
            ).fetchone()
            configuration_row = connection.execute(
                "SELECT bundle_json, evidence_status FROM node_configurations"
            ).fetchone()
        configuration = json.loads(str(configuration_row[0])) if configuration_row else {}
        desired = configuration.get("configuration") if isinstance(configuration, dict) else None
        audit_text = paths["audit"].read_text(encoding="utf-8")
        events = [json.loads(line) for line in audit_text.splitlines() if line]
        event_types = [str(event.get("event_type", "")) for event in events]
        private_key = str(documents["state"].get("private_key", ""))
        safe_outputs = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name not in {"database", "audit", "state"}
        )
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "minimum_version_persisted": bool(configuration_row)
            and configuration_row[1] == "complete"
            and isinstance(desired, dict)
            and desired.get("minimum_node_version") == "0.2.0",
            "below_minimum_observed": documents["below"].get("version_posture") == "below_minimum"
            and documents["below"].get("last_observed_node_version") == "0.1.0",
            "operator_upgrade_observed": documents["upgrade"].get("version_posture")
            == "meets_minimum"
            and documents["upgrade_inventory"].get("last_observed_node_version") == "0.2.0",
            "restart_preserved_upgrade_posture": documents["restart"].get("version_posture")
            == "meets_minimum"
            and documents["restart"].get("last_observed_node_version") == "0.2.0",
            "operator_rollback_observed": documents["rollback"].get("version_posture")
            == "below_minimum"
            and documents["rollback_inventory"].get("last_observed_node_version") == "0.1.0",
            "invalid_version_denied": documents["invalid"].get("status") == 400,
            "revocation_preserved_last_observation": bool(node_row)
            and node_row[0] == "revoked"
            and node_row[1] == "complete"
            and node_row[2] == "0.1.0"
            and node_row[3] == 1,
            "post_revocation_heartbeat_denied": documents["post_revocation"].get(
                "post_revocation_heartbeat"
            )
            == "denied",
            "signed_heartbeat_events_present": event_types.count("node.heartbeat.accepted") == 3,
            "audit_chain_valid": verification.valid,
            "state_file_mode_0600": stat.S_IMODE(paths["state"].stat().st_mode) == 0o600,
            "private_key_absent_from_safe_evidence_and_audit": bool(private_key)
            and private_key not in safe_outputs
            and private_key not in audit_text,
        }
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    checks = {"tool_count_unchanged": tool_count == 24, **runtime}
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "signed_version_posture_and_operator_managed_maintenance_observation",
        "non_claims": [
            "node_self_update",
            "package_authenticity",
            "process_or_runner_health",
            "automatic_rollback_or_fleet_rollout",
            "production_readiness_or_uat_approval",
        ],
        "tool_count": tool_count,
        "checks": checks,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node version-posture POC evidence check",
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
        raise ValueError(f"invalid version-posture evidence: {path.name}")
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
