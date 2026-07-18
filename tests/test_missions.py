from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.missions import (
    EVIDENCE_COMPLETE,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_PENDING,
    MISSION_QUEUED,
    MISSION_UNADMITTED,
    MissionAdmissionPayload,
    MissionAuthoritySnapshot,
    MissionConflictError,
    MissionError,
    MissionRunnerReportPayload,
    MissionStore,
)
from ithildin_api.promotion_authority import AdminPrincipalContext
from pydantic import ValidationError

SHA_A = "sha256:" + ("a" * 64)
SHA_B = "sha256:" + ("b" * 64)
SHA_C = "sha256:" + ("c" * 64)
SHA_D = "sha256:" + ("d" * 64)
SHA_E = "sha256:" + ("e" * 64)
SHA_F = "sha256:" + ("f" * 64)
SHA_1 = "sha256:" + ("1" * 64)
SHA_2 = "sha256:" + ("2" * 64)
NODE_ID = "node_" + ("1" * 32)


def test_mission_models_reject_caller_authored_or_unsafe_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MissionAdmissionPayload.model_validate(
            {
                **_payload().model_dump(mode="json"),
                "objective": "caller-authored prompt",
            }
        )
    with pytest.raises(ValidationError, match="unsafe mission client request ID"):
        _payload(client_request_id="unsafe/identifier")
    with pytest.raises(ValidationError):
        _payload(mission_template_id="arbitrary_runner_command")


def test_runner_report_model_is_closed_and_semantically_bound() -> None:
    report = _runner_report()

    assert report.report_kind == "runner_succeeded"
    assert report.outcome_code == "succeeded"
    assert report.canonical_digest().startswith("sha256:")
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MissionRunnerReportPayload.model_validate(
            {**report.model_dump(mode="json"), "summary": "caller-authored report"}
        )
    with pytest.raises(ValidationError, match="kind and outcome do not match"):
        _runner_report(outcome_code="failed")
    with pytest.raises(ValidationError, match="requires a reason code"):
        _runner_report(
            report_kind="runner_failed",
            outcome_code="failed",
            artifact_digest=None,
        )
    with pytest.raises(ValidationError, match="artifact digest is not allowed"):
        _runner_report(report_kind="runner_running", outcome_code="started")
    with pytest.raises(ValidationError):
        _runner_report(
            report_kind="runner_failed",
            outcome_code="failed",
            reason_code="private_data",
            artifact_digest=None,
        )
    with pytest.raises(ValidationError, match="frozen"):
        report.reason_code = "runner_error"


def test_admission_payload_is_immutable_after_validation() -> None:
    payload = _payload()

    with pytest.raises(ValidationError, match="frozen"):
        payload.client_request_id = "changed-after-validation"


def test_admission_stages_without_advancing_lifecycle_or_public_inventory(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)

    staged = store.stage_admission(_payload(), authority=_authority(), now=now)

    assert staged.idempotent_replay is False
    assert staged.mission.lifecycle_state == MISSION_UNADMITTED
    assert staged.mission.lifecycle_revision == 0
    assert staged.mission.admitted_at is None
    assert staged.transition.evidence_status == EVIDENCE_PENDING
    assert staged.transition.prior_lifecycle_state == MISSION_UNADMITTED
    assert staged.transition.proposed_lifecycle_state == MISSION_QUEUED
    assert staged.transition.audit_event_id is None
    assert store.list_admitted() == []
    summary = staged.mission.safe_summary()
    assert "objective" not in summary
    assert "summary" not in summary
    assert summary["runner_state_authority"] == "runner_reported_only"
    assert summary["model_provider_state_known"] is False


def test_admission_finalizes_only_with_bound_audit_evidence(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    staged = store.stage_admission(_payload(), authority=_authority(), now=now)
    event_id = "evt_" + ("9" * 32)

    admitted = store.finalize_admission(
        staged.transition.transition_id,
        audit_event_id=event_id,
        audit_event_hash=SHA_1,
        now=now + timedelta(seconds=1),
    )

    assert admitted.lifecycle_state == MISSION_QUEUED
    assert admitted.lifecycle_revision == 1
    assert admitted.admitted_at == (now + timedelta(seconds=1)).isoformat()
    transition = store.get_transition(staged.transition.transition_id)
    assert transition.evidence_status == EVIDENCE_COMPLETE
    assert transition.audit_event_id == event_id
    assert transition.audit_event_hash == SHA_1
    assert len(store.list_admitted()) == 1

    replay = store.finalize_admission(
        staged.transition.transition_id,
        audit_event_id=event_id,
        audit_event_hash=SHA_1,
    )
    assert replay.mission_id == admitted.mission_id
    with pytest.raises(MissionConflictError, match="evidence conflicts"):
        store.finalize_admission(
            staged.transition.transition_id,
            audit_event_id="evt_" + ("8" * 32),
            audit_event_hash=SHA_2,
        )


def test_audit_evidence_cannot_finalize_two_missions(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.stage_admission(_payload(), authority=_authority())
    second = store.stage_admission(
        _payload(client_request_id="operator-request-002"),
        authority=_authority(),
    )
    event_id = "evt_" + ("9" * 32)
    store.finalize_admission(
        first.transition.transition_id,
        audit_event_id=event_id,
        audit_event_hash=SHA_1,
    )

    with pytest.raises(MissionConflictError, match="audit evidence is already bound"):
        store.finalize_admission(
            second.transition.transition_id,
            audit_event_id=event_id,
            audit_event_hash=SHA_1,
        )
    assert store.get(second.mission.mission_id).lifecycle_state == MISSION_UNADMITTED
    assert store.get_transition(second.transition.transition_id).evidence_status == EVIDENCE_PENDING


def test_evidence_interruption_preserves_prior_lifecycle_and_blocks_finalize(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    staged = store.stage_admission(_payload(), authority=_authority())

    failed = store.mark_transition_evidence_incomplete(
        staged.transition.transition_id,
        failure_reason_code="audit_write_failed",
    )

    assert failed.evidence_status == EVIDENCE_INCOMPLETE
    assert failed.failure_reason_code == "audit_write_failed"
    mission = store.get(staged.mission.mission_id)
    assert mission.lifecycle_state == MISSION_UNADMITTED
    assert mission.lifecycle_revision == 0
    assert mission.admitted_at is None
    assert store.list_admitted() == []
    replay = store.mark_transition_evidence_incomplete(
        staged.transition.transition_id,
        failure_reason_code="audit_write_failed",
    )
    assert replay == failed
    with pytest.raises(MissionConflictError, match="evidence is incomplete"):
        store.finalize_admission(
            staged.transition.transition_id,
            audit_event_id="evt_" + ("9" * 32),
            audit_event_hash=SHA_1,
        )


def test_admission_idempotency_is_exact_and_authority_namespaced(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = _payload()
    authority = _authority()
    first = store.stage_admission(payload, authority=authority)

    exact = store.stage_admission(payload, authority=authority)

    assert exact.idempotent_replay is True
    assert exact.mission.mission_id == first.mission.mission_id
    assert exact.transition.transition_id == first.transition.transition_id
    with pytest.raises(MissionConflictError, match="client request ID conflicts"):
        store.stage_admission(
            _payload(requested_timeout_seconds=301),
            authority=authority,
        )

    next_generation = _authority(requester_identity_generation=SHA_2)
    namespaced = store.stage_admission(payload, authority=next_generation)
    assert namespaced.mission.mission_id != first.mission.mission_id
    assert namespaced.mission.requester_identity_generation == SHA_2


def test_admission_rejects_payload_authority_mismatch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(MissionConflictError, match="target Node authority mismatch"):
        store.stage_admission(
            _payload(),
            authority=_authority(target_node_id="node_" + ("2" * 32)),
        )


def test_stored_authority_tamper_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_admission(_payload(), authority=_authority())
    db_path = tmp_path / "ithildin.sqlite3"
    with sqlite3.connect(db_path) as connection:
        snapshot = json.loads(
            connection.execute(
                "SELECT authority_snapshot_json FROM missions WHERE mission_id = ?",
                (staged.mission.mission_id,),
            ).fetchone()[0]
        )
        snapshot["workspace_id"] = "tampered"
        connection.execute(
            "UPDATE missions SET authority_snapshot_json = ? WHERE mission_id = ?",
            (json.dumps(snapshot), staged.mission.mission_id),
        )
        connection.commit()

    with pytest.raises(MissionError, match="snapshot hash is invalid"):
        store.get(staged.mission.mission_id)


def test_stored_indexed_authority_or_digest_tamper_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_admission(_payload(), authority=_authority())
    db_path = tmp_path / "ithildin.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE missions SET workspace_id = ? WHERE mission_id = ?",
            ("tampered", staged.mission.mission_id),
        )
        connection.commit()
    with pytest.raises(MissionError, match="authority bindings are inconsistent"):
        store.get(staged.mission.mission_id)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE missions SET workspace_id = ?, envelope_digest = ? WHERE mission_id = ?",
            ("default", SHA_A, staged.mission.mission_id),
        )
        connection.commit()
    with pytest.raises(MissionError, match="envelope digest is invalid"):
        store.get(staged.mission.mission_id)


def test_stored_transition_metadata_tamper_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_admission(_payload(), authority=_authority())
    db_path = tmp_path / "ithildin.sqlite3"
    with sqlite3.connect(db_path) as connection:
        metadata = json.loads(
            connection.execute(
                "SELECT safe_metadata_json FROM mission_transition_attempts "
                "WHERE transition_id = ?",
                (staged.transition.transition_id,),
            ).fetchone()[0]
        )
        metadata["workspace_id"] = "tampered"
        connection.execute(
            "UPDATE mission_transition_attempts SET safe_metadata_json = ? "
            "WHERE transition_id = ?",
            (json.dumps(metadata), staged.transition.transition_id),
        )
        connection.commit()

    with pytest.raises(MissionError, match="transition bindings are inconsistent"):
        store.get_transition(staged.transition.transition_id)


def test_claim_and_report_rows_cannot_cross_mission_authority(tmp_path: Path) -> None:
    store = _store(tmp_path)
    mission_a = store.stage_admission(_payload(), authority=_authority())
    mission_b = store.stage_admission(
        _payload(client_request_id="operator-request-002"),
        authority=_authority(),
    )
    db_path = tmp_path / "ithildin.sqlite3"
    now = "2026-07-18T12:00:00+00:00"
    claim_id = "mclaim_" + ("4" * 32)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                """
                INSERT INTO mission_claims (
                    claim_id, mission_id, transition_id, node_id,
                    node_identity_key_id, envelope_digest, authority_snapshot_json,
                    authority_snapshot_hash, lifecycle_revision, claim_status,
                    claimed_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'staged', ?, ?)
                """,
                (
                    claim_id,
                    mission_a.mission.mission_id,
                    mission_b.transition.transition_id,
                    NODE_ID,
                    SHA_B,
                    mission_a.mission.envelope_digest,
                    json.dumps(_authority().model_dump(mode="json")),
                    _authority().canonical_hash(),
                    now,
                    "2026-07-18T12:05:00+00:00",
                ),
            )
        connection.execute(
            """
            INSERT INTO mission_claims (
                claim_id, mission_id, transition_id, node_id,
                node_identity_key_id, envelope_digest, authority_snapshot_json,
                authority_snapshot_hash, lifecycle_revision, claim_status,
                claimed_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'staged', ?, ?)
            """,
            (
                claim_id,
                mission_a.mission.mission_id,
                mission_a.transition.transition_id,
                NODE_ID,
                SHA_B,
                mission_a.mission.envelope_digest,
                json.dumps(_authority().model_dump(mode="json")),
                _authority().canonical_hash(),
                now,
                "2026-07-18T12:05:00+00:00",
            ),
        )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                """
                INSERT INTO mission_report_receipts (
                    report_id, mission_id, claim_id, node_id,
                    verified_node_identity_key_id, envelope_digest,
                    expected_lifecycle_revision, report_kind, outcome_code,
                    reason_code, artifact_digest, request_digest,
                    receipt_posture_json, receipt_disposition, evidence_status,
                    audit_event_id, audit_event_hash, failure_reason_code,
                    received_at, finalized_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, 'runner_running', 'started',
                    NULL, NULL, ?, '{}', 'pending', 'pending', NULL, NULL, NULL, ?, NULL)
                """,
                (
                    "mreport_" + ("5" * 32),
                    mission_b.mission.mission_id,
                    claim_id,
                    NODE_ID,
                    SHA_B,
                    mission_a.mission.envelope_digest,
                    SHA_C,
                    now,
                ),
            )


def _store(tmp_path: Path) -> MissionStore:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    store = MissionStore(db_path)
    store.initialize()
    return store


def _payload(**updates: object) -> MissionAdmissionPayload:
    document: dict[str, object] = {
        "target_node_id": NODE_ID,
        "mission_template_id": "synthetic_read_review_v1",
        "requested_timeout_seconds": 300,
        "client_request_id": "operator-request-001",
    }
    document.update(updates)
    return MissionAdmissionPayload.model_validate(document)


def _authority(**updates: object) -> MissionAuthoritySnapshot:
    requester_generation = str(updates.pop("requester_identity_generation", SHA_1))
    document: dict[str, object] = {
        "requesting_principal": AdminPrincipalContext(
            principal_id="admin:local-ui",
            principal_type="admin",
            roles=("Admin",),
            authentication_method="local_admin_bearer",
            identity_source="principal_registry",
            identity_generation=requester_generation,
        ),
        "target_node_id": NODE_ID,
        "target_node_principal_id": f"agent:node.{NODE_ID}",
        "workspace_id": "default",
        "node_record_hash": SHA_A,
        "node_identity_key_id": SHA_B,
        "configuration_generation": 1,
        "configuration_digest": SHA_C,
        "policy_digest": SHA_D,
        "manifest_lock_digest": SHA_E,
        "tool_count": 24,
        "mission_template_id": "synthetic_read_review_v1",
        "template_registry_generation": SHA_F,
        "template_payload_digest": SHA_2,
    }
    document.update(updates)
    return MissionAuthoritySnapshot.model_validate(document)


def _runner_report(**updates: object) -> MissionRunnerReportPayload:
    document: dict[str, object] = {
        "mission_id": "mission_" + ("1" * 32),
        "claim_id": "mclaim_" + ("2" * 32),
        "envelope_digest": SHA_A,
        "expected_lifecycle_revision": 2,
        "report_id": "mreport_" + ("3" * 32),
        "report_kind": "runner_succeeded",
        "outcome_code": "succeeded",
        "reason_code": None,
        "artifact_digest": SHA_B,
    }
    document.update(updates)
    return MissionRunnerReportPayload.model_validate(document)
