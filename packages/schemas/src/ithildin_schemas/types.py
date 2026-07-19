"""Shared schema type aliases and enums."""

from __future__ import annotations

from enum import StrEnum

from pydantic import JsonValue

JsonObject = dict[str, JsonValue]

__all__ = [
    "ApprovalDecisionValue",
    "ApprovalStatus",
    "AuditEventType",
    "JsonObject",
    "JsonValue",
    "PolicyDecisionValue",
    "ToolRisk",
]


class ToolRisk(StrEnum):
    READ = "read"
    WRITE_PROPOSAL = "write-proposal"
    WRITE = "write"
    NETWORK = "network"
    DESTRUCTIVE = "destructive"


class PolicyDecisionValue(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ApprovalStatus(StrEnum):
    LEGACY_UNBOUND = "legacy_unbound"
    CREATED = "created"
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    DENIED = "denied"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class ApprovalDecisionValue(StrEnum):
    APPROVE = "approve"
    DENY = "deny"


class AuditEventType(StrEnum):
    AGENT_SESSION_STARTED = "agent.session.started"
    NODE_ENROLLMENT_CODE_ISSUED = "node.enrollment_code.issued"
    NODE_ENROLLED = "node.enrolled"
    NODE_HEARTBEAT_ACCEPTED = "node.heartbeat.accepted"
    NODE_IDENTITY_KEY_ROTATION_CHALLENGE_ISSUED = (
        "node.identity_key_rotation.challenge_issued"
    )
    NODE_IDENTITY_KEY_ROTATED = "node.identity_key.rotated"
    NODE_REVOKED = "node.revoked"
    NODE_CONFIGURATION_ASSIGNED = "node.configuration.assigned"
    NODE_CONFIGURATION_ROLLBACK_ASSIGNED = "node.configuration.rollback_assigned"
    NODE_CONFIGURATION_RETRIEVED = "node.configuration.retrieved"
    NODE_CONFIGURATION_ACKNOWLEDGED = "node.configuration.acknowledged"
    NODE_CONFIGURATION_TRUST_TRANSITION_ASSIGNED = (
        "node.configuration_trust_transition.assigned"
    )
    NODE_CONFIGURATION_TRUST_TRANSITION_RETRIEVED = (
        "node.configuration_trust_transition.retrieved"
    )
    NODE_CONFIGURATION_TRUST_TRANSITION_ACKNOWLEDGED = (
        "node.configuration_trust_transition.acknowledged"
    )
    MISSION_ADMISSION_STAGED = "mission.admission.staged"
    MISSION_CLAIM_STAGED = "mission.claim.staged"
    MISSION_CLAIM_EXPIRY_STAGED = "mission.claim_expiry.staged"
    MISSION_CANCELLATION_STAGED = "mission.cancellation.staged"
    MISSION_REPORT_RECEIPT_STAGED = "mission.report_receipt.staged"
    MISSION_REPORT_TRANSITION_STAGED = "mission.report_transition.staged"
    MISSION_CONTROL_OBSERVATION_STAGED = "mission.control_observation.staged"
    MISSION_CONTROL_POLLED = "mission.control.polled"
    TOOL_LIST_REQUESTED = "tool.list.requested"
    TOOL_CALL_PROPOSED = "tool.call.proposed"
    POLICY_EVALUATED = "policy.evaluated"
    APPROVAL_CREATED = "approval.created"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_DENIED = "approval.denied"
    TOOL_EXECUTION_STARTED = "tool.execution.started"
    TOOL_EXECUTION_COMPLETED = "tool.execution.completed"
    TOOL_EXECUTION_FAILED = "tool.execution.failed"
    SANDBOX_DESCRIPTOR_SUBMITTED = "sandbox.descriptor.submitted"
    AUDIT_EXPORTED = "audit.exported"
    POLICY_CHANGED = "policy.changed"
