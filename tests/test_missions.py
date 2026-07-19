from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.missions import (
    EVIDENCE_COMPLETE,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_PENDING,
    MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED,
    MISSION_CLAIMED,
    MISSION_QUEUED,
    MISSION_UNADMITTED,
    MissionAdmissionPayload,
    MissionAuthoritySnapshot,
    MissionCancellationPayload,
    MissionClaimAuthoritySnapshot,
    MissionClaimRequestPayload,
    MissionConflictError,
    MissionError,
    MissionNotFoundError,
    MissionRecord,
    MissionRunnerReportPayload,
    MissionStore,
    mission_claim_transition_audit_metadata,
    mission_transition_audit_metadata,
)
from ithildin_api.promotion_authority import AdminPrincipalContext
from ithildin_audit_core import AuditWriter
from ithildin_schemas import AuditEventType, JsonObject
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


def test_operator_summary_keeps_mission_truth_sources_separate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    audit_writer = AuditWriter(store.db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    staged = store.stage_admission(_payload(), authority=_authority())
    admission_event = audit_writer.write_event(
        event_id="evt_" + ("7" * 32),
        event_type=AuditEventType.MISSION_ADMISSION_STAGED,
        request_id="req_operator_summary_admission",
        principal={"id": "admin:local-ui", "roles": ["Admin"]},
        input_hash=staged.transition.request_digest,
        metadata=mission_transition_audit_metadata(staged.transition, staged.mission),
    )
    admitted = store.finalize_admission(
        staged.transition.transition_id,
        audit_event_id=admission_event.event_id,
        audit_event_hash=admission_event.event_hash,
    )
    claim_authority = _claim_authority(admitted)
    staged_claim = store.stage_claim(
        admitted.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=claim_authority,
    )
    claim_event = audit_writer.write_event(
        event_id="evt_" + ("6" * 32),
        event_type=AuditEventType.MISSION_CLAIM_STAGED,
        request_id="req_operator_summary_claim",
        principal={"id": admitted.target_node_principal_id, "roles": []},
        input_hash=staged_claim.transition.request_digest,
        metadata=mission_claim_transition_audit_metadata(
            staged_claim.transition,
            staged_claim.claim,
            admitted,
        ),
    )
    claim = store.finalize_claim(
        staged_claim.transition.transition_id,
        audit_event_id=claim_event.event_id,
        audit_event_hash=claim_event.event_hash,
        authority_precondition=lambda: claim_authority,
    )
    admitted = store.get(admitted.mission_id)
    matching_run: JsonObject = {
        "run_id": "run_matching",
        "principal_id": admitted.target_node_principal_id,
        "workspace_id": admitted.workspace_id,
        "status": "active",
        "tool_call_count": 2,
        "updated_at": admitted.updated_at,
        "metadata": {
            "mission_id": admitted.mission_id,
            "ingress_kind": "node_governed_access",
            "identity_source": "gateway_derived_node",
            "node_id": admitted.target_node_id,
            "mission_claim_id": claim.claim_id,
            "mission_envelope_digest": admitted.envelope_digest,
            "mission_binding_source": "gateway_validated_claim_session",
        },
    }
    mismatched_run: JsonObject = {
        **matching_run,
        "run_id": "run_mismatch",
        "workspace_id": "wrong-workspace",
    }

    summary = store.operator_summary(
        admitted.mission_id,
        agent_runs=[matching_run, mismatched_run],
    )

    assert summary["lifecycle_state"] == MISSION_CLAIMED
    assert summary["delivery"] == {
        "authority": "gateway_node_claim",
        "state": "claim_delivered",
        "claim": claim.safe_summary(),
    }
    assert summary["runner_reports"] == {
        "authority": "runner_reported_through_authenticated_node",
        "latest": None,
        "receipts": [],
        "quarantined_count": 0,
        "report_conflict_count": 0,
    }
    governed_agent_runs = cast(JsonObject, summary["governed_agent_runs"])
    assert governed_agent_runs["count"] == 1
    assert governed_agent_runs["runs"] == [
        {
            "run_id": "run_matching",
            "principal_id": admitted.target_node_principal_id,
            "workspace_id": admitted.workspace_id,
            "status": "active",
            "tool_call_count": 2,
            "updated_at": admitted.updated_at,
        }
    ]
    assert governed_agent_runs["rejected_correlation_count"] == 1
    assert summary["attention_codes"] == ["agent_run_correlation_mismatch"]
    assert summary["model_provider"] == {
        "state": "unknown",
        "authority": "external_runner_or_provider",
        "inference_known": False,
        "output_verified": False,
    }
    mission_session = (
        f"mission:{admitted.mission_id}:{claim.claim_id}:"
        f"{admitted.envelope_digest.removeprefix('sha256:')[:16]}"
    )
    before_expiry = datetime.fromisoformat(claim.expires_at) - timedelta(seconds=1)
    binding = store.governed_run_mission_binding(
        node_id=admitted.target_node_id,
        session_id=mission_session,
        now=before_expiry,
    )
    assert binding is not None
    assert binding["mission_id"] == admitted.mission_id
    with pytest.raises(MissionConflictError, match="session binding conflicts"):
        store.governed_run_mission_binding(
            node_id=admitted.target_node_id,
            session_id=mission_session,
            now=datetime.fromisoformat(claim.expires_at),
        )
    cancellation = store.stage_cancellation(
        admitted.mission_id,
        MissionCancellationPayload(client_request_id="operator-summary-cancel"),
        requester=_authority().requesting_principal,
    )
    store.mark_transition_evidence_incomplete(
        cancellation.transition.transition_id,
        failure_reason_code="audit_write_failed",
    )
    with pytest.raises(MissionConflictError, match="operator recovery"):
        store.governed_run_mission_binding(
            node_id=admitted.target_node_id,
            session_id=mission_session,
            now=before_expiry,
        )


@pytest.mark.parametrize("tamper", ["binding", "event", "payload", "transition"])
def test_operator_summary_fails_closed_when_admission_evidence_is_missing(
    tmp_path: Path,
    tamper: str,
) -> None:
    store = _store(tmp_path)
    audit_writer = AuditWriter(store.db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    staged = store.stage_admission(_payload(), authority=_authority())
    admission_event = audit_writer.write_event(
        event_id="evt_" + ("7" * 32),
        event_type=AuditEventType.MISSION_ADMISSION_STAGED,
        request_id="req_operator_tamper_admission",
        principal={"id": "admin:local-ui", "roles": ["Admin"]},
        input_hash=staged.transition.request_digest,
        metadata=mission_transition_audit_metadata(staged.transition, staged.mission),
    )
    admitted = store.finalize_admission(
        staged.transition.transition_id,
        audit_event_id=admission_event.event_id,
        audit_event_hash=admission_event.event_hash,
    )
    with sqlite3.connect(store.db_path) as connection:
        if tamper == "binding":
            connection.execute(
                "DELETE FROM mission_audit_evidence_bindings WHERE owner_id = ?",
                (staged.transition.transition_id,),
            )
        elif tamper == "event":
            connection.execute(
                "DELETE FROM audit_events WHERE event_id = ?",
                (admission_event.event_id,),
            )
        elif tamper == "payload":
            row = connection.execute(
                "SELECT payload_json FROM audit_events WHERE event_id = ?",
                (admission_event.event_id,),
            ).fetchone()
            assert row is not None
            payload = json.loads(str(row[0]))
            payload["principal"] = {"id": "attacker", "roles": []}
            connection.execute(
                "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
                (
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    admission_event.event_id,
                ),
            )
        else:
            connection.execute(
                "DELETE FROM mission_transition_attempts WHERE transition_id = ?",
                (staged.transition.transition_id,),
            )
        connection.commit()

    with pytest.raises(MissionError, match="evidence|admission|audit"):
        store.operator_summary(admitted.mission_id)


@pytest.mark.parametrize(
    "drift",
    ["missing", "content_edit_same_head", "missing_terminal_newline"],
)
def test_mission_trust_surfaces_fail_closed_when_audit_jsonl_lifecycle_drifts(
    tmp_path: Path,
    drift: str,
) -> None:
    store = _store(tmp_path)
    audit_writer = AuditWriter(store.db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    staged = store.stage_admission(_payload(), authority=_authority())
    event = audit_writer.write_event(
        event_id="evt_" + ("8" * 32),
        event_type=AuditEventType.MISSION_ADMISSION_STAGED,
        request_id="req_operator_jsonl_drift",
        principal={"id": "admin:local-ui", "roles": ["Admin"]},
        input_hash=staged.transition.request_digest,
        metadata=mission_transition_audit_metadata(staged.transition, staged.mission),
    )
    admitted = store.finalize_admission(
        staged.transition.transition_id,
        audit_event_id=event.event_id,
        audit_event_hash=event.event_hash,
    )
    if drift == "missing":
        audit_writer.jsonl_path.write_text("", encoding="utf-8")
    elif drift == "content_edit_same_head":
        payload = json.loads(audit_writer.jsonl_path.read_text(encoding="utf-8"))
        payload["principal"]["id"] = "admin:edited"
        audit_writer.jsonl_path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    else:
        audit_writer.jsonl_path.write_bytes(
            audit_writer.jsonl_path.read_bytes().removesuffix(b"\n")
        )

    with pytest.raises(MissionError, match="audit lifecycle requires recovery"):
        store.operator_summary(admitted.mission_id)
    session_id = (
        f"mission:{admitted.mission_id}:mclaim_{'a' * 32}:"
        f"{admitted.envelope_digest.removeprefix('sha256:')[:16]}"
    )
    with pytest.raises(MissionError, match="audit lifecycle requires recovery"):
        store.governed_run_mission_binding(
            node_id=admitted.target_node_id,
            session_id=session_id,
            now=datetime.now(UTC),
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


def test_queued_cancellation_is_staged_audited_and_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    admission = store.stage_admission(_payload(), authority=_authority())
    admitted = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
    )
    cancellation_payload = MissionCancellationPayload(client_request_id="cancel-request-001")

    staged = store.stage_cancellation(
        admitted.mission_id,
        cancellation_payload,
        requester=_authority().requesting_principal,
    )

    assert staged.idempotent_replay is False
    assert staged.mission.lifecycle_state == MISSION_QUEUED
    assert staged.transition.proposed_lifecycle_state == "canceled"
    assert store.get(admitted.mission_id).lifecycle_state == MISSION_QUEUED
    replay = store.stage_cancellation(
        admitted.mission_id,
        cancellation_payload,
        requester=_authority().requesting_principal,
    )
    assert replay.idempotent_replay is True
    assert replay.transition.transition_id == staged.transition.transition_id

    cancellation_event_id = "evt_" + ("2" * 32)
    with sqlite3.connect(store.db_path) as connection:
        connection.execute(
            "CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO audit_events (event_id, payload_json) VALUES (?, ?)",
            (
                cancellation_event_id,
                json.dumps(
                    {
                        "event_id": cancellation_event_id,
                        "event_hash": SHA_B,
                        "event_type": "mission.cancellation.staged",
                        "principal": {
                            "id": "admin:local-ui",
                            "roles": ["Admin"],
                        },
                        "input_hash": staged.transition.request_digest,
                        "metadata": mission_transition_audit_metadata(
                            staged.transition,
                            staged.mission,
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        )
        connection.commit()

    canceled = store.finalize_cancellation(
        staged.transition.transition_id,
        audit_event_id=cancellation_event_id,
        audit_event_hash=SHA_B,
    )
    assert canceled.lifecycle_state == "canceled"
    assert canceled.lifecycle_revision == 2
    assert canceled.admitted_at == admitted.admitted_at
    exact = store.stage_cancellation(
        admitted.mission_id,
        cancellation_payload,
        requester=_authority().requesting_principal,
    )
    assert exact.idempotent_replay is True
    assert exact.mission.lifecycle_state == "canceled"
    with pytest.raises(MissionConflictError, match="cancellation request conflicts"):
        store.stage_cancellation(
            admitted.mission_id,
            MissionCancellationPayload(client_request_id="cancel-request-002"),
            requester=_authority().requesting_principal,
        )


def test_claim_stages_without_delivery_and_finalizes_exactly_once(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    admission = store.stage_admission(_payload(), authority=_authority(), now=now)
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
        now=now,
    )
    authority = _claim_authority(mission)

    staged = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=authority,
        now=now + timedelta(seconds=1),
    )

    assert staged.mission.lifecycle_state == MISSION_QUEUED
    assert staged.claim.claim_status == "staged"
    assert staged.claim.lifecycle_revision == 2
    assert staged.claim.expires_at == (now + timedelta(seconds=301)).isoformat()
    assert staged.transition.evidence_status == EVIDENCE_PENDING
    assert staged.transition.proposed_lifecycle_state == MISSION_CLAIMED
    claimed = store.finalize_claim(
        staged.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
        authority_precondition=lambda: authority,
        now=now + timedelta(seconds=2),
    )
    assert claimed.claim_status == "delivered"
    assert store.get(mission.mission_id).lifecycle_state == MISSION_CLAIMED
    assert store.get(mission.mission_id).lifecycle_revision == 2
    replay = store.finalize_claim(
        staged.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
        authority_precondition=lambda: authority,
    )
    assert replay == claimed


def test_claim_evidence_failure_preserves_queue_and_blocks_another_claim(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    admission = store.stage_admission(_payload(), authority=_authority())
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
    )
    claim = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=_claim_authority(mission),
    )

    failed = store.mark_transition_evidence_incomplete(
        claim.transition.transition_id,
        failure_reason_code="audit_write_failed",
    )

    assert failed.evidence_status == EVIDENCE_INCOMPLETE
    assert store.get(mission.mission_id).lifecycle_state == MISSION_QUEUED
    assert store.get_claim(mission.mission_id).claim_status == "evidence_incomplete"
    with pytest.raises(MissionNotFoundError, match="no queued mission"):
        store.next_queued_for_node(NODE_ID)
    with pytest.raises(MissionConflictError, match="already has a claim"):
        store.stage_claim(
            mission.mission_id,
            MissionClaimRequestPayload(protocol_version="1"),
            authority=_claim_authority(mission),
        )


def test_claim_authority_precondition_change_has_zero_claim_effects(tmp_path: Path) -> None:
    store = _store(tmp_path)
    admission = store.stage_admission(_payload(), authority=_authority())
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
    )
    authority = _claim_authority(mission)
    changed = authority.model_copy(update={"current_node_record_hash": SHA_2})

    with pytest.raises(MissionConflictError, match="claim authority changed"):
        store.stage_claim(
            mission.mission_id,
            MissionClaimRequestPayload(protocol_version="1"),
            authority=authority,
            authority_precondition=lambda: changed,
        )

    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM mission_claims").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts WHERE transition_kind = ?",
            ("claim_pending_evidence",),
        ).fetchone() == (0,)


def test_claim_expired_before_finalization_is_not_delivered(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    admission = store.stage_admission(
        _payload(requested_timeout_seconds=60),
        authority=_authority(),
        now=now,
    )
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
        now=now,
    )
    authority = _claim_authority(mission)
    staged = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=authority,
        now=now,
    )

    with pytest.raises(MissionConflictError, match="expired before delivery"):
        store.finalize_claim(
            staged.transition.transition_id,
            audit_event_id="evt_" + ("2" * 32),
            audit_event_hash=SHA_B,
            authority_precondition=lambda: authority,
            now=now + timedelta(seconds=60),
        )
    failed = store.mark_transition_evidence_incomplete(
        staged.transition.transition_id,
        failure_reason_code="finalization_failed",
        now=now + timedelta(seconds=60),
    )

    assert failed.evidence_status == EVIDENCE_INCOMPLETE
    assert store.get(mission.mission_id).lifecycle_state == MISSION_QUEUED
    assert store.get_claim(mission.mission_id).claim_status == "evidence_incomplete"


def test_claim_expiry_enters_attention_without_requeue(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    admission = store.stage_admission(
        _payload(requested_timeout_seconds=60),
        authority=_authority(),
        now=now,
    )
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
        now=now,
    )
    claim = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=_claim_authority(mission),
        now=now,
    )
    delivered = store.finalize_claim(
        claim.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
        authority_precondition=lambda: _claim_authority(mission),
        now=now,
    )
    assert store.due_delivered_claims(now=now + timedelta(seconds=59)) == []
    assert store.due_delivered_claims(now=now + timedelta(seconds=60)) == [delivered]

    staged_expiry = store.stage_claim_expiry(
        mission.mission_id,
        now=now + timedelta(seconds=60),
    )

    assert staged_expiry.mission.lifecycle_state == MISSION_CLAIMED
    assert staged_expiry.claim.claim_status == "delivered"
    assert staged_expiry.transition.proposed_lifecycle_state == (
        MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
    )
    expired = store.finalize_claim_expiry(
        staged_expiry.transition.transition_id,
        audit_event_id="evt_" + ("3" * 32),
        audit_event_hash=SHA_C,
        now=now + timedelta(seconds=60),
    )
    assert expired.lifecycle_state == MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
    assert expired.lifecycle_revision == 3
    assert store.get_claim(mission.mission_id).claim_status == "expired_review_required"
    assert store.get_transition(claim.transition.transition_id).evidence_status == EVIDENCE_COMPLETE
    assert (
        store.get_transition(staged_expiry.transition.transition_id).evidence_status
        == EVIDENCE_COMPLETE
    )
    assert store.due_delivered_claims(now=now + timedelta(days=1)) == []
    with pytest.raises(MissionNotFoundError, match="no queued mission"):
        store.next_queued_for_node(NODE_ID)


@pytest.mark.parametrize("mutation_kind", ["earlier_deadline", "later_deadline", "status"])
def test_claim_expiry_rejects_tampered_claim_row_without_lifecycle_effects(
    tmp_path: Path,
    mutation_kind: str,
) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    admission = store.stage_admission(
        _payload(requested_timeout_seconds=60),
        authority=_authority(),
        now=now,
    )
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
        now=now,
    )
    authority = _claim_authority(mission)
    staged = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=authority,
        now=now,
    )
    store.finalize_claim(
        staged.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
        authority_precondition=lambda: authority,
        now=now,
    )
    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        if mutation_kind == "status":
            connection.execute(
                "UPDATE mission_claims SET claim_status = 'staged' WHERE mission_id = ?",
                (mission.mission_id,),
            )
        else:
            offset_seconds = 1 if mutation_kind == "earlier_deadline" else 120
            connection.execute(
                "UPDATE mission_claims SET expires_at = ? WHERE mission_id = ?",
                (
                    (now + timedelta(seconds=offset_seconds)).isoformat(),
                    mission.mission_id,
                ),
            )
        connection.commit()

    with pytest.raises(
        MissionError,
        match="stored mission claim transition bindings are inconsistent",
    ):
        store.due_delivered_claims(now=now + timedelta(seconds=61))

    assert store.get(mission.mission_id).lifecycle_state == MISSION_CLAIMED
    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_expiry_pending_evidence'"
        ).fetchone() == (0,)


def test_report_at_claim_deadline_is_staged_for_quarantine(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    admission = store.stage_admission(
        _payload(requested_timeout_seconds=60),
        authority=_authority(),
        now=now,
    )
    mission = store.finalize_admission(
        admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
        now=now,
    )
    claim_authority = _claim_authority(mission)
    staged_claim = store.stage_claim(
        mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=claim_authority,
        now=now,
    )
    claim = store.finalize_claim(
        staged_claim.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
        authority_precondition=lambda: claim_authority,
        now=now,
    )
    report = MissionRunnerReportPayload(
        mission_id=mission.mission_id,
        claim_id=claim.claim_id,
        envelope_digest=mission.envelope_digest,
        expected_lifecycle_revision=2,
        report_id="mreport_" + ("a" * 32),
        report_kind="runner_running",
        outcome_code="started",
        reason_code=None,
        artifact_digest=None,
    )
    posture: JsonObject = {
        "node_status": "enrolled",
        "node_evidence_status": "complete",
        "verified_node_identity_key_id": SHA_B,
        "current_node_identity_key_id": SHA_B,
        "state": "eligible",
        "reason_code": "ready_read_only",
    }
    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        staged_report = store.stage_authenticated_report_receipt(
            connection,
            report,
            node_id=NODE_ID,
            verified_node_identity_key_id=SHA_B,
            receipt_posture=posture,
            authority_eligible=True,
            now=now + timedelta(seconds=60),
        )
        connection.commit()

    assert staged_report.receipt.receipt_posture["proposed_disposition"] == "quarantined"
    assert staged_report.receipt.receipt_posture["quarantine_reason_code"] == ("claim_expired")
    assert store.get(mission.mission_id).lifecycle_state == MISSION_CLAIMED
    assert store.get_report_transition(report.report_id) is None


def test_tampered_blocking_claim_node_cannot_enable_second_claim(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first_admission = store.stage_admission(
        _payload(client_request_id="mission-claim-blocker-001"),
        authority=_authority(),
    )
    first_mission = store.finalize_admission(
        first_admission.transition.transition_id,
        audit_event_id="evt_" + ("1" * 32),
        audit_event_hash=SHA_A,
    )
    second_admission = store.stage_admission(
        _payload(client_request_id="mission-claim-blocker-002"),
        authority=_authority(),
    )
    second_mission = store.finalize_admission(
        second_admission.transition.transition_id,
        audit_event_id="evt_" + ("2" * 32),
        audit_event_hash=SHA_B,
    )
    store.stage_claim(
        first_mission.mission_id,
        MissionClaimRequestPayload(protocol_version="1"),
        authority=_claim_authority(first_mission),
    )
    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        connection.execute(
            "UPDATE mission_claims SET node_id = ? WHERE mission_id = ?",
            ("node_" + ("2" * 32), first_mission.mission_id),
        )
        connection.commit()

    with pytest.raises(
        MissionError,
        match="stored mission claim authority bindings are inconsistent",
    ):
        store.stage_claim(
            second_mission.mission_id,
            MissionClaimRequestPayload(protocol_version="1"),
            authority=_claim_authority(second_mission),
        )

    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM mission_claims").fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE mission_id = ? AND transition_kind = 'claim_pending_evidence'",
            (second_mission.mission_id,),
        ).fetchone() == (0,)


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


def test_admission_authority_precondition_failure_has_zero_effects(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def deny_changed_authority() -> None:
        raise MissionConflictError("authority changed while staging")

    with pytest.raises(MissionConflictError, match="authority changed while staging"):
        store.stage_admission(
            _payload(),
            authority=_authority(),
            authority_precondition=deny_changed_authority,
        )
    with sqlite3.connect(tmp_path / "ithildin.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM missions").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts"
        ).fetchone() == (0,)


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
            "UPDATE mission_transition_attempts SET safe_metadata_json = ? WHERE transition_id = ?",
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


def _claim_authority(mission: MissionRecord) -> MissionClaimAuthoritySnapshot:
    return MissionClaimAuthoritySnapshot(
        mission_id=mission.mission_id,
        admitted_authority_snapshot_hash=mission.authority_snapshot_hash,
        envelope_digest=mission.envelope_digest,
        target_node_id=mission.target_node_id,
        target_node_principal_id=mission.target_node_principal_id,
        workspace_id=mission.workspace_id,
        current_node_record_hash=SHA_A,
        node_identity_key_id=SHA_B,
        configuration_generation=mission.configuration_generation,
        configuration_digest=mission.configuration_digest,
        policy_digest=mission.policy_digest,
        manifest_lock_digest=mission.manifest_lock_digest,
        tool_count=24,
        mission_template_id="synthetic_read_review_v1",
        template_registry_generation=mission.template_registry_generation,
        template_payload_digest=mission.template_payload_digest,
    )


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
