"""Validate exact-candidate evidence from the MCC-006 Mission Command POC."""

from __future__ import annotations

import argparse
import json
import sqlite3
import stat
import subprocess
from pathlib import Path
from typing import Any, cast

from ithildin_audit_core import AuditWriter

try:
    from scripts.mission_command_control_plane_poc import (
        ADVERSARIAL_TESTS,
        DEFAULT_EVIDENCE_ROOT,
        RUNNER_OUTPUT_SENTINEL,
    )
except ModuleNotFoundError:
    from mission_command_control_plane_poc import (  # type: ignore[import-not-found,no-redef]
        ADVERSARIAL_TESTS,
        DEFAULT_EVIDENCE_ROOT,
        RUNNER_OUTPUT_SENTINEL,
    )

ROOT = Path(__file__).resolve().parents[1]


def build_report(repo_root: Path, evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    root = evidence_root if evidence_root.is_absolute() else repo_root / evidence_root
    paths = {
        "database": root / "db/ithildin.sqlite3",
        "audit": root / "logs/audit.jsonl",
        "state": root / "client/state.json",
        "configuration": root / "client/current-configuration.json",
        "candidate": root / "evidence/candidate.json",
        "enrollment": root / "evidence/enrollment-safe.json",
        "node_ready": root / "evidence/node-ready.json",
        "response_loss": root / "evidence/admission-response-loss-and-replay.json",
        "admission_drift": root / "evidence/admission-drifted-replay-denial.json",
        "claim": root / "evidence/primary-claim-safe.json",
        "running": root / "evidence/primary-running-report.json",
        "governed": root / "evidence/primary-governed-run.json",
        "before_restart": root / "evidence/primary-before-restart.json",
        "partition": root / "evidence/partition-denial.json",
        "claim_replay": root / "evidence/claim-nonce-replay-after-restart.json",
        "report_replay": root / "evidence/report-id-replay-after-restart.json",
        "admission_replay": root / "evidence/admission-replay-after-restart.json",
        "succeeded": root / "evidence/primary-succeeded-report.json",
        "primary_final": root / "evidence/primary-final.json",
        "cancellation": root / "evidence/cancellation-race.json",
        "revoked": root / "evidence/revoked-late-report.json",
        "audit_verification": root / "evidence/audit-verification.json",
        "inventory": root / "evidence/final-mission-inventory.json",
        "focused_tests": root / "evidence/focused-adversarial-tests.json",
        "focused_transcript": root / "evidence/focused-adversarial-tests.txt",
    }
    failures = [
        f"missing MCC-006 evidence: {name}" for name, path in paths.items() if not path.is_file()
    ]
    runtime: dict[str, Any] = {}
    if not failures:
        documents = {
            name: _json(path)
            for name, path in paths.items()
            if name not in {"database", "audit", "focused_transcript"}
        }
        current_commit = _git(repo_root, "rev-parse", "HEAD")
        current_dirty = bool(_git(repo_root, "status", "--short"))
        candidate = documents["candidate"]
        node_ready = documents["node_ready"]
        response_loss = documents["response_loss"]
        claim = documents["claim"]
        before_restart = documents["before_restart"]
        primary_final = documents["primary_final"]
        cancellation = documents["cancellation"]
        revoked = documents["revoked"]
        focused_tests = documents["focused_tests"]
        transcript = paths["focused_transcript"].read_text(encoding="utf-8")
        audit_text = paths["audit"].read_text(encoding="utf-8")
        evidence_text = "\n".join(
            path.read_text(encoding="utf-8")
            for name, path in paths.items()
            if name not in {"database", "audit", "state", "configuration"}
        )
        safe_and_log_text = (
            evidence_text
            + "\n"
            + audit_text
            + "\n"
            + "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted((root / "logs").glob("gateway-*.log"))
            )
        )
        state = documents["state"]
        private_key = str(state.get("private_key", ""))
        database = _database_evidence(paths["database"])
        writer = AuditWriter(paths["database"], paths["audit"])
        verification = writer.verify_chain()
        diagnostics = cast(dict[str, Any], writer.diagnostics())
        lifecycle = cast(dict[str, Any], diagnostics.get("lifecycle", {}))
        sqlite_jsonl_payloads_match = _sqlite_jsonl_payloads_match(
            paths["database"],
            paths["audit"],
        )
        template_payload_absent = _forbidden_payload_keys_absent(root / "evidence")
        transcript_valid = _focused_transcript_valid(transcript, focused_tests)
        runtime = {
            "candidate_commit_matches_current": candidate.get("git_commit") == current_commit,
            "candidate_and_current_tree_clean": candidate.get("source_tree_clean") is True
            and not current_dirty,
            "candidate_claim_is_review_only": candidate.get("claim_level")
            == "mission_control_plane_candidate_ready_for_external_review"
            and candidate.get("runner_launch_claimed") is False
            and candidate.get("production_deployment_authorized") is False
            and candidate.get("uat_acceptance_recorded") is False,
            "node_ready_with_gateway_derived_identity": str(
                node_ready.get("principal_id", "")
            ).startswith("agent:node.node_")
            and node_ready.get("workspace_id") == "default"
            and node_ready.get("heartbeat_observed_state") == "observed_connected",
            "response_loss_replayed_same_admission": response_loss.get("response_status_observed")
            == 200
            and response_loss.get("response_body_observed") is False
            and response_loss.get("replay_lifecycle_state") == "queued"
            and response_loss.get("replay_lifecycle_revision") == 1,
            "drifted_admission_replay_denied": documents["admission_drift"].get("status_code")
            == 409,
            "claim_delivered_without_saved_template_payload": claim.get("gateway_delivery_recorded")
            is True
            and claim.get("gateway_lifecycle_state") == "claimed"
            and claim.get("template_payload_included_in_saved_evidence") is False,
            "runner_running_and_agent_run_correlated_before_restart": before_restart.get(
                "lifecycle_state"
            )
            == "runner_reported_running"
            and before_restart.get("governed_agent_run_count") == 1
            and before_restart.get("governed_agent_run_correlation_basis")
            == "gateway_validated_claim_session",
            "governed_call_used_derived_node_authority": documents["governed"].get("status")
            == "completed"
            and documents["governed"].get("identity_source") == "gateway_derived_node"
            and documents["governed"].get("workspace_id") == "default"
            and documents["governed"].get("offline_fallback_used") is False,
            "partition_failed_closed_without_fallback": documents["partition"].get("status")
            == "failed_closed"
            and documents["partition"].get("local_execution_used") is False
            and documents["partition"].get("buffered_or_queued") is False
            and documents["partition"].get("automatic_retry_used") is False,
            "claim_nonce_replay_denied_after_restart": documents["claim_replay"].get("status_code")
            == 401,
            "exact_report_replay_idempotent_after_restart": documents["report_replay"].get(
                "status_code"
            )
            == 200
            and documents["report_replay"].get("evidence_status") == "complete",
            "admission_replay_durable_after_restart": documents["admission_replay"].get(
                "mission_id"
            )
            == response_loss.get("replay_mission_id"),
            "primary_mission_succeeded_without_provider_overclaim": primary_final.get(
                "lifecycle_state"
            )
            == "runner_reported_succeeded"
            and primary_final.get("model_provider_state") == "unknown"
            and primary_final.get("model_inference_known") is False
            and primary_final.get("model_output_verified") is False,
            "cancellation_race_preserved_both_truths": cancellation.get("cancel_lifecycle_state")
            == "cancel_requested"
            and cancellation.get("runner_stop_proven") is False
            and cast(dict[str, Any], cancellation.get("final_projection", {})).get(
                "lifecycle_state"
            )
            == "runner_reported_succeeded",
            "revoked_late_report_quarantined": revoked.get("node_status") == "revoked"
            and revoked.get("receipt_disposition") == "quarantined"
            and revoked.get("quarantine_reason_code") == "node_revoked"
            and cast(dict[str, Any], revoked.get("final_projection", {})).get("lifecycle_state")
            == "runner_reported_running",
            "focused_adversarial_matrix_passed": transcript_valid,
            "audit_chain_and_sqlite_jsonl_lifecycle_clean": verification.valid
            and sqlite_jsonl_payloads_match
            and lifecycle.get("status") == "clean"
            and diagnostics.get("sqlite_jsonl_event_count_match") is not False
            and lifecycle.get("sqlite_jsonl_event_count_match") is True
            and lifecycle.get("sqlite_jsonl_head_hash_match") is True
            and documents["audit_verification"].get("valid") is True,
            "database_lifecycle_and_correlation_proven": database.get("valid") is True,
            "template_payload_absent_from_saved_evidence": template_payload_absent
            and '"template_payload":' not in safe_and_log_text
            and '"mission_kind":"synthetic_read_review"' not in safe_and_log_text,
            "runner_output_absent_from_evidence": RUNNER_OUTPUT_SENTINEL not in safe_and_log_text,
            "node_private_key_absent_from_safe_evidence": bool(private_key)
            and private_key not in safe_and_log_text,
            "private_node_files_mode_0600": all(
                stat.S_IMODE(paths[name].stat().st_mode) == 0o600
                for name in ("state", "configuration")
            ),
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
        "claim_level": "mission_control_plane_candidate_ready_for_external_review",
        "non_claims": [
            "runner_launch",
            "runner_process_stop",
            "model_inference_custody",
            "output_correctness",
            "production_deployment",
            "release",
            "uat_acceptance",
            "arbitrary_host_control",
        ],
        "tool_count": tool_count,
        "checks": checks,
        "runtime": runtime,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin MCC-006 Mission Command POC evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"claim_level: {report['claim_level']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(f"{name}: {str(value).lower()}" for name, value in report["checks"].items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _database_evidence(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as connection:
        missions = connection.execute(
            "SELECT client_request_id, lifecycle_state FROM missions ORDER BY client_request_id"
        ).fetchall()
        quarantined = connection.execute(
            "SELECT count(*) FROM mission_report_receipts WHERE receipt_disposition = 'quarantined'"
        ).fetchone()[0]
        correlated = connection.execute(
            "SELECT count(*) FROM agent_runs WHERE metadata_json LIKE ?",
            ('%"mission_binding_source":"gateway_validated_claim_session"%',),
        ).fetchone()[0]
        replay_nonce = connection.execute(
            "SELECT count(*) FROM node_nonces WHERE nonce = ?",
            ("c0" * 16,),
        ).fetchone()[0]
        incomplete = connection.execute(
            "SELECT count(*) FROM mission_transition_attempts WHERE evidence_status != 'complete'"
        ).fetchone()[0]
        bindings = connection.execute(
            "SELECT count(*) FROM mission_audit_evidence_bindings"
        ).fetchone()[0]
    by_request = {str(request_id): str(state) for request_id, state in missions}
    return {
        "valid": by_request
        == {
            "mcc006-cancellation-race": "runner_reported_succeeded",
            "mcc006-primary-response-loss": "runner_reported_succeeded",
            "mcc006-revoked-late-report": "runner_reported_running",
        }
        and quarantined >= 1
        and correlated == 1
        and replay_nonce == 1
        and incomplete == 0
        and bindings >= 10,
        "mission_states": by_request,
        "quarantined_receipts": quarantined,
        "correlated_agent_runs": correlated,
        "replay_nonce_count": replay_nonce,
        "incomplete_transitions": incomplete,
        "audit_evidence_bindings": bindings,
    }


def _sqlite_jsonl_payloads_match(db_path: Path, audit_path: Path) -> bool:
    with sqlite3.connect(db_path) as connection:
        committed = [
            str(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM audit_events ORDER BY rowid ASC"
            ).fetchall()
        ]
    return audit_path.read_text(encoding="utf-8").splitlines() == committed


def _forbidden_payload_keys_absent(evidence_dir: Path) -> bool:
    forbidden = {"template_payload", "runner_output", "model_output", "prompt", "chain_of_thought"}
    for path in evidence_dir.glob("*.json"):
        if not _object_keys_absent(_json(path), forbidden):
            return False
    return True


def _object_keys_absent(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return not (set(value) & forbidden) and all(
            _object_keys_absent(item, forbidden) for item in value.values()
        )
    if isinstance(value, list):
        return all(_object_keys_absent(item, forbidden) for item in value)
    return True


def _focused_transcript_valid(transcript: str, document: dict[str, Any]) -> bool:
    selected = document.get("selected_tests")
    return (
        document.get("returncode") == 0
        and document.get("all_selected_tests_passed") is True
        and selected == list(ADVERSARIAL_TESTS)
        and all(test in transcript for test in ADVERSARIAL_TESTS)
        and transcript.count(" PASSED ") >= len(ADVERSARIAL_TESTS)
    )


def _json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"invalid MCC-006 evidence document: {path.name}")
    return cast(dict[str, Any], document)


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


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
