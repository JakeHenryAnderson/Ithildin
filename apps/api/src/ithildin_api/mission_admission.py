"""Authenticated Mission Command admission over existing Gateway authorities."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_policy_core import PolicyEngine
from ithildin_schemas import AuditEventType, JsonObject, ToolRisk, sha256_digest

from ithildin_api.identity import PrincipalRegistry
from ithildin_api.manifest_lock import ManifestLockError, manifest_lock_digest
from ithildin_api.mission_templates import MissionTemplateRegistry
from ithildin_api.missions import (
    EVIDENCE_COMPLETE,
    EVIDENCE_INCOMPLETE,
    MISSION_CANCELLATION_TRANSITION_KIND,
    MissionAdmissionPayload,
    MissionAuthoritySnapshot,
    MissionCancellationPayload,
    MissionError,
    MissionNotFoundError,
    MissionRecord,
    MissionStore,
    MissionTransitionAttempt,
    mission_transition_audit_metadata,
)
from ithildin_api.node_configuration import (
    NodeConfigurationNotFoundError,
    NodeConfigurationRecord,
    NodeConfigurationStore,
)
from ithildin_api.node_governed_access import node_governed_access_posture
from ithildin_api.nodes import NodeNotFoundError, NodeRecord, NodeStore, node_identity_key_id
from ithildin_api.promotion_authority import AdminPrincipalContext
from ithildin_api.registry import ToolRegistry, UnknownToolDenied
from ithildin_api.workspaces import WorkspaceRegistry


class MissionAdmissionError(RuntimeError):
    """Raised when mission admission or cancellation cannot complete safely."""


class MissionAdmissionNotFoundError(MissionAdmissionError):
    """Raised when a public Mission Command resource does not exist."""


class MissionAdmissionUnavailableError(MissionAdmissionError):
    """Raised when a required server-owned authority is unavailable."""


class MissionAdmissionService:
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

    def admit(
        self,
        payload: MissionAdmissionPayload,
        *,
        requester: AdminPrincipalContext,
        now: datetime | None = None,
    ) -> JsonObject:
        effective_now = now or datetime.now(UTC)
        replay = self.mission_store.replay_admission(payload, requester=requester)
        if replay is not None:
            if replay.transition.evidence_status == EVIDENCE_COMPLETE:
                return replay.mission.safe_summary()
            raise MissionAdmissionError("mission admission requires evidence recovery")
        current_manifest_lock_digest = self._current_manifest_lock_digest()
        authority = self._admission_authority(
            payload,
            requester=requester,
            current_manifest_lock_digest=current_manifest_lock_digest,
            now=effective_now,
        )
        staged = self.mission_store.stage_admission(
            payload,
            authority=authority,
            authority_precondition=lambda: self._require_authority_still_current(
                payload,
                requester=requester,
                expected=authority,
                now=now or datetime.now(UTC),
            ),
            now=effective_now,
        )
        if staged.idempotent_replay:
            if staged.transition.evidence_status == EVIDENCE_COMPLETE:
                return staged.mission.safe_summary()
            raise MissionAdmissionError("mission admission requires evidence recovery")
        return self._audit_and_finalize(
            transition=staged.transition,
            mission=staged.mission,
            requester=requester,
            event_type=AuditEventType.MISSION_ADMISSION_STAGED,
            finalize=self.mission_store.finalize_admission,
            now=effective_now,
        ).safe_summary()

    def cancel(
        self,
        mission_id: str,
        payload: MissionCancellationPayload,
        *,
        requester: AdminPrincipalContext,
        now: datetime | None = None,
    ) -> JsonObject:
        effective_now = now or datetime.now(UTC)
        try:
            staged = self.mission_store.stage_cancellation(
                mission_id,
                payload,
                requester=requester,
                now=effective_now,
            )
        except MissionNotFoundError as exc:
            raise MissionAdmissionNotFoundError("unknown mission") from exc
        if staged.idempotent_replay:
            if staged.transition.evidence_status == EVIDENCE_COMPLETE:
                return staged.mission.safe_summary()
            raise MissionAdmissionError("mission cancellation requires evidence recovery")
        return self._audit_and_finalize(
            transition=staged.transition,
            mission=staged.mission,
            requester=requester,
            event_type=AuditEventType.MISSION_CANCELLATION_STAGED,
            finalize=self.mission_store.finalize_cancellation,
            now=effective_now,
        ).safe_summary()

    def _admission_authority(
        self,
        payload: MissionAdmissionPayload,
        *,
        requester: AdminPrincipalContext,
        current_manifest_lock_digest: str,
        now: datetime,
    ) -> MissionAuthoritySnapshot:
        try:
            node = self.node_store.get(payload.target_node_id)
        except NodeNotFoundError as exc:
            raise MissionAdmissionNotFoundError("unknown Node") from exc
        desired = self._desired_configuration(node)
        template = self.template_registry.get(payload.mission_template_id)
        tools = self.tool_registry.list_tools()
        if len(tools) != 24:
            raise MissionAdmissionUnavailableError("mission tool authority is unavailable")
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
            raise MissionAdmissionError(f"mission target Node is not ready: {safe_reason}")
        return MissionAuthoritySnapshot(
            requesting_principal=requester,
            target_node_id=node.node_id,
            target_node_principal_id=node.principal_id,
            workspace_id=node.workspace_id,
            node_record_hash=mission_node_authority_hash(node),
            node_identity_key_id=node_identity_key_id(node.public_key),
            configuration_generation=desired.generation,
            configuration_digest=desired.configuration_digest,
            policy_digest=self.policy_engine.policy_hash,
            manifest_lock_digest=current_manifest_lock_digest,
            tool_count=24,
            mission_template_id=payload.mission_template_id,
            template_registry_generation=self.template_registry.registry_generation,
            template_payload_digest=template.payload_digest,
        )

    def _require_template_tools_are_governed_reads(
        self,
        tool_names: tuple[str, ...],
    ) -> None:
        for tool_name in tool_names:
            try:
                registered = self.tool_registry.get_tool(tool_name)
            except UnknownToolDenied as exc:
                raise MissionAdmissionUnavailableError(
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
                raise MissionAdmissionUnavailableError(
                    "mission template tool authority is unavailable"
                )

    def _require_authority_still_current(
        self,
        payload: MissionAdmissionPayload,
        *,
        requester: AdminPrincipalContext,
        expected: MissionAuthoritySnapshot,
        now: datetime,
    ) -> None:
        current = self._admission_authority(
            payload,
            requester=requester,
            current_manifest_lock_digest=self._current_manifest_lock_digest(),
            now=now,
        )
        if current.canonical_hash() != expected.canonical_hash():
            raise MissionAdmissionError("mission authority changed before admission")

    def _current_manifest_lock_digest(self) -> str:
        if self.verified_manifest_lock_digest is None:
            raise MissionAdmissionUnavailableError(
                "mission manifest authority is unavailable"
            )
        try:
            current_digest = manifest_lock_digest(self.manifest_lock_path)
        except (OSError, ManifestLockError) as exc:
            raise MissionAdmissionUnavailableError(
                "mission manifest authority is unavailable"
            ) from exc
        if current_digest != self.verified_manifest_lock_digest:
            raise MissionAdmissionUnavailableError("mission manifest authority is unavailable")
        return current_digest

    def _desired_configuration(self, node: NodeRecord) -> NodeConfigurationRecord:
        generation = node.desired_configuration_generation
        if generation is None:
            raise MissionAdmissionError(
                "mission target Node is not ready: configuration_unassigned"
            )
        try:
            return self.node_configuration_store.get(node.node_id, generation)
        except NodeConfigurationNotFoundError as exc:
            raise MissionAdmissionError(
                "mission target Node is not ready: configuration_invalid"
            ) from exc

    def _audit_and_finalize(
        self,
        *,
        transition: MissionTransitionAttempt,
        mission: MissionRecord,
        requester: AdminPrincipalContext,
        event_type: AuditEventType,
        finalize: Callable[..., MissionRecord],
        now: datetime,
    ) -> MissionRecord:
        try:
            event = self.audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=event_type,
                request_id=f"req_{uuid4().hex}",
                principal={"id": requester.principal_id, "roles": list(requester.roles)},
                input_hash=transition.request_digest,
                metadata=mission_transition_audit_metadata(transition, mission),
                timestamp=now,
            )
        except AuditWriteError as exc:
            self._record_evidence_failure(transition, "audit_write_failed", now=now)
            raise MissionAdmissionError("mission transition audit evidence failed") from exc
        try:
            return finalize(
                transition.transition_id,
                audit_event_id=event.event_id,
                audit_event_hash=event.event_hash,
                now=now,
            )
        except MissionError as exc:
            self._record_evidence_failure(transition, "finalization_failed", now=now)
            raise MissionAdmissionError("mission transition finalization failed") from exc

    def _record_evidence_failure(
        self,
        transition: MissionTransitionAttempt,
        reason_code: str,
        *,
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
def mission_node_authority_hash(node: NodeRecord) -> str:
    return sha256_digest(
        {
            "node_id": node.node_id,
            "principal_id": node.principal_id,
            "workspace_id": node.workspace_id,
            "status": node.status,
            "evidence_status": node.evidence_status,
            "descriptor_hash": node.descriptor_hash,
            "active_identity_key_id": node_identity_key_id(node.public_key),
            "last_seen_at": node.last_seen_at,
            "last_heartbeat_hash": node.last_heartbeat_hash,
            "last_node_version": node.last_node_version,
            "last_configuration_digest": node.last_configuration_digest,
            "desired_configuration_generation": node.desired_configuration_generation,
            "desired_configuration_digest": node.desired_configuration_digest,
            "acknowledged_configuration_generation": (
                node.acknowledged_configuration_generation
            ),
            "acknowledged_configuration_digest": node.acknowledged_configuration_digest,
            "acknowledged_configuration_signing_key_id": (
                node.acknowledged_configuration_signing_key_id
            ),
            "acknowledged_active_configuration_signing_key_id": (
                node.acknowledged_active_configuration_signing_key_id
            ),
            "configuration_acknowledgment_status": (
                node.configuration_acknowledgment_status
            ),
        }
    )


assert MISSION_CANCELLATION_TRANSITION_KIND == "cancellation_pending_evidence"
assert EVIDENCE_INCOMPLETE == "evidence_incomplete"
