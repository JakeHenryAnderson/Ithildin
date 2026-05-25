"""Pydantic models shared across Ithildin components."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ithildin_schemas.types import (
    ApprovalDecisionValue,
    ApprovalStatus,
    AuditEventType,
    JsonObject,
    JsonValue,
    PolicyDecisionValue,
    ToolRisk,
)

SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("datetime must be timezone-aware")
    return value


class ToolManifest(StrictBaseModel):
    name: str
    version: str
    title: str
    risk: ToolRisk
    category: str
    input_schema: JsonObject
    mcp: Optional[JsonObject] = None
    sandbox: Optional[JsonObject] = None
    approval: Optional[JsonObject] = None
    metadata: JsonObject = Field(default_factory=dict)


class ToolCallRequest(StrictBaseModel):
    request_id: str
    principal: JsonObject
    tool_name: str
    arguments: JsonObject
    session_id: str
    created_at: datetime

    _created_at_must_have_timezone = field_validator("created_at")(_validate_timezone)


class ToolCallResult(StrictBaseModel):
    request_id: str
    tool_name: str
    status: str
    content: JsonValue
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: JsonObject = Field(default_factory=dict)


class PolicyInput(StrictBaseModel):
    principal: JsonObject
    tool: JsonObject
    resource: JsonObject
    context: JsonObject


class PolicyDecision(StrictBaseModel):
    decision: PolicyDecisionValue
    reason: str
    policy_version: str
    matched_rules: list[str] = Field(default_factory=list)
    obligations: JsonObject = Field(default_factory=dict)


class ApprovalRequest(StrictBaseModel):
    approval_id: str
    request_id: str
    request_hash: str = Field(pattern=SHA256_PATTERN)
    principal: JsonObject
    tool_name: str
    resource: JsonObject
    status: ApprovalStatus
    summary: str
    expires_at: datetime
    one_time_scope: JsonObject
    metadata: JsonObject = Field(default_factory=dict)

    _expires_at_must_have_timezone = field_validator("expires_at")(_validate_timezone)


class ApprovalDecision(StrictBaseModel):
    approval_id: str
    decision: ApprovalDecisionValue
    decided_by: str
    decided_at: datetime
    reason: Optional[str] = None

    _decided_at_must_have_timezone = field_validator("decided_at")(_validate_timezone)


class AuditEvent(StrictBaseModel):
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    request_id: str
    principal: JsonObject
    tool_name: Optional[str] = None
    resource: Optional[JsonObject] = None
    decision: Optional[PolicyDecisionValue] = None
    policy_version: Optional[str] = None
    matched_rules: list[str] = Field(default_factory=list)
    input_hash: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    redactions: list[str] = Field(default_factory=list)
    metadata: JsonObject = Field(default_factory=dict)
    prev_event_hash: str = Field(pattern=SHA256_PATTERN)
    event_hash: str = Field(pattern=SHA256_PATTERN)

    _timestamp_must_have_timezone = field_validator("timestamp")(_validate_timezone)
