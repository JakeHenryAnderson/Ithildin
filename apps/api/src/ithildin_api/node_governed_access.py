"""Bounded Node-authenticated ingress for existing governed read tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from ithildin_schemas import JsonObject, ToolRisk
from ithildin_schemas.models import SHA256_PATTERN, StrictBaseModel
from pydantic import Field, field_validator

from ithildin_api.identity import (
    PrincipalRecord,
    PrincipalRegistry,
    PrincipalRole,
    PrincipalType,
)
from ithildin_api.node_configuration import (
    CONFIGURATION_ACK_STATUS,
    NodeConfigurationRecord,
    NodeDesiredConfigurationPayload,
)
from ithildin_api.node_versions import node_version_posture
from ithildin_api.nodes import NODE_PROTOCOL_VERSION, NodeRecord
from ithildin_api.registry import RegisteredTool, ToolRegistry
from ithildin_api.workspaces import WorkspaceRegistry, WorkspaceRegistryError

NODE_READ_ONLY_PROFILE_ID = "agent:node-local-preview-readonly"


class NodeGovernedAccessError(RuntimeError):
    """Raised when Node authority prerequisites fail closed."""


class NodeGovernedToolCallPayload(StrictBaseModel):
    protocol_version: Literal["1"]
    configuration_generation: int = Field(ge=1)
    configuration_digest: str = Field(pattern=SHA256_PATTERN)
    node_version: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=128)
    arguments: JsonObject = Field(default_factory=dict)

    @field_validator("session_id", "tool_name")
    @classmethod
    def _safe_label(cls, value: str) -> str:
        if not value[0].isalnum() or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:@-/"
            for character in value
        ):
            raise ValueError("unsafe governed-access label")
        return value

    def safe_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json"))


@dataclass(frozen=True)
class NodeGovernedAccessContext:
    principal_registry: PrincipalRegistry
    principal: JsonObject
    arguments: JsonObject
    session_id: str
    configuration_generation: int
    configuration_digest: str


def prepare_node_governed_access(
    *,
    node: NodeRecord,
    desired: NodeConfigurationRecord,
    payload: NodeGovernedToolCallPayload,
    principal_registry: PrincipalRegistry,
    workspace_registry: WorkspaceRegistry,
    current_policy_digest: str,
    current_manifest_lock_digest: str,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> NodeGovernedAccessContext:
    effective_now = now or datetime.now(UTC)
    _require_node_posture(node, stale_after_seconds=stale_after_seconds, now=effective_now)
    closed = _desired_configuration(desired)
    _require_configuration_binding(
        node=node,
        desired=desired,
        closed=closed,
        payload=payload,
        current_policy_digest=current_policy_digest,
        current_manifest_lock_digest=current_manifest_lock_digest,
    )
    _require_active_workspace(workspace_registry, node.workspace_id)
    profile = _node_read_only_profile(principal_registry)
    derived_principal = PrincipalRecord(
        id=node.principal_id,
        type=PrincipalType.AGENT,
        display_name=node.display_name,
        roles=profile.roles,
        enabled=True,
        metadata={
            "identity_source": "gateway_node_store",
            "authorization_profile": profile.id,
            "workspace_id": node.workspace_id,
        },
    )
    derived_registry = PrincipalRegistry(
        {derived_principal.id: derived_principal},
        Path("gateway-derived-node-principal"),
    )
    return NodeGovernedAccessContext(
        principal_registry=derived_registry,
        principal=derived_principal.trusted_principal(),
        arguments=payload.arguments,
        session_id=(
            f"node:{node.node_id}:cfg:{desired.generation}:"
            f"{desired.configuration_digest}:{payload.session_id}"
        ),
        configuration_generation=desired.generation,
        configuration_digest=desired.configuration_digest,
    )


def bind_node_tool_arguments(
    *,
    context: NodeGovernedAccessContext,
    registered_tool: RegisteredTool,
    workspace_id: str,
) -> NodeGovernedAccessContext:
    return NodeGovernedAccessContext(
        principal_registry=context.principal_registry,
        principal=context.principal,
        arguments=_workspace_bound_arguments(
            registered_tool=registered_tool,
            arguments=context.arguments,
            workspace_id=workspace_id,
        ),
        session_id=context.session_id,
        configuration_generation=context.configuration_generation,
        configuration_digest=context.configuration_digest,
    )


def _require_node_posture(
    node: NodeRecord, *, stale_after_seconds: int, now: datetime
) -> None:
    if node.summary(now=now, stale_after_seconds=stale_after_seconds)["observed_state"] != (
        "observed_connected"
    ):
        raise NodeGovernedAccessError("Node is not currently observed by the Gateway")


def _desired_configuration(record: NodeConfigurationRecord) -> NodeDesiredConfigurationPayload:
    configuration = record.bundle.get("configuration")
    if not isinstance(configuration, dict):
        raise NodeGovernedAccessError("desired Node configuration is invalid")
    try:
        return NodeDesiredConfigurationPayload.model_validate(configuration)
    except ValueError as exc:
        raise NodeGovernedAccessError("desired Node configuration is invalid") from exc


def _require_configuration_binding(
    *,
    node: NodeRecord,
    desired: NodeConfigurationRecord,
    closed: NodeDesiredConfigurationPayload,
    payload: NodeGovernedToolCallPayload,
    current_policy_digest: str,
    current_manifest_lock_digest: str,
) -> None:
    if (
        payload.configuration_generation != desired.generation
        or payload.configuration_digest != desired.configuration_digest
    ):
        raise NodeGovernedAccessError("Node governed request configuration is not desired")
    if (
        node.acknowledged_configuration_generation != desired.generation
        or node.acknowledged_configuration_digest != desired.configuration_digest
        or node.configuration_acknowledgment_status != CONFIGURATION_ACK_STATUS
    ):
        raise NodeGovernedAccessError("Node desired configuration is not acknowledged")
    if node.last_configuration_digest != desired.configuration_digest:
        raise NodeGovernedAccessError("Node heartbeat configuration is not current")
    if node.last_node_version != payload.node_version:
        raise NodeGovernedAccessError("Node request version differs from its accepted heartbeat")
    posture = node_version_posture(
        node_status=node.status,
        node_evidence_status=node.evidence_status,
        desired_assigned=True,
        desired_evidence_complete=desired.evidence_status == "complete",
        observed_version=node.last_node_version,
        minimum_version=closed.minimum_node_version,
    )
    if posture != "meets_minimum":
        raise NodeGovernedAccessError("Node version does not meet the desired minimum")
    if closed.offline_posture != "deny_governed_actions":
        raise NodeGovernedAccessError("Node offline posture is not fail closed")
    if closed.policy_digest != current_policy_digest:
        raise NodeGovernedAccessError("Node desired policy is not current")
    if closed.manifest_lock_digest != current_manifest_lock_digest:
        raise NodeGovernedAccessError("Node desired tool manifest is not current")


def _require_active_workspace(registry: WorkspaceRegistry, workspace_id: str) -> None:
    try:
        registry.resolve_active(workspace_id)
    except WorkspaceRegistryError as exc:
        raise NodeGovernedAccessError("Node workspace is not active") from exc


def _node_read_only_profile(registry: PrincipalRegistry) -> PrincipalRecord:
    try:
        profile = registry.resolve_active(NODE_READ_ONLY_PROFILE_ID)
    except RuntimeError as exc:
        raise NodeGovernedAccessError("Node authorization profile is unavailable") from exc
    if profile.type is not PrincipalType.AGENT or profile.roles != [PrincipalRole.AGENT_READ_ONLY]:
        raise NodeGovernedAccessError("Node authorization profile is not read-only")
    return profile


def _workspace_bound_arguments(
    *, registered_tool: RegisteredTool, arguments: JsonObject, workspace_id: str
) -> JsonObject:
    manifest = registered_tool.manifest
    if manifest.risk is not ToolRisk.READ:
        raise NodeGovernedAccessError("Node governed access is limited to read tools")
    if (manifest.mcp or {}).get("exposed") is not True:
        raise NodeGovernedAccessError("tool is not exposed for governed agent access")
    schema_properties = manifest.input_schema.get("properties")
    if not isinstance(schema_properties, dict) or "workspace_id" not in schema_properties:
        raise NodeGovernedAccessError("read tool lacks an explicit workspace binding")
    requested_workspace = arguments.get("workspace_id")
    if requested_workspace is not None and requested_workspace != workspace_id:
        raise NodeGovernedAccessError("Node governed request workspace mismatch")
    return {**arguments, "workspace_id": workspace_id}


assert NODE_PROTOCOL_VERSION == "1"


def node_governed_access_posture(
    *,
    node: NodeRecord,
    desired: NodeConfigurationRecord | None,
    principal_registry: PrincipalRegistry,
    workspace_registry: WorkspaceRegistry,
    tool_registry: ToolRegistry,
    current_policy_digest: str,
    current_manifest_lock_digest: str,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> JsonObject:
    read_tools = [
        registered
        for registered in tool_registry.list_tools()
        if registered.manifest.risk is ToolRisk.READ
        and (registered.manifest.mcp or {}).get("exposed") is True
        and isinstance(registered.manifest.input_schema.get("properties"), dict)
        and "workspace_id"
        in cast(
            dict[str, object],
            registered.manifest.input_schema["properties"],
        )
    ]
    base: JsonObject = {
        "identity_source": "gateway_derived_node",
        "authorization_profile": NODE_READ_ONLY_PROFILE_ID,
        "workspace_id": node.workspace_id,
        "allowed_risks": ["read"],
        "allowed_tool_count": len(read_tools),
        "enforcement_point": "gateway_governed_tool_pipeline",
        "node_configuration_enforcement_proven": False,
        "runner_enforcement_proven": False,
        "offline_fallback_allowed": False,
    }
    if desired is None:
        return {**base, "state": "blocked", "reason_code": "configuration_unassigned"}
    try:
        desired_expiry = datetime.fromisoformat(desired.expires_at)
    except ValueError:
        return {**base, "state": "blocked", "reason_code": "configuration_invalid"}
    effective_now = now or datetime.now(UTC)
    if desired.evidence_status != "complete":
        return {**base, "state": "blocked", "reason_code": "configuration_evidence_incomplete"}
    if desired_expiry.tzinfo is None or desired_expiry <= effective_now:
        return {**base, "state": "blocked", "reason_code": "configuration_expired"}
    try:
        prepare_node_governed_access(
            node=node,
            desired=desired,
            payload=NodeGovernedToolCallPayload(
                protocol_version="1",
                configuration_generation=desired.generation,
                configuration_digest=desired.configuration_digest,
                node_version=node.last_node_version or "0.0.0",
                session_id="posture-preview",
                tool_name="fs.read",
                arguments={},
            ),
            principal_registry=principal_registry,
            workspace_registry=workspace_registry,
            current_policy_digest=current_policy_digest,
            current_manifest_lock_digest=current_manifest_lock_digest,
            stale_after_seconds=stale_after_seconds,
            now=effective_now,
        )
    except NodeGovernedAccessError as exc:
        return {
            **base,
            "state": "blocked",
            "reason_code": _posture_reason_code(str(exc)),
            "configuration_generation": desired.generation,
            "configuration_digest": desired.configuration_digest,
        }
    return {
        **base,
        "state": "ready_read_only",
        "reason_code": "all_gateway_prerequisites_current",
        "configuration_generation": desired.generation,
        "configuration_digest": desired.configuration_digest,
    }


def _posture_reason_code(reason: str) -> str:
    reasons = {
        "Node is not currently observed by the Gateway": "node_not_currently_observed",
        "Node governed request configuration is not desired": "configuration_not_desired",
        "Node desired configuration is not acknowledged": "configuration_not_acknowledged",
        "Node heartbeat configuration is not current": "heartbeat_configuration_drift",
        "Node request version differs from its accepted heartbeat": "reported_version_drift",
        "Node version does not meet the desired minimum": "node_version_below_minimum",
        "Node offline posture is not fail closed": "offline_posture_not_fail_closed",
        "Node desired policy is not current": "policy_digest_drift",
        "Node desired tool manifest is not current": "manifest_lock_digest_drift",
        "Node workspace is not active": "workspace_not_active",
        "Node authorization profile is unavailable": "authorization_profile_unavailable",
        "Node authorization profile is not read-only": "authorization_profile_not_read_only",
        "desired Node configuration is invalid": "configuration_invalid",
    }
    return reasons.get(reason, "authority_prerequisite_failed")
