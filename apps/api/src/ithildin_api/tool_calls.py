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
    sha256_digest,
)
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from ithildin_api.approvals import ApprovalError, ApprovalService, CreateApprovalInput
from ithildin_api.http_tools import HttpFetchError, HttpFetchExecutor
from ithildin_api.patches import (
    PATCH_APPLY_TOOL,
    PATCH_PROPOSE_TOOL,
    PatchProposalError,
    PatchProposalService,
)
from ithildin_api.read_tools import ReadToolError, ReadToolExecutor
from ithildin_api.redaction import RedactionResult, RedactionService, RedactionSummary
from ithildin_api.registry import ToolRegistry, UnknownToolDenied
from ithildin_api.resources import resource_from_arguments


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
        http_fetch_executor: HttpFetchExecutor | None = None,
        redaction_service: RedactionService | None = None,
    ) -> None:
        self.registry = registry
        self.policy_evaluator = policy_evaluator
        self.approval_service = approval_service
        self.audit_writer = audit_writer
        self.read_tool_executor = read_tool_executor
        self.patch_proposal_service = patch_proposal_service
        self.http_fetch_executor = http_fetch_executor
        self.redaction_service = redaction_service or RedactionService()

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
                content=self._redact_content({"reason": "unknown tool"}).value,
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
                content=self._redact_content({"reason": "invalid tool arguments"}).value,
                is_error=True,
            )

        resource = resource_from_arguments(
            arguments,
            manifest.risk,
            http_allowlist=(
                self.http_fetch_executor.allowlist if self.http_fetch_executor is not None else None
            ),
        )
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
        redaction_keys = _redact_fields(policy_decision.obligations)

        if policy_decision.decision == PolicyDecisionValue.DENY:
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content=self._redact_content(
                    {"reason": policy_decision.reason},
                    extra_keys=redaction_keys,
                ).value,
                is_error=True,
            )

        if policy_decision.decision == PolicyDecisionValue.REQUIRE_APPROVAL:
            if self.patch_proposal_service is not None and tool_name == PATCH_APPLY_TOOL:
                if "approval_id" in arguments:
                    return self._execute_approved_patch(
                        request_id=request_id,
                        principal=principal,
                        tool_name=tool_name,
                        resource=resource,
                        input_hash=request_hash,
                        approval_id=_string_argument(arguments, "approval_id"),
                        redaction_keys=redaction_keys,
                    )
                if "proposal_id" in arguments:
                    try:
                        one_time_scope = self.patch_proposal_service.approval_scope(
                            _string_argument(arguments, "proposal_id"),
                            registered_tool.manifest_hash,
                        )
                    except PatchProposalError as exc:
                        return GovernedToolCallResult(
                            status="denied",
                            request_id=request_id,
                            tool_name=tool_name,
                            content=self._redact_content(
                                {"reason": exc.reason},
                                extra_keys=redaction_keys,
                            ).value,
                            is_error=True,
                        )
                    approval = self.approval_service.create_pending(
                        CreateApprovalInput(
                            request_id=request_id,
                            request_hash=request_hash,
                            principal=principal,
                            tool_name=tool_name,
                            resource=resource,
                            summary=f"Apply patch {one_time_scope['proposal_id']}",
                            one_time_scope=one_time_scope,
                            metadata={
                                "policy_reason": policy_decision.reason,
                                "proposal_id": one_time_scope["proposal_id"],
                                "proposal_hash": one_time_scope["proposal_hash"],
                            },
                        )
                    )
                    content = self._redact_content(
                        {
                            "approval_id": approval.approval_id,
                            "request_id": request_id,
                            "tool_name": tool_name,
                            "proposal_id": one_time_scope["proposal_id"],
                            "proposal_hash": one_time_scope["proposal_hash"],
                            "path": one_time_scope["path"],
                            "summary": approval.summary,
                            "expires_at": approval.expires_at.isoformat(),
                            "policy_reason": policy_decision.reason,
                        },
                        extra_keys=redaction_keys,
                    ).value
                    return GovernedToolCallResult(
                        status="approval_required",
                        request_id=request_id,
                        tool_name=tool_name,
                        content=content,
                    )

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
            content = self._redact_content(
                {
                    "approval_id": approval.approval_id,
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "summary": approval.summary,
                    "expires_at": approval.expires_at.isoformat(),
                    "policy_reason": policy_decision.reason,
                },
                extra_keys=redaction_keys,
            ).value
            return GovernedToolCallResult(
                status="approval_required",
                request_id=request_id,
                tool_name=tool_name,
                content=content,
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
                redacted = self._redact_content(
                    {"reason": exc.reason},
                    extra_keys=redaction_keys,
                )
                self._audit_execution(
                    event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    input_hash=request_hash,
                    metadata=_with_redaction_summary(
                        {"executor": "patch_proposal", "reason": exc.reason},
                        redacted.summary,
                    ),
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content=redacted.value,
                    is_error=True,
                )

            redacted = self._redact_content(proposal.tool_result(), extra_keys=redaction_keys)
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata=_with_redaction_summary(
                    {
                        "executor": "patch_proposal",
                        "proposal_id": proposal.proposal_id,
                        "proposal_hash": proposal.proposal_hash,
                    },
                    redacted.summary,
                ),
            )
            return GovernedToolCallResult(
                status="completed",
                request_id=request_id,
                tool_name=tool_name,
                content=redacted.value,
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
                redacted = self._redact_content(
                    {"reason": exc.reason},
                    extra_keys=redaction_keys,
                )
                self._audit_execution(
                    event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    input_hash=request_hash,
                    metadata=_with_redaction_summary(
                        {"executor": "in_process_read", "reason": exc.reason},
                        redacted.summary,
                    ),
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content=redacted.value,
                    is_error=True,
                )

            redacted = self._redact_content(content, extra_keys=redaction_keys)
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata=_with_redaction_summary(
                    {"executor": "in_process_read"},
                    redacted.summary,
                ),
            )
            return GovernedToolCallResult(
                status="completed",
                request_id=request_id,
                tool_name=tool_name,
                content=redacted.value,
            )

        if self.http_fetch_executor is not None and self.http_fetch_executor.supports(tool_name):
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_STARTED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata={"executor": "in_process_http"},
            )
            try:
                content = self.http_fetch_executor.execute(tool_name, arguments)
            except HttpFetchError as exc:
                redacted = self._redact_content(
                    {"reason": exc.reason},
                    extra_keys=redaction_keys,
                )
                self._audit_execution(
                    event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    resource=resource,
                    input_hash=request_hash,
                    metadata=_with_redaction_summary(
                        {"executor": "in_process_http", "reason": exc.reason},
                        redacted.summary,
                    ),
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content=redacted.value,
                    is_error=True,
                )

            redacted = self._redact_content(content, extra_keys=redaction_keys)
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=request_hash,
                metadata=_with_redaction_summary(
                    {"executor": "in_process_http"},
                    redacted.summary,
                ),
            )
            return GovernedToolCallResult(
                status="completed",
                request_id=request_id,
                tool_name=tool_name,
                content=redacted.value,
            )

        redacted = self._redact_content(
            {
                "request_id": request_id,
                "tool_name": tool_name,
                "message": "Governance approved; execution is not implemented in this sprint.",
            },
            extra_keys=redaction_keys,
        )
        return GovernedToolCallResult(
            status="allowed",
            request_id=request_id,
            tool_name=tool_name,
            content=redacted.value,
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

    def _execute_approved_patch(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        tool_name: str,
        resource: JsonObject,
        input_hash: str,
        approval_id: str,
        redaction_keys: set[str] | None = None,
    ) -> GovernedToolCallResult:
        if self.patch_proposal_service is None:
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content=self._redact_content(
                    {"reason": "patch application is not configured"},
                    extra_keys=redaction_keys,
                ).value,
                is_error=True,
            )

        self._audit_execution(
            event_type=AuditEventType.TOOL_EXECUTION_STARTED,
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            resource=resource,
            input_hash=input_hash,
            metadata={"executor": "patch_apply", "approval_id": approval_id},
        )
        try:
            proposal = self.patch_proposal_service.apply_approved(
                approval_service=self.approval_service,
                approval_id=approval_id,
            )
        except (ApprovalError, PatchProposalError) as exc:
            redacted = self._redact_content(
                {"reason": str(exc)},
                extra_keys=redaction_keys,
            )
            self._audit_execution(
                event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=input_hash,
                metadata=_with_redaction_summary(
                    {
                        "executor": "patch_apply",
                        "approval_id": approval_id,
                        "reason": str(exc),
                    },
                    redacted.summary,
                ),
            )
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content=redacted.value,
                is_error=True,
            )

        content: JsonObject = {
            "approval_id": approval_id,
            "proposal_id": proposal.proposal_id,
            "proposal_hash": proposal.proposal_hash,
            "path": proposal.path,
            "proposal_status": proposal.status,
        }
        redacted = self._redact_content(content, extra_keys=redaction_keys)
        self._audit_execution(
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            resource=resource,
            input_hash=input_hash,
            metadata=_with_redaction_summary(
                {
                    "executor": "patch_apply",
                    "approval_id": approval_id,
                    "proposal_id": proposal.proposal_id,
                    "proposal_hash": proposal.proposal_hash,
                },
                redacted.summary,
            ),
        )
        return GovernedToolCallResult(
            status="completed",
            request_id=request_id,
            tool_name=tool_name,
            content=redacted.value,
        )

    def _redact_content(
        self,
        content: JsonObject,
        *,
        extra_keys: set[str] | None = None,
    ) -> RedactionResult:
        return self.redaction_service.redact(content, extra_keys=extra_keys)

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


def _with_redaction_summary(metadata: JsonObject, summary: RedactionSummary) -> JsonObject:
    return {**metadata, **summary.as_metadata()}


def _redact_fields(obligations: JsonObject) -> set[str]:
    redact_fields = obligations.get("redact_fields")
    if not isinstance(redact_fields, list):
        return set()
    return {field for field in redact_fields if isinstance(field, str)}


def _string_argument(arguments: JsonObject, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str):
        raise PatchProposalError(f"{name} must be a string")
    return value
