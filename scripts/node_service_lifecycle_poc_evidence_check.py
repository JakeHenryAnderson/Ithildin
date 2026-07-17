"""Validate safe evidence from the observed Node service lifecycle POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-service-lifecycle-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    evidence = root / "evidence"
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "audit_private": root / "keys/audit-private.pem",
        "configuration_private": root / "keys/configuration-private.pem",
        "enrollment": evidence / "enrollment-safe.json",
        "assignment": evidence / "assignment.json",
        "initial": evidence / "initial-cycle.json",
        "initial_inventory": evidence / "initial-inventory.json",
        "concurrent_denial": evidence / "concurrent-service-denial.json",
        "graceful_stop": evidence / "graceful-service-stop.json",
        "image": evidence / "image-config.json",
        "modes": evidence / "private-file-modes.json",
        "partition": evidence / "partition-cycle.json",
        "restart": evidence / "restart-inventory.json",
        "upgrade": evidence / "operator-upgrade-cycle.json",
        "upgrade_inventory": evidence / "operator-upgrade-inventory.json",
        "rollback": evidence / "operator-rollback-cycle.json",
        "rollback_inventory": evidence / "operator-rollback-inventory.json",
        "final_status": evidence / "final-node-status.json",
        "revocation": evidence / "revocation.json",
        "post_revocation": evidence / "post-revocation-cycle.json",
    }
    failures = [
        f"missing Node service lifecycle evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, bool] = {}
    if not failures:
        documents = {
            name: _json(path)
            for name, path in paths.items()
            if name not in {"database", "audit", "audit_private", "configuration_private"}
        }
        with sqlite3.connect(paths["database"]) as connection:
            node_row = connection.execute(
                "SELECT status, evidence_status, last_node_version, "
                "desired_configuration_generation FROM nodes"
            ).fetchone()
        audit_text = paths["audit"].read_text(encoding="utf-8")
        events = [json.loads(line) for line in audit_text.splitlines() if line]
        event_types = [str(event.get("event_type", "")) for event in events]
        safe_text = "\n".join(path.read_text(encoding="utf-8") for path in evidence.glob("*.json"))
        private_material = (
            paths["audit_private"].read_text(encoding="utf-8"),
            paths["configuration_private"].read_text(encoding="utf-8"),
        )
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "initial_cycle_below_minimum": documents["initial"].get("status") == "synchronized"
            and documents["initial_inventory"].get("version_posture") == "below_minimum",
            "gateway_partition_failed_closed": documents["partition"].get("exit_code") == 1
            and documents["partition"].get("status") == "degraded_retrying"
            and documents["partition"].get("error") == "Gateway is unavailable",
            "concurrent_identity_use_denied": documents["concurrent_denial"].get("exit_code")
            == 2
            and documents["concurrent_denial"].get("identity_already_in_use") is True,
            "service_manager_stop_was_graceful": documents["graceful_stop"].get("stopped")
            is True,
            "gateway_restart_preserved_identity_and_configuration": documents[
                "restart"
            ].get("node_id")
            == documents["enrollment"].get("node_id")
            and documents["restart"].get("acknowledged_configuration_generation") == 1,
            "operator_upgrade_observed": documents["upgrade"].get("status") == "synchronized"
            and documents["upgrade_inventory"].get("last_observed_node_version") == "0.2.0"
            and documents["upgrade_inventory"].get("version_posture") == "meets_minimum",
            "operator_rollback_observed": documents["rollback"].get("status") == "synchronized"
            and documents["rollback_inventory"].get("last_observed_node_version") == "0.1.0"
            and documents["rollback_inventory"].get("version_posture") == "below_minimum",
            "identity_reused_across_containers": documents["final_status"].get("node_id")
            == documents["enrollment"].get("node_id")
            and documents["final_status"].get("active_identity_key_id")
            == documents["enrollment"].get("active_identity_key_id"),
            "revocation_denied_service_cycle": documents["post_revocation"].get("exit_code") == 1
            and documents["post_revocation"].get("status") == "degraded_retrying"
            and documents["post_revocation"].get("error")
            == "Gateway rejected Node request with HTTP 401",
            "node_files_mode_0600": documents["modes"].get("state") == "600"
            and documents["modes"].get("configuration") == "600"
            and documents["modes"].get("service_lease") == "600",
            "image_runs_unprivileged_without_listener": documents["image"].get("User")
            == "10002:10002"
            and documents["image"].get("ExposedPorts") in (None, {}),
            "service_nonclaims_present": all(
                document.get("runner_execution_authority") is False
                and document.get("self_update_authority") is False
                for document in (
                    documents["initial"],
                    documents["partition"],
                    documents["upgrade"],
                    documents["rollback"],
                    documents["post_revocation"],
                )
            ),
            "accepted_service_audit_events_present": event_types.count(
                "node.heartbeat.accepted"
            )
            == 4
            and event_types.count("node.configuration.retrieved") == 4,
            "revocation_is_durable": bool(node_row)
            and node_row[0] == "revoked"
            and node_row[1] == "complete"
            and node_row[2] == "0.1.0"
            and node_row[3] == 1,
            "audit_chain_valid": verification.valid,
            "private_keys_absent_from_safe_evidence_and_audit": all(
                value not in safe_text and value not in audit_text for value in private_material
            ),
        }
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    checks = {"tool_count_unchanged": tool_count == 24, **runtime}
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "operator_managed_node_service_restart_partition_and_identity_continuity",
        "non_claims": [
            "node_self_update_or_package_provenance",
            "automatic_upgrade_or_rollback",
            "runner_execution_health_or_enforcement",
            "production_transport_identity_or_storage",
            "production_readiness_or_uat_approval",
        ],
        "tool_count": tool_count,
        "checks": checks,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Node service lifecycle POC evidence check",
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
        raise ValueError(f"invalid service lifecycle evidence: {path.name}")
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
