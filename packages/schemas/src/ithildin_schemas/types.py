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
