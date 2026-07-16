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
    NODE_REVOKED = "node.revoked"
    NODE_CONFIGURATION_ASSIGNED = "node.configuration.assigned"
    NODE_CONFIGURATION_ROLLBACK_ASSIGNED = "node.configuration.rollback_assigned"
    NODE_CONFIGURATION_RETRIEVED = "node.configuration.retrieved"
    NODE_CONFIGURATION_ACKNOWLEDGED = "node.configuration.acknowledged"
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
