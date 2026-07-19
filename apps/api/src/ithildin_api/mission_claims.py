"""Signed Node mission claim and evidence-finalized delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_policy_core import PolicyEngine
from ithildin_schemas import AuditEventType, JsonObject, ToolRisk

from ithildin_api.identity import PrincipalRegistry
from ithildin_api.manifest_lock import ManifestLockError, manifest_lock_digest
from ithildin_api.mission_admission import mission_node_authority_hash
from ithildin_api.mission_templates import MissionTemplateRegistry
from ithildin_api.missions import (
    MISSION_TEMPLATE_ID,
    MissionClaimAuthoritySnapshot,
    MissionClaimRecord,
    MissionClaimRequestPayload,
    MissionConflictError,
    MissionError,
    MissionNotFoundError,
    MissionRecord,
    MissionStore,
    MissionTransitionAttempt,
)
from ithildin_api.node_configuration import (
    NodeConfigurationNotFoundError,
    NodeConfigurationStore,
)
from ithildin_api.node_governed_access import node_governed_access_posture
from ithildin_api.nodes import NodeNotFoundError, NodeRecord, NodeStore, node_identity_key_id
from ithildin_api.registry import ToolRegistry, UnknownToolDenied
from ithildin_api.workspaces import WorkspaceRegistry


class MissionClaimError(RuntimeError):
    """Raised when a signed mission claim cannot complete safely."""


class MissionClaimNotFoundError(MissionClaimError):
    """Raised when the authenticated Node has no claimable mission."""


class MissionClaimUnavailableError(MissionClaimError):
    """Raised when a required claim authority is unavailable."""


class MissionClaimService:
    def __init__(
        self,
        *,
        mission_store: MissionStore,
        node_store: NodeStore,
        node_configuration_store: NodeConfigurationStore,
        template_registry: MissionTemplateRegistry,
        principal_registry: PrincipalRegistry,
        workspace_registry: WorkspaceRegistry,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
        audit_writer: AuditWriter,
        node_stale_after_seconds: int,
        manifest_lock_path: Path,
        verified_manifest_lock_digest: str | None,
    ) -> None:
        self.mission_store = mission_store
        self.node_store = node_store
        self.node_configuration_store = node_configuration_store
        self.template_registry = template_registry
        self.principal_registry = principal_registry
        self.workspace_registry = workspace_registry
        self.tool_registry = tool_registry
        self.policy_engine = policy_engine
        self.audit_writer = audit_writer
        self.node_stale_after_seconds = node_stale_after_seconds
        self.manifest_lock_path = manifest_lock_path
        self.verified_manifest_lock_digest = verified_manifest_lock_digest

    def claim(
        self,
        payload: MissionClaimRequestPayload,
        *,
        authenticated_node: NodeRecord,
        now: datetime | None = None,
    ) -> JsonObject:
        effective_now = now or datetime.now(UTC)
        self.reconcile_expired_claims(now=effective_now)
        try:
            mission = self.mission_store.next_queued_for_node(authenticated_node.node_id)
        except MissionNotFoundError as exc:
            raise MissionClaimNotFoundError("no queued mission for Node") from exc
        authenticated_key_id = node_identity_key_id(authenticated_node.public_key)
        authority = self.current_claim_authority(
            mission,
            authenticated_node_id=authenticated_node.node_id,
            authenticated_key_id=authenticated_key_id,
            now=effective_now,
        )
        try:
            staged = self.mission_store.stage_claim(
                mission.mission_id,
                payload,
                authority=authority,
                authority_precondition=lambda: self.current_claim_authority(
                    mission,
                    authenticated_node_id=authenticated_node.node_id,
                    authenticated_key_id=authenticated_key_id,
                    now=now or datetime.now(UTC),
                ),
                now=effective_now,
            )
        except MissionConflictError as exc:
            raise MissionClaimError(str(exc)) from exc
        try:
            event = self.audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=AuditEventType.MISSION_CLAIM_STAGED,
                request_id=f"req_{uuid4().hex}",
                principal={"id": authenticated_node.principal_id, "roles": []},
                input_hash=staged.transition.request_digest,
                metadata=_claim_audit_metadata(staged.transition, staged.claim, mission),
                timestamp=effective_now,
            )
        except AuditWriteError as exc:
            self._record_evidence_failure(
                staged.transition,
                reason_code="audit_write_failed",
                now=effective_now,
            )
            raise MissionClaimError("mission claim audit evidence failed") from exc
        try:
            claim = self.mission_store.finalize_claim(
                staged.transition.transition_id,
                audit_event_id=event.event_id,
                audit_event_hash=event.event_hash,
                authority_precondition=lambda: self.current_claim_authority(
                    mission,
                    authenticated_node_id=authenticated_node.node_id,
                    authenticated_key_id=authenticated_key_id,
                    now=now or datetime.now(UTC),
                ),
                now=now,
            )
        except (MissionError, MissionClaimError) as exc:
            self._record_evidence_failure(
                staged.transition,
                reason_code="finalization_failed",
                now=effective_now,
            )
            raise MissionClaimError("mission claim finalization failed") from exc
        claimed_mission = self.mission_store.get(mission.mission_id)
        return self._delivery_envelope(claimed_mission, claim)

    def reconcile_expired_claims(self, *, now: datetime | None = None) -> int:
        effective_now = now or datetime.now(UTC)
        reconciled = 0
        for due_claim in self.mission_store.due_delivered_claims(now=effective_now):
            try:
                staged = self.mission_store.stage_claim_expiry(
                    due_claim.mission_id,
                    now=effective_now,
                )
            except MissionConflictError:
                continue
            try:
                event = self.audit_writer.write_event(
                    event_id=f"evt_{uuid4().hex}",
                    event_type=AuditEventType.MISSION_CLAIM_EXPIRY_STAGED,
                    request_id=f"req_{uuid4().hex}",
                    principal={"id": "gateway:mission-expiry", "roles": []},
                    input_hash=staged.transition.request_digest,
                    metadata=_claim_expiry_audit_metadata(
                        staged.transition,
                        staged.claim,
                        staged.mission,
                    ),
                    timestamp=effective_now,
                )
            except AuditWriteError as exc:
                self._record_evidence_failure(
                    staged.transition,
                    reason_code="audit_write_failed",
                    now=effective_now,
                )
                raise MissionClaimError("mission claim expiry audit evidence failed") from exc
            try:
                self.mission_store.finalize_claim_expiry(
                    staged.transition.transition_id,
                    audit_event_id=event.event_id,
                    audit_event_hash=event.event_hash,
                    now=effective_now,
                )
            except MissionError as exc:
                self._record_evidence_failure(
                    staged.transition,
                    reason_code="finalization_failed",
                    now=effective_now,
                )
                raise MissionClaimError("mission claim expiry finalization failed") from exc
            reconciled += 1
        return reconciled

    def current_claim_authority(
        self,
        mission: MissionRecord,
        *,
        authenticated_node_id: str,
        authenticated_key_id: str,
        now: datetime,
    ) -> MissionClaimAuthoritySnapshot:
        try:
            node = self.node_store.get(authenticated_node_id)
        except NodeNotFoundError as exc:
            raise MissionClaimNotFoundError("unknown Node") from exc
        current_key_id = node_identity_key_id(node.public_key)
        if current_key_id != authenticated_key_id:
            raise MissionClaimError("Node identity changed before mission claim")
        generation = node.desired_configuration_generation
        if generation is None:
            raise MissionClaimError("mission target Node is not ready: configuration_unassigned")
        try:
            desired = self.node_configuration_store.get(node.node_id, generation)
        except NodeConfigurationNotFoundError as exc:
            raise MissionClaimError(
                "mission target Node is not ready: configuration_invalid"
            ) from exc
        current_manifest_lock_digest = self._current_manifest_lock_digest()
        tools = self.tool_registry.list_tools()
        if len(tools) != 24:
            raise MissionClaimUnavailableError("mission tool authority is unavailable")
        template = self.template_registry.get(mission.mission_template_id)
        self._require_template_tools_are_governed_reads(template.operation_tool_names)
        posture = node_governed_access_posture(
            node=node,
            desired=desired,
            principal_registry=self.principal_registry,
            workspace_registry=self.workspace_registry,
            tool_registry=self.tool_registry,
            current_policy_digest=self.policy_engine.policy_hash,
            current_manifest_lock_digest=current_manifest_lock_digest,
            stale_after_seconds=self.node_stale_after_seconds,
            now=now,
        )
        if posture.get("state") != "ready_read_only":
            reason = posture.get("reason_code")
            safe_reason = reason if isinstance(reason, str) else "authority_prerequisite_failed"
            raise MissionClaimError(f"mission target Node is not ready: {safe_reason}")
        authority = MissionClaimAuthoritySnapshot(
            mission_id=mission.mission_id,
            admitted_authority_snapshot_hash=mission.authority_snapshot_hash,
            envelope_digest=mission.envelope_digest,
            target_node_id=node.node_id,
            target_node_principal_id=node.principal_id,
            workspace_id=node.workspace_id,
            current_node_record_hash=mission_node_authority_hash(node),
            node_identity_key_id=current_key_id,
            configuration_generation=desired.generation,
            configuration_digest=desired.configuration_digest,
            policy_digest=self.policy_engine.policy_hash,
            manifest_lock_digest=current_manifest_lock_digest,
            tool_count=24,
            mission_template_id=MISSION_TEMPLATE_ID,
            template_registry_generation=self.template_registry.registry_generation,
            template_payload_digest=template.payload_digest,
        )
        return authority

    def _current_manifest_lock_digest(self) -> str:
        if self.verified_manifest_lock_digest is None:
            raise MissionClaimUnavailableError("mission manifest authority is unavailable")
        try:
            current_digest = manifest_lock_digest(self.manifest_lock_path)
        except (OSError, ManifestLockError) as exc:
            raise MissionClaimUnavailableError("mission manifest authority is unavailable") from exc
        if current_digest != self.verified_manifest_lock_digest:
            raise MissionClaimUnavailableError("mission manifest authority is unavailable")
        return current_digest

    def _require_template_tools_are_governed_reads(
        self,
        tool_names: tuple[str, ...],
    ) -> None:
        for tool_name in tool_names:
            try:
                registered = self.tool_registry.get_tool(tool_name)
            except UnknownToolDenied as exc:
                raise MissionClaimUnavailableError(
                    "mission template tool authority is unavailable"
                ) from exc
            manifest = registered.manifest
            properties = manifest.input_schema.get("properties")
            if (
                manifest.risk is not ToolRisk.READ
                or (manifest.mcp or {}).get("exposed") is not True
                or not isinstance(properties, dict)
                or "workspace_id" not in properties
            ):
                raise MissionClaimUnavailableError(
                    "mission template tool authority is unavailable"
                )

    def _delivery_envelope(
        self,
        mission: MissionRecord,
        claim: MissionClaimRecord,
    ) -> JsonObject:
        template = self.template_registry.get(mission.mission_template_id)
        return {
            "delivery_schema_version": "1",
            "mission_id": mission.mission_id,
            "claim_id": claim.claim_id,
            "envelope_digest": mission.envelope_digest,
            "claim_lifecycle_revision": claim.lifecycle_revision,
            "claim_expires_at": claim.expires_at,
            "workspace_id": mission.workspace_id,
            "mission_template_id": mission.mission_template_id,
            "template_registry_generation": mission.template_registry_generation,
            "template_payload_digest": mission.template_payload_digest,
            "template_payload": template.payload_copy(),
            "gateway_lifecycle_state": mission.lifecycle_state,
            "gateway_delivery_recorded": True,
            "runner_state_authority": "runner_reported_only",
            "model_provider_state_known": False,
        }

    def _record_evidence_failure(
        self,
        transition: MissionTransitionAttempt,
        *,
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


def _claim_audit_metadata(
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
        "evidence_status": "pending",
        "target_node_id": mission.target_node_id,
        "workspace_id": mission.workspace_id,
        "envelope_digest": mission.envelope_digest,
        "authority_snapshot_hash": claim.authority_snapshot_hash,
        "claim_expires_at": claim.expires_at,
        "staged_proposal_only": True,
        "runner_started_proven": False,
        "model_provider_state_known": False,
    }


def _claim_expiry_audit_metadata(
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
        "evidence_status": "pending",
        "target_node_id": mission.target_node_id,
        "envelope_digest": mission.envelope_digest,
        "claim_expires_at": claim.expires_at,
        "staged_proposal_only": True,
        "automatic_requeue": False,
        "runner_state_authority": "runner_reported_only",
    }
