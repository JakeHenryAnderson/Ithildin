"""Governance-only tool call pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import (
    AuditEventType,
    JsonObject,
    PolicyDecisionValue,
    PolicyInput,
    ToolRisk,
    sha256_digest,
)
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from ithildin_api.approvals import ApprovalService, CreateApprovalInput
from ithildin_api.patches import PATCH_PROPOSE_TOOL, PatchProposalError, PatchProposalService
from ithildin_api.read_tools import ReadToolError, ReadToolExecutor
from ithildin_api.registry import ToolRegistry, UnknownToolDenied


@dataclass(frozen=True)
class GovernedToolCallResult:
    status: str
    request_id: str
    tool_name: str
    content: JsonObject
    is_error: bool = False


class GovernedToolCallService:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_evaluator: PolicyEvaluator,
        approval_service: ApprovalService,
        audit_writer: AuditWriter,
        read_tool_executor: ReadToolExecutor | None = None,
        patch_proposal_service: PatchProposalService | None = None,
    ) -> None:
        self.registry = registry
        self.policy_evaluator = policy_evaluator
        self.approval_service = approval_service
        self.audit_writer = audit_writer
        self.read_tool_executor = read_tool_executor
        self.patch_proposal_service = patch_proposal_service

    def call_tool(
        self,
        *,
        tool_name: str,
        arguments: JsonObject,
        principal: JsonObject,
        session_id: str,
    ) -> GovernedToolCallResult:
        request_id = _new_id("req")
        request_hash = _tool_call_hash(request_id, tool_name, arguments, principal, session_id)

        try:
            registered_tool = self.registry.get_tool(tool_name)
        except UnknownToolDenied as exc:
            self._audit_decision(
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                decision=PolicyDecisionValue.DENY,
                input_hash=request_hash,
                metadata=exc.audit_metadata,
            )
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content={"reason": "unknown tool"},
                is_error=True,
            )

        manifest = registered_tool.manifest
        try:
            validate_json_schema(instance=arguments, schema=manifest.input_schema)
        except JsonSchemaValidationError as exc:
            self._audit_decision(
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                decision=PolicyDecisionValue.DENY,
                input_hash=request_hash,
                metadata={"reason": "invalid tool arguments", "validation_error": exc.message},
            )
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content={"reason": "invalid tool arguments"},
                is_error=True,
            )

        resource = _resource_from_arguments(arguments, manifest.risk)
        policy_input = PolicyInput(
            principal=principal,
            tool={
                "name": manifest.name,
                "risk": manifest.risk.value,
                "version": manifest.version,
                "manifest_hash": registered_tool.manifest_hash,
            },
            resource=resource,
            context={"session_id": session_id},
        )
        policy_decision = self.policy_evaluator.evaluate(policy_input)
        self._audit_decision(
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            decision=policy_decision.decision,
            policy_version=policy_decision.policy_version,
            matched_rules=policy_decision.matched_rules,
            input_hash=request_hash,
            metadata={"reason": policy_decision.reason},
        )

        if policy_decision.decision == PolicyDecisionValue.DENY:
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content={"reason": policy_decision.reason},
                is_error=True,
            )

        if policy_decision.decision == PolicyDecisionValue.REQUIRE_APPROVAL:
            approval = self.approval_service.create_pending(
                CreateApprovalInput(
                    request_id=request_id,
                    request_hash=request_hash,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    summary=f"Approve {tool_name}",
                    one_time_scope={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "manifest_hash": registered_tool.manifest_hash,
                    },
                    metadata={"policy_reason": policy_decision.reason},
                )
            )
            return GovernedToolCallResult(
                status="approval_required",
                request_id=request_id,
                tool_name=tool_name,
                content={
                    "approval_id": approval.approval_id,
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "summary": approval.summary,
                    "expires_at": approval.expires_at.isoformat(),
                    "policy_reason": policy_decision.reason,
                },
            )

        if self.patch_proposal_service is not None and tool_name == PATCH_PROPOSE_TOOL:
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_STARTED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata={"executor": "patch_proposal"},
            )
            try:
                proposal = self.patch_proposal_service.create_proposal(
                    request_id=request_id,
                    principal=principal,
                    path=_string_argument(arguments, "path"),
                    unified_diff=_string_argument(arguments, "unified_diff"),
                )
            except PatchProposalError as exc:
                self._audit_execution(
                    event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    input_hash=request_hash,
                    metadata={"executor": "patch_proposal", "reason": exc.reason},
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content={"reason": exc.reason},
                    is_error=True,
                )

            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata={
                    "executor": "patch_proposal",
                    "proposal_id": proposal.proposal_id,
                    "proposal_hash": proposal.proposal_hash,
                },
            )
            return GovernedToolCallResult(
                status="completed",
                request_id=request_id,
                tool_name=tool_name,
                content=proposal.tool_result(),
            )

        if self.read_tool_executor is not None and self.read_tool_executor.supports(tool_name):
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_STARTED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata={"executor": "in_process_read"},
            )
            try:
                content = self.read_tool_executor.execute(tool_name, arguments)
            except ReadToolError as exc:
                self._audit_execution(
                    event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    input_hash=request_hash,
                    metadata={"executor": "in_process_read", "reason": exc.reason},
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content={"reason": exc.reason},
                    is_error=True,
                )

            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata={"executor": "in_process_read"},
            )
            return GovernedToolCallResult(
                status="completed",
                request_id=request_id,
                tool_name=tool_name,
                content=content,
            )

        return GovernedToolCallResult(
            status="allowed",
            request_id=request_id,
            tool_name=tool_name,
            content={
                "request_id": request_id,
                "tool_name": tool_name,
                "message": "Governance approved; execution is not implemented in this sprint.",
            },
        )

    def _audit_decision(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        tool_name: str,
        decision: PolicyDecisionValue,
        input_hash: str,
        metadata: JsonObject,
        policy_version: str | None = None,
        matched_rules: list[str] | None = None,
    ) -> None:
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            decision=decision,
            policy_version=policy_version,
            matched_rules=matched_rules or [],
            input_hash=input_hash,
            metadata=metadata,
        )

    def _audit_execution(
        self,
        *,
        event_type: AuditEventType,
        request_id: str,
        principal: JsonObject,
        tool_name: str,
        resource: JsonObject,
        input_hash: str,
        metadata: JsonObject,
    ) -> None:
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=event_type,
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            resource=resource,
            input_hash=input_hash,
            metadata=metadata,
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _tool_call_hash(
    request_id: str,
    tool_name: str,
    arguments: JsonObject,
    principal: JsonObject,
    session_id: str,
) -> str:
    return sha256_digest(
        {
            "request_id": request_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "principal": principal,
            "session_id": session_id,
        }
    )


def _resource_from_arguments(arguments: JsonObject, risk: ToolRisk) -> JsonObject:
    resource: JsonObject = {
        "type": "tool_call",
        "in_scope": True,
        "risk": risk.value,
    }
    if "path" in arguments:
        resource["path"] = arguments["path"]
        resource["type"] = "file"
    return resource


def _string_argument(arguments: JsonObject, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str):
        raise PatchProposalError(f"{name} must be a string")
    return value
