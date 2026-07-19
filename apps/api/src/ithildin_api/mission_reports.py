"""Evidence-first signed runner reports and bounded Mission Command control polling."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import AuditEventType, JsonObject, sha256_digest

from ithildin_api.mission_claims import MissionClaimError, MissionClaimService
from ithildin_api.missions import (
    EVIDENCE_COMPLETE,
    MISSION_CANCEL_REQUESTED,
    MISSION_CLAIMED,
    MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
    MISSION_RUNNER_REPORTED_RUNNING,
    MissionClaimRecord,
    MissionControlPollPayload,
    MissionError,
    MissionRecord,
    MissionReportReceipt,
    MissionReportReceiptStage,
    MissionRunnerReportPayload,
    MissionStore,
    MissionTransitionAttempt,
    mission_report_receipt_audit_metadata,
    mission_report_transition_audit_metadata,
)
from ithildin_api.nodes import NodeNotFoundError, NodeRecord, NodeStore, node_identity_key_id


class MissionReportError(RuntimeError):
    """Raised when report evidence or control delivery cannot complete safely."""


class MissionReportService:
    def __init__(
        self,
        *,
        mission_store: MissionStore,
        node_store: NodeStore,
        mission_claim_service: MissionClaimService,
        audit_writer: AuditWriter,
    ) -> None:
        self.mission_store = mission_store
        self.node_store = node_store
        self.mission_claim_service = mission_claim_service
        self.audit_writer = audit_writer

    def accept_report(
        self,
        report: MissionRunnerReportPayload,
        *,
        authenticated_node: NodeRecord,
        verified_node_identity_key_id: str,
        staged: MissionReportReceiptStage,
        now: datetime | None = None,
    ) -> JsonObject:
        effective_now = now or datetime.now(UTC)
        try:
            mission = self.mission_store.get_admitted(report.mission_id)
        except MissionError as exc:
            raise MissionReportError(str(exc)) from exc
        if staged.idempotent_replay:
            if staged.receipt.evidence_status != EVIDENCE_COMPLETE:
                raise MissionReportError("mission report receipt requires evidence recovery")
            transition = self.mission_store.get_report_transition(report.report_id)
            if transition is not None and transition.evidence_status != EVIDENCE_COMPLETE:
                raise MissionReportError("mission report transition requires evidence recovery")
            return self._response(staged.receipt)
        try:
            receipt_event = self.audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=AuditEventType.MISSION_REPORT_RECEIPT_STAGED,
                request_id=f"req_{uuid4().hex}",
                principal={"id": authenticated_node.principal_id, "roles": []},
                input_hash=staged.receipt.request_digest,
                metadata=mission_report_receipt_audit_metadata(staged.receipt),
                timestamp=effective_now,
            )
        except AuditWriteError as exc:
            self._mark_receipt_incomplete(staged.receipt, "audit_write_failed", effective_now)
            raise MissionReportError("mission report receipt audit evidence failed") from exc
        try:
            finalized = self.mission_store.finalize_report_receipt(
                report.report_id,
                audit_event_id=receipt_event.event_id,
                audit_event_hash=receipt_event.event_hash,
                advancement_precondition=lambda: self._advancement_posture(
                    mission,
                    node_id=authenticated_node.node_id,
                    verified_node_identity_key_id=verified_node_identity_key_id,
                    now=now or datetime.now(UTC),
                ),
                now=now,
            )
        except (MissionError, MissionClaimError) as exc:
            self._mark_receipt_incomplete(staged.receipt, "finalization_failed", effective_now)
            raise MissionReportError("mission report receipt finalization failed") from exc
        if finalized.transition is not None:
            self._audit_and_finalize_transition(
                finalized.transition,
                mission=mission,
                authenticated_node=authenticated_node,
                verified_node_identity_key_id=verified_node_identity_key_id,
                now=now,
                effective_now=effective_now,
            )
        return self._response(self.mission_store.get_report_receipt(report.report_id))

    def stage_authenticated_report(
        self,
        connection: sqlite3.Connection,
        report: MissionRunnerReportPayload,
        *,
        authenticated_node: NodeRecord,
        verified_node_identity_key_id: str,
        now: datetime | None = None,
    ) -> MissionReportReceiptStage:
        effective_now = now or datetime.now(UTC)
        mission = self.mission_store.get_admitted(report.mission_id)
        receipt_eligible, receipt_posture = self._advancement_posture(
            mission,
            node_id=authenticated_node.node_id,
            verified_node_identity_key_id=verified_node_identity_key_id,
            now=effective_now,
        )
        return self.mission_store.stage_authenticated_report_receipt(
            connection,
            report,
            node_id=authenticated_node.node_id,
            verified_node_identity_key_id=verified_node_identity_key_id,
            receipt_posture=receipt_posture,
            authority_eligible=receipt_eligible,
            now=effective_now,
        )

    def control_decision(
        self,
        payload: MissionControlPollPayload,
        *,
        authenticated_node: NodeRecord,
        now: datetime | None = None,
    ) -> JsonObject:
        effective_now = now or datetime.now(UTC)
        try:
            mission = self.mission_store.get_admitted(payload.mission_id)
            claim = self.mission_store.get_claim(payload.mission_id)
        except MissionError as exc:
            raise MissionReportError(str(exc)) from exc
        self._require_control_binding(payload, mission, claim, authenticated_node)
        try:
            claim_expires_at = datetime.fromisoformat(claim.expires_at)
        except ValueError as exc:
            raise MissionReportError("stored mission claim expiry is invalid") from exc
        if claim_expires_at.tzinfo is None or (
            mission.lifecycle_state == MISSION_CLAIMED
            and effective_now >= claim_expires_at
        ):
            raise MissionReportError("mission claim has expired")
        if mission.lifecycle_state == MISSION_CANCEL_REQUESTED:
            decision = "cancel_requested"
            cancellation = self.mission_store.get_cancellation_transition(
                mission.mission_id
            )
            if cancellation is None or cancellation.evidence_status != EVIDENCE_COMPLETE:
                raise MissionReportError("mission cancellation decision evidence is unavailable")
            decision_revision = cancellation.proposed_lifecycle_revision
        elif mission.lifecycle_state in {MISSION_CLAIMED, MISSION_RUNNER_REPORTED_RUNNING}:
            decision = "continue"
            decision_revision = mission.lifecycle_revision
        else:
            raise MissionReportError("mission has no active control decision")
        response: JsonObject = {
            "control_schema_version": "1",
            "mission_id": mission.mission_id,
            "claim_id": claim.claim_id,
            "envelope_digest": mission.envelope_digest,
            "control_decision": decision,
            "decision_revision": decision_revision,
            "runner_stop_proven": False,
        }
        input_hash = sha256_digest(
            {
                "payload": payload.model_dump(mode="json"),
                "node_id": authenticated_node.node_id,
                "verified_node_identity_key_id": node_identity_key_id(
                    authenticated_node.public_key
                ),
            }
        )
        try:
            self.audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=AuditEventType.MISSION_CONTROL_POLLED,
                request_id=f"req_{uuid4().hex}",
                principal={"id": authenticated_node.principal_id, "roles": []},
                input_hash=input_hash,
                metadata={
                    "mission_id": mission.mission_id,
                    "claim_id": claim.claim_id,
                    "envelope_digest": mission.envelope_digest,
                    "control_decision": decision,
                    "decision_revision": decision_revision,
                    "runner_stop_proven": False,
                },
                timestamp=effective_now,
            )
        except AuditWriteError as exc:
            raise MissionReportError("mission control audit evidence failed") from exc
        try:
            self.mission_store.require_current_control_decision(
                payload,
                node_id=authenticated_node.node_id,
                authenticated_public_key=authenticated_node.public_key,
                expected_lifecycle_state=mission.lifecycle_state,
                expected_lifecycle_revision=mission.lifecycle_revision,
                expected_decision=decision,
                expected_decision_revision=decision_revision,
                now=now if now is not None else datetime.now(UTC),
            )
        except MissionError as exc:
            raise MissionReportError(
                "mission control authority changed before delivery"
            ) from exc
        return response

    def _audit_and_finalize_transition(
        self,
        transition: MissionTransitionAttempt,
        *,
        mission: MissionRecord,
        authenticated_node: NodeRecord,
        verified_node_identity_key_id: str,
        now: datetime | None,
        effective_now: datetime,
    ) -> None:
        try:
            event = self.audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=(
                    AuditEventType.MISSION_CONTROL_OBSERVATION_STAGED
                    if transition.transition_kind
                    == MISSION_CONTROL_OBSERVATION_TRANSITION_KIND
                    else AuditEventType.MISSION_REPORT_TRANSITION_STAGED
                ),
                request_id=f"req_{uuid4().hex}",
                principal={"id": authenticated_node.principal_id, "roles": []},
                input_hash=transition.request_digest,
                metadata=mission_report_transition_audit_metadata(transition),
                timestamp=effective_now,
            )
        except AuditWriteError as exc:
            self._mark_transition_incomplete(transition, "audit_write_failed", effective_now)
            raise MissionReportError("mission report transition audit evidence failed") from exc
        try:
            self.mission_store.finalize_report_transition(
                transition.transition_id,
                audit_event_id=event.event_id,
                audit_event_hash=event.event_hash,
                advancement_precondition=lambda: self._advancement_posture(
                    mission,
                    node_id=authenticated_node.node_id,
                    verified_node_identity_key_id=verified_node_identity_key_id,
                    now=now or datetime.now(UTC),
                )[0],
                now=now,
            )
        except (MissionError, MissionClaimError) as exc:
            self._mark_transition_incomplete(transition, "finalization_failed", effective_now)
            raise MissionReportError("mission report transition finalization failed") from exc

    def _advancement_posture(
        self,
        mission: MissionRecord,
        *,
        node_id: str,
        verified_node_identity_key_id: str,
        now: datetime,
    ) -> tuple[bool, JsonObject]:
        try:
            node = self.node_store.get(node_id)
        except NodeNotFoundError:
            return False, {"state": "quarantined", "reason_code": "unknown_node"}
        current_key_id = node_identity_key_id(node.public_key)
        base: JsonObject = {
            "node_status": node.status,
            "node_evidence_status": node.evidence_status,
            "verified_node_identity_key_id": verified_node_identity_key_id,
            "current_node_identity_key_id": current_key_id,
        }
        if node.status == "revoked":
            return False, {
                **base,
                "state": "quarantined",
                "reason_code": "node_revoked",
            }
        rotation = self.node_store.latest_identity_rotation(node.node_id)
        if rotation is not None and rotation.status == "pending":
            try:
                rotation_expires_at = datetime.fromisoformat(rotation.expires_at)
            except ValueError:
                rotation_expires_at = None
            if (
                rotation_expires_at is None
                or rotation_expires_at.tzinfo is None
                or now < rotation_expires_at
            ):
                return False, {
                    **base,
                    "state": "quarantined",
                    "reason_code": "identity_rotation_pending",
                }
        if current_key_id != verified_node_identity_key_id:
            return False, {**base, "state": "quarantined", "reason_code": "retired_key"}
        try:
            claim = self.mission_store.get_claim(mission.mission_id)
            expires_at = datetime.fromisoformat(claim.expires_at)
        except (MissionError, ValueError):
            return False, {
                **base,
                "state": "quarantined",
                "reason_code": "claim_authority_invalid",
            }
        if expires_at.tzinfo is None or (
            mission.lifecycle_state == MISSION_CLAIMED and now >= expires_at
        ):
            return False, {
                **base,
                "state": "quarantined",
                "reason_code": "claim_expired",
            }
        try:
            authority = self.mission_claim_service.current_claim_authority(
                mission,
                authenticated_node_id=node_id,
                authenticated_key_id=verified_node_identity_key_id,
                now=now,
            )
        except MissionClaimError:
            return False, {
                **base,
                "state": "quarantined",
                "reason_code": "posture_ineligible",
            }
        bindings_match = (
            authority.target_node_id == mission.target_node_id
            and authority.target_node_principal_id == mission.target_node_principal_id
            and authority.workspace_id == mission.workspace_id
            and authority.node_identity_key_id == verified_node_identity_key_id
            and authority.configuration_generation == mission.configuration_generation
            and authority.configuration_digest == mission.configuration_digest
            and authority.policy_digest == mission.policy_digest
            and authority.manifest_lock_digest == mission.manifest_lock_digest
            and authority.template_registry_generation == mission.template_registry_generation
            and authority.template_payload_digest == mission.template_payload_digest
        )
        if not bindings_match:
            return False, {**base, "state": "quarantined", "reason_code": "authority_drift"}
        return True, {**base, "state": "eligible", "reason_code": "ready_read_only"}

    @staticmethod
    def _require_control_binding(
        payload: MissionControlPollPayload,
        mission: MissionRecord,
        claim: MissionClaimRecord,
        node: NodeRecord,
    ) -> None:
        if (
            payload.mission_id != mission.mission_id
            or payload.claim_id != claim.claim_id
            or payload.envelope_digest != mission.envelope_digest
            or claim.node_id != node.node_id
            or mission.target_node_id != node.node_id
            or payload.observed_lifecycle_revision > mission.lifecycle_revision
        ):
            raise MissionReportError("mission control binding conflicts")

    def _mark_receipt_incomplete(
        self,
        receipt: MissionReportReceipt,
        reason_code: str,
        now: datetime,
    ) -> None:
        try:
            self.mission_store.mark_report_receipt_evidence_incomplete(
                receipt.report.report_id,
                failure_reason_code=reason_code,
                now=now,
            )
        except MissionError:
            pass

    def _mark_transition_incomplete(
        self,
        transition: MissionTransitionAttempt,
        reason_code: str,
        now: datetime,
    ) -> None:
        try:
            self.mission_store.mark_transition_evidence_incomplete(
                transition.transition_id,
                failure_reason_code=reason_code,
                now=now,
            )
        except MissionError:
            pass

    def _response(self, receipt: MissionReportReceipt) -> JsonObject:
        mission = self.mission_store.get_admitted(receipt.report.mission_id)
        return {
            "receipt": receipt.safe_summary(),
            "gateway_lifecycle_state": mission.lifecycle_state,
            "gateway_lifecycle_revision": mission.lifecycle_revision,
            "runner_state_authority": "runner_reported_only",
            "runner_behavior_proven": False,
            "model_provider_state_known": False,
        }
