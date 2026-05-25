from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ithildin_schemas import (
    ApprovalDecision,
    ApprovalDecisionValue,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    JsonObject,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyInput,
    ToolCallRequest,
    ToolCallResult,
    ToolManifest,
    ToolRisk,
    canonical_json,
    sha256_digest,
)
from pydantic import ValidationError

VALID_HASH = "sha256:" + ("a" * 64)
PREV_HASH = "sha256:" + ("b" * 64)
EVENT_HASH = "sha256:" + ("c" * 64)
NOW = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)


def test_valid_models_construct() -> None:
    ToolManifest(
        name="fs.read",
        version="1.0.0",
        title="Read file",
        risk=ToolRisk.READ,
        category="filesystem",
        input_schema={
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
        mcp={"exposed": True},
        sandbox={"filesystem": {"allowed_mounts": ["/workspace"]}},
        approval={"required": False},
    )
    ToolCallRequest(
        request_id="req_123",
        principal={"id": "agent:local-dev", "roles": ["AgentDeveloper"]},
        tool_name="fs.read",
        arguments={"path": "README.md"},
        session_id="sess_123",
        created_at=NOW,
    )
    ToolCallResult(
        request_id="req_123",
        tool_name="fs.read",
        status="completed",
        content={"text": "ok"},
    )
    PolicyInput(
        principal={"id": "agent:local-dev"},
        tool={"name": "fs.read", "risk": "read"},
        resource={"type": "file", "path": "/workspace/README.md"},
        context={"session_id": "sess_123"},
    )
    PolicyDecision(
        decision=PolicyDecisionValue.ALLOW,
        reason="read within assigned workspace",
        policy_version="2026-05-25.1",
        matched_rules=["allow_agent_read_workspace"],
        obligations={"audit_level": "full"},
    )
    ApprovalRequest(
        approval_id="appr_123",
        request_id="req_123",
        request_hash=VALID_HASH,
        principal={"id": "agent:local-dev"},
        tool_name="fs.apply_patch",
        resource={"path": "/workspace/app.py"},
        status=ApprovalStatus.PENDING,
        summary="Modify app.py",
        expires_at=NOW,
        one_time_scope={"request_id": "req_123", "tool_name": "fs.apply_patch"},
    )
    ApprovalDecision(
        approval_id="appr_123",
        decision=ApprovalDecisionValue.APPROVE,
        decided_by="user:alice",
        decided_at=NOW,
    )
    AuditEvent(
        event_id="evt_123",
        timestamp=NOW,
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_123",
        principal={"id": "agent:local-dev"},
        tool_name="fs.read",
        resource={"path": "/workspace/README.md"},
        decision=PolicyDecisionValue.ALLOW,
        policy_version="2026-05-25.1",
        input_hash=VALID_HASH,
        prev_event_hash=PREV_HASH,
        event_hash=EVENT_HASH,
    )


def test_named_models_reject_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ToolManifest.model_validate(
            {
                "name": "fs.read",
                "version": "1.0.0",
                "title": "Read file",
                "risk": "read",
                "category": "filesystem",
                "input_schema": {"type": "object"},
                "unexpected": True,
            }
        )


def test_missing_required_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ToolCallRequest.model_validate(
            {
                "request_id": "req_123",
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.read",
                "arguments": {},
                "created_at": NOW,
            }
        )


def test_invalid_enum_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ToolManifest.model_validate(
            {
                "name": "fs.read",
                "version": "1.0.0",
                "title": "Read file",
                "risk": "admin",
                "category": "filesystem",
                "input_schema": {"type": "object"},
            }
        )


def test_policy_decision_values_are_limited() -> None:
    for decision in [
        PolicyDecisionValue.ALLOW,
        PolicyDecisionValue.DENY,
        PolicyDecisionValue.REQUIRE_APPROVAL,
    ]:
        model = PolicyDecision(
            decision=decision,
            reason="ok",
            policy_version="2026-05-25.1",
        )
        assert model.decision == decision

    with pytest.raises(ValidationError):
        PolicyDecision.model_validate(
            {
                "decision": "maybe",
                "reason": "not allowed",
                "policy_version": "2026-05-25.1",
            }
        )


def test_invalid_hash_strings_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ApprovalRequest(
            approval_id="appr_123",
            request_id="req_123",
            request_hash="sha256:not-a-real-hash",
            principal={"id": "agent:local-dev"},
            tool_name="fs.apply_patch",
            resource={"path": "/workspace/app.py"},
            status=ApprovalStatus.PENDING,
            summary="Modify app.py",
            expires_at=NOW,
            one_time_scope={"request_id": "req_123"},
        )


def test_approval_request_requires_hash_expiry_and_scope() -> None:
    with pytest.raises(ValidationError):
        ApprovalRequest.model_validate(
            {
                "approval_id": "appr_123",
                "request_id": "req_123",
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "/workspace/app.py"},
                "status": ApprovalStatus.PENDING,
                "summary": "Modify app.py",
            }
        )


def test_audit_event_requires_hash_chain_fields() -> None:
    with pytest.raises(ValidationError):
        AuditEvent.model_validate(
            {
                "event_id": "evt_123",
                "timestamp": NOW,
                "event_type": AuditEventType.POLICY_EVALUATED,
                "request_id": "req_123",
                "principal": {"id": "agent:local-dev"},
            }
        )


def test_datetimes_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        ToolCallRequest(
            request_id="req_123",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
            arguments={},
            session_id="sess_123",
            created_at=datetime(2026, 5, 25, 12, 0),
        )


def test_json_schema_objects_are_accepted() -> None:
    manifest = ToolManifest(
        name="fs.read",
        version="1.0.0",
        title="Read file",
        risk=ToolRisk.READ,
        category="filesystem",
        input_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        },
    )

    assert manifest.input_schema["properties"] == {"path": {"type": "string", "minLength": 1}}


def test_hash_helpers_are_stable_and_canonical() -> None:
    left: JsonObject = {"b": [2, 1], "a": {"z": True, "m": None}}
    right: JsonObject = {"a": {"m": None, "z": True}, "b": [2, 1]}

    assert canonical_json(left) == canonical_json(right)
    assert sha256_digest(left) == sha256_digest(right)
    assert sha256_digest(left).startswith("sha256:")
    assert len(sha256_digest(left)) == 71
