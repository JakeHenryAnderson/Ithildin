from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ithildin_api.identity import (
    PrincipalRecord,
    PrincipalRegistry,
    PrincipalRole,
    PrincipalType,
)
from ithildin_api.node_configuration import NodeConfigurationRecord
from ithildin_api.node_governed_access import (
    NODE_READ_ONLY_PROFILE_ID,
    NodeGovernedAccessError,
    NodeGovernedToolCallPayload,
    bind_node_tool_arguments,
    node_governed_access_posture,
    prepare_node_governed_access,
)
from ithildin_api.nodes import NodeRecord
from ithildin_api.registry import RegisteredTool, ToolRegistry
from ithildin_api.workspaces import (
    WorkspaceRecord,
    WorkspaceRegistry,
    WorkspaceRegistryDocument,
)
from ithildin_schemas import JsonObject, ToolManifest, ToolRisk, sha256_digest

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
POLICY_DIGEST = "sha256:" + ("a" * 64)
MANIFEST_DIGEST = "sha256:" + ("b" * 64)
CONFIGURATION: JsonObject = {
    "schema_version": "1",
    "policy_version": "test-v1",
    "policy_digest": POLICY_DIGEST,
    "manifest_lock_digest": MANIFEST_DIGEST,
    "minimum_node_version": "0.1.0",
    "heartbeat_interval_seconds": 30,
    "offline_posture": "deny_governed_actions",
    "evidence_buffer_max_events": 1000,
    "enforcement_status": "stored_not_enforced",
}
CONFIGURATION_DIGEST = sha256_digest(CONFIGURATION)


def test_node_governed_access_derives_read_only_principal_and_forces_workspace() -> None:
    node = _node()
    payload = _payload()
    context = prepare_node_governed_access(
        node=node,
        desired=_desired(),
        payload=payload,
        principal_registry=_principals(),
        workspace_registry=_workspaces(),
        current_policy_digest=POLICY_DIGEST,
        current_manifest_lock_digest=MANIFEST_DIGEST,
        stale_after_seconds=90,
        now=NOW,
    )
    bound = bind_node_tool_arguments(
        context=context, registered_tool=_tool(), workspace_id="default"
    )

    principal = context.principal_registry.resolve_active(node.principal_id)
    assert principal.roles == [PrincipalRole.AGENT_READ_ONLY]
    assert context.principal == {
        "id": node.principal_id,
        "type": "agent",
        "roles": ["AgentReadOnly"],
    }
    assert bound.arguments == {"path": "README.md", "workspace_id": "default"}
    assert bound.session_id == (
        f"node:{node.node_id}:cfg:1:{CONFIGURATION_DIGEST}:hermes-read"
    )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("stale", "not currently observed"),
        ("acknowledgment", "not acknowledged"),
        ("heartbeat", "heartbeat configuration"),
        ("version", "does not meet"),
        ("policy", "policy is not current"),
        ("manifest", "manifest is not current"),
        ("request", "configuration is not desired"),
    ],
)
def test_node_governed_access_fails_closed_for_authority_drift(
    mutation: str,
    reason: str,
) -> None:
    node = _node()
    desired = _desired()
    payload = _payload()
    if mutation == "stale":
        node = replace(node, last_seen_at=(NOW - timedelta(seconds=91)).isoformat())
    elif mutation == "acknowledgment":
        node = replace(
            node, acknowledged_configuration_digest="sha256:" + ("c" * 64)
        )
    elif mutation == "heartbeat":
        node = replace(node, last_configuration_digest="sha256:" + ("c" * 64))
    elif mutation == "version":
        node = replace(node, last_node_version="0.0.9")
        payload = _payload(node_version="0.0.9")
    elif mutation == "policy":
        desired = _desired(
            configuration={**CONFIGURATION, "policy_digest": "sha256:" + ("c" * 64)}
        )
    elif mutation == "manifest":
        desired = _desired(
            configuration={
                **CONFIGURATION,
                "manifest_lock_digest": "sha256:" + ("c" * 64),
            }
        )
    elif mutation == "request":
        payload = _payload(configuration_generation=2)
    with pytest.raises(NodeGovernedAccessError, match=reason):
        prepare_node_governed_access(
            node=node,
            desired=desired,
            payload=payload,
            principal_registry=_principals(),
            workspace_registry=_workspaces(),
            current_policy_digest=POLICY_DIGEST,
            current_manifest_lock_digest=MANIFEST_DIGEST,
            stale_after_seconds=90,
            now=NOW,
        )


def test_node_governed_access_rejects_profile_tool_and_workspace_expansion() -> None:
    with pytest.raises(NodeGovernedAccessError, match="profile is unavailable"):
        prepare_node_governed_access(
            node=_node(),
            desired=_desired(),
            payload=_payload(),
            principal_registry=PrincipalRegistry({}, Path("principals.yaml")),
            workspace_registry=_workspaces(),
            current_policy_digest=POLICY_DIGEST,
            current_manifest_lock_digest=MANIFEST_DIGEST,
            stale_after_seconds=90,
            now=NOW,
        )
    developer_profile = _principals(role=PrincipalRole.AGENT_DEVELOPER)
    with pytest.raises(NodeGovernedAccessError, match="not read-only"):
        prepare_node_governed_access(
            node=_node(),
            desired=_desired(),
            payload=_payload(),
            principal_registry=developer_profile,
            workspace_registry=_workspaces(),
            current_policy_digest=POLICY_DIGEST,
            current_manifest_lock_digest=MANIFEST_DIGEST,
            stale_after_seconds=90,
            now=NOW,
        )

    context = prepare_node_governed_access(
        node=_node(),
        desired=_desired(),
        payload=_payload(arguments={"path": "README.md", "workspace_id": "other"}),
        principal_registry=_principals(),
        workspace_registry=_workspaces(),
        current_policy_digest=POLICY_DIGEST,
        current_manifest_lock_digest=MANIFEST_DIGEST,
        stale_after_seconds=90,
        now=NOW,
    )
    with pytest.raises(NodeGovernedAccessError, match="workspace mismatch"):
        bind_node_tool_arguments(
            context=context, registered_tool=_tool(), workspace_id="default"
        )
    with pytest.raises(NodeGovernedAccessError, match="limited to read"):
        bind_node_tool_arguments(
            context=replace(context, arguments={"path": "README.md"}),
            registered_tool=_tool(risk=ToolRisk.WRITE),
            workspace_id="default",
        )


def test_node_governed_access_posture_is_explicitly_ready_or_blocked() -> None:
    registry = ToolRegistry({"fs.read": _tool()})
    ready = node_governed_access_posture(
        node=_node(),
        desired=_desired(),
        principal_registry=_principals(),
        workspace_registry=_workspaces(),
        tool_registry=registry,
        current_policy_digest=POLICY_DIGEST,
        current_manifest_lock_digest=MANIFEST_DIGEST,
        stale_after_seconds=90,
        now=NOW,
    )
    blocked = node_governed_access_posture(
        node=_node(),
        desired=None,
        principal_registry=_principals(),
        workspace_registry=_workspaces(),
        tool_registry=registry,
        current_policy_digest=POLICY_DIGEST,
        current_manifest_lock_digest=MANIFEST_DIGEST,
        stale_after_seconds=90,
        now=NOW,
    )

    assert ready["state"] == "ready_read_only"
    assert ready["allowed_tool_count"] == 1
    assert ready["offline_fallback_allowed"] is False
    assert ready["runner_enforcement_proven"] is False
    assert blocked["state"] == "blocked"
    assert blocked["reason_code"] == "configuration_unassigned"


def _node() -> NodeRecord:
    node_id = "node_" + ("1" * 32)
    return NodeRecord(
        node_id=node_id,
        principal_id=f"agent:node.{node_id}",
        workspace_id="default",
        display_name="Governed Node",
        status="enrolled",
        evidence_status="complete",
        public_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        descriptor_hash="sha256:" + ("d" * 64),
        descriptor={},
        enrolled_at=(NOW - timedelta(hours=1)).isoformat(),
        updated_at=NOW.isoformat(),
        last_seen_at=NOW.isoformat(),
        revoked_at=None,
        last_heartbeat_hash="sha256:" + ("e" * 64),
        last_node_version="0.1.0",
        last_configuration_digest=CONFIGURATION_DIGEST,
        last_mission_id="mission-1",
        desired_configuration_generation=1,
        desired_configuration_digest=CONFIGURATION_DIGEST,
        acknowledged_configuration_generation=1,
        acknowledged_configuration_digest=CONFIGURATION_DIGEST,
        acknowledged_configuration_signing_key_id="sha256:" + ("f" * 64),
        acknowledged_active_configuration_signing_key_id="sha256:" + ("f" * 64),
        configuration_acknowledged_at=NOW.isoformat(),
        configuration_acknowledgment_status="stored_not_enforced",
    )


def _desired(configuration: JsonObject = CONFIGURATION) -> NodeConfigurationRecord:
    return NodeConfigurationRecord(
        configuration_id="ncfg_" + ("2" * 32),
        node_id="node_" + ("1" * 32),
        generation=1,
        configuration_digest=CONFIGURATION_DIGEST,
        bundle={"configuration": configuration},
        issued_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(hours=1)).isoformat(),
        evidence_status="complete",
        assignment_kind="assignment",
        rollback_source_generation=None,
    )


def _payload(**updates: object) -> NodeGovernedToolCallPayload:
    document: dict[str, object] = {
        "protocol_version": "1",
        "configuration_generation": 1,
        "configuration_digest": CONFIGURATION_DIGEST,
        "node_version": "0.1.0",
        "session_id": "hermes-read",
        "tool_name": "fs.read",
        "arguments": {"path": "README.md"},
    }
    document.update(updates)
    return NodeGovernedToolCallPayload.model_validate(document)


def _principals(
    *, role: PrincipalRole = PrincipalRole.AGENT_READ_ONLY
) -> PrincipalRegistry:
    profile = PrincipalRecord(
        id=NODE_READ_ONLY_PROFILE_ID,
        type=PrincipalType.AGENT,
        display_name="Node profile",
        roles=[role],
    )
    return PrincipalRegistry({profile.id: profile}, Path("principals.yaml"))


def _workspaces() -> WorkspaceRegistry:
    record = WorkspaceRecord(id="default", root="workspaces", display_name="Default")
    return WorkspaceRegistry(
        document=WorkspaceRegistryDocument(
            version="test", default_workspace_id="default", workspaces=[record]
        ),
        roots={"default": Path("workspaces").resolve()},
        path=Path("workspaces.yaml"),
        required=True,
    )


def _tool(*, risk: ToolRisk = ToolRisk.READ) -> RegisteredTool:
    return RegisteredTool(
        manifest=ToolManifest(
            name="fs.read",
            version="1.0.0",
            title="Read",
            risk=risk,
            category="filesystem",
            mcp={"exposed": True},
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"},
                    "workspace_id": {"type": "string"},
                },
            },
        ),
        manifest_hash="sha256:" + ("9" * 64),
        source_path=Path("fs-read.yaml"),
    )
