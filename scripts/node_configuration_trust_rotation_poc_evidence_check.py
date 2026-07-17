"""Validate redacted evidence from the observed configuration trust-rotation POC."""

from __future__ import annotations

import json
import sqlite3
import stat
from pathlib import Path
from typing import Any

from ithildin_api.node_configuration import NodeConfigurationSigner
from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "var/node-config-poc-trust-rotation-20260716"


def build_report(root: Path = EVIDENCE_ROOT) -> dict[str, Any]:
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "configuration": root / "client/current-configuration.json",
        "k1_private": root / "keys/k1-private.pem",
        "k1_public": root / "keys/k1-public.pem",
        "k2_private": root / "keys/k2-private.pem",
        "k2_public": root / "keys/k2-public.pem",
        "staged_state": root / "evidence/k1-staged-state-safe.json",
        "active_state": root / "evidence/k2-active-state-safe.json",
        "recovery_state": root / "evidence/k1-recovery-state-safe.json",
        "staged_inventory": root / "evidence/k1-staged-inventory.json",
        "active_inventory": root / "evidence/k2-active-inventory.json",
        "recovery_inventory": root / "evidence/k1-recovery-inventory.json",
    }
    failures = [
        f"missing trust-rotation evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    checks: dict[str, bool] = {}
    if not failures:
        documents = {
            name: _json(path)
            for name, path in paths.items()
            if name
            not in {
                "database",
                "audit",
                "k1_private",
                "k1_public",
                "k2_private",
                "k2_public",
            }
        }
        k1 = NodeConfigurationSigner.load(paths["k1_private"], paths["k1_public"])
        k2 = NodeConfigurationSigner.load(paths["k2_private"], paths["k2_public"])
        with sqlite3.connect(paths["database"]) as connection:
            rows = connection.execute(
                "SELECT generation, bundle_json, evidence_status FROM node_configurations "
                "ORDER BY generation"
            ).fetchall()
            transition = connection.execute(
                "SELECT current_key_id, next_key_id, evidence_status, "
                "acknowledgment_evidence_status FROM node_configuration_trust_transitions"
            ).fetchone()
        signer_ids = []
        for row in rows:
            bundle = json.loads(str(row[1]))
            signer_ids.append(str(bundle["signature"]["key_id"]))
        audit_text = paths["audit"].read_text(encoding="utf-8")
        events = [json.loads(line) for line in audit_text.splitlines() if line]
        event_types = [str(event.get("event_type", "")) for event in events]
        staged_state = documents["staged_state"]
        active_state = documents["active_state"]
        recovery_state = documents["recovery_state"]
        staged_transition = documents["staged_inventory"].get(
            "configuration_trust_transition", {}
        )
        active_transition = documents["active_inventory"].get(
            "configuration_trust_transition", {}
        )
        recovery_inventory = documents["recovery_inventory"]
        recovery_transition = recovery_inventory.get("configuration_trust_transition", {})
        private_values = [
            str(documents["state"].get("private_key", "")),
            paths["k1_private"].read_text(encoding="utf-8"),
            paths["k2_private"].read_text(encoding="utf-8"),
        ]
        safe_text = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name in {
                "staged_state",
                "active_state",
                "recovery_state",
                "staged_inventory",
                "active_inventory",
                "recovery_inventory",
            }
        )
        checks = {
            "k1_signed_targeted_transition_persisted": bool(transition)
            and transition[0] == k1.trust.key_id
            and transition[1] == k2.trust.key_id
            and transition[2] == "complete"
            and transition[3] == "complete",
            "node_staged_k2_without_activation": staged_state.get(
                "configuration_trust_key_id"
            )
            == k1.trust.key_id
            and staged_state.get("pending_configuration_key_id") == k2.trust.key_id
            and staged_transition.get("rotation_state") == "staged_not_active",
            "k2_configuration_promoted_active_trust": active_state.get(
                "configuration_trust_key_id"
            )
            == k2.trust.key_id
            and active_state.get("previous_configuration_key_id") == k1.trust.key_id
            and active_transition.get("rotation_state") == "active_not_enforced"
            and active_transition.get("activation_proven") is True,
            "k1_recovery_did_not_demote_k2": recovery_state.get(
                "configuration_trust_key_id"
            )
            == k2.trust.key_id
            and recovery_state.get("previous_configuration_key_id") == k1.trust.key_id
            and recovery_inventory.get("acknowledged_configuration_signing_key_id")
            == k1.trust.key_id
            and recovery_inventory.get("acknowledged_active_configuration_signing_key_id")
            == k2.trust.key_id
            and recovery_transition.get("rotation_state") == "active_not_enforced",
            "restart_signer_sequence_persisted": [row[0] for row in rows] == [1, 2, 3]
            and signer_ids == [k1.trust.key_id, k2.trust.key_id, k1.trust.key_id]
            and all(row[2] == "complete" for row in rows),
            "private_files_mode_0600": all(
                stat.S_IMODE(paths[name].stat().st_mode) == 0o600
                for name in ("state", "configuration", "k1_private", "k2_private")
            ),
            "private_material_absent_from_safe_evidence_and_audit": all(
                value and value not in safe_text and value not in audit_text
                for value in private_values
            ),
            "transition_audit_events_present": all(
                event_type in event_types
                for event_type in (
                    "node.configuration_trust_transition.assigned",
                    "node.configuration_trust_transition.retrieved",
                    "node.configuration_trust_transition.acknowledged",
                )
            ),
            "configuration_audit_events_present": event_types.count(
                "node.configuration.assigned"
            )
            == 3
            and event_types.count("node.configuration.retrieved") == 3
            and event_types.count("node.configuration.acknowledged") == 3,
            "audit_chain_valid": AuditWriter(
                paths["database"], paths["audit"]
            ).verify_chain().valid,
            "tool_count_unchanged": len(
                _json(ROOT / "tool-manifests.lock.json").get("manifests", [])
            )
            == 24,
        }
        failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checks": checks,
        "claim_level": "restart_based_per_node_configuration_trust_rotation_and_recovery",
        "non_claims": [
            "runner_enforcement",
            "automatic_fleet_rotation",
            "production_pki_or_key_custody",
            "production_identity_transport_storage_or_telemetry",
            "release_or_uat_approval",
        ],
    }


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


if __name__ == "__main__":
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["valid"] else 1)
