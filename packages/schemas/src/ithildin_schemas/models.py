"""Pydantic models shared across Ithildin components."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


def _validate_optional_timezone(value: Optional[datetime]) -> Optional[datetime]:
    return _validate_timezone(value) if value is not None else None


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
    approval_contract_version: str = Field(pattern=r"^[12]$")
    requester_principal_id: Optional[str] = None
    requester_principal_generation: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    deciding_principal_id: Optional[str] = None
    deciding_principal_generation: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    decided_at: Optional[datetime] = None
    decision_reason_hash: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    decision_authority_snapshot_hash: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    decision_hash: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    executor_principal_id: Optional[str] = None
    executor_principal_generation: Optional[str] = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )

    _expires_at_must_have_timezone = field_validator("expires_at")(_validate_timezone)
    _decided_at_must_have_timezone = field_validator("decided_at")(
        _validate_optional_timezone
    )

    @model_validator(mode="after")
    def _authority_fields_match_contract(self) -> ApprovalRequest:
        decision_values = (
            self.deciding_principal_id,
            self.deciding_principal_generation,
            self.decided_at,
            self.decision_reason_hash,
            self.decision_hash,
        )
        if self.approval_contract_version == "2":
            if self.requester_principal_id is None or self.requester_principal_generation is None:
                raise ValueError("version-2 approval requester authority is required")
            decision_statuses = {
                ApprovalStatus.APPROVED,
                ApprovalStatus.DENIED,
                ApprovalStatus.EXECUTING,
                ApprovalStatus.EXECUTED,
                ApprovalStatus.FAILED,
            }
            if self.status in decision_statuses and not all(
                value is not None for value in decision_values
            ):
                raise ValueError("version-2 terminal approval decision authority is required")
            if self.status in {ApprovalStatus.CREATED, ApprovalStatus.PENDING} and any(
                value is not None for value in decision_values
            ):
                raise ValueError("version-2 nonterminal approval cannot claim a decision")
        elif any(
            value is not None
            for value in (
                self.requester_principal_id,
                self.requester_principal_generation,
                self.deciding_principal_id,
                self.deciding_principal_generation,
                self.decided_at,
                self.decision_reason_hash,
                self.decision_authority_snapshot_hash,
                self.decision_hash,
                self.executor_principal_id,
                self.executor_principal_generation,
            )
        ):
            raise ValueError("legacy approval cannot claim version-2 authority")
        if any(value is not None for value in decision_values) and not all(
            value is not None for value in decision_values
        ):
            raise ValueError("approval decision authority must be complete")
        executor_values = (
            self.executor_principal_id,
            self.executor_principal_generation,
        )
        if any(value is not None for value in executor_values) and not all(
            value is not None for value in executor_values
        ):
            raise ValueError("approval executor authority must be complete")
        return self


class ApprovalDecision(StrictBaseModel):
    approval_id: str
    decision: ApprovalDecisionValue
    deciding_principal_id: str
    deciding_principal_generation: str = Field(pattern=SHA256_PATTERN)
    decided_at: datetime
    reason_hash: str = Field(pattern=SHA256_PATTERN)
    authority_snapshot_hash: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    decision_hash: str = Field(pattern=SHA256_PATTERN)

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
