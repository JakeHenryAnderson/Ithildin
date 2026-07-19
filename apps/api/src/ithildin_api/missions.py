"""Gateway-owned Mission Command authority models and fail-closed persistence."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest
from ithildin_schemas.models import SHA256_PATTERN
from pydantic import Field, field_validator, model_validator

from ithildin_api.promotion_authority import AdminPrincipalContext, FrozenAuthorityModel
from ithildin_api.trusted_host_promotion_v2_migration import verify_database_v2

MISSION_TEMPLATE_ID: Literal["synthetic_read_review_v1"] = "synthetic_read_review_v1"
MISSION_AUTHORITY_SCHEMA_VERSION = "1"
MISSION_ADMISSION_TRANSITION_KIND = "admission_pending_evidence"
MISSION_CLAIM_TRANSITION_KIND = "claim_pending_evidence"
MISSION_CLAIM_EXPIRY_TRANSITION_KIND = "claim_expiry_pending_evidence"
MISSION_CANCELLATION_TRANSITION_KIND = "cancellation_pending_evidence"
MISSION_CONTROL_OBSERVATION_TRANSITION_KIND = "control_observation_pending_evidence"
MISSION_REPORT_TRANSITION_KIND = "report_pending_evidence"
MISSION_UNADMITTED = "unadmitted"
MISSION_QUEUED = "queued"
MISSION_CLAIMED = "claimed"
MISSION_RUNNER_REPORTED_RUNNING = "runner_reported_running"
MISSION_RUNNER_REPORTED_SUCCEEDED = "runner_reported_succeeded"
MISSION_RUNNER_REPORTED_FAILED = "runner_reported_failed"
MISSION_CANCEL_REQUESTED = "cancel_requested"
MISSION_RUNNER_REPORTED_CANCELED = "runner_reported_canceled"
MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED = "claim_expired_review_required"
MISSION_CANCELED = "canceled"
EVIDENCE_PENDING = "pending"
EVIDENCE_COMPLETE = "complete"
EVIDENCE_INCOMPLETE = "evidence_incomplete"

_NODE_ID_PATTERN = re.compile(r"^node_[0-9a-f]{32}$")
_MISSION_ID_PATTERN = re.compile(r"^mission_[0-9a-f]{32}$")
_TRANSITION_ID_PATTERN = re.compile(r"^mtransition_[0-9a-f]{32}$")
_CLAIM_ID_PATTERN = re.compile(r"^mclaim_[0-9a-f]{32}$")
_REPORT_ID_PATTERN = re.compile(r"^mreport_[0-9a-f]{32}$")
_EVENT_ID_PATTERN = re.compile(r"^evt_[0-9a-f]{32}$")
_SAFE_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")
_MISSION_RUN_SESSION_PATTERN = re.compile(
    r"^mission:(mission_[0-9a-f]{32}):(mclaim_[0-9a-f]{32}):([0-9a-f]{16})$"
)


class MissionError(RuntimeError):
    """Raised when mission authority or persistence fails closed."""


class MissionNotFoundError(MissionError):
    """Raised when a mission or transition does not exist."""


class MissionConflictError(MissionError):
    """Raised when an idempotency or lifecycle precondition conflicts."""


class MissionAdmissionPayload(FrozenAuthorityModel):
    target_node_id: str = Field(pattern=r"^node_[0-9a-f]{32}$")
    mission_template_id: Literal["synthetic_read_review_v1"]
    requested_timeout_seconds: int = Field(ge=60, le=3600)
    client_request_id: str = Field(min_length=1, max_length=128)

    @field_validator("client_request_id")
    @classmethod
    def _safe_client_request_id(cls, value: str) -> str:
        if not _SAFE_LABEL_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("unsafe mission client request ID")
        return value

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json"))


class MissionCancellationPayload(FrozenAuthorityModel):
    client_request_id: str = Field(min_length=1, max_length=128)

    @field_validator("client_request_id")
    @classmethod
    def _safe_client_request_id(cls, value: str) -> str:
        if not _SAFE_LABEL_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("unsafe mission cancellation request ID")
        return value


class MissionClaimRequestPayload(FrozenAuthorityModel):
    protocol_version: Literal["1"]


class MissionControlPollPayload(FrozenAuthorityModel):
    protocol_version: Literal["1"]
    mission_id: str = Field(pattern=r"^mission_[0-9a-f]{32}$")
    claim_id: str = Field(pattern=r"^mclaim_[0-9a-f]{32}$")
    envelope_digest: str = Field(pattern=SHA256_PATTERN)
    observed_lifecycle_revision: int = Field(ge=2)


class MissionAuthoritySnapshot(FrozenAuthorityModel):
    snapshot_schema_version: Literal["1"] = "1"
    requesting_principal: AdminPrincipalContext
    target_node_id: str = Field(pattern=r"^node_[0-9a-f]{32}$")
    target_node_principal_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    node_record_hash: str = Field(pattern=SHA256_PATTERN)
    node_identity_key_id: str = Field(pattern=SHA256_PATTERN)
    configuration_generation: int = Field(ge=1)
    configuration_digest: str = Field(pattern=SHA256_PATTERN)
    policy_digest: str = Field(pattern=SHA256_PATTERN)
    manifest_lock_digest: str = Field(pattern=SHA256_PATTERN)
    tool_count: Literal[24]
    mission_template_id: Literal["synthetic_read_review_v1"]
    template_registry_generation: str = Field(pattern=SHA256_PATTERN)
    template_payload_digest: str = Field(pattern=SHA256_PATTERN)

    @field_validator("target_node_principal_id", "workspace_id")
    @classmethod
    def _safe_authority_label(cls, value: str) -> str:
        if not _SAFE_LABEL_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("unsafe mission authority label")
        return value


class MissionClaimAuthoritySnapshot(FrozenAuthorityModel):
    snapshot_schema_version: Literal["1"] = "1"
    mission_id: str = Field(pattern=r"^mission_[0-9a-f]{32}$")
    admitted_authority_snapshot_hash: str = Field(pattern=SHA256_PATTERN)
    envelope_digest: str = Field(pattern=SHA256_PATTERN)
    target_node_id: str = Field(pattern=r"^node_[0-9a-f]{32}$")
    target_node_principal_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    current_node_record_hash: str = Field(pattern=SHA256_PATTERN)
    node_identity_key_id: str = Field(pattern=SHA256_PATTERN)
    configuration_generation: int = Field(ge=1)
    configuration_digest: str = Field(pattern=SHA256_PATTERN)
    policy_digest: str = Field(pattern=SHA256_PATTERN)
    manifest_lock_digest: str = Field(pattern=SHA256_PATTERN)
    tool_count: Literal[24]
    mission_template_id: Literal["synthetic_read_review_v1"]
    template_registry_generation: str = Field(pattern=SHA256_PATTERN)
    template_payload_digest: str = Field(pattern=SHA256_PATTERN)

    @field_validator("target_node_principal_id", "workspace_id")
    @classmethod
    def _safe_claim_authority_label(cls, value: str) -> str:
        if not _SAFE_LABEL_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError("unsafe mission claim authority label")
        return value


class MissionRunnerReportPayload(FrozenAuthorityModel):
    """Closed runner observation; it is never itself Gateway lifecycle authority."""

    mission_id: str = Field(pattern=r"^mission_[0-9a-f]{32}$")
    claim_id: str = Field(pattern=r"^mclaim_[0-9a-f]{32}$")
    envelope_digest: str = Field(pattern=SHA256_PATTERN)
    expected_lifecycle_revision: int = Field(ge=1)
    report_id: str = Field(pattern=r"^mreport_[0-9a-f]{32}$")
    report_kind: Literal[
        "runner_running",
        "runner_succeeded",
        "runner_failed",
        "cancel_observed",
        "runner_canceled",
    ]
    outcome_code: Literal[
        "started",
        "succeeded",
        "failed",
        "cancellation_observed",
        "canceled",
    ]
    reason_code: (
        Literal[
            "runner_error",
            "runner_timeout",
            "runner_output_invalid",
            "runner_dependency_unavailable",
        ]
        | None
    ) = None
    artifact_digest: str | None = Field(default=None, pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def _closed_report_semantics(self) -> MissionRunnerReportPayload:
        expected_outcome = {
            "runner_running": "started",
            "runner_succeeded": "succeeded",
            "runner_failed": "failed",
            "cancel_observed": "cancellation_observed",
            "runner_canceled": "canceled",
        }[self.report_kind]
        if self.outcome_code != expected_outcome:
            raise ValueError("mission report kind and outcome do not match")
        if self.report_kind == "runner_failed" and self.reason_code is None:
            raise ValueError("failed mission report requires a reason code")
        if self.report_kind != "runner_failed" and self.reason_code is not None:
            raise ValueError("mission report reason code is not allowed for this kind")
        if self.report_kind != "runner_succeeded" and self.artifact_digest is not None:
            raise ValueError("mission report artifact digest is not allowed for this kind")
        return self

    def canonical_digest(self) -> str:
        return sha256_digest(cast(JsonObject, self.model_dump(mode="json")))


@dataclass(frozen=True)
class MissionRecord:
    mission_id: str
    requester_principal_id: str
    requester_identity_generation: str
    client_request_id: str
    admission_request_digest: str
    authority_snapshot: MissionAuthoritySnapshot
    authority_snapshot_hash: str
    target_node_id: str
    target_node_principal_id: str
    workspace_id: str
    configuration_generation: int
    configuration_digest: str
    policy_digest: str
    manifest_lock_digest: str
    mission_template_id: str
    template_registry_generation: str
    template_payload_digest: str
    envelope_digest: str
    requested_timeout_seconds: int
    lifecycle_state: str
    lifecycle_revision: int
    created_at: str
    updated_at: str
    admitted_at: str | None

    def safe_summary(self) -> JsonObject:
        return {
            "mission_id": self.mission_id,
            "requester_principal_id": self.requester_principal_id,
            "requester_identity_generation": self.requester_identity_generation,
            "client_request_id": self.client_request_id,
            "admission_request_digest": self.admission_request_digest,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "target_node_id": self.target_node_id,
            "target_node_principal_id": self.target_node_principal_id,
            "workspace_id": self.workspace_id,
            "configuration_generation": self.configuration_generation,
            "configuration_digest": self.configuration_digest,
            "policy_digest": self.policy_digest,
            "manifest_lock_digest": self.manifest_lock_digest,
            "mission_template_id": self.mission_template_id,
            "template_registry_generation": self.template_registry_generation,
            "template_payload_digest": self.template_payload_digest,
            "envelope_digest": self.envelope_digest,
            "requested_timeout_seconds": self.requested_timeout_seconds,
            "lifecycle_state": self.lifecycle_state,
            "lifecycle_revision": self.lifecycle_revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "admitted_at": self.admitted_at,
            "lifecycle_authority": "gateway",
            "runner_state_authority": "runner_reported_only",
            "model_provider_state_known": False,
        }


@dataclass(frozen=True)
class MissionTransitionAttempt:
    transition_id: str
    mission_id: str
    transition_kind: str
    prior_lifecycle_state: str
    prior_lifecycle_revision: int
    proposed_lifecycle_state: str
    proposed_lifecycle_revision: int
    request_digest: str
    safe_metadata: JsonObject
    evidence_status: str
    audit_event_id: str | None
    audit_event_hash: str | None
    failure_reason_code: str | None
    created_at: str
    finalized_at: str | None

    def safe_summary(self) -> JsonObject:
        return {
            "transition_id": self.transition_id,
            "mission_id": self.mission_id,
            "transition_kind": self.transition_kind,
            "prior_lifecycle_state": self.prior_lifecycle_state,
            "prior_lifecycle_revision": self.prior_lifecycle_revision,
            "proposed_lifecycle_state": self.proposed_lifecycle_state,
            "proposed_lifecycle_revision": self.proposed_lifecycle_revision,
            "request_digest": self.request_digest,
            "safe_metadata": self.safe_metadata,
            "evidence_status": self.evidence_status,
            "audit_event_id": self.audit_event_id,
            "audit_event_hash": self.audit_event_hash,
            "failure_reason_code": self.failure_reason_code,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
        }


@dataclass(frozen=True)
class MissionClaimRecord:
    claim_id: str
    mission_id: str
    transition_id: str
    node_id: str
    node_identity_key_id: str
    envelope_digest: str
    authority_snapshot: MissionClaimAuthoritySnapshot
    authority_snapshot_hash: str
    lifecycle_revision: int
    claim_status: str
    claimed_at: str
    expires_at: str

    def safe_summary(self) -> JsonObject:
        return {
            "claim_id": self.claim_id,
            "mission_id": self.mission_id,
            "node_id": self.node_id,
            "node_identity_key_id": self.node_identity_key_id,
            "envelope_digest": self.envelope_digest,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "lifecycle_revision": self.lifecycle_revision,
            "claim_status": self.claim_status,
            "claimed_at": self.claimed_at,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class MissionAdmissionStage:
    mission: MissionRecord
    transition: MissionTransitionAttempt
    idempotent_replay: bool


@dataclass(frozen=True)
class MissionCancellationStage:
    mission: MissionRecord
    transition: MissionTransitionAttempt
    idempotent_replay: bool


@dataclass(frozen=True)
class MissionClaimStage:
    mission: MissionRecord
    claim: MissionClaimRecord
    transition: MissionTransitionAttempt


@dataclass(frozen=True)
class MissionClaimExpiryStage:
    mission: MissionRecord
    claim: MissionClaimRecord
    transition: MissionTransitionAttempt


@dataclass(frozen=True)
class MissionReportReceipt:
    report: MissionRunnerReportPayload
    node_id: str
    verified_node_identity_key_id: str
    request_digest: str
    receipt_posture: JsonObject
    receipt_disposition: str
    evidence_status: str
    audit_event_id: str | None
    audit_event_hash: str | None
    failure_reason_code: str | None
    received_at: str
    finalized_at: str | None

    def safe_summary(self) -> JsonObject:
        return {
            **cast(JsonObject, self.report.model_dump(mode="json")),
            "node_id": self.node_id,
            "verified_node_identity_key_id": self.verified_node_identity_key_id,
            "request_digest": self.request_digest,
            "receipt_posture": self.receipt_posture,
            "receipt_disposition": self.receipt_disposition,
            "evidence_status": self.evidence_status,
            "audit_event_id": self.audit_event_id,
            "audit_event_hash": self.audit_event_hash,
            "failure_reason_code": self.failure_reason_code,
            "received_at": self.received_at,
            "finalized_at": self.finalized_at,
            "runner_state_authority": "runner_reported_only",
        }


@dataclass(frozen=True)
class MissionReportReceiptStage:
    receipt: MissionReportReceipt
    idempotent_replay: bool


@dataclass(frozen=True)
class MissionReportReceiptFinalization:
    receipt: MissionReportReceipt
    transition: MissionTransitionAttempt | None


class MissionStore:
    """Persist staged mission authority without exposing incomplete lifecycle claims."""

    def __init__(self, db_path: Path, audit_jsonl_path: Path | None = None) -> None:
        self.db_path = db_path
        self.audit_jsonl_path = audit_jsonl_path or _mission_audit_jsonl_path(db_path)

    def initialize(self) -> None:
        verify_database_v2(self.db_path)

    def replay_admission(
        self,
        payload: MissionAdmissionPayload,
        *,
        requester: AdminPrincipalContext,
    ) -> MissionAdmissionStage | None:
        with _mission_connection(self.db_path) as connection:
            existing = _mission_by_idempotency_namespace(
                connection,
                requester_principal_id=requester.principal_id,
                requester_identity_generation=requester.identity_generation,
                client_request_id=payload.client_request_id,
            )
            if existing is None:
                return None
            request_digest = mission_admission_request_digest(
                payload,
                authority=existing.authority_snapshot,
            )
            if existing.admission_request_digest != request_digest:
                raise MissionConflictError("mission client request ID conflicts")
            return MissionAdmissionStage(
                mission=existing,
                transition=_admission_transition_for_mission(
                    connection,
                    existing.mission_id,
                ),
                idempotent_replay=True,
            )

    def stage_admission(
        self,
        payload: MissionAdmissionPayload,
        *,
        authority: MissionAuthoritySnapshot,
        authority_precondition: Callable[[], None] | None = None,
        now: datetime | None = None,
    ) -> MissionAdmissionStage:
        _require_payload_matches_authority(payload, authority)
        effective_now = now or datetime.now(UTC)
        request_digest = mission_admission_request_digest(payload, authority=authority)
        authority_hash = authority.canonical_hash()
        requester = authority.requesting_principal
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = _mission_by_idempotency_namespace(
                connection,
                requester_principal_id=requester.principal_id,
                requester_identity_generation=requester.identity_generation,
                client_request_id=payload.client_request_id,
            )
            if existing is not None:
                if existing.admission_request_digest != request_digest:
                    raise MissionConflictError("mission client request ID conflicts")
                transition = _admission_transition_for_mission(connection, existing.mission_id)
                connection.commit()
                return MissionAdmissionStage(
                    mission=existing,
                    transition=transition,
                    idempotent_replay=True,
                )
            if authority_precondition is not None:
                authority_precondition()

            mission_id = f"mission_{uuid4().hex}"
            transition_id = f"mtransition_{uuid4().hex}"
            now_text = effective_now.isoformat()
            envelope_digest = mission_envelope_digest(
                mission_id=mission_id,
                payload=payload,
                authority=authority,
                authority_snapshot_hash=authority_hash,
            )
            try:
                connection.execute(
                    """
                    INSERT INTO missions (
                        mission_id, requester_principal_id, requester_identity_generation,
                        client_request_id, admission_request_digest, authority_snapshot_json,
                        authority_snapshot_hash, target_node_id, target_node_principal_id,
                        workspace_id, configuration_generation, configuration_digest,
                        policy_digest, manifest_lock_digest, mission_template_id,
                        template_registry_generation, template_payload_digest, envelope_digest,
                        requested_timeout_seconds, lifecycle_state, lifecycle_revision,
                        created_at, updated_at, admitted_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL
                    )
                    """,
                    (
                        mission_id,
                        requester.principal_id,
                        requester.identity_generation,
                        payload.client_request_id,
                        request_digest,
                        canonical_json(authority.canonical_payload()),
                        authority_hash,
                        authority.target_node_id,
                        authority.target_node_principal_id,
                        authority.workspace_id,
                        authority.configuration_generation,
                        authority.configuration_digest,
                        authority.policy_digest,
                        authority.manifest_lock_digest,
                        authority.mission_template_id,
                        authority.template_registry_generation,
                        authority.template_payload_digest,
                        envelope_digest,
                        payload.requested_timeout_seconds,
                        MISSION_UNADMITTED,
                        0,
                        now_text,
                        now_text,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO mission_transition_attempts (
                        transition_id, mission_id, transition_kind,
                        prior_lifecycle_state, prior_lifecycle_revision,
                        proposed_lifecycle_state, proposed_lifecycle_revision,
                        request_digest, safe_metadata_json, evidence_status,
                        audit_event_id, audit_event_hash, failure_reason_code,
                        created_at, finalized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, NULL)
                    """,
                    (
                        transition_id,
                        mission_id,
                        MISSION_ADMISSION_TRANSITION_KIND,
                        MISSION_UNADMITTED,
                        0,
                        MISSION_QUEUED,
                        1,
                        request_digest,
                        canonical_json(
                            {
                                "mission_template_id": authority.mission_template_id,
                                "target_node_id": authority.target_node_id,
                                "workspace_id": authority.workspace_id,
                                "envelope_digest": envelope_digest,
                            }
                        ),
                        EVIDENCE_PENDING,
                        now_text,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission admission conflicts") from exc
            connection.commit()
        return MissionAdmissionStage(
            mission=self.get(mission_id),
            transition=self.get_transition(transition_id),
            idempotent_replay=False,
        )

    def next_queued_for_node(self, node_id: str) -> MissionRecord:
        if not _NODE_ID_PATTERN.fullmatch(node_id):
            raise MissionNotFoundError("no queued mission for Node")
        with _mission_connection(self.db_path) as connection:
            row = connection.execute(
                f"""
                {_MISSION_SELECT}
                WHERE target_node_id = ? AND lifecycle_state = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM mission_claims
                      WHERE mission_claims.mission_id = missions.mission_id
                  )
                ORDER BY admitted_at ASC, mission_id ASC LIMIT 1
                """,
                (node_id, MISSION_QUEUED),
            ).fetchone()
        if row is None:
            raise MissionNotFoundError("no queued mission for Node")
        return _mission_from_row(row)

    def stage_claim(
        self,
        mission_id: str,
        payload: MissionClaimRequestPayload,
        *,
        authority: MissionClaimAuthoritySnapshot,
        authority_precondition: Callable[[], MissionClaimAuthoritySnapshot] | None = None,
        now: datetime | None = None,
    ) -> MissionClaimStage:
        _require_mission_id(mission_id)
        effective_now = now or datetime.now(UTC)
        now_text = effective_now.isoformat()
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            mission = _mission_by_id(connection, mission_id)
            _require_claim_authority_matches_mission(authority, mission)
            if mission.lifecycle_state != MISSION_QUEUED:
                raise MissionConflictError("mission is not queued for claim")
            if _claim_by_mission_optional(connection, mission_id) is not None:
                raise MissionConflictError("mission already has a claim")
            if _node_has_blocking_claim(connection, authority.target_node_id):
                raise MissionConflictError("Node already has unresolved mission delivery")
            if authority_precondition is not None:
                current_authority = authority_precondition()
                if current_authority.canonical_hash() != authority.canonical_hash():
                    raise MissionConflictError("mission claim authority changed")

            claim_id = f"mclaim_{uuid4().hex}"
            transition_id = f"mtransition_{uuid4().hex}"
            proposed_revision = mission.lifecycle_revision + 1
            expires_at = effective_now + timedelta(seconds=mission.requested_timeout_seconds)
            expires_at_text = expires_at.isoformat()
            authority_hash = authority.canonical_hash()
            request_digest = mission_claim_request_digest(
                mission=mission,
                payload=payload,
                claim_id=claim_id,
                authority_snapshot_hash=authority_hash,
                expires_at=expires_at_text,
                prior_lifecycle_state=mission.lifecycle_state,
                prior_lifecycle_revision=mission.lifecycle_revision,
            )
            safe_metadata = {
                "claim_id": claim_id,
                "node_id": authority.target_node_id,
                "node_identity_key_id": authority.node_identity_key_id,
                "envelope_digest": mission.envelope_digest,
                "authority_snapshot_hash": authority_hash,
                "expires_at": expires_at_text,
            }
            try:
                connection.execute(
                    """
                    INSERT INTO mission_transition_attempts (
                        transition_id, mission_id, transition_kind,
                        prior_lifecycle_state, prior_lifecycle_revision,
                        proposed_lifecycle_state, proposed_lifecycle_revision,
                        request_digest, safe_metadata_json, evidence_status,
                        audit_event_id, audit_event_hash, failure_reason_code,
                        created_at, finalized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, NULL)
                    """,
                    (
                        transition_id,
                        mission.mission_id,
                        MISSION_CLAIM_TRANSITION_KIND,
                        mission.lifecycle_state,
                        mission.lifecycle_revision,
                        MISSION_CLAIMED,
                        proposed_revision,
                        request_digest,
                        canonical_json(cast(JsonObject, safe_metadata)),
                        EVIDENCE_PENDING,
                        now_text,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO mission_claims (
                        claim_id, mission_id, transition_id, node_id,
                        node_identity_key_id, envelope_digest, authority_snapshot_json,
                        authority_snapshot_hash, lifecycle_revision, claim_status,
                        claimed_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'staged', ?, ?)
                    """,
                    (
                        claim_id,
                        mission.mission_id,
                        transition_id,
                        authority.target_node_id,
                        authority.node_identity_key_id,
                        mission.envelope_digest,
                        canonical_json(authority.canonical_payload()),
                        authority_hash,
                        proposed_revision,
                        now_text,
                        expires_at_text,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission claim conflicts") from exc
            connection.commit()
        return MissionClaimStage(
            mission=self.get(mission_id),
            claim=self.get_claim(mission_id),
            transition=self.get_transition(transition_id),
        )

    def due_delivered_claims(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[MissionClaimRecord]:
        effective_now = now or datetime.now(UTC)
        if effective_now.tzinfo is None:
            raise MissionConflictError("mission claim reconciliation time must be timezone-aware")
        bounded_limit = max(1, min(limit, 100))
        with _mission_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT mission_id FROM missions
                WHERE lifecycle_state = ?
                  AND EXISTS (
                      SELECT 1 FROM mission_claims
                      WHERE mission_claims.mission_id = missions.mission_id
                  ) AND NOT EXISTS (
                      SELECT 1 FROM mission_transition_attempts
                      WHERE mission_transition_attempts.mission_id = missions.mission_id
                        AND mission_transition_attempts.transition_kind = ?
                  )
                ORDER BY mission_id ASC
                """,
                (
                    MISSION_CLAIMED,
                    MISSION_CLAIM_EXPIRY_TRANSITION_KIND,
                ),
            ).fetchall()
            due_claims: list[tuple[datetime, MissionClaimRecord]] = []
            for row in rows:
                claim = _claim_by_mission(connection, str(row[0]))
                if claim.claim_status != "delivered":
                    raise MissionError("stored claimed mission has no delivered claim")
                expires_at = datetime.fromisoformat(claim.expires_at)
                if expires_at <= effective_now:
                    due_claims.append((expires_at, claim))
        due_claims.sort(key=lambda item: (item[0], item[1].claim_id))
        return [claim for _, claim in due_claims[:bounded_limit]]

    def stage_claim_expiry(
        self,
        mission_id: str,
        *,
        now: datetime | None = None,
    ) -> MissionClaimExpiryStage:
        _require_mission_id(mission_id)
        effective_now = now or datetime.now(UTC)
        now_text = effective_now.isoformat()
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            mission = _mission_by_id(connection, mission_id)
            claim = _claim_by_mission(connection, mission_id)
            if _mission_has_other_unresolved_report_receipt(
                connection,
                mission_id=mission_id,
                report_id="",
            ):
                raise MissionConflictError("mission report receipt requires evidence recovery")
            if mission.lifecycle_state != MISSION_CLAIMED or claim.claim_status != "delivered":
                raise MissionConflictError("mission claim is not eligible for expiry")
            try:
                expires_at = datetime.fromisoformat(claim.expires_at)
            except ValueError as exc:
                raise MissionError("stored mission claim expiry is invalid") from exc
            if expires_at.tzinfo is None or effective_now < expires_at:
                raise MissionConflictError("mission claim has not expired")
            transition_id = f"mtransition_{uuid4().hex}"
            proposed_revision = mission.lifecycle_revision + 1
            request_digest = mission_claim_expiry_request_digest(
                mission=mission,
                claim=claim,
                prior_lifecycle_state=mission.lifecycle_state,
                prior_lifecycle_revision=mission.lifecycle_revision,
            )
            safe_metadata: JsonObject = {
                "claim_id": claim.claim_id,
                "node_id": claim.node_id,
                "envelope_digest": claim.envelope_digest,
                "expires_at": claim.expires_at,
            }
            try:
                connection.execute(
                    """
                    INSERT INTO mission_transition_attempts (
                        transition_id, mission_id, transition_kind,
                        prior_lifecycle_state, prior_lifecycle_revision,
                        proposed_lifecycle_state, proposed_lifecycle_revision,
                        request_digest, safe_metadata_json, evidence_status,
                        audit_event_id, audit_event_hash, failure_reason_code,
                        created_at, finalized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, NULL)
                    """,
                    (
                        transition_id,
                        mission.mission_id,
                        MISSION_CLAIM_EXPIRY_TRANSITION_KIND,
                        mission.lifecycle_state,
                        mission.lifecycle_revision,
                        MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED,
                        proposed_revision,
                        request_digest,
                        canonical_json(safe_metadata),
                        EVIDENCE_PENDING,
                        now_text,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission claim expiry conflicts") from exc
            connection.commit()
        return MissionClaimExpiryStage(
            mission=self.get(mission_id),
            claim=self.get_claim(mission_id),
            transition=self.get_transition(transition_id),
        )

    def stage_authenticated_report_receipt(
        self,
        connection: sqlite3.Connection,
        report: MissionRunnerReportPayload,
        *,
        node_id: str,
        verified_node_identity_key_id: str,
        receipt_posture: JsonObject,
        authority_eligible: bool,
        now: datetime | None = None,
    ) -> MissionReportReceiptStage:
        if not _NODE_ID_PATTERN.fullmatch(node_id):
            raise MissionConflictError("invalid mission report Node")
        if not re.fullmatch(SHA256_PATTERN, verified_node_identity_key_id):
            raise MissionConflictError("invalid verified Node identity key ID")
        effective_now = now or datetime.now(UTC)
        request_digest = mission_report_request_digest(report)
        existing = _report_receipt_optional(connection, report.report_id)
        if existing is not None:
            if existing.request_digest != request_digest or existing.node_id != node_id:
                raise MissionConflictError("mission report ID conflicts")
            return MissionReportReceiptStage(
                receipt=existing,
                idempotent_replay=True,
            )
        mission = _mission_by_id(connection, report.mission_id)
        claim = _claim_by_mission(connection, report.mission_id)
        _require_report_matches_claim(
            report,
            mission=mission,
            claim=claim,
            node_id=node_id,
        )
        proposed_state = _report_proposed_state(
            connection,
            receipt=None,
            report=report,
            mission=mission,
            claim=claim,
            now=effective_now,
        )
        lifecycle_advancing = (
            authority_eligible
            and not _mission_has_unresolved_transition(connection, mission.mission_id)
            and not _mission_has_other_unresolved_report_receipt(
                connection,
                mission_id=mission.mission_id,
                report_id=report.report_id,
            )
            and proposed_state is not None
        )
        if not authority_eligible:
            quarantine_reason_code = receipt_posture.get("reason_code")
        elif _mission_has_unresolved_transition(connection, mission.mission_id):
            quarantine_reason_code = "transition_evidence_unresolved"
        elif _mission_has_other_unresolved_report_receipt(
            connection,
            mission_id=mission.mission_id,
            report_id=report.report_id,
        ):
            quarantine_reason_code = "report_evidence_unresolved"
        elif proposed_state is None:
            quarantine_reason_code = _report_lifecycle_quarantine_reason(
                connection,
                report=report,
                mission=mission,
                claim=claim,
                now=effective_now,
            )
        else:
            quarantine_reason_code = None
        proposed_disposition = "lifecycle_advancing" if lifecycle_advancing else "quarantined"
        stored_posture: JsonObject = {
            "authenticated_receipt": receipt_posture,
            "proposed_advancement": receipt_posture,
            "proposed_disposition": proposed_disposition,
            "quarantine_reason_code": quarantine_reason_code,
        }
        try:
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'pending', ?, NULL, NULL, NULL, ?, NULL)
                """,
                (
                    report.report_id,
                    report.mission_id,
                    report.claim_id,
                    node_id,
                    verified_node_identity_key_id,
                    report.envelope_digest,
                    report.expected_lifecycle_revision,
                    report.report_kind,
                    report.outcome_code,
                    report.reason_code,
                    report.artifact_digest,
                    request_digest,
                    canonical_json(stored_posture),
                    EVIDENCE_PENDING,
                    effective_now.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise MissionConflictError("mission report receipt conflicts") from exc
        return MissionReportReceiptStage(
            receipt=_report_receipt(connection, report.report_id),
            idempotent_replay=False,
        )

    def finalize_report_receipt(
        self,
        report_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        advancement_precondition: Callable[[], tuple[bool, JsonObject]],
        now: datetime | None = None,
    ) -> MissionReportReceiptFinalization:
        _require_report_id(report_id)
        if not _EVENT_ID_PATTERN.fullmatch(audit_event_id):
            raise MissionConflictError("invalid mission report audit event ID")
        if not re.fullmatch(SHA256_PATTERN, audit_event_hash):
            raise MissionConflictError("invalid mission report audit event hash")
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = _report_receipt(connection, report_id)
            if receipt.evidence_status == EVIDENCE_COMPLETE:
                if (
                    receipt.audit_event_id != audit_event_id
                    or receipt.audit_event_hash != audit_event_hash
                ):
                    raise MissionConflictError("mission report receipt evidence conflicts")
                connection.commit()
                existing_transition = _transition_for_report_optional(connection, report_id)
                return MissionReportReceiptFinalization(receipt, existing_transition)
            if receipt.evidence_status != EVIDENCE_PENDING:
                raise MissionConflictError("mission report receipt evidence is incomplete")
            mission = _mission_by_id(connection, receipt.report.mission_id)
            claim = _claim_by_mission(connection, mission.mission_id)
            _require_report_matches_claim(
                receipt.report,
                mission=mission,
                claim=claim,
                node_id=receipt.node_id,
            )
            eligible, advancement_posture = advancement_precondition()
            finalization_now = now or datetime.now(UTC)
            proposed_state = _report_proposed_state(
                connection,
                report=receipt.report,
                mission=mission,
                claim=claim,
                now=finalization_now,
            )
            lifecycle_advancing = (
                eligible
                and not _mission_has_unresolved_transition(connection, mission.mission_id)
                and not _mission_has_other_unresolved_report_receipt(
                    connection,
                    mission_id=mission.mission_id,
                    report_id=receipt.report.report_id,
                )
                and proposed_state is not None
            )
            disposition = "lifecycle_advancing" if lifecycle_advancing else "quarantined"
            staged_disposition = receipt.receipt_posture.get("proposed_disposition")
            if staged_disposition == "quarantined":
                disposition = "quarantined"
                lifecycle_advancing = False
                proposed_state = None
            elif (
                staged_disposition != "lifecycle_advancing"
                or disposition != "lifecycle_advancing"
                or receipt.receipt_posture.get("proposed_advancement") != advancement_posture
            ):
                raise MissionConflictError(
                    "mission report authority changed before receipt finalization"
                )
            now_text = finalization_now.isoformat()
            try:
                connection.execute(
                    """
                    INSERT INTO mission_audit_evidence_bindings (
                        audit_event_id, audit_event_hash, owner_kind, owner_id,
                        request_digest, bound_at
                    ) VALUES (?, ?, 'mission_report_receipt', ?, ?, ?)
                    """,
                    (
                        audit_event_id,
                        audit_event_hash,
                        report_id,
                        receipt.request_digest,
                        now_text,
                    ),
                )
                updated = connection.execute(
                    """
                    UPDATE mission_report_receipts
                    SET receipt_posture_json = ?, receipt_disposition = ?,
                        evidence_status = ?, audit_event_id = ?, audit_event_hash = ?,
                        finalized_at = ?
                    WHERE report_id = ? AND evidence_status = ?
                    """,
                    (
                        canonical_json(receipt.receipt_posture),
                        disposition,
                        EVIDENCE_COMPLETE,
                        audit_event_id,
                        audit_event_hash,
                        now_text,
                        report_id,
                        EVIDENCE_PENDING,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission report evidence is already bound") from exc
            if updated.rowcount != 1:
                raise MissionConflictError("mission report receipt evidence changed")
            transition: MissionTransitionAttempt | None = None
            if lifecycle_advancing and proposed_state is not None:
                transition = _insert_report_transition(
                    connection,
                    receipt=receipt,
                    mission=mission,
                    proposed_state=proposed_state,
                    now_text=now_text,
                )
            connection.commit()
        return MissionReportReceiptFinalization(
            receipt=self.get_report_receipt(report_id),
            transition=(
                self.get_transition(transition.transition_id) if transition is not None else None
            ),
        )

    def mark_report_receipt_evidence_incomplete(
        self,
        report_id: str,
        *,
        failure_reason_code: str,
        now: datetime | None = None,
    ) -> MissionReportReceipt:
        _require_report_id(report_id)
        if not _SAFE_LABEL_PATTERN.fullmatch(failure_reason_code) or ".." in failure_reason_code:
            raise MissionConflictError("invalid mission report evidence failure reason")
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = _report_receipt(connection, report_id)
            if receipt.evidence_status == EVIDENCE_INCOMPLETE:
                if receipt.failure_reason_code == failure_reason_code:
                    connection.commit()
                    return receipt
                raise MissionConflictError("mission report evidence failure reason conflicts")
            if receipt.evidence_status != EVIDENCE_PENDING:
                raise MissionConflictError("completed mission report evidence cannot be changed")
            connection.execute(
                """
                UPDATE mission_report_receipts
                SET receipt_disposition = 'evidence_incomplete', evidence_status = ?,
                    failure_reason_code = ?, finalized_at = ?
                WHERE report_id = ? AND evidence_status = ?
                """,
                (
                    EVIDENCE_INCOMPLETE,
                    failure_reason_code,
                    (now or datetime.now(UTC)).isoformat(),
                    report_id,
                    EVIDENCE_PENDING,
                ),
            )
            connection.commit()
        return self.get_report_receipt(report_id)

    def get_report_receipt(self, report_id: str) -> MissionReportReceipt:
        _require_report_id(report_id)
        with _mission_connection(self.db_path) as connection:
            return _report_receipt(connection, report_id)

    def get_report_transition(self, report_id: str) -> MissionTransitionAttempt | None:
        _require_report_id(report_id)
        with _mission_connection(self.db_path) as connection:
            return _transition_for_report_optional(connection, report_id)

    def get_cancellation_transition(
        self,
        mission_id: str,
    ) -> MissionTransitionAttempt | None:
        _require_mission_id(mission_id)
        with _mission_connection(self.db_path) as connection:
            return _transition_for_mission_kind(
                connection,
                mission_id=mission_id,
                transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
            )

    def require_current_control_decision(
        self,
        payload: MissionControlPollPayload,
        *,
        node_id: str,
        authenticated_public_key: str,
        expected_lifecycle_state: str,
        expected_lifecycle_revision: int,
        expected_decision: str,
        expected_decision_revision: int,
        now: datetime | None = None,
    ) -> None:
        effective_now = now or datetime.now(UTC)
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            mission = _mission_by_id(connection, payload.mission_id)
            claim = _claim_by_mission(connection, payload.mission_id)
            node_row = connection.execute(
                "SELECT status, evidence_status, public_key, principal_id, workspace_id "
                "FROM nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            pending_rotation = connection.execute(
                "SELECT expires_at FROM node_identity_key_rotations "
                "WHERE node_id = ? AND status = 'pending' LIMIT 1",
                (node_id,),
            ).fetchone()
            active_pending_rotation = False
            if pending_rotation is not None:
                try:
                    rotation_expires_at = datetime.fromisoformat(str(pending_rotation[0]))
                except ValueError:
                    rotation_expires_at = None
                active_pending_rotation = (
                    rotation_expires_at is None
                    or rotation_expires_at.tzinfo is None
                    or effective_now < rotation_expires_at
                )
            if (
                node_row is None
                or tuple(str(value) for value in node_row[:3])
                != ("enrolled", EVIDENCE_COMPLETE, authenticated_public_key)
                or str(node_row[3]) != mission.target_node_principal_id
                or str(node_row[4]) != mission.workspace_id
                or active_pending_rotation
                or mission.target_node_id != node_id
                or claim.node_id != node_id
                or claim.claim_status != "delivered"
                or payload.claim_id != claim.claim_id
                or payload.envelope_digest != mission.envelope_digest
                or claim.envelope_digest != mission.envelope_digest
                or mission.lifecycle_state != expected_lifecycle_state
                or mission.lifecycle_revision != expected_lifecycle_revision
                or payload.observed_lifecycle_revision > mission.lifecycle_revision
            ):
                raise MissionConflictError("mission control authority changed before delivery")
            try:
                expires_at = datetime.fromisoformat(claim.expires_at)
            except ValueError as exc:
                raise MissionError("stored mission claim expiry is invalid") from exc
            if expires_at.tzinfo is None or (
                mission.lifecycle_state == MISSION_CLAIMED and effective_now >= expires_at
            ):
                raise MissionConflictError("mission control authority changed before delivery")
            if expected_decision == "continue":
                valid_decision = (
                    mission.lifecycle_state in {MISSION_CLAIMED, MISSION_RUNNER_REPORTED_RUNNING}
                    and expected_decision_revision == mission.lifecycle_revision
                )
            elif expected_decision == "cancel_requested":
                cancellation = _transition_for_mission_kind(
                    connection,
                    mission_id=mission.mission_id,
                    transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
                )
                valid_decision = (
                    mission.lifecycle_state == MISSION_CANCEL_REQUESTED
                    and cancellation is not None
                    and cancellation.evidence_status == EVIDENCE_COMPLETE
                    and cancellation.proposed_lifecycle_state == MISSION_CANCEL_REQUESTED
                    and cancellation.proposed_lifecycle_revision == expected_decision_revision
                )
            else:
                valid_decision = False
            if not valid_decision:
                raise MissionConflictError("mission control authority changed before delivery")
            connection.commit()

    def stage_cancellation(
        self,
        mission_id: str,
        payload: MissionCancellationPayload,
        *,
        requester: AdminPrincipalContext,
        now: datetime | None = None,
    ) -> MissionCancellationStage:
        _require_mission_id(mission_id)
        now_text = (now or datetime.now(UTC)).isoformat()
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            mission = _mission_by_id(connection, mission_id)
            existing = _transition_for_mission_kind(
                connection,
                mission_id=mission_id,
                transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
            )
            if existing is not None:
                expected_digest = mission_cancellation_request_digest(
                    mission=mission,
                    payload=payload,
                    requester=requester,
                    prior_lifecycle_state=existing.prior_lifecycle_state,
                    prior_lifecycle_revision=existing.prior_lifecycle_revision,
                )
                if existing.request_digest != expected_digest:
                    raise MissionConflictError("mission cancellation request conflicts")
                connection.commit()
                return MissionCancellationStage(
                    mission=mission,
                    transition=existing,
                    idempotent_replay=True,
                )
            if _mission_has_other_unresolved_report_receipt(
                connection,
                mission_id=mission_id,
                report_id="",
            ):
                raise MissionConflictError("mission report receipt requires evidence recovery")
            if _mission_has_unresolved_transition(connection, mission_id):
                raise MissionConflictError("mission transition requires evidence recovery")
            if mission.lifecycle_state not in {
                MISSION_QUEUED,
                MISSION_CLAIMED,
                MISSION_RUNNER_REPORTED_RUNNING,
            }:
                raise MissionConflictError("mission is not eligible for cancellation")
            proposed_state = (
                MISSION_CANCELED
                if mission.lifecycle_state == MISSION_QUEUED
                else MISSION_CANCEL_REQUESTED
            )
            request_digest = mission_cancellation_request_digest(
                mission=mission,
                payload=payload,
                requester=requester,
                prior_lifecycle_state=mission.lifecycle_state,
                prior_lifecycle_revision=mission.lifecycle_revision,
            )
            transition_id = f"mtransition_{uuid4().hex}"
            try:
                connection.execute(
                    """
                    INSERT INTO mission_transition_attempts (
                        transition_id, mission_id, transition_kind,
                        prior_lifecycle_state, prior_lifecycle_revision,
                        proposed_lifecycle_state, proposed_lifecycle_revision,
                        request_digest, safe_metadata_json, evidence_status,
                        audit_event_id, audit_event_hash, failure_reason_code,
                        created_at, finalized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, NULL)
                    """,
                    (
                        transition_id,
                        mission_id,
                        MISSION_CANCELLATION_TRANSITION_KIND,
                        mission.lifecycle_state,
                        mission.lifecycle_revision,
                        proposed_state,
                        mission.lifecycle_revision + 1,
                        request_digest,
                        canonical_json(
                            {
                                "requester_principal_id": requester.principal_id,
                                "requester_identity_generation": requester.identity_generation,
                                "client_request_id": payload.client_request_id,
                                "mission_template_id": mission.mission_template_id,
                                "target_node_id": mission.target_node_id,
                                "workspace_id": mission.workspace_id,
                                "envelope_digest": mission.envelope_digest,
                            }
                        ),
                        EVIDENCE_PENDING,
                        now_text,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission cancellation conflicts") from exc
            connection.commit()
        return MissionCancellationStage(
            mission=self.get(mission_id),
            transition=self.get_transition(transition_id),
            idempotent_replay=False,
        )

    def finalize_admission(
        self,
        transition_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        now: datetime | None = None,
    ) -> MissionRecord:
        return self._finalize_transition(
            transition_id,
            expected_kind=MISSION_ADMISSION_TRANSITION_KIND,
            audit_event_id=audit_event_id,
            audit_event_hash=audit_event_hash,
            now=now,
        )

    def finalize_cancellation(
        self,
        transition_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        now: datetime | None = None,
    ) -> MissionRecord:
        return self._finalize_transition(
            transition_id,
            expected_kind=MISSION_CANCELLATION_TRANSITION_KIND,
            audit_event_id=audit_event_id,
            audit_event_hash=audit_event_hash,
            now=now,
        )

    def finalize_claim(
        self,
        transition_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        authority_precondition: Callable[[], MissionClaimAuthoritySnapshot],
        now: datetime | None = None,
    ) -> MissionClaimRecord:
        mission = self._finalize_transition(
            transition_id,
            expected_kind=MISSION_CLAIM_TRANSITION_KIND,
            audit_event_id=audit_event_id,
            audit_event_hash=audit_event_hash,
            claim_authority_precondition=authority_precondition,
            now=now,
        )
        return self.get_claim(mission.mission_id)

    def finalize_claim_expiry(
        self,
        transition_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        now: datetime | None = None,
    ) -> MissionRecord:
        return self._finalize_transition(
            transition_id,
            expected_kind=MISSION_CLAIM_EXPIRY_TRANSITION_KIND,
            audit_event_id=audit_event_id,
            audit_event_hash=audit_event_hash,
            now=now,
        )

    def finalize_report_transition(
        self,
        transition_id: str,
        *,
        audit_event_id: str,
        audit_event_hash: str,
        advancement_precondition: Callable[[], bool],
        now: datetime | None = None,
    ) -> MissionRecord:
        transition = self.get_transition(transition_id)
        if transition.transition_kind not in {
            MISSION_REPORT_TRANSITION_KIND,
            MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
        }:
            raise MissionConflictError("mission transition is not report-sourced")
        return self._finalize_transition(
            transition_id,
            expected_kind=transition.transition_kind,
            audit_event_id=audit_event_id,
            audit_event_hash=audit_event_hash,
            report_advancement_precondition=advancement_precondition,
            now=now,
        )

    def _finalize_transition(
        self,
        transition_id: str,
        *,
        expected_kind: str,
        audit_event_id: str,
        audit_event_hash: str,
        now: datetime | None,
        claim_authority_precondition: (Callable[[], MissionClaimAuthoritySnapshot] | None) = None,
        report_advancement_precondition: Callable[[], bool] | None = None,
    ) -> MissionRecord:
        _require_transition_id(transition_id)
        if not _EVENT_ID_PATTERN.fullmatch(audit_event_id):
            raise MissionConflictError("invalid mission audit event ID")
        if not re.fullmatch(SHA256_PATTERN, audit_event_hash):
            raise MissionConflictError("invalid mission audit event hash")
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            transition = _transition_by_id(connection, transition_id)
            if transition.transition_kind != expected_kind:
                raise MissionConflictError("mission transition kind does not match")
            if transition.evidence_status == EVIDENCE_COMPLETE:
                if (
                    transition.audit_event_id == audit_event_id
                    and transition.audit_event_hash == audit_event_hash
                ):
                    _verify_audit_evidence_binding(
                        connection,
                        transition=transition,
                        audit_event_id=audit_event_id,
                        audit_event_hash=audit_event_hash,
                    )
                    connection.commit()
                    return _mission_by_id(connection, transition.mission_id)
                raise MissionConflictError("mission transition evidence conflicts")
            if transition.evidence_status != EVIDENCE_PENDING:
                raise MissionConflictError("mission transition evidence is incomplete")
            mission = _mission_by_id(connection, transition.mission_id)
            if (
                mission.lifecycle_state != transition.prior_lifecycle_state
                or mission.lifecycle_revision != transition.prior_lifecycle_revision
            ):
                raise MissionConflictError("mission lifecycle changed before evidence finalization")
            if expected_kind == MISSION_CLAIM_TRANSITION_KIND:
                if claim_authority_precondition is None:
                    raise MissionConflictError("mission claim authority precondition is required")
                claim = _claim_by_mission(connection, mission.mission_id)
                current_authority = claim_authority_precondition()
                if current_authority.canonical_hash() != claim.authority_snapshot_hash:
                    raise MissionConflictError("mission claim authority changed before delivery")
                try:
                    expires_at = datetime.fromisoformat(claim.expires_at)
                except ValueError as exc:
                    raise MissionError("stored mission claim expiry is invalid") from exc
                finalization_now = now or datetime.now(UTC)
                if expires_at.tzinfo is None or finalization_now >= expires_at:
                    raise MissionConflictError("mission claim expired before delivery")
            else:
                finalization_now = now or datetime.now(UTC)
            if expected_kind in {
                MISSION_REPORT_TRANSITION_KIND,
                MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
            } and (
                report_advancement_precondition is None or not report_advancement_precondition()
            ):
                raise MissionConflictError(
                    "mission report authority changed before lifecycle advancement"
                )
            now_text = finalization_now.isoformat()
            try:
                connection.execute(
                    """
                    INSERT INTO mission_audit_evidence_bindings (
                        audit_event_id, audit_event_hash, owner_kind, owner_id,
                        request_digest, bound_at
                    ) VALUES (?, ?, 'mission_transition', ?, ?, ?)
                    """,
                    (
                        audit_event_id,
                        audit_event_hash,
                        transition.transition_id,
                        transition.request_digest,
                        now_text,
                    ),
                )
                updated_transition = connection.execute(
                    """
                    UPDATE mission_transition_attempts
                    SET evidence_status = ?, audit_event_id = ?, audit_event_hash = ?,
                        finalized_at = ?
                    WHERE transition_id = ? AND evidence_status = ?
                    """,
                    (
                        EVIDENCE_COMPLETE,
                        audit_event_id,
                        audit_event_hash,
                        now_text,
                        transition_id,
                        EVIDENCE_PENDING,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise MissionConflictError("mission audit evidence is already bound") from exc
            if updated_transition.rowcount != 1:
                raise MissionConflictError("mission transition evidence changed")
            if expected_kind == MISSION_ADMISSION_TRANSITION_KIND:
                updated_mission = connection.execute(
                    """
                    UPDATE missions
                    SET lifecycle_state = ?, lifecycle_revision = ?, updated_at = ?, admitted_at = ?
                    WHERE mission_id = ? AND lifecycle_state = ? AND lifecycle_revision = ?
                    """,
                    (
                        transition.proposed_lifecycle_state,
                        transition.proposed_lifecycle_revision,
                        now_text,
                        now_text,
                        mission.mission_id,
                        transition.prior_lifecycle_state,
                        transition.prior_lifecycle_revision,
                    ),
                )
            else:
                updated_mission = connection.execute(
                    """
                    UPDATE missions
                    SET lifecycle_state = ?, lifecycle_revision = ?, updated_at = ?
                    WHERE mission_id = ? AND lifecycle_state = ? AND lifecycle_revision = ?
                    """,
                    (
                        transition.proposed_lifecycle_state,
                        transition.proposed_lifecycle_revision,
                        now_text,
                        mission.mission_id,
                        transition.prior_lifecycle_state,
                        transition.prior_lifecycle_revision,
                    ),
                )
            if updated_mission.rowcount != 1:
                raise MissionConflictError("mission lifecycle finalization conflicted")
            if expected_kind == MISSION_CLAIM_TRANSITION_KIND:
                updated_claim = connection.execute(
                    """
                    UPDATE mission_claims SET claim_status = 'delivered'
                    WHERE mission_id = ? AND transition_id = ? AND claim_status = 'staged'
                    """,
                    (mission.mission_id, transition.transition_id),
                )
                if updated_claim.rowcount != 1:
                    raise MissionConflictError("mission claim finalization conflicted")
            elif expected_kind == MISSION_CLAIM_EXPIRY_TRANSITION_KIND:
                updated_claim = connection.execute(
                    """
                    UPDATE mission_claims SET claim_status = 'expired_review_required'
                    WHERE mission_id = ? AND claim_status = 'delivered'
                    """,
                    (mission.mission_id,),
                )
                if updated_claim.rowcount != 1:
                    raise MissionConflictError("mission claim expiry finalization conflicted")
            connection.commit()
            return _mission_by_id(connection, mission.mission_id)

    def mark_transition_evidence_incomplete(
        self,
        transition_id: str,
        *,
        failure_reason_code: str,
        now: datetime | None = None,
    ) -> MissionTransitionAttempt:
        _require_transition_id(transition_id)
        if not _SAFE_LABEL_PATTERN.fullmatch(failure_reason_code) or ".." in failure_reason_code:
            raise MissionConflictError("invalid mission evidence failure reason")
        now_text = (now or datetime.now(UTC)).isoformat()
        with _mission_connection(self.db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            transition = _transition_by_id(connection, transition_id)
            if transition.evidence_status == EVIDENCE_INCOMPLETE:
                if transition.failure_reason_code == failure_reason_code:
                    connection.commit()
                    return transition
                raise MissionConflictError("mission evidence failure reason conflicts")
            if transition.evidence_status != EVIDENCE_PENDING:
                raise MissionConflictError("completed mission evidence cannot be changed")
            updated = connection.execute(
                """
                UPDATE mission_transition_attempts
                SET evidence_status = ?, failure_reason_code = ?, finalized_at = ?
                WHERE transition_id = ? AND evidence_status = ?
                """,
                (
                    EVIDENCE_INCOMPLETE,
                    failure_reason_code,
                    now_text,
                    transition_id,
                    EVIDENCE_PENDING,
                ),
            )
            if updated.rowcount != 1:
                raise MissionConflictError("mission transition evidence changed")
            if transition.transition_kind == MISSION_CLAIM_TRANSITION_KIND:
                updated_claim = connection.execute(
                    """
                    UPDATE mission_claims SET claim_status = 'evidence_incomplete'
                    WHERE transition_id = ? AND claim_status = 'staged'
                    """,
                    (transition.transition_id,),
                )
                if updated_claim.rowcount != 1:
                    raise MissionConflictError("mission claim evidence status changed")
            connection.commit()
            return _transition_by_id(connection, transition_id)

    def get(self, mission_id: str) -> MissionRecord:
        _require_mission_id(mission_id)
        with _mission_connection(self.db_path) as connection:
            return _mission_by_id(connection, mission_id)

    def get_admitted(self, mission_id: str) -> MissionRecord:
        mission = self.get(mission_id)
        if mission.lifecycle_state == MISSION_UNADMITTED:
            raise MissionNotFoundError("unknown mission")
        return mission

    def get_transition(self, transition_id: str) -> MissionTransitionAttempt:
        _require_transition_id(transition_id)
        with _mission_connection(self.db_path) as connection:
            return _transition_by_id(connection, transition_id)

    def get_claim(self, mission_id: str) -> MissionClaimRecord:
        _require_mission_id(mission_id)
        with _mission_connection(self.db_path) as connection:
            return _claim_by_mission(connection, mission_id)

    def list_admitted(self, *, limit: int = 50) -> list[JsonObject]:
        bounded_limit = max(1, min(limit, 200))
        with _mission_connection(self.db_path) as connection:
            rows = connection.execute(
                f"""
                {_MISSION_SELECT}
                WHERE lifecycle_state != ?
                ORDER BY updated_at DESC, mission_id ASC LIMIT ?
                """,
                (MISSION_UNADMITTED, bounded_limit),
            ).fetchall()
        return [_mission_from_row(row).safe_summary() for row in rows]

    def operator_summary(
        self,
        mission_id: str,
        *,
        agent_runs: list[JsonObject] | None = None,
    ) -> JsonObject:
        """Return a validated, read-only projection for Command Center.

        The projection keeps Gateway lifecycle, Node delivery, runner reports, and
        governed Agent Runs on separate axes. It never treats correlation as proof
        that a runner started or that provider inference is known.
        """

        _require_mission_id(mission_id)
        _verify_mission_audit_chain(self.db_path, self.audit_jsonl_path)
        with _mission_connection(self.db_path) as connection:
            mission = _mission_by_id(connection, mission_id)
            if mission.lifecycle_state == MISSION_UNADMITTED:
                raise MissionNotFoundError("unknown mission")
            claim = _claim_by_mission_optional(connection, mission_id)
            transitions = [
                transition
                for transition in _validated_transitions(connection)
                if transition.mission_id == mission_id
            ]
            receipts = [
                receipt
                for receipt in _validated_report_receipts(connection)
                if receipt.report.mission_id == mission_id
            ]
            _verify_operator_lifecycle_chain(mission, transitions)
            _verify_operator_transition_audit_events(
                connection,
                mission=mission,
                claim=claim,
                transitions=transitions,
            )

        transition_summaries = [transition.safe_summary() for transition in transitions]
        receipt_summaries = [receipt.safe_summary() for receipt in receipts]
        evidence_incomplete = any(
            transition.evidence_status != EVIDENCE_COMPLETE for transition in transitions
        ) or any(receipt.evidence_status != EVIDENCE_COMPLETE for receipt in receipts)
        quarantined = [
            receipt for receipt in receipts if receipt.receipt_disposition == "quarantined"
        ]
        report_conflicts = [
            receipt
            for receipt in quarantined
            if _quarantined_receipt_conflicts_with_mission(receipt, mission)
        ]
        lifecycle_receipts = [
            receipt
            for receipt in receipts
            if receipt.evidence_status == EVIDENCE_COMPLETE
            and receipt.receipt_disposition == "lifecycle_advancing"
        ]
        latest_runner_report = lifecycle_receipts[-1].safe_summary() if lifecycle_receipts else None
        cancellation_transition = next(
            (
                transition
                for transition in reversed(transitions)
                if transition.transition_kind == MISSION_CANCELLATION_TRANSITION_KIND
            ),
            None,
        )
        cancellation_observation = next(
            (
                receipt
                for receipt in reversed(receipts)
                if receipt.report.report_kind == "cancel_observed"
                and receipt.evidence_status == EVIDENCE_COMPLETE
                and receipt.receipt_disposition == "lifecycle_advancing"
            ),
            None,
        )
        runner_cancellation = next(
            (
                receipt
                for receipt in reversed(receipts)
                if receipt.report.report_kind == "runner_canceled"
                and receipt.evidence_status == EVIDENCE_COMPLETE
                and receipt.receipt_disposition == "lifecycle_advancing"
            ),
            None,
        )
        correlated_runs, rejected_correlations = _correlated_agent_runs(
            mission,
            claim,
            agent_runs or [],
        )
        attention_codes: list[str] = []
        if evidence_incomplete:
            attention_codes.append("evidence_incomplete")
        if (
            mission.lifecycle_state == MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
            or (claim is not None and claim.claim_status == "expired_review_required")
            or any(
                receipt.receipt_posture.get("quarantine_reason_code") == "claim_expired"
                for receipt in receipts
            )
        ):
            attention_codes.append("claim_expiry")
        if quarantined:
            attention_codes.append("quarantine")
        if report_conflicts:
            attention_codes.append("report_conflict")
        if rejected_correlations:
            attention_codes.append("agent_run_correlation_mismatch")

        return {
            **mission.safe_summary(),
            "delivery": {
                "authority": "gateway_node_claim",
                "state": _mission_delivery_state(claim),
                "claim": claim.safe_summary() if claim is not None else None,
            },
            "evidence": {
                "authority": "gateway_audit_binding",
                "state": "evidence_incomplete" if evidence_incomplete else "complete",
                "transitions": cast(JsonValue, transition_summaries),
            },
            "runner_reports": {
                "authority": "runner_reported_through_authenticated_node",
                "latest": latest_runner_report,
                "receipts": cast(JsonValue, receipt_summaries),
                "quarantined_count": len(quarantined),
                "report_conflict_count": len(report_conflicts),
            },
            "governed_agent_runs": {
                "authority": "gateway_agent_run_evidence",
                "correlation_basis": "gateway_validated_claim_session",
                "count": len(correlated_runs),
                "runs": cast(JsonValue, correlated_runs),
                "rejected_correlation_count": len(rejected_correlations),
            },
            "cancellation": {
                "authority": "gateway_decision_and_runner_reported_observation",
                "recorded": cancellation_transition is not None
                and cancellation_transition.evidence_status == EVIDENCE_COMPLETE,
                "observed_by_node": cancellation_observation is not None,
                "runner_reported_canceled": runner_cancellation is not None,
                "runner_process_stop_proven": False,
            },
            "attention_codes": cast(JsonValue, attention_codes),
            "model_provider": {
                "state": "unknown",
                "authority": "external_runner_or_provider",
                "inference_known": False,
                "output_verified": False,
            },
        }

    def list_operator_summaries(
        self,
        *,
        limit: int = 50,
        agent_runs: list[JsonObject] | None = None,
    ) -> list[JsonObject]:
        return [
            self.operator_summary(
                cast(str, mission["mission_id"]),
                agent_runs=agent_runs,
            )
            for mission in self.list_admitted(limit=limit)
        ]

    def governed_run_mission_binding(
        self,
        *,
        node_id: str,
        session_id: str,
        now: datetime | None = None,
    ) -> JsonObject | None:
        """Resolve a closed Node session label to an active Gateway claim.

        Non-mission sessions remain ordinary Node governed-access sessions. A
        mission-shaped session must match the stored mission, claim, envelope,
        authenticated Node, and active control state or it fails closed.
        """

        match = _MISSION_RUN_SESSION_PATTERN.fullmatch(session_id)
        if match is None:
            if session_id.startswith("mission:"):
                raise MissionConflictError("mission governed-run session binding conflicts")
            return None
        mission_id, claim_id, envelope_prefix = match.groups()
        _require_node_id(node_id)
        _verify_mission_audit_chain(self.db_path, self.audit_jsonl_path)
        with _mission_connection(self.db_path) as connection:
            mission = _mission_by_id(connection, mission_id)
            claim = _claim_by_mission(connection, mission_id)
            transitions = [
                transition
                for transition in _validated_transitions(connection)
                if transition.mission_id == mission_id
            ]
            receipts = [
                receipt
                for receipt in _validated_report_receipts(connection)
                if receipt.report.mission_id == mission_id
            ]
            _verify_operator_lifecycle_chain(mission, transitions)
            _verify_operator_transition_audit_events(
                connection,
                mission=mission,
                claim=claim,
                transitions=transitions,
            )
            if any(
                transition.evidence_status != EVIDENCE_COMPLETE for transition in transitions
            ) or any(receipt.evidence_status != EVIDENCE_COMPLETE for receipt in receipts):
                raise MissionConflictError(
                    "mission governed-run evidence requires operator recovery"
                )
        try:
            claim_expires_at = datetime.fromisoformat(claim.expires_at)
        except ValueError as exc:
            raise MissionError("stored mission claim expiry is invalid") from exc
        effective_now = now or datetime.now(UTC)
        if (
            mission.lifecycle_state
            not in {
                MISSION_CLAIMED,
                MISSION_RUNNER_REPORTED_RUNNING,
            }
            or claim.claim_status != "delivered"
            or claim_expires_at.tzinfo is None
            or (mission.lifecycle_state == MISSION_CLAIMED and effective_now >= claim_expires_at)
            or mission.target_node_id != node_id
            or claim.node_id != node_id
            or claim.claim_id != claim_id
            or mission.envelope_digest.removeprefix("sha256:")[:16] != envelope_prefix
        ):
            raise MissionConflictError("mission governed-run session binding conflicts")
        return {
            "mission_id": mission.mission_id,
            "mission_claim_id": claim.claim_id,
            "mission_envelope_digest": mission.envelope_digest,
            "mission_binding_source": "gateway_validated_claim_session",
        }


def mission_admission_request_digest(
    payload: MissionAdmissionPayload,
    *,
    authority: MissionAuthoritySnapshot,
) -> str:
    requester = authority.requesting_principal
    return sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "requester_principal_id": requester.principal_id,
            "requester_identity_generation": requester.identity_generation,
            "client_request_id": payload.client_request_id,
            "request": payload.safe_payload(),
            "authority_snapshot_hash": authority.canonical_hash(),
        }
    )


def mission_cancellation_request_digest(
    *,
    mission: MissionRecord,
    payload: MissionCancellationPayload,
    requester: AdminPrincipalContext,
    prior_lifecycle_state: str,
    prior_lifecycle_revision: int,
) -> str:
    return sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "requester_principal_id": requester.principal_id,
            "requester_identity_generation": requester.identity_generation,
            "client_request_id": payload.client_request_id,
            "mission_id": mission.mission_id,
            "envelope_digest": mission.envelope_digest,
            "prior_lifecycle_state": prior_lifecycle_state,
            "prior_lifecycle_revision": prior_lifecycle_revision,
            "requested_transition": (
                MISSION_CANCELED
                if prior_lifecycle_state == MISSION_QUEUED
                else MISSION_CANCEL_REQUESTED
            ),
        }
    )


def mission_claim_request_digest(
    *,
    mission: MissionRecord,
    payload: MissionClaimRequestPayload,
    claim_id: str,
    authority_snapshot_hash: str,
    expires_at: str,
    prior_lifecycle_state: str,
    prior_lifecycle_revision: int,
) -> str:
    if not _CLAIM_ID_PATTERN.fullmatch(claim_id):
        raise MissionConflictError("invalid mission claim ID")
    return sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "request": cast(JsonObject, payload.model_dump(mode="json")),
            "mission_id": mission.mission_id,
            "claim_id": claim_id,
            "envelope_digest": mission.envelope_digest,
            "prior_lifecycle_state": prior_lifecycle_state,
            "prior_lifecycle_revision": prior_lifecycle_revision,
            "authority_snapshot_hash": authority_snapshot_hash,
            "expires_at": expires_at,
            "requested_transition": MISSION_CLAIMED,
        }
    )


def mission_claim_expiry_request_digest(
    *,
    mission: MissionRecord,
    claim: MissionClaimRecord,
    prior_lifecycle_state: str,
    prior_lifecycle_revision: int,
) -> str:
    return sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "mission_id": mission.mission_id,
            "claim_id": claim.claim_id,
            "envelope_digest": claim.envelope_digest,
            "expires_at": claim.expires_at,
            "prior_lifecycle_state": prior_lifecycle_state,
            "prior_lifecycle_revision": prior_lifecycle_revision,
            "requested_transition": MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED,
        }
    )


def mission_report_request_digest(
    report: MissionRunnerReportPayload,
) -> str:
    return sha256_digest(cast(JsonObject, report.model_dump(mode="json")))


def mission_report_receipt_audit_metadata(
    receipt: MissionReportReceipt,
) -> JsonObject:
    report = receipt.report
    return {
        "report_id": report.report_id,
        "mission_id": report.mission_id,
        "claim_id": report.claim_id,
        "node_id": receipt.node_id,
        "verified_node_identity_key_id": receipt.verified_node_identity_key_id,
        "envelope_digest": report.envelope_digest,
        "expected_lifecycle_revision": report.expected_lifecycle_revision,
        "report_kind": report.report_kind,
        "outcome_code": report.outcome_code,
        "reason_code": report.reason_code,
        "artifact_digest": report.artifact_digest,
        "request_digest": receipt.request_digest,
        "proposed_disposition": receipt.receipt_posture["proposed_disposition"],
        "receipt_posture_digest": sha256_digest(receipt.receipt_posture),
        "staged_proposal_only": True,
        "runner_behavior_proven": False,
    }


def mission_report_transition_audit_metadata(
    transition: MissionTransitionAttempt,
) -> JsonObject:
    return {
        "transition_id": transition.transition_id,
        "mission_id": transition.mission_id,
        "transition_kind": transition.transition_kind,
        "prior_lifecycle_state": transition.prior_lifecycle_state,
        "prior_lifecycle_revision": transition.prior_lifecycle_revision,
        "proposed_lifecycle_state": transition.proposed_lifecycle_state,
        "proposed_lifecycle_revision": transition.proposed_lifecycle_revision,
        "request_digest": transition.request_digest,
        "safe_metadata": transition.safe_metadata,
        "staged_proposal_only": True,
        "runner_behavior_proven": False,
    }


def mission_transition_audit_metadata(
    transition: MissionTransitionAttempt,
    mission: MissionRecord,
) -> JsonObject:
    return {
        "transition_id": transition.transition_id,
        "mission_id": mission.mission_id,
        "transition_kind": transition.transition_kind,
        "prior_lifecycle_state": transition.prior_lifecycle_state,
        "prior_lifecycle_revision": transition.prior_lifecycle_revision,
        "proposed_lifecycle_state": transition.proposed_lifecycle_state,
        "proposed_lifecycle_revision": transition.proposed_lifecycle_revision,
        "request_digest": transition.request_digest,
        "evidence_status": EVIDENCE_PENDING,
        "target_node_id": mission.target_node_id,
        "workspace_id": mission.workspace_id,
        "mission_template_id": mission.mission_template_id,
        "authority_snapshot_hash": mission.authority_snapshot_hash,
        "envelope_digest": mission.envelope_digest,
        "staged_proposal_only": True,
        "runner_stop_proven": False,
        "model_provider_state_known": False,
    }


def mission_claim_transition_audit_metadata(
    transition: MissionTransitionAttempt,
    claim: MissionClaimRecord,
    mission: MissionRecord,
) -> JsonObject:
    return {
        "transition_id": transition.transition_id,
        "mission_id": mission.mission_id,
        "claim_id": claim.claim_id,
        "transition_kind": transition.transition_kind,
        "prior_lifecycle_state": transition.prior_lifecycle_state,
        "prior_lifecycle_revision": transition.prior_lifecycle_revision,
        "proposed_lifecycle_state": transition.proposed_lifecycle_state,
        "proposed_lifecycle_revision": transition.proposed_lifecycle_revision,
        "request_digest": transition.request_digest,
        "evidence_status": EVIDENCE_PENDING,
        "target_node_id": mission.target_node_id,
        "workspace_id": mission.workspace_id,
        "envelope_digest": mission.envelope_digest,
        "authority_snapshot_hash": claim.authority_snapshot_hash,
        "claim_expires_at": claim.expires_at,
        "staged_proposal_only": True,
        "runner_started_proven": False,
        "model_provider_state_known": False,
    }


def mission_claim_expiry_audit_metadata(
    transition: MissionTransitionAttempt,
    claim: MissionClaimRecord,
    mission: MissionRecord,
) -> JsonObject:
    return {
        "transition_id": transition.transition_id,
        "mission_id": mission.mission_id,
        "claim_id": claim.claim_id,
        "transition_kind": transition.transition_kind,
        "prior_lifecycle_state": transition.prior_lifecycle_state,
        "prior_lifecycle_revision": transition.prior_lifecycle_revision,
        "proposed_lifecycle_state": transition.proposed_lifecycle_state,
        "proposed_lifecycle_revision": transition.proposed_lifecycle_revision,
        "request_digest": transition.request_digest,
        "evidence_status": EVIDENCE_PENDING,
        "target_node_id": mission.target_node_id,
        "envelope_digest": mission.envelope_digest,
        "claim_expires_at": claim.expires_at,
        "staged_proposal_only": True,
        "automatic_requeue": False,
        "runner_state_authority": "runner_reported_only",
    }


def _mission_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def mission_envelope_digest(
    *,
    mission_id: str,
    payload: MissionAdmissionPayload,
    authority: MissionAuthoritySnapshot,
    authority_snapshot_hash: str,
) -> str:
    _require_mission_id(mission_id)
    return sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "mission_id": mission_id,
            "mission_template_id": authority.mission_template_id,
            "template_registry_generation": authority.template_registry_generation,
            "template_payload_digest": authority.template_payload_digest,
            "target_node_id": authority.target_node_id,
            "target_node_principal_id": authority.target_node_principal_id,
            "workspace_id": authority.workspace_id,
            "configuration_generation": authority.configuration_generation,
            "configuration_digest": authority.configuration_digest,
            "requested_timeout_seconds": payload.requested_timeout_seconds,
            "authority_snapshot_hash": authority_snapshot_hash,
        }
    )


_MISSION_SELECT = """
SELECT mission_id, requester_principal_id, requester_identity_generation,
       client_request_id, admission_request_digest, authority_snapshot_json,
       authority_snapshot_hash, target_node_id, target_node_principal_id,
       workspace_id, configuration_generation, configuration_digest,
       policy_digest, manifest_lock_digest, mission_template_id,
       template_registry_generation, template_payload_digest, envelope_digest,
       requested_timeout_seconds, lifecycle_state, lifecycle_revision,
       created_at, updated_at, admitted_at
FROM missions
"""

_TRANSITION_SELECT = """
SELECT transition_id, mission_id, transition_kind, prior_lifecycle_state,
       prior_lifecycle_revision, proposed_lifecycle_state,
       proposed_lifecycle_revision, request_digest, safe_metadata_json,
       evidence_status, audit_event_id, audit_event_hash, failure_reason_code,
       created_at, finalized_at
FROM mission_transition_attempts
"""

_CLAIM_SELECT = """
SELECT claim_id, mission_id, transition_id, node_id, node_identity_key_id,
       envelope_digest, authority_snapshot_json, authority_snapshot_hash,
       lifecycle_revision, claim_status, claimed_at, expires_at
FROM mission_claims
"""

_REPORT_RECEIPT_SELECT = """
SELECT report_id, mission_id, claim_id, node_id, verified_node_identity_key_id,
       envelope_digest, expected_lifecycle_revision, report_kind, outcome_code,
       reason_code, artifact_digest, request_digest, receipt_posture_json,
       receipt_disposition, evidence_status, audit_event_id, audit_event_hash,
       failure_reason_code, received_at, finalized_at
FROM mission_report_receipts
"""


def _mission_by_id(connection: sqlite3.Connection, mission_id: str) -> MissionRecord:
    row = connection.execute(f"{_MISSION_SELECT} WHERE mission_id = ?", (mission_id,)).fetchone()
    if row is None:
        raise MissionNotFoundError("unknown mission")
    return _mission_from_row(row)


def _mission_by_idempotency_namespace(
    connection: sqlite3.Connection,
    *,
    requester_principal_id: str,
    requester_identity_generation: str,
    client_request_id: str,
) -> MissionRecord | None:
    row = connection.execute(
        f"""
        {_MISSION_SELECT}
        WHERE requester_principal_id = ? AND requester_identity_generation = ?
              AND client_request_id = ?
        """,
        (requester_principal_id, requester_identity_generation, client_request_id),
    ).fetchone()
    return _mission_from_row(row) if row is not None else None


def _claim_by_mission_raw_optional(
    connection: sqlite3.Connection,
    mission_id: str,
) -> MissionClaimRecord | None:
    row = connection.execute(
        f"{_CLAIM_SELECT} WHERE mission_id = ?",
        (mission_id,),
    ).fetchone()
    return _claim_from_row(row) if row is not None else None


def _claim_by_mission_optional(
    connection: sqlite3.Connection,
    mission_id: str,
) -> MissionClaimRecord | None:
    claim = _claim_by_mission_raw_optional(connection, mission_id)
    if claim is None:
        return None
    try:
        _require_claim_authority_matches_mission(
            claim.authority_snapshot,
            _mission_by_id(connection, mission_id),
        )
    except MissionConflictError as exc:
        raise MissionError("stored mission claim authority is inconsistent") from exc
    _verify_claim_source_transition(connection, claim)
    return claim


def _claim_by_mission(
    connection: sqlite3.Connection,
    mission_id: str,
) -> MissionClaimRecord:
    claim = _claim_by_mission_optional(connection, mission_id)
    if claim is None:
        raise MissionNotFoundError("unknown mission claim")
    return claim


def _report_receipt_optional(
    connection: sqlite3.Connection,
    report_id: str,
) -> MissionReportReceipt | None:
    rows = connection.execute(f"{_REPORT_RECEIPT_SELECT} ORDER BY report_id ASC").fetchall()
    match: MissionReportReceipt | None = None
    for row in rows:
        receipt = _report_receipt_from_row(row)
        _verify_report_receipt_bindings(connection, receipt)
        if receipt.report.report_id == report_id:
            if match is not None:
                raise MissionError("stored mission report ID is duplicated")
            match = receipt
    return match


def _verify_report_receipt_bindings(
    connection: sqlite3.Connection,
    receipt: MissionReportReceipt,
) -> None:
    mission = _mission_by_id(connection, receipt.report.mission_id)
    claim = _claim_by_mission(connection, mission.mission_id)
    _require_report_matches_claim(
        receipt.report,
        mission=mission,
        claim=claim,
        node_id=receipt.node_id,
    )
    if receipt.request_digest != mission_report_request_digest(receipt.report):
        raise MissionError("stored mission report request digest is invalid")
    authenticated_posture = receipt.receipt_posture.get("authenticated_receipt")
    if (
        not isinstance(authenticated_posture, dict)
        or authenticated_posture.get("verified_node_identity_key_id")
        != receipt.verified_node_identity_key_id
    ):
        raise MissionError("stored mission report verified key binding is inconsistent")
    if receipt.evidence_status == EVIDENCE_COMPLETE:
        binding = connection.execute(
            """
            SELECT audit_event_hash, owner_kind, owner_id, request_digest
            FROM mission_audit_evidence_bindings WHERE audit_event_id = ?
            """,
            (receipt.audit_event_id,),
        ).fetchone()
        if binding != (
            receipt.audit_event_hash,
            "mission_report_receipt",
            receipt.report.report_id,
            receipt.request_digest,
        ):
            raise MissionError("stored mission report audit binding is inconsistent")
        event_row = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = ?",
            (receipt.audit_event_id,),
        ).fetchone()
        try:
            event_payload = json.loads(
                str(event_row[0]) if event_row is not None else "",
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise MissionError("stored mission report audit event is invalid") from exc
        if (
            not isinstance(event_payload, dict)
            or event_payload.get("event_id") != receipt.audit_event_id
            or event_payload.get("event_hash") != receipt.audit_event_hash
            or event_payload.get("event_type") != "mission.report_receipt.staged"
            or event_payload.get("input_hash") != receipt.request_digest
            or not isinstance(event_payload.get("principal"), dict)
            or event_payload["principal"].get("id") != mission.target_node_principal_id
            or event_payload.get("metadata") != mission_report_receipt_audit_metadata(receipt)
        ):
            raise MissionError("stored mission report audit event binding is inconsistent")


def _report_receipt(
    connection: sqlite3.Connection,
    report_id: str,
) -> MissionReportReceipt:
    receipt = _report_receipt_optional(connection, report_id)
    if receipt is None:
        raise MissionNotFoundError("unknown mission report")
    return receipt


def _report_receipt_from_row(
    row: sqlite3.Row | tuple[Any, ...],
) -> MissionReportReceipt:
    try:
        posture = json.loads(str(row[12]), object_pairs_hook=_reject_duplicate_keys)
        report = MissionRunnerReportPayload.model_validate(
            {
                "report_id": str(row[0]),
                "mission_id": str(row[1]),
                "claim_id": str(row[2]),
                "envelope_digest": str(row[5]),
                "expected_lifecycle_revision": int(row[6]),
                "report_kind": str(row[7]),
                "outcome_code": str(row[8]),
                "reason_code": str(row[9]) if row[9] is not None else None,
                "artifact_digest": str(row[10]) if row[10] is not None else None,
            }
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise MissionError("stored mission report receipt is invalid") from exc
    if (
        not isinstance(posture, dict)
        or "authenticated_receipt" not in posture
        or not _valid_report_authority_posture(posture["authenticated_receipt"])
        or not _valid_report_authority_posture(posture.get("proposed_advancement"))
        or posture.get("proposed_disposition") not in {"lifecycle_advancing", "quarantined"}
        or frozenset(posture)
        not in {
            frozenset(
                {
                    "authenticated_receipt",
                    "proposed_advancement",
                    "proposed_disposition",
                }
            ),
            frozenset(
                {
                    "authenticated_receipt",
                    "proposed_advancement",
                    "proposed_disposition",
                    "quarantine_reason_code",
                }
            ),
        }
        or (
            "quarantine_reason_code" in posture
            and posture["quarantine_reason_code"] is not None
            and (
                not isinstance(posture["quarantine_reason_code"], str)
                or not _SAFE_LABEL_PATTERN.fullmatch(posture["quarantine_reason_code"])
                or ".." in posture["quarantine_reason_code"]
            )
        )
    ):
        raise MissionError("stored mission report posture is invalid")
    receipt = MissionReportReceipt(
        report=report,
        node_id=str(row[3]),
        verified_node_identity_key_id=str(row[4]),
        request_digest=str(row[11]),
        receipt_posture=cast(JsonObject, posture),
        receipt_disposition=str(row[13]),
        evidence_status=str(row[14]),
        audit_event_id=str(row[15]) if row[15] is not None else None,
        audit_event_hash=str(row[16]) if row[16] is not None else None,
        failure_reason_code=str(row[17]) if row[17] is not None else None,
        received_at=str(row[18]),
        finalized_at=str(row[19]) if row[19] is not None else None,
    )
    if (
        not _NODE_ID_PATTERN.fullmatch(receipt.node_id)
        or not re.fullmatch(SHA256_PATTERN, receipt.verified_node_identity_key_id)
        or receipt.receipt_disposition
        not in {"pending", "lifecycle_advancing", "quarantined", "evidence_incomplete"}
        or receipt.evidence_status not in {EVIDENCE_PENDING, EVIDENCE_COMPLETE, EVIDENCE_INCOMPLETE}
        or (
            receipt.evidence_status == EVIDENCE_PENDING
            and (
                receipt.receipt_disposition != "pending"
                or receipt.audit_event_id is not None
                or receipt.finalized_at is not None
            )
        )
        or (
            receipt.evidence_status == EVIDENCE_COMPLETE
            and (
                receipt.receipt_disposition not in {"lifecycle_advancing", "quarantined"}
                or receipt.audit_event_id is None
                or receipt.audit_event_hash is None
                or receipt.finalized_at is None
                or receipt.receipt_posture.get("proposed_disposition")
                != receipt.receipt_disposition
            )
        )
        or (
            receipt.evidence_status == EVIDENCE_INCOMPLETE
            and (
                receipt.receipt_disposition != "evidence_incomplete"
                or receipt.failure_reason_code is None
                or receipt.finalized_at is None
            )
        )
    ):
        raise MissionError("stored mission report evidence state is invalid")
    return receipt


def _valid_report_authority_posture(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "node_status",
        "node_evidence_status",
        "verified_node_identity_key_id",
        "current_node_identity_key_id",
        "state",
        "reason_code",
    }:
        return False
    return (
        value.get("node_status") in {"enrolled", "revoked"}
        and value.get("node_evidence_status")
        in {EVIDENCE_PENDING, EVIDENCE_COMPLETE, EVIDENCE_INCOMPLETE}
        and isinstance(value.get("verified_node_identity_key_id"), str)
        and re.fullmatch(
            SHA256_PATTERN,
            cast(str, value["verified_node_identity_key_id"]),
        )
        is not None
        and isinstance(value.get("current_node_identity_key_id"), str)
        and re.fullmatch(
            SHA256_PATTERN,
            cast(str, value["current_node_identity_key_id"]),
        )
        is not None
        and value.get("state") in {"eligible", "quarantined"}
        and value.get("reason_code")
        in {
            "ready_read_only",
            "node_revoked",
            "posture_ineligible",
            "retired_key",
            "authority_drift",
            "claim_authority_invalid",
            "claim_expired",
            "identity_rotation_pending",
        }
    )


def _require_report_matches_claim(
    report: MissionRunnerReportPayload,
    *,
    mission: MissionRecord,
    claim: MissionClaimRecord,
    node_id: str,
) -> None:
    if (
        report.mission_id != mission.mission_id
        or report.claim_id != claim.claim_id
        or report.envelope_digest != mission.envelope_digest
        or claim.envelope_digest != mission.envelope_digest
        or node_id != mission.target_node_id
        or claim.node_id != node_id
    ):
        raise MissionConflictError("mission report does not match delivered claim")


def _mission_has_unresolved_transition(
    connection: sqlite3.Connection,
    mission_id: str,
) -> bool:
    try:
        transitions = _validated_transitions(connection)
    except MissionError as exc:
        raise MissionConflictError("mission transition evidence is invalid") from exc
    return any(
        transition.mission_id == mission_id
        and transition.evidence_status in {EVIDENCE_PENDING, EVIDENCE_INCOMPLETE}
        for transition in transitions
    )


def _mission_has_other_unresolved_report_receipt(
    connection: sqlite3.Connection,
    *,
    mission_id: str,
    report_id: str,
) -> bool:
    _report_receipt_optional(connection, report_id)
    return (
        connection.execute(
            """
            SELECT 1 FROM mission_report_receipts
            WHERE mission_id = ? AND report_id != ? AND evidence_status IN (?, ?)
            LIMIT 1
            """,
            (mission_id, report_id, EVIDENCE_PENDING, EVIDENCE_INCOMPLETE),
        ).fetchone()
        is not None
    )


def _has_complete_cancel_observation(
    connection: sqlite3.Connection,
    *,
    mission_id: str,
    claim_id: str,
    decision_revision: int,
) -> bool:
    _report_receipt_optional(connection, "")
    row = connection.execute(
        """
        SELECT report_id FROM mission_report_receipts
        WHERE mission_id = ? AND claim_id = ? AND report_kind = 'cancel_observed'
          AND expected_lifecycle_revision = ? AND evidence_status = ?
          AND receipt_disposition = 'lifecycle_advancing'
        ORDER BY received_at, report_id LIMIT 1
        """,
        (mission_id, claim_id, decision_revision, EVIDENCE_COMPLETE),
    ).fetchone()
    if row is None:
        return False
    receipt = _report_receipt(connection, str(row[0]))
    transition = _transition_for_mission_kind(
        connection,
        mission_id=mission_id,
        transition_kind=MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
    )
    if transition is None:
        raise MissionError("stored cancel observation transition is missing")
    if transition.evidence_status in {EVIDENCE_PENDING, EVIDENCE_INCOMPLETE}:
        return False
    if (
        transition.transition_kind != MISSION_CONTROL_OBSERVATION_TRANSITION_KIND
        or transition.evidence_status != EVIDENCE_COMPLETE
        or transition.prior_lifecycle_state != MISSION_CANCEL_REQUESTED
        or transition.prior_lifecycle_revision != decision_revision
        or transition.proposed_lifecycle_state != MISSION_CANCEL_REQUESTED
        or transition.proposed_lifecycle_revision != decision_revision + 1
        or transition.safe_metadata.get("report_id") != receipt.report.report_id
    ):
        raise MissionError("stored cancel observation transition is inconsistent")
    return True


def _report_proposed_state(
    connection: sqlite3.Connection,
    *,
    receipt: MissionReportReceipt | None = None,
    report: MissionRunnerReportPayload | None = None,
    mission: MissionRecord,
    claim: MissionClaimRecord,
    now: datetime,
) -> str | None:
    effective_report = receipt.report if receipt is not None else report
    if effective_report is None:  # pragma: no cover - internal call contract
        raise MissionError("mission report proposal is missing")
    try:
        expires_at = datetime.fromisoformat(claim.expires_at)
    except ValueError as exc:
        raise MissionError("stored mission claim expiry is invalid") from exc
    if expires_at.tzinfo is None or (
        mission.lifecycle_state == MISSION_CLAIMED and now >= expires_at
    ):
        return None
    exact_current_revision = (
        effective_report.expected_lifecycle_revision == mission.lifecycle_revision
    )
    cancellation = (
        _transition_for_mission_kind(
            connection,
            mission_id=mission.mission_id,
            transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
        )
        if mission.lifecycle_state == MISSION_CANCEL_REQUESTED
        else None
    )
    if effective_report.report_kind == "cancel_observed":
        if (
            cancellation is None
            or cancellation.evidence_status != EVIDENCE_COMPLETE
            or cancellation.proposed_lifecycle_state != MISSION_CANCEL_REQUESTED
            or mission.lifecycle_revision != cancellation.proposed_lifecycle_revision
            or effective_report.expected_lifecycle_revision
            != cancellation.proposed_lifecycle_revision
            or _has_complete_cancel_observation(
                connection,
                mission_id=mission.mission_id,
                claim_id=effective_report.claim_id,
                decision_revision=cancellation.proposed_lifecycle_revision,
            )
        ):
            return None
        return MISSION_CANCEL_REQUESTED
    cancellation_prior_revision = False
    if mission.lifecycle_state == MISSION_CANCEL_REQUESTED and effective_report.report_kind in {
        "runner_succeeded",
        "runner_failed",
    }:
        observation_advances_current_revision = (
            cancellation is not None
            and _has_complete_cancel_observation(
                connection,
                mission_id=mission.mission_id,
                claim_id=effective_report.claim_id,
                decision_revision=cancellation.proposed_lifecycle_revision,
            )
            and mission.lifecycle_revision == cancellation.proposed_lifecycle_revision + 1
        )
        cancellation_prior_revision = (
            cancellation is not None
            and cancellation.evidence_status == EVIDENCE_COMPLETE
            and cancellation.prior_lifecycle_state == MISSION_RUNNER_REPORTED_RUNNING
            and cancellation.proposed_lifecycle_state == MISSION_CANCEL_REQUESTED
            and (
                cancellation.proposed_lifecycle_revision == mission.lifecycle_revision
                or observation_advances_current_revision
            )
            and effective_report.expected_lifecycle_revision
            == cancellation.prior_lifecycle_revision
        )
    if not exact_current_revision and not cancellation_prior_revision:
        return None
    if effective_report.report_kind == "runner_running":
        return (
            MISSION_RUNNER_REPORTED_RUNNING if mission.lifecycle_state == MISSION_CLAIMED else None
        )
    if effective_report.report_kind == "runner_succeeded":
        return (
            MISSION_RUNNER_REPORTED_SUCCEEDED
            if mission.lifecycle_state
            in {MISSION_RUNNER_REPORTED_RUNNING, MISSION_CANCEL_REQUESTED}
            else None
        )
    if effective_report.report_kind == "runner_failed":
        return (
            MISSION_RUNNER_REPORTED_FAILED
            if mission.lifecycle_state
            in {MISSION_RUNNER_REPORTED_RUNNING, MISSION_CANCEL_REQUESTED}
            else None
        )
    if effective_report.report_kind == "runner_canceled":
        if mission.lifecycle_state != MISSION_CANCEL_REQUESTED or not exact_current_revision:
            return None
        if (
            cancellation is None
            or not _has_complete_cancel_observation(
                connection,
                mission_id=mission.mission_id,
                claim_id=effective_report.claim_id,
                decision_revision=cancellation.proposed_lifecycle_revision,
            )
            or mission.lifecycle_revision != cancellation.proposed_lifecycle_revision + 1
        ):
            return None
        return MISSION_RUNNER_REPORTED_CANCELED
    return None


def _report_lifecycle_quarantine_reason(
    connection: sqlite3.Connection,
    *,
    report: MissionRunnerReportPayload,
    mission: MissionRecord,
    claim: MissionClaimRecord,
    now: datetime,
) -> str:
    try:
        expires_at = datetime.fromisoformat(claim.expires_at)
    except ValueError as exc:
        raise MissionError("stored mission claim expiry is invalid") from exc
    if expires_at.tzinfo is None or (
        mission.lifecycle_state == MISSION_CLAIMED and now >= expires_at
    ):
        return "claim_expired"
    if report.report_kind == "cancel_observed":
        cancellation = _transition_for_mission_kind(
            connection,
            mission_id=mission.mission_id,
            transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
        )
        if (
            cancellation is not None
            and cancellation.evidence_status == EVIDENCE_COMPLETE
            and _has_complete_cancel_observation(
                connection,
                mission_id=mission.mission_id,
                claim_id=report.claim_id,
                decision_revision=cancellation.proposed_lifecycle_revision,
            )
        ):
            return "duplicate_observation"
    return "lifecycle_conflict"


def _insert_report_transition(
    connection: sqlite3.Connection,
    *,
    receipt: MissionReportReceipt,
    mission: MissionRecord,
    proposed_state: str,
    now_text: str,
) -> MissionTransitionAttempt:
    transition_id = f"mtransition_{uuid4().hex}"
    transition_kind = (
        MISSION_CONTROL_OBSERVATION_TRANSITION_KIND
        if receipt.report.report_kind == "cancel_observed"
        else MISSION_REPORT_TRANSITION_KIND
    )
    metadata: JsonObject = {
        "report_id": receipt.report.report_id,
        "claim_id": receipt.report.claim_id,
        "node_id": receipt.node_id,
        "verified_node_identity_key_id": receipt.verified_node_identity_key_id,
        "envelope_digest": receipt.report.envelope_digest,
        "report_kind": receipt.report.report_kind,
    }
    request_digest = sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "report_request_digest": receipt.request_digest,
            "prior_lifecycle_state": mission.lifecycle_state,
            "prior_lifecycle_revision": mission.lifecycle_revision,
            "proposed_lifecycle_state": proposed_state,
            "proposed_lifecycle_revision": mission.lifecycle_revision + 1,
        }
    )
    try:
        connection.execute(
            """
            INSERT INTO mission_transition_attempts (
                transition_id, mission_id, transition_kind,
                prior_lifecycle_state, prior_lifecycle_revision,
                proposed_lifecycle_state, proposed_lifecycle_revision,
                request_digest, safe_metadata_json, evidence_status,
                audit_event_id, audit_event_hash, failure_reason_code,
                created_at, finalized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, NULL)
            """,
            (
                transition_id,
                mission.mission_id,
                transition_kind,
                mission.lifecycle_state,
                mission.lifecycle_revision,
                proposed_state,
                mission.lifecycle_revision + 1,
                request_digest,
                canonical_json(metadata),
                EVIDENCE_PENDING,
                now_text,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise MissionConflictError("mission report transition conflicts") from exc
    row = connection.execute(
        f"{_TRANSITION_SELECT} WHERE transition_id = ?",
        (transition_id,),
    ).fetchone()
    if row is None:  # pragma: no cover - same-transaction insertion invariant
        raise MissionError("mission report transition insertion failed")
    return _transition_from_row(row)


def _transition_for_report_optional(
    connection: sqlite3.Connection,
    report_id: str,
) -> MissionTransitionAttempt | None:
    matches: list[MissionTransitionAttempt] = []
    for transition in _validated_transitions(connection):
        if (
            transition.transition_kind
            in {
                MISSION_REPORT_TRANSITION_KIND,
                MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
            }
            and transition.safe_metadata.get("report_id") == report_id
        ):
            matches.append(transition)
    if len(matches) > 1:
        raise MissionError("stored mission report has multiple lifecycle transitions")
    return matches[0] if matches else None


def _validated_transitions(
    connection: sqlite3.Connection,
) -> list[MissionTransitionAttempt]:
    rows = connection.execute(
        f"{_TRANSITION_SELECT} ORDER BY created_at, transition_id",
    ).fetchall()
    transitions: list[MissionTransitionAttempt] = []
    for row in rows:
        transition = _transition_from_row(row)
        _verify_transition_bindings(connection, transition)
        transitions.append(transition)
    return transitions


def _validated_report_receipts(
    connection: sqlite3.Connection,
) -> list[MissionReportReceipt]:
    rows = connection.execute(
        f"{_REPORT_RECEIPT_SELECT} ORDER BY received_at, report_id",
    ).fetchall()
    receipts: list[MissionReportReceipt] = []
    for row in rows:
        receipt = _report_receipt_from_row(row)
        _verify_report_receipt_bindings(connection, receipt)
        receipts.append(receipt)
    return receipts


def _mission_delivery_state(claim: MissionClaimRecord | None) -> str:
    if claim is None:
        return "not_claimed"
    return {
        "staged": "claim_pending_evidence",
        "delivered": "claim_delivered",
        "evidence_incomplete": "claim_evidence_incomplete",
        "expired_review_required": "claim_expired_review_required",
    }.get(claim.claim_status, "unknown")


def _quarantined_receipt_conflicts_with_mission(
    receipt: MissionReportReceipt,
    mission: MissionRecord,
) -> bool:
    del mission
    return receipt.receipt_posture.get("quarantine_reason_code") == "lifecycle_conflict"


def _verify_mission_audit_chain(db_path: Path, audit_jsonl_path: Path) -> None:
    """Require the canonical audit chain before trusting mission projections."""

    writer = AuditWriter(db_path, audit_jsonl_path)
    try:
        verification = writer.verify_chain()
    except AuditWriteError as exc:
        raise MissionError("stored mission audit chain is unavailable") from exc
    if not verification.valid:
        raise MissionError("stored mission audit chain is invalid")
    diagnostics = writer.diagnostics()
    lifecycle = diagnostics.get("lifecycle")
    if not isinstance(lifecycle, dict) or lifecycle.get("status") != "clean":
        raise MissionError("stored mission audit lifecycle requires recovery")


def _mission_audit_jsonl_path(db_path: Path) -> Path:
    """Resolve the configured colocated audit mirror for mission validation."""

    if db_path.parent.name == "db":
        return db_path.parent.parent / "logs/audit.jsonl"
    return db_path.with_name("audit.jsonl")


def _verify_operator_lifecycle_chain(
    mission: MissionRecord,
    transitions: list[MissionTransitionAttempt],
) -> None:
    complete = [
        transition for transition in transitions if transition.evidence_status == EVIDENCE_COMPLETE
    ]
    by_revision: dict[int, MissionTransitionAttempt] = {}
    for transition in complete:
        revision = transition.proposed_lifecycle_revision
        if revision in by_revision:
            raise MissionError("stored mission lifecycle revision is duplicated")
        by_revision[revision] = transition
    if set(by_revision) != set(range(1, mission.lifecycle_revision + 1)):
        raise MissionError("stored mission lifecycle evidence chain is incomplete")
    prior_state = MISSION_UNADMITTED
    for revision in range(1, mission.lifecycle_revision + 1):
        transition = by_revision[revision]
        if (
            transition.prior_lifecycle_revision != revision - 1
            or transition.prior_lifecycle_state != prior_state
            or transition.proposed_lifecycle_revision != revision
        ):
            raise MissionError("stored mission lifecycle evidence chain is inconsistent")
        if revision == 1 and transition.transition_kind != MISSION_ADMISSION_TRANSITION_KIND:
            raise MissionError("stored mission admission transition is missing")
        prior_state = transition.proposed_lifecycle_state
    if prior_state != mission.lifecycle_state:
        raise MissionError("stored mission lifecycle evidence does not match current state")


def _verify_operator_transition_audit_events(
    connection: sqlite3.Connection,
    *,
    mission: MissionRecord,
    claim: MissionClaimRecord | None,
    transitions: list[MissionTransitionAttempt],
) -> None:
    for transition in transitions:
        if transition.transition_kind == MISSION_ADMISSION_TRANSITION_KIND:
            event_type = "mission.admission.staged"
            metadata = mission_transition_audit_metadata(transition, mission)
            principal_id = mission.requester_principal_id
        elif transition.transition_kind == MISSION_CLAIM_TRANSITION_KIND:
            if claim is None:
                raise MissionError("stored mission claim transition has no claim")
            event_type = "mission.claim.staged"
            metadata = mission_claim_transition_audit_metadata(
                transition,
                claim,
                mission,
            )
            principal_id = mission.target_node_principal_id
        elif transition.transition_kind == MISSION_CLAIM_EXPIRY_TRANSITION_KIND:
            if claim is None:
                raise MissionError("stored mission claim expiry transition has no claim")
            event_type = "mission.claim_expiry.staged"
            metadata = mission_claim_expiry_audit_metadata(
                transition,
                claim,
                mission,
            )
            principal_id = "gateway:mission-expiry"
        else:
            continue
        _verify_bound_transition_evidence(
            connection,
            transition,
            expected_event_type=event_type,
            expected_metadata=metadata,
            expected_principal_id=principal_id,
        )


def _correlated_agent_runs(
    mission: MissionRecord,
    claim: MissionClaimRecord | None,
    agent_runs: list[JsonObject],
) -> tuple[list[JsonObject], list[JsonObject]]:
    correlated: list[JsonObject] = []
    rejected: list[JsonObject] = []
    for run in agent_runs:
        metadata = run.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("mission_id") != mission.mission_id:
            continue
        safe_reference: JsonObject = {
            "run_id": run.get("run_id"),
            "principal_id": run.get("principal_id"),
            "workspace_id": run.get("workspace_id"),
            "status": run.get("status"),
            "tool_call_count": run.get("tool_call_count"),
            "updated_at": run.get("updated_at"),
        }
        if (
            claim is not None
            and metadata.get("ingress_kind") == "node_governed_access"
            and metadata.get("identity_source") == "gateway_derived_node"
            and metadata.get("node_id") == mission.target_node_id
            and metadata.get("mission_claim_id") == claim.claim_id
            and metadata.get("mission_envelope_digest") == mission.envelope_digest
            and metadata.get("mission_binding_source") == "gateway_validated_claim_session"
            and run.get("principal_id") == mission.target_node_principal_id
            and run.get("workspace_id") == mission.workspace_id
        ):
            correlated.append(safe_reference)
        else:
            rejected.append(safe_reference)
    return correlated, rejected


def _node_has_blocking_claim(
    connection: sqlite3.Connection,
    node_id: str,
) -> bool:
    rows = connection.execute(
        "SELECT mission_id FROM mission_claims ORDER BY mission_id ASC"
    ).fetchall()
    for row in rows:
        mission = _mission_by_id(connection, str(row[0]))
        claim = _claim_by_mission(connection, mission.mission_id)
        if claim.node_id != node_id:
            continue
        if claim.claim_status in {
            "staged",
            "evidence_incomplete",
            "expired_review_required",
        } or mission.lifecycle_state in {
            MISSION_CLAIMED,
            "runner_reported_running",
            "cancel_requested",
            MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED,
        }:
            return True
    return False


def _admission_transition_for_mission(
    connection: sqlite3.Connection, mission_id: str
) -> MissionTransitionAttempt:
    row = connection.execute(
        f"{_TRANSITION_SELECT} WHERE mission_id = ? AND transition_kind = ?",
        (mission_id, MISSION_ADMISSION_TRANSITION_KIND),
    ).fetchone()
    if row is None:
        raise MissionConflictError("mission admission transition is missing")
    transition = _transition_from_row(row)
    _verify_admission_transition_bindings(connection, transition)
    return transition


def _transition_for_mission_kind(
    connection: sqlite3.Connection,
    *,
    mission_id: str,
    transition_kind: str,
) -> MissionTransitionAttempt | None:
    row = connection.execute(
        f"{_TRANSITION_SELECT} WHERE mission_id = ? AND transition_kind = ?",
        (mission_id, transition_kind),
    ).fetchone()
    if row is None:
        return None
    transition = _transition_from_row(row)
    _verify_transition_bindings(connection, transition)
    return transition


def _transition_by_id(
    connection: sqlite3.Connection, transition_id: str
) -> MissionTransitionAttempt:
    row = connection.execute(
        f"{_TRANSITION_SELECT} WHERE transition_id = ?", (transition_id,)
    ).fetchone()
    if row is None:
        raise MissionNotFoundError("unknown mission transition")
    transition = _transition_from_row(row)
    _verify_transition_bindings(connection, transition)
    return transition


def _verify_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    if transition.transition_kind == MISSION_ADMISSION_TRANSITION_KIND:
        _verify_admission_transition_bindings(connection, transition)
        _verify_transition_evidence_record(connection, transition)
    elif transition.transition_kind == MISSION_CLAIM_TRANSITION_KIND:
        _verify_claim_transition_bindings(connection, transition)
        _verify_transition_evidence_record(connection, transition)
    elif transition.transition_kind == MISSION_CLAIM_EXPIRY_TRANSITION_KIND:
        _verify_claim_expiry_transition_bindings(connection, transition)
        _verify_transition_evidence_record(connection, transition)
    elif transition.transition_kind in {
        MISSION_REPORT_TRANSITION_KIND,
        MISSION_CONTROL_OBSERVATION_TRANSITION_KIND,
    }:
        _verify_report_transition_bindings(connection, transition)
        _verify_bound_transition_evidence(
            connection,
            transition,
            expected_event_type=(
                "mission.control_observation.staged"
                if transition.transition_kind == MISSION_CONTROL_OBSERVATION_TRANSITION_KIND
                else "mission.report_transition.staged"
            ),
            expected_metadata=mission_report_transition_audit_metadata(transition),
            expected_principal_id=_mission_by_id(
                connection, transition.mission_id
            ).target_node_principal_id,
        )
    elif transition.transition_kind == MISSION_CANCELLATION_TRANSITION_KIND:
        _verify_cancellation_transition_bindings(connection, transition)
        _verify_bound_transition_evidence(
            connection,
            transition,
            expected_event_type="mission.cancellation.staged",
            expected_metadata=mission_transition_audit_metadata(
                transition,
                _mission_by_id(connection, transition.mission_id),
            ),
            expected_principal_id=str(transition.safe_metadata["requester_principal_id"]),
        )
    else:
        raise MissionError("stored mission transition kind is unsupported")


def _mission_from_row(row: sqlite3.Row | tuple[Any, ...]) -> MissionRecord:
    try:
        authority_raw = json.loads(
            str(row[5]),
            object_pairs_hook=_reject_duplicate_keys,
        )
        authority = MissionAuthoritySnapshot.model_validate(authority_raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise MissionError("stored mission authority snapshot is invalid") from exc
    if authority.canonical_hash() != str(row[6]):
        raise MissionError("stored mission authority snapshot hash is invalid")
    record = MissionRecord(
        mission_id=str(row[0]),
        requester_principal_id=str(row[1]),
        requester_identity_generation=str(row[2]),
        client_request_id=str(row[3]),
        admission_request_digest=str(row[4]),
        authority_snapshot=authority,
        authority_snapshot_hash=str(row[6]),
        target_node_id=str(row[7]),
        target_node_principal_id=str(row[8]),
        workspace_id=str(row[9]),
        configuration_generation=int(row[10]),
        configuration_digest=str(row[11]),
        policy_digest=str(row[12]),
        manifest_lock_digest=str(row[13]),
        mission_template_id=str(row[14]),
        template_registry_generation=str(row[15]),
        template_payload_digest=str(row[16]),
        envelope_digest=str(row[17]),
        requested_timeout_seconds=int(row[18]),
        lifecycle_state=str(row[19]),
        lifecycle_revision=int(row[20]),
        created_at=str(row[21]),
        updated_at=str(row[22]),
        admitted_at=str(row[23]) if row[23] is not None else None,
    )
    _verify_stored_mission_bindings(record)
    return record


def _transition_from_row(row: sqlite3.Row | tuple[Any, ...]) -> MissionTransitionAttempt:
    try:
        metadata = json.loads(
            str(row[8]),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise MissionError("stored mission transition metadata is invalid") from exc
    transition_kind = str(row[2])
    expected_metadata_fields = {
        MISSION_ADMISSION_TRANSITION_KIND: {
            "mission_template_id",
            "target_node_id",
            "workspace_id",
            "envelope_digest",
        },
        MISSION_CANCELLATION_TRANSITION_KIND: {
            "requester_principal_id",
            "requester_identity_generation",
            "client_request_id",
            "mission_template_id",
            "target_node_id",
            "workspace_id",
            "envelope_digest",
        },
        MISSION_CLAIM_TRANSITION_KIND: {
            "claim_id",
            "node_id",
            "node_identity_key_id",
            "envelope_digest",
            "authority_snapshot_hash",
            "expires_at",
        },
        MISSION_CLAIM_EXPIRY_TRANSITION_KIND: {
            "claim_id",
            "node_id",
            "envelope_digest",
            "expires_at",
        },
        MISSION_REPORT_TRANSITION_KIND: {
            "report_id",
            "claim_id",
            "node_id",
            "verified_node_identity_key_id",
            "envelope_digest",
            "report_kind",
        },
        MISSION_CONTROL_OBSERVATION_TRANSITION_KIND: {
            "report_id",
            "claim_id",
            "node_id",
            "verified_node_identity_key_id",
            "envelope_digest",
            "report_kind",
        },
    }.get(transition_kind)
    if (
        not isinstance(metadata, dict)
        or expected_metadata_fields is None
        or set(metadata) != expected_metadata_fields
    ):
        raise MissionError("stored mission transition metadata is invalid")
    return MissionTransitionAttempt(
        transition_id=str(row[0]),
        mission_id=str(row[1]),
        transition_kind=transition_kind,
        prior_lifecycle_state=str(row[3]),
        prior_lifecycle_revision=int(row[4]),
        proposed_lifecycle_state=str(row[5]),
        proposed_lifecycle_revision=int(row[6]),
        request_digest=str(row[7]),
        safe_metadata=cast(JsonObject, metadata),
        evidence_status=str(row[9]),
        audit_event_id=str(row[10]) if row[10] is not None else None,
        audit_event_hash=str(row[11]) if row[11] is not None else None,
        failure_reason_code=str(row[12]) if row[12] is not None else None,
        created_at=str(row[13]),
        finalized_at=str(row[14]) if row[14] is not None else None,
    )


def _claim_from_row(row: sqlite3.Row | tuple[Any, ...]) -> MissionClaimRecord:
    try:
        authority_raw = json.loads(
            str(row[6]),
            object_pairs_hook=_reject_duplicate_keys,
        )
        authority = MissionClaimAuthoritySnapshot.model_validate(authority_raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise MissionError("stored mission claim authority snapshot is invalid") from exc
    record = MissionClaimRecord(
        claim_id=str(row[0]),
        mission_id=str(row[1]),
        transition_id=str(row[2]),
        node_id=str(row[3]),
        node_identity_key_id=str(row[4]),
        envelope_digest=str(row[5]),
        authority_snapshot=authority,
        authority_snapshot_hash=str(row[7]),
        lifecycle_revision=int(row[8]),
        claim_status=str(row[9]),
        claimed_at=str(row[10]),
        expires_at=str(row[11]),
    )
    if authority.canonical_hash() != record.authority_snapshot_hash:
        raise MissionError("stored mission claim authority snapshot hash is invalid")
    expected_bindings: tuple[tuple[object, object], ...] = (
        (record.mission_id, authority.mission_id),
        (record.node_id, authority.target_node_id),
        (record.node_identity_key_id, authority.node_identity_key_id),
        (record.envelope_digest, authority.envelope_digest),
    )
    if any(stored != expected for stored, expected in expected_bindings):
        raise MissionError("stored mission claim authority bindings are inconsistent")
    return record


def _verify_stored_mission_bindings(record: MissionRecord) -> None:
    authority = record.authority_snapshot
    requester = authority.requesting_principal
    expected_bindings: tuple[tuple[object, object], ...] = (
        (record.requester_principal_id, requester.principal_id),
        (record.requester_identity_generation, requester.identity_generation),
        (record.target_node_id, authority.target_node_id),
        (record.target_node_principal_id, authority.target_node_principal_id),
        (record.workspace_id, authority.workspace_id),
        (record.configuration_generation, authority.configuration_generation),
        (record.configuration_digest, authority.configuration_digest),
        (record.policy_digest, authority.policy_digest),
        (record.manifest_lock_digest, authority.manifest_lock_digest),
        (record.mission_template_id, authority.mission_template_id),
        (record.template_registry_generation, authority.template_registry_generation),
        (record.template_payload_digest, authority.template_payload_digest),
    )
    if any(stored != expected for stored, expected in expected_bindings):
        raise MissionError("stored mission authority bindings are inconsistent")
    try:
        payload = MissionAdmissionPayload(
            target_node_id=record.target_node_id,
            mission_template_id=MISSION_TEMPLATE_ID,
            requested_timeout_seconds=record.requested_timeout_seconds,
            client_request_id=record.client_request_id,
        )
    except ValueError as exc:
        raise MissionError("stored mission admission request is invalid") from exc
    if record.admission_request_digest != mission_admission_request_digest(
        payload,
        authority=authority,
    ):
        raise MissionError("stored mission admission request digest is invalid")
    if record.envelope_digest != mission_envelope_digest(
        mission_id=record.mission_id,
        payload=payload,
        authority=authority,
        authority_snapshot_hash=record.authority_snapshot_hash,
    ):
        raise MissionError("stored mission envelope digest is invalid")


def _verify_admission_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    mission = _mission_by_id(connection, transition.mission_id)
    if (
        transition.prior_lifecycle_state != MISSION_UNADMITTED
        or transition.prior_lifecycle_revision != 0
        or transition.proposed_lifecycle_state != MISSION_QUEUED
        or transition.proposed_lifecycle_revision != 1
        or transition.request_digest != mission.admission_request_digest
        or transition.safe_metadata
        != {
            "mission_template_id": mission.mission_template_id,
            "target_node_id": mission.target_node_id,
            "workspace_id": mission.workspace_id,
            "envelope_digest": mission.envelope_digest,
        }
    ):
        raise MissionError("stored mission admission transition bindings are inconsistent")


def _verify_claim_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    mission = _mission_by_id(connection, transition.mission_id)
    claim = _claim_by_mission_raw_optional(connection, transition.mission_id)
    if claim is None:
        raise MissionError("stored mission claim transition has no claim")
    _verify_claim_transition_records(connection, transition, mission, claim)


def _verify_claim_source_transition(
    connection: sqlite3.Connection,
    claim: MissionClaimRecord,
) -> None:
    row = connection.execute(
        f"{_TRANSITION_SELECT} WHERE transition_id = ?",
        (claim.transition_id,),
    ).fetchone()
    if row is None:
        raise MissionError("stored mission claim transition is missing")
    transition = _transition_from_row(row)
    mission = _mission_by_id(connection, claim.mission_id)
    _verify_claim_transition_records(connection, transition, mission, claim)


def _verify_claim_transition_records(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
    mission: MissionRecord,
    claim: MissionClaimRecord,
) -> None:
    authority = claim.authority_snapshot
    try:
        _require_claim_authority_matches_mission(authority, mission)
    except MissionConflictError as exc:
        raise MissionError("stored mission claim authority is inconsistent") from exc
    if transition.evidence_status == EVIDENCE_COMPLETE:
        claim_status_matches = claim.claim_status == "delivered"
        if claim.claim_status == "expired_review_required":
            expiry_row = connection.execute(
                """
                SELECT evidence_status FROM mission_transition_attempts
                WHERE mission_id = ? AND transition_kind = ?
                """,
                (mission.mission_id, MISSION_CLAIM_EXPIRY_TRANSITION_KIND),
            ).fetchone()
            claim_status_matches = (
                mission.lifecycle_state == MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
                and expiry_row == (EVIDENCE_COMPLETE,)
            )
    else:
        expected_claim_status = {
            EVIDENCE_PENDING: "staged",
            EVIDENCE_INCOMPLETE: "evidence_incomplete",
        }.get(transition.evidence_status)
        claim_status_matches = claim.claim_status == expected_claim_status
    expected_metadata = {
        "claim_id": claim.claim_id,
        "node_id": claim.node_id,
        "node_identity_key_id": claim.node_identity_key_id,
        "envelope_digest": claim.envelope_digest,
        "authority_snapshot_hash": claim.authority_snapshot_hash,
        "expires_at": claim.expires_at,
    }
    try:
        claimed_at = datetime.fromisoformat(claim.claimed_at)
        expires_at = datetime.fromisoformat(claim.expires_at)
    except ValueError as exc:
        raise MissionError("stored mission claim timestamps are invalid") from exc
    if (
        transition.transition_kind != MISSION_CLAIM_TRANSITION_KIND
        or transition.prior_lifecycle_state != MISSION_QUEUED
        or transition.proposed_lifecycle_state != MISSION_CLAIMED
        or transition.proposed_lifecycle_revision != transition.prior_lifecycle_revision + 1
        or claim.transition_id != transition.transition_id
        or claim.lifecycle_revision != transition.proposed_lifecycle_revision
        or not claim_status_matches
        or claimed_at.tzinfo is None
        or expires_at.tzinfo is None
        or expires_at <= claimed_at
        or transition.safe_metadata != expected_metadata
        or transition.request_digest
        != mission_claim_request_digest(
            mission=mission,
            payload=MissionClaimRequestPayload(protocol_version="1"),
            claim_id=claim.claim_id,
            authority_snapshot_hash=claim.authority_snapshot_hash,
            expires_at=claim.expires_at,
            prior_lifecycle_state=transition.prior_lifecycle_state,
            prior_lifecycle_revision=transition.prior_lifecycle_revision,
        )
    ):
        raise MissionError("stored mission claim transition bindings are inconsistent")


def _verify_claim_expiry_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    mission = _mission_by_id(connection, transition.mission_id)
    claim = _claim_by_mission(connection, transition.mission_id)
    expected_claim_status = (
        "expired_review_required"
        if transition.evidence_status == EVIDENCE_COMPLETE
        else "delivered"
    )
    expected_metadata = {
        "claim_id": claim.claim_id,
        "node_id": claim.node_id,
        "envelope_digest": claim.envelope_digest,
        "expires_at": claim.expires_at,
    }
    if (
        transition.transition_kind != MISSION_CLAIM_EXPIRY_TRANSITION_KIND
        or transition.prior_lifecycle_state != MISSION_CLAIMED
        or transition.proposed_lifecycle_state != MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
        or transition.proposed_lifecycle_revision != transition.prior_lifecycle_revision + 1
        or claim.claim_status != expected_claim_status
        or transition.safe_metadata != expected_metadata
        or transition.request_digest
        != mission_claim_expiry_request_digest(
            mission=mission,
            claim=claim,
            prior_lifecycle_state=transition.prior_lifecycle_state,
            prior_lifecycle_revision=transition.prior_lifecycle_revision,
        )
    ):
        raise MissionError("stored mission claim expiry bindings are inconsistent")


def _verify_report_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    metadata = transition.safe_metadata
    report_id = metadata.get("report_id")
    if not isinstance(report_id, str):
        raise MissionError("stored mission report transition metadata is invalid")
    receipt = _report_receipt(connection, report_id)
    report = receipt.report
    mission = _mission_by_id(connection, transition.mission_id)
    expected_proposed_state = {
        (MISSION_CLAIMED, "runner_running"): MISSION_RUNNER_REPORTED_RUNNING,
        (
            MISSION_RUNNER_REPORTED_RUNNING,
            "runner_succeeded",
        ): MISSION_RUNNER_REPORTED_SUCCEEDED,
        (MISSION_CANCEL_REQUESTED, "runner_succeeded"): MISSION_RUNNER_REPORTED_SUCCEEDED,
        (
            MISSION_RUNNER_REPORTED_RUNNING,
            "runner_failed",
        ): MISSION_RUNNER_REPORTED_FAILED,
        (MISSION_CANCEL_REQUESTED, "runner_failed"): MISSION_RUNNER_REPORTED_FAILED,
        (MISSION_CANCEL_REQUESTED, "runner_canceled"): MISSION_RUNNER_REPORTED_CANCELED,
        (MISSION_CANCEL_REQUESTED, "cancel_observed"): MISSION_CANCEL_REQUESTED,
    }.get((transition.prior_lifecycle_state, report.report_kind))
    expected_metadata = {
        "report_id": report.report_id,
        "claim_id": report.claim_id,
        "node_id": receipt.node_id,
        "verified_node_identity_key_id": receipt.verified_node_identity_key_id,
        "envelope_digest": report.envelope_digest,
        "report_kind": report.report_kind,
    }
    expected_digest = sha256_digest(
        {
            "schema_version": MISSION_AUTHORITY_SCHEMA_VERSION,
            "report_request_digest": receipt.request_digest,
            "prior_lifecycle_state": transition.prior_lifecycle_state,
            "prior_lifecycle_revision": transition.prior_lifecycle_revision,
            "proposed_lifecycle_state": transition.proposed_lifecycle_state,
            "proposed_lifecycle_revision": transition.proposed_lifecycle_revision,
        }
    )
    report_revision_matches = (
        report.expected_lifecycle_revision == transition.prior_lifecycle_revision
    )
    if (
        not report_revision_matches
        and transition.prior_lifecycle_state == MISSION_CANCEL_REQUESTED
        and report.report_kind in {"runner_succeeded", "runner_failed"}
    ):
        cancellation = _transition_for_mission_kind(
            connection,
            mission_id=mission.mission_id,
            transition_kind=MISSION_CANCELLATION_TRANSITION_KIND,
        )
        report_revision_matches = (
            cancellation is not None
            and cancellation.evidence_status == EVIDENCE_COMPLETE
            and cancellation.prior_lifecycle_state == MISSION_RUNNER_REPORTED_RUNNING
            and (
                cancellation.proposed_lifecycle_revision == transition.prior_lifecycle_revision
                or (
                    _has_complete_cancel_observation(
                        connection,
                        mission_id=mission.mission_id,
                        claim_id=report.claim_id,
                        decision_revision=cancellation.proposed_lifecycle_revision,
                    )
                    and transition.prior_lifecycle_revision
                    == cancellation.proposed_lifecycle_revision + 1
                )
            )
            and report.expected_lifecycle_revision == cancellation.prior_lifecycle_revision
        )
    if (
        transition.transition_kind
        != (
            MISSION_CONTROL_OBSERVATION_TRANSITION_KIND
            if report.report_kind == "cancel_observed"
            else MISSION_REPORT_TRANSITION_KIND
        )
        or receipt.evidence_status != EVIDENCE_COMPLETE
        or receipt.receipt_disposition != "lifecycle_advancing"
        or mission.mission_id != report.mission_id
        or not report_revision_matches
        or expected_proposed_state is None
        or transition.proposed_lifecycle_state != expected_proposed_state
        or transition.proposed_lifecycle_revision != transition.prior_lifecycle_revision + 1
        or metadata != expected_metadata
        or transition.request_digest != expected_digest
    ):
        raise MissionError("stored mission report transition bindings are inconsistent")


def _verify_bound_transition_evidence(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
    *,
    expected_event_type: str,
    expected_metadata: JsonObject,
    expected_principal_id: str,
) -> None:
    _verify_transition_evidence_record(connection, transition)
    if transition.evidence_status != EVIDENCE_COMPLETE:
        return
    assert transition.audit_event_id is not None
    assert transition.audit_event_hash is not None
    event_row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE event_id = ?",
        (transition.audit_event_id,),
    ).fetchone()
    try:
        event_payload = json.loads(
            str(event_row[0]) if event_row is not None else "",
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise MissionError("stored mission transition audit event is invalid") from exc
    if (
        not isinstance(event_payload, dict)
        or event_payload.get("event_id") != transition.audit_event_id
        or event_payload.get("event_hash") != transition.audit_event_hash
        or event_payload.get("event_type") != expected_event_type
        or event_payload.get("input_hash") != transition.request_digest
        or not isinstance(event_payload.get("principal"), dict)
        or event_payload["principal"].get("id") != expected_principal_id
        or event_payload.get("metadata") != expected_metadata
    ):
        raise MissionError("stored mission transition audit event binding is inconsistent")


def _verify_transition_evidence_record(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    try:
        created_at = datetime.fromisoformat(transition.created_at)
        finalized_at = (
            datetime.fromisoformat(transition.finalized_at)
            if transition.finalized_at is not None
            else None
        )
    except ValueError as exc:
        raise MissionError("stored mission transition timestamps are invalid") from exc
    if (
        not _TRANSITION_ID_PATTERN.fullmatch(transition.transition_id)
        or not _MISSION_ID_PATTERN.fullmatch(transition.mission_id)
        or not re.fullmatch(SHA256_PATTERN, transition.request_digest)
        or created_at.tzinfo is None
        or (finalized_at is not None and finalized_at.tzinfo is None)
    ):
        raise MissionError("stored mission transition evidence state is invalid")
    if transition.evidence_status == EVIDENCE_PENDING:
        if (
            transition.audit_event_id is not None
            or transition.audit_event_hash is not None
            or transition.failure_reason_code is not None
            or transition.finalized_at is not None
        ):
            raise MissionError("stored mission transition evidence state is invalid")
        return
    if transition.evidence_status == EVIDENCE_INCOMPLETE:
        if (
            transition.audit_event_id is not None
            or transition.audit_event_hash is not None
            or transition.failure_reason_code is None
            or not _SAFE_LABEL_PATTERN.fullmatch(transition.failure_reason_code)
            or ".." in transition.failure_reason_code
            or finalized_at is None
        ):
            raise MissionError("stored mission transition evidence state is invalid")
        return
    if (
        transition.evidence_status != EVIDENCE_COMPLETE
        or transition.audit_event_id is None
        or not _EVENT_ID_PATTERN.fullmatch(transition.audit_event_id)
        or transition.audit_event_hash is None
        or not re.fullmatch(SHA256_PATTERN, transition.audit_event_hash)
        or transition.failure_reason_code is not None
        or finalized_at is None
    ):
        raise MissionError("stored mission transition evidence state is invalid")
    _verify_audit_evidence_binding(
        connection,
        transition=transition,
        audit_event_id=transition.audit_event_id,
        audit_event_hash=transition.audit_event_hash,
    )


def _verify_cancellation_transition_bindings(
    connection: sqlite3.Connection,
    transition: MissionTransitionAttempt,
) -> None:
    mission = _mission_by_id(connection, transition.mission_id)
    metadata = transition.safe_metadata
    try:
        requester = AdminPrincipalContext(
            principal_id=cast(Literal["admin:local-ui"], metadata["requester_principal_id"]),
            principal_type="admin",
            roles=("Admin",),
            authentication_method="local_admin_bearer",
            identity_source="principal_registry",
            identity_generation=str(metadata["requester_identity_generation"]),
        )
        payload = MissionCancellationPayload(client_request_id=str(metadata["client_request_id"]))
    except (KeyError, ValueError) as exc:
        raise MissionError("stored mission cancellation authority is invalid") from exc
    expected_metadata = {
        "requester_principal_id": requester.principal_id,
        "requester_identity_generation": requester.identity_generation,
        "client_request_id": payload.client_request_id,
        "mission_template_id": mission.mission_template_id,
        "target_node_id": mission.target_node_id,
        "workspace_id": mission.workspace_id,
        "envelope_digest": mission.envelope_digest,
    }
    expected_proposed_state = (
        MISSION_CANCELED
        if transition.prior_lifecycle_state == MISSION_QUEUED
        else MISSION_CANCEL_REQUESTED
    )
    if (
        transition.prior_lifecycle_state
        not in {MISSION_QUEUED, MISSION_CLAIMED, MISSION_RUNNER_REPORTED_RUNNING}
        or transition.proposed_lifecycle_state != expected_proposed_state
        or transition.proposed_lifecycle_revision != transition.prior_lifecycle_revision + 1
        or metadata != expected_metadata
        or transition.request_digest
        != mission_cancellation_request_digest(
            mission=mission,
            payload=payload,
            requester=requester,
            prior_lifecycle_state=transition.prior_lifecycle_state,
            prior_lifecycle_revision=transition.prior_lifecycle_revision,
        )
    ):
        raise MissionError("stored mission cancellation transition bindings are inconsistent")


def _require_claim_authority_matches_mission(
    authority: MissionClaimAuthoritySnapshot,
    mission: MissionRecord,
) -> None:
    expected_bindings: tuple[tuple[object, object], ...] = (
        (authority.mission_id, mission.mission_id),
        (authority.admitted_authority_snapshot_hash, mission.authority_snapshot_hash),
        (authority.envelope_digest, mission.envelope_digest),
        (authority.target_node_id, mission.target_node_id),
        (authority.target_node_principal_id, mission.target_node_principal_id),
        (authority.workspace_id, mission.workspace_id),
        (authority.node_identity_key_id, mission.authority_snapshot.node_identity_key_id),
        (authority.configuration_generation, mission.configuration_generation),
        (authority.configuration_digest, mission.configuration_digest),
        (authority.policy_digest, mission.policy_digest),
        (authority.manifest_lock_digest, mission.manifest_lock_digest),
        (authority.mission_template_id, mission.mission_template_id),
        (authority.template_registry_generation, mission.template_registry_generation),
        (authority.template_payload_digest, mission.template_payload_digest),
    )
    if any(current != admitted for current, admitted in expected_bindings):
        raise MissionConflictError("mission claim authority does not match admission")


def _verify_audit_evidence_binding(
    connection: sqlite3.Connection,
    *,
    transition: MissionTransitionAttempt,
    audit_event_id: str,
    audit_event_hash: str,
) -> None:
    row = connection.execute(
        """
        SELECT audit_event_hash, owner_kind, owner_id, request_digest
        FROM mission_audit_evidence_bindings WHERE audit_event_id = ?
        """,
        (audit_event_id,),
    ).fetchone()
    if row != (
        audit_event_hash,
        "mission_transition",
        transition.transition_id,
        transition.request_digest,
    ):
        raise MissionError("stored mission audit evidence binding is invalid")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON member: {key}")
        document[key] = value
    return document


def _require_payload_matches_authority(
    payload: MissionAdmissionPayload, authority: MissionAuthoritySnapshot
) -> None:
    if payload.target_node_id != authority.target_node_id:
        raise MissionConflictError("mission target Node authority mismatch")
    if payload.mission_template_id != authority.mission_template_id:
        raise MissionConflictError("mission template authority mismatch")


def _require_mission_id(value: str) -> None:
    if not _MISSION_ID_PATTERN.fullmatch(value):
        raise MissionNotFoundError("unknown mission")


def _require_node_id(value: str) -> None:
    if not _NODE_ID_PATTERN.fullmatch(value):
        raise MissionConflictError("invalid Node ID")


def _require_transition_id(value: str) -> None:
    if not _TRANSITION_ID_PATTERN.fullmatch(value):
        raise MissionNotFoundError("unknown mission transition")


def _require_report_id(value: str) -> None:
    if not _REPORT_ID_PATTERN.fullmatch(value):
        raise MissionNotFoundError("unknown mission report")


assert MISSION_AUTHORITY_SCHEMA_VERSION == "1"
assert MISSION_TEMPLATE_ID == "synthetic_read_review_v1"
