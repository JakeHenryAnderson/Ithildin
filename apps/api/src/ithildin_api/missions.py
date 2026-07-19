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

from ithildin_schemas import JsonObject, canonical_json, sha256_digest
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
MISSION_UNADMITTED = "unadmitted"
MISSION_QUEUED = "queued"
MISSION_CLAIMED = "claimed"
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
    reason_code: Literal[
        "runner_error",
        "runner_timeout",
        "runner_output_invalid",
        "runner_dependency_unavailable",
    ] | None = None
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


class MissionStore:
    """Persist staged mission authority without exposing incomplete lifecycle claims."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

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
            expires_at = effective_now + timedelta(
                seconds=mission.requested_timeout_seconds
            )
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
            if mission.lifecycle_state != MISSION_QUEUED:
                raise MissionConflictError("mission is not queued for cancellation")
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
                        MISSION_CANCELED,
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

    def _finalize_transition(
        self,
        transition_id: str,
        *,
        expected_kind: str,
        audit_event_id: str,
        audit_event_hash: str,
        now: datetime | None,
        claim_authority_precondition: (
            Callable[[], MissionClaimAuthoritySnapshot] | None
        ) = None,
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
                if (
                    current_authority.canonical_hash()
                    != claim.authority_snapshot_hash
                ):
                    raise MissionConflictError(
                        "mission claim authority changed before delivery"
                    )
                try:
                    expires_at = datetime.fromisoformat(claim.expires_at)
                except ValueError as exc:
                    raise MissionError("stored mission claim expiry is invalid") from exc
                finalization_now = now or datetime.now(UTC)
                if expires_at.tzinfo is None or finalization_now >= expires_at:
                    raise MissionConflictError("mission claim expired before delivery")
            else:
                finalization_now = now or datetime.now(UTC)
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
            "requested_transition": MISSION_CANCELED,
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
    if transition_kind == MISSION_CANCELLATION_TRANSITION_KIND:
        _verify_cancellation_transition_bindings(connection, transition)
    elif transition_kind == MISSION_CLAIM_TRANSITION_KIND:
        _verify_claim_transition_bindings(connection, transition)
    elif transition_kind == MISSION_CLAIM_EXPIRY_TRANSITION_KIND:
        _verify_claim_expiry_transition_bindings(connection, transition)
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
    if transition.transition_kind == MISSION_ADMISSION_TRANSITION_KIND:
        _verify_admission_transition_bindings(connection, transition)
    elif transition.transition_kind == MISSION_CLAIM_TRANSITION_KIND:
        _verify_claim_transition_bindings(connection, transition)
    elif transition.transition_kind == MISSION_CLAIM_EXPIRY_TRANSITION_KIND:
        _verify_claim_expiry_transition_bindings(connection, transition)
    elif transition.transition_kind == MISSION_CANCELLATION_TRANSITION_KIND:
        _verify_cancellation_transition_bindings(connection, transition)
    return transition


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
        or transition.proposed_lifecycle_state
        != MISSION_CLAIM_EXPIRED_REVIEW_REQUIRED
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
        payload = MissionCancellationPayload(
            client_request_id=str(metadata["client_request_id"])
        )
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
    if (
        transition.prior_lifecycle_state != MISSION_QUEUED
        or transition.proposed_lifecycle_state != MISSION_CANCELED
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


def _require_transition_id(value: str) -> None:
    if not _TRANSITION_ID_PATTERN.fullmatch(value):
        raise MissionNotFoundError("unknown mission transition")


assert MISSION_AUTHORITY_SCHEMA_VERSION == "1"
assert MISSION_TEMPLATE_ID == "synthetic_read_review_v1"
