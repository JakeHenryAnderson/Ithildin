"""Validate redacted evidence from the observed signed Node configuration POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
from pathlib import Path
from typing import Any, cast

from ithildin_api.node_configuration import NodeConfigurationSigner
from ithildin_audit_core import AuditWriter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = Path("var/node-config-poc-20260716")


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "configuration": root / "client/current-configuration.json",
        "enrollment": root / "evidence/enrollment-safe.json",
        "first_assignment": root / "evidence/assignment-generation-1.json",
        "first_ack": root / "evidence/generation-1-acknowledgment.json",
        "tamper": root / "evidence/tamper-result.json",
        "second_assignment": root / "evidence/assignment-generation-2.json",
        "drift": root / "evidence/pre-restart-drift-inventory.json",
        "restart_ack": root / "evidence/post-restart-generation-2-acknowledgment.json",
        "restart_heartbeat": root / "evidence/post-restart-heartbeat.json",
        "current": root / "evidence/post-restart-current-inventory.json",
        "revocation": root / "evidence/revocation.json",
        "post_revocation": root / "evidence/post-revocation-result.json",
        "config_private": root / "keys/config-private.pem",
        "config_public": root / "keys/config-public.pem",
    }
    failures = [
        f"missing Node configuration POC evidence: {name}"
        for name, path in paths.items()
        if not path.is_file()
    ]
    runtime: dict[str, Any] = {}
    if not failures:
        documents = {
            name: _json(path)
            for name, path in paths.items()
            if name
            not in {"database", "audit", "config_private", "config_public"}
        }
        state = documents["state"]
        configuration = documents["configuration"]
        signer = NodeConfigurationSigner.load(paths["config_private"], paths["config_public"])
        with sqlite3.connect(paths["database"]) as connection:
            configuration_rows = connection.execute(
                "SELECT generation, configuration_digest, evidence_status "
                "FROM node_configurations ORDER BY generation"
            ).fetchall()
            node_row = connection.execute(
                "SELECT status, desired_configuration_generation, "
                "acknowledged_configuration_generation, "
                "configuration_acknowledgment_status FROM nodes"
            ).fetchone()
        audit_text = paths["audit"].read_text(encoding="utf-8")
        events = [json.loads(line) for line in audit_text.splitlines() if line]
        event_types = [str(event.get("event_type", "")) for event in events]
        private_key = str(state.get("private_key", ""))
        safe_outputs = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name
            not in {
                "database",
                "audit",
                "state",
                "configuration",
                "config_private",
                "config_public",
            }
        )
        verification = AuditWriter(paths["database"], paths["audit"]).verify_chain()
        runtime = {
            "dedicated_configuration_trust_pinned": state.get("gateway_configuration_key_id")
            == signer.trust.key_id
            and state.get("gateway_configuration_public_key") == signer.trust.public_key,
            "immutable_generations_persisted": [row[0] for row in configuration_rows] == [1, 2]
            and len({row[1] for row in configuration_rows}) == 2,
            "assignment_evidence_complete": all(row[2] == "complete" for row in configuration_rows),
            "generation_one_stored_not_enforced": documents["first_ack"].get(
                "configuration_acknowledgment_status"
            )
            == "stored_not_enforced",
            "tampered_bundle_denied": documents["tamper"].get("tampered_bundle_outcome")
            == "denied",
            "drift_observed": documents["drift"].get("configuration_state")
            == "configuration_drift"
            and documents["drift"].get("desired_configuration_generation") == 2
            and documents["drift"].get("acknowledged_configuration_generation") == 1,
            "restart_retrieval_and_ack_observed": documents["current"].get(
                "configuration_state"
            )
            == "stored_current_not_enforced"
            and documents["current"].get("desired_configuration_generation") == 2
            and documents["current"].get("acknowledged_configuration_generation") == 2,
            "stored_bundle_matches_gateway_ack": configuration.get("generation") == 2
            and configuration.get("configuration_digest")
            == documents["current"].get("acknowledged_configuration_digest"),
            "revocation_persisted": bool(node_row)
            and node_row[0] == "revoked"
            and documents["revocation"].get("status") == "revoked",
            "post_revocation_retrieval_denied": documents["post_revocation"].get(
                "post_revocation_configuration_retrieval"
            )
            == "denied",
            "private_files_mode_0600": all(
                stat.S_IMODE(paths[name].stat().st_mode) == 0o600
                for name in ("state", "configuration", "config_private")
            ),
            "private_key_absent_from_outputs_and_audit": bool(private_key)
            and private_key not in safe_outputs
            and private_key not in audit_text,
            "configuration_audit_events_present": all(
                event_types.count(event_type) == 2
                for event_type in (
                    "node.configuration.assigned",
                    "node.configuration.retrieved",
                    "node.configuration.acknowledged",
                    "node.heartbeat.accepted",
                )
            ),
            "audit_chain_valid": verification.valid,
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
        "claim_level": "signed_configuration_distribution_and_stored_acknowledgment",
        "non_claims": [
            "configuration_enforcement",
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
        "Ithildin Node configuration POC evidence check",
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
        raise ValueError(f"invalid Node configuration POC evidence: {path.name}")
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
