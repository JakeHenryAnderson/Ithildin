"""Governance-only tool call pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEngine
from ithildin_schemas import (
    AuditEventType,
    JsonObject,
    JsonValue,
    PolicyDecisionValue,
    PolicyInput,
    sha256_digest,
)
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema
from jsonschema.exceptions import SchemaError as JsonSchemaSchemaError

from ithildin_api.agent_runs import AgentRunContext, AgentRunStore
from ithildin_api.approvals import ApprovalError, ApprovalService, CreateApprovalInput
from ithildin_api.decision_evidence import policy_decision_evidence
from ithildin_api.http_tools import HttpFetchError, HttpFetchExecutor
from ithildin_api.identity import (
    PrincipalRegistry,
    PrincipalRegistryError,
    can_access_risk,
    principal_denial_metadata,
    resolve_trusted_principal,
)
from ithildin_api.patches import (
    PATCH_APPLY_TOOL,
    PATCH_PROPOSE_TOOL,
    PatchProposal,
    PatchProposalError,
    PatchProposalService,
)
from ithildin_api.read_tools import ReadToolError, ReadToolExecutor
from ithildin_api.redaction import RedactionResult, RedactionService, RedactionSummary
from ithildin_api.registry import ToolRegistry, UnknownToolDenied
from ithildin_api.resources import resource_from_arguments
from ithildin_api.schema_validation import safe_json_schema_error
from ithildin_api.telemetry import Telemetry, safe_span_attributes


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
        policy_evaluator: PolicyEngine,
        approval_service: ApprovalService,
        audit_writer: AuditWriter,
        read_tool_executor: ReadToolExecutor | None = None,
        patch_proposal_service: PatchProposalService | None = None,
        http_fetch_executor: HttpFetchExecutor | None = None,
        redaction_service: RedactionService | None = None,
        principal_registry: PrincipalRegistry | None = None,
        telemetry: Telemetry | None = None,
        agent_run_store: AgentRunStore | None = None,
    ) -> None:
        self.registry = registry
        self.policy_evaluator = policy_evaluator
        self.approval_service = approval_service
        self.audit_writer = audit_writer
        self.read_tool_executor = read_tool_executor
        self.patch_proposal_service = patch_proposal_service
        self.http_fetch_executor = http_fetch_executor
        self.redaction_service = redaction_service or RedactionService()
        self.principal_registry = principal_registry
        self.agent_run_store = agent_run_store
        self.telemetry = telemetry or Telemetry(
            enabled=False,
            service_name="ithildin-api",
            console_export=False,
            otlp_endpoint="",
        )

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
        agent_run: AgentRunContext | None = None

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
        if self.principal_registry is not None:
            try:
                principal_record = resolve_trusted_principal(self.principal_registry, principal)
            except PrincipalRegistryError as exc:
                self._audit_decision(
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    decision=PolicyDecisionValue.DENY,
                    input_hash=request_hash,
                    metadata=principal_denial_metadata(str(exc)),
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content=self._redact_content({"reason": str(exc)}).value,
                    is_error=True,
                )

            principal = principal_record.trusted_principal()
            request_hash = _tool_call_hash(request_id, tool_name, arguments, principal, session_id)
            if not can_access_risk(principal_record, manifest.risk):
                reason = (
                    f"principal {principal_record.id} is not authorized "
                    f"for {manifest.risk.value} tools"
                )
                self._audit_decision(
                    request_id=request_id,
                    principal=principal,
                    tool_name=tool_name,
                    decision=PolicyDecisionValue.DENY,
                    input_hash=request_hash,
                    metadata={
                        **principal_denial_metadata(reason),
                        "manifest_hash": registered_tool.manifest_hash,
                        "tool_risk": manifest.risk.value,
                    },
                )
                return GovernedToolCallResult(
                    status="denied",
                    request_id=request_id,
                    tool_name=tool_name,
                    content=self._redact_content({"reason": reason}).value,
                    is_error=True,
                )

        try:
            validate_json_schema(instance=arguments, schema=manifest.input_schema)
        except (JsonSchemaValidationError, JsonSchemaSchemaError) as exc:
            self._audit_decision(
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                decision=PolicyDecisionValue.DENY,
                input_hash=request_hash,
                metadata={
                    "reason": "invalid tool arguments",
                    "validation_error": safe_json_schema_error(exc),
                },
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
            tool_name=manifest.name,
            http_allowlist=(
                self.http_fetch_executor.allowlist if self.http_fetch_executor is not None else None
            ),
            read_tool_executor=self.read_tool_executor,
        )
        agent_run = self._ensure_agent_run(
            principal=principal,
            session_id=session_id,
            workspace_id=_workspace_id_for_resource(resource, self.read_tool_executor),
            request_id=request_id,
            tool_name=tool_name,
            resource=resource,
            input_hash=request_hash,
            tool_manifest_hash=registered_tool.manifest_hash,
        )
        if resource.get("in_scope") is False:
            reason = _resource_scope_denial_reason(resource)
            self._audit_decision(
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                decision=PolicyDecisionValue.DENY,
                input_hash=request_hash,
                metadata={"reason": reason, "resource": resource},
                agent_run=agent_run,
            )
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content=self._redact_content({"reason": reason}).value,
                is_error=True,
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
        with self.telemetry.start_span(
            "ithildin.tool.policy_evaluate",
            safe_span_attributes(
                tool_name=manifest.name,
                tool_risk=manifest.risk.value,
                policy_engine=self.policy_evaluator.engine_name,
                resource_type=resource.get("type"),
            ),
        ):
            policy_decision = self.policy_evaluator.evaluate(policy_input)
        decision_evidence = policy_decision_evidence(
            policy_engine=self.policy_evaluator.engine_name,
            policy_hash=self.policy_evaluator.policy_hash,
            policy_document_version=self.policy_evaluator.document_version,
            policy_input=policy_input,
            policy_decision=policy_decision,
        )
        self._audit_decision(
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            decision=policy_decision.decision,
            policy_version=policy_decision.policy_version,
            matched_rules=policy_decision.matched_rules,
            input_hash=request_hash,
            metadata=decision_evidence,
            agent_run=agent_run,
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
                        manifest_hash=registered_tool.manifest_hash,
                        manifest_version=manifest.version,
                        tool_input_schema_hash=sha256_digest(manifest.input_schema),
                        policy_engine=self.policy_evaluator.engine_name,
                        policy_hash=self.policy_evaluator.policy_hash,
                        policy_version=policy_decision.policy_version,
                        policy_document_version=self.policy_evaluator.document_version,
                        matched_rules=policy_decision.matched_rules,
                        redaction_keys=redaction_keys,
                        agent_run=agent_run,
                    )
                if "proposal_id" in arguments:
                    approval_expires_at = datetime.now(UTC) + self.approval_service.default_expiry
                    try:
                        one_time_scope = self.patch_proposal_service.approval_scope(
                            _string_argument(arguments, "proposal_id"),
                            manifest_hash=registered_tool.manifest_hash,
                            manifest_version=manifest.version,
                            tool_input_schema_hash=sha256_digest(manifest.input_schema),
                            policy_engine=self.policy_evaluator.engine_name,
                            policy_hash=self.policy_evaluator.policy_hash,
                            policy_version=policy_decision.policy_version,
                            policy_document_version=self.policy_evaluator.document_version,
                            matched_rules=policy_decision.matched_rules,
                            requesting_principal=principal,
                            request_hash=request_hash,
                            expires_at=approval_expires_at,
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
                            expires_at=approval_expires_at,
                            metadata=cast(JsonObject, {
                                "policy_reason": policy_decision.reason,
                                "policy_engine": self.policy_evaluator.engine_name,
                                "policy_hash": self.policy_evaluator.policy_hash,
                                "policy_version": policy_decision.policy_version,
                                "policy_document_version": self.policy_evaluator.document_version,
                                "matched_rules": policy_decision.matched_rules,
                                "manifest_hash": registered_tool.manifest_hash,
                                "manifest_version": manifest.version,
                                "tool_input_schema_hash": sha256_digest(manifest.input_schema),
                                "approval_scope_hash": sha256_digest(one_time_scope),
                                "proposal_id": one_time_scope["proposal_id"],
                                "proposal_hash": one_time_scope["proposal_hash"],
                                "base_file_hash": one_time_scope["base_file_hash"],
                                **_agent_run_metadata(agent_run),
                            }),
                        )
                    )
                    content = self._redact_content(
                        {
                            "approval_id": approval.approval_id,
                            "request_id": request_id,
                            "tool_name": tool_name,
                            "proposal_id": one_time_scope["proposal_id"],
                            "proposal_hash": one_time_scope["proposal_hash"],
                            "workspace_id": one_time_scope["workspace_id"],
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
                    metadata={
                        "policy_reason": policy_decision.reason,
                        **_agent_run_metadata(agent_run),
                    },
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
                agent_run=agent_run,
            )
            try:
                with self.telemetry.start_span(
                    "ithildin.tool.execute",
                    safe_span_attributes(tool_name=tool_name, executor="patch_proposal"),
                ):
                    proposal = self.patch_proposal_service.create_proposal(
                        request_id=request_id,
                        principal=principal,
                        path=_string_argument(arguments, "path"),
                        unified_diff=_string_argument(arguments, "unified_diff"),
                        workspace_id=_optional_string_argument(arguments, "workspace_id"),
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
                    agent_run=agent_run,
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
                        "workspace_id": proposal.workspace_id,
                    },
                    redacted.summary,
                ),
                agent_run=agent_run,
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
                agent_run=agent_run,
            )
            try:
                with self.telemetry.start_span(
                    "ithildin.tool.execute",
                    safe_span_attributes(tool_name=tool_name, executor="in_process_read"),
                ):
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
                    agent_run=agent_run,
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
                    _read_tool_execution_metadata(tool_name, content),
                    redacted.summary,
                ),
                agent_run=agent_run,
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
                agent_run=agent_run,
            )
            try:
                with self.telemetry.start_span(
                    "ithildin.tool.execute",
                    safe_span_attributes(tool_name=tool_name, executor="in_process_http"),
                ):
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
                    agent_run=agent_run,
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
                agent_run=agent_run,
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

    def deny_tool_call(
        self,
        *,
        tool_name: str,
        arguments: JsonObject,
        principal: JsonObject,
        session_id: str,
        reason: str,
        metadata: JsonObject,
    ) -> GovernedToolCallResult:
        """Record a safe pre-policy denial for an ingress-layer guardrail."""
        request_id = _new_id("req")
        input_hash = _tool_call_hash(request_id, tool_name, arguments, principal, session_id)
        self._audit_decision(
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            decision=PolicyDecisionValue.DENY,
            input_hash=input_hash,
            metadata={"reason": reason, **metadata},
        )
        return GovernedToolCallResult(
            status="denied",
            request_id=request_id,
            tool_name=tool_name,
            content=self._redact_content({"reason": reason}).value,
            is_error=True,
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
        agent_run: AgentRunContext | None = None,
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
            metadata=_metadata_with_agent_run(metadata, agent_run),
        )

    def _ensure_agent_run(
        self,
        *,
        principal: JsonObject,
        session_id: str,
        workspace_id: str,
        request_id: str,
        tool_name: str,
        resource: JsonObject,
        input_hash: str,
        tool_manifest_hash: str,
    ) -> AgentRunContext | None:
        if self.agent_run_store is None:
            return None
        agent_run, created = self.agent_run_store.ensure_for_tool_call(
            principal=principal,
            session_id=session_id,
            workspace_id=workspace_id,
            request_id=request_id,
            tool_name=tool_name,
            policy_hash=self.policy_evaluator.policy_hash,
            tool_manifest_hash=tool_manifest_hash,
        )
        if created:
            self.audit_writer.write_event(
                event_id=_new_id("evt"),
                event_type=AuditEventType.AGENT_SESSION_STARTED,
                request_id=request_id,
                principal=principal,
                tool_name=tool_name,
                resource=resource,
                input_hash=input_hash,
                metadata={
                    **agent_run.metadata(),
                    "status": "active",
                    "created_by": "governed_tool_call",
                },
            )
        return agent_run

    def _execute_approved_patch(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        tool_name: str,
        resource: JsonObject,
        input_hash: str,
        approval_id: str,
        manifest_hash: str,
        manifest_version: str,
        tool_input_schema_hash: str,
        policy_engine: str,
        policy_hash: str,
        policy_version: str,
        policy_document_version: str,
        matched_rules: list[str],
        redaction_keys: set[str] | None = None,
        agent_run: AgentRunContext | None = None,
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
            agent_run=agent_run,
        )
        completed_redacted: RedactionResult | None = None

        def write_completion_audit(proposal: PatchProposal) -> None:
            nonlocal completed_redacted
            proposal_id = proposal.proposal_id
            proposal_hash = proposal.proposal_hash
            base_file_hash = proposal.base_file_hash
            workspace_id = proposal.workspace_id
            path = proposal.path
            proposal_status = proposal.status
            completed_content: JsonObject = {
                "approval_id": approval_id,
                "proposal_id": proposal_id,
                "proposal_hash": proposal_hash,
                "workspace_id": workspace_id,
                "path": path,
                "proposal_status": proposal_status,
            }
            completed_redacted = self._redact_content(
                completed_content,
                extra_keys=redaction_keys,
            )
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
                        "approval_binding_verified": True,
                        "proposal_id": proposal_id,
                        "proposal_hash": proposal_hash,
                        "base_file_hash": base_file_hash,
                        "workspace_id": workspace_id,
                        "manifest_hash": manifest_hash,
                        "manifest_version": manifest_version,
                        "policy_hash": policy_hash,
                        "policy_version": policy_version,
                    },
                    completed_redacted.summary,
                ),
                agent_run=agent_run,
            )

        try:
            with self.telemetry.start_span(
                "ithildin.tool.execute",
                safe_span_attributes(tool_name=tool_name, executor="patch_apply"),
            ):
                proposal = self.patch_proposal_service.apply_approved(
                    approval_service=self.approval_service,
                    approval_id=approval_id,
                    expected_manifest_hash=manifest_hash,
                    expected_manifest_version=manifest_version,
                    expected_tool_input_schema_hash=tool_input_schema_hash,
                    expected_policy_engine=policy_engine,
                    expected_policy_hash=policy_hash,
                    expected_policy_version=policy_version,
                    expected_policy_document_version=policy_document_version,
                    expected_matched_rules=matched_rules,
                    expected_principal=principal,
                    completion_hook=write_completion_audit,
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
                        "approval_binding_verified": False,
                        "reason": str(exc),
                    },
                    redacted.summary,
                ),
                agent_run=agent_run,
            )
            return GovernedToolCallResult(
                status="denied",
                request_id=request_id,
                tool_name=tool_name,
                content=redacted.value,
                is_error=True,
            )

        if completed_redacted is None:
            completed_redacted = self._redact_content(
                {
                    "approval_id": approval_id,
                    "proposal_id": proposal.proposal_id,
                    "proposal_hash": proposal.proposal_hash,
                    "workspace_id": proposal.workspace_id,
                    "path": proposal.path,
                    "proposal_status": proposal.status,
                },
                extra_keys=redaction_keys,
            )
        return GovernedToolCallResult(
            status="completed",
            request_id=request_id,
            tool_name=tool_name,
            content=completed_redacted.value,
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
        agent_run: AgentRunContext | None = None,
    ) -> None:
        self.audit_writer.write_event(
            event_id=_new_id("evt"),
            event_type=event_type,
            request_id=request_id,
            principal=principal,
            tool_name=tool_name,
            resource=resource,
            input_hash=input_hash,
            metadata=_metadata_with_agent_run(metadata, agent_run),
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


def _metadata_with_agent_run(
    metadata: JsonObject,
    agent_run: AgentRunContext | None,
) -> JsonObject:
    if agent_run is None:
        return metadata
    return {**metadata, **agent_run.metadata()}


def _agent_run_metadata(agent_run: AgentRunContext | None) -> JsonObject:
    return agent_run.metadata() if agent_run is not None else {}


def _workspace_id_for_resource(
    resource: JsonObject,
    read_tool_executor: ReadToolExecutor | None,
) -> str:
    workspace_id = resource.get("workspace_id")
    if isinstance(workspace_id, str) and workspace_id:
        return workspace_id
    resource_type = resource.get("type")
    if isinstance(resource_type, str) and resource_type in {"network", "http"}:
        return "network"
    if read_tool_executor is not None:
        return read_tool_executor.default_workspace_id
    return "unscoped"


def _read_tool_execution_metadata(tool_name: str, content: JsonObject) -> JsonObject:
    metadata: JsonObject = {"executor": "in_process_read"}
    if tool_name in {
        "project.dependency.summary",
        "project.manifest.summary",
        "project.structure.summary",
        "project.test.summary",
        "project.docs.summary",
        "project.config.summary",
        "project.ci.summary",
        "project.language.summary",
    }:
        output_policy = content.get("output_policy")
        for key in ("manifest_count",):
            value = content.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                metadata[key] = value
        if tool_name == "project.dependency.summary":
            value = content.get("total_direct_dependency_count")
            if isinstance(value, int) and not isinstance(value, bool):
                metadata["total_direct_dependency_count"] = value
        if tool_name == "project.structure.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_directory_count",
                    "visible_file_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in ("directory_categories", "file_kinds", "skipped_counts"):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        if tool_name == "project.test.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_test_directory_count",
                    "visible_test_file_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in (
                "framework_hints",
                "test_location_counts",
                "language_family_counts",
                "skipped_counts",
            ):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        if tool_name == "project.docs.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_documentation_directory_count",
                    "visible_documentation_file_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in (
                "documentation_type_counts",
                "documentation_location_counts",
                "language_family_counts",
                "skipped_counts",
            ):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        if tool_name == "project.config.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_config_directory_count",
                    "visible_config_like_file_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in (
                "config_category_counts",
                "config_location_counts",
                "skipped_counts",
            ):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        if tool_name == "project.ci.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_ci_directory_count",
                    "visible_ci_config_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in (
                "provider_counts",
                "trigger_category_counts",
                "job_category_counts",
                "location_bucket_counts",
                "skipped_counts",
            ):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        if tool_name == "project.language.summary":
            summary = content.get("summary")
            if isinstance(summary, dict):
                for key in (
                    "visible_source_directory_count",
                    "visible_source_like_file_count",
                    "max_observed_depth",
                    "inspected_entry_count",
                ):
                    value = summary.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        metadata[key] = value
            for section_key in (
                "language_family_counts",
                "extension_family_counts",
                "source_location_counts",
                "skipped_counts",
            ):
                section = content.get(section_key)
                if isinstance(section, dict):
                    metadata[f"{section_key}_keys"] = cast(
                        JsonValue,
                        sorted(key for key in section if isinstance(key, str)),
                    )
        truncated = content.get("truncated")
        if isinstance(truncated, bool):
            metadata["truncated"] = truncated
        root = content.get("root")
        if isinstance(root, str):
            metadata["root"] = root
        manifests = content.get("manifests")
        if isinstance(manifests, list):
            kinds = []
            parse_statuses = []
            for item in manifests:
                if isinstance(item, dict):
                    kind = item.get("kind")
                    parse_status = item.get("parse_status")
                    if isinstance(kind, str):
                        kinds.append(kind)
                    if isinstance(parse_status, str):
                        parse_statuses.append(parse_status)
            metadata["manifest_kinds"] = cast(JsonValue, kinds)
            metadata["parse_statuses"] = cast(JsonValue, parse_statuses)
        if isinstance(output_policy, dict):
            for key in (
                "file_contents_included",
                "raw_recursive_listing_included",
                "raw_paths_included",
                "raw_file_names_included",
                "raw_sensitive_paths_included",
                "test_file_names_included",
                "test_case_names_included",
                "documentation_file_names_included",
                "language_file_names_included",
                "config_file_names_included",
                "documentation_headings_included",
                "raw_extensions_included",
                "stable_path_ids_included",
                "source_snippets_included",
                "config_contents_included",
                "config_values_included",
                "dependency_names_included",
                "dependency_versions_included",
                "package_names_included",
                "package_script_names_included",
                "package_script_values_included",
                "environment_names_or_values_included",
                "registry_urls_included",
                "coverage_data_included",
                "documentation_build_claims_included",
                "language_detector_claims_included",
                "command_discovery_included",
                "test_pass_fail_claims_included",
                "command_output_included",
                "lockfile_contents_included",
                "registry_or_network_access_used",
                "package_manager_execution_used",
                "test_execution_used",
                "documentation_build_execution_used",
                "language_detector_execution_used",
                "config_parser_execution_used",
                "recursive_discovery_used",
                "transitive_dependencies_resolved",
                "license_vulnerability_or_compliance_claims_included",
            ):
                value = output_policy.get(key)
                if isinstance(value, bool):
                    metadata[key] = value
        return metadata

    if tool_name == "git.show.tag_metadata":
        selector = content.get("selector")
        output_policy = content.get("output_policy")
        if isinstance(selector, dict) and isinstance(selector.get("kind"), str):
            metadata["selector_kind"] = selector["kind"]
        for key in ("tag_count", "total_tag_count", "skipped_non_commit_tag_count"):
            value = content.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                metadata[key] = value
        truncated = content.get("truncated")
        if isinstance(truncated, bool):
            metadata["truncated"] = truncated
        if isinstance(output_policy, dict):
            for key in (
                "tag_names_included",
                "tag_messages_included",
                "tag_signatures_included",
                "stable_tag_hashes_included",
                "tag_ids_are_response_local",
            ):
                value = output_policy.get(key)
                if isinstance(value, bool):
                    metadata[key] = value
        return metadata

    if tool_name != "git.show.ref_summary":
        return metadata

    selector = content.get("selector")
    output_policy = content.get("output_policy")
    if isinstance(selector, dict) and isinstance(selector.get("kind"), str):
        metadata["selector_kind"] = selector["kind"]
    for key in ("ref_count", "total_ref_count"):
        value = content.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            metadata[key] = value
    truncated = content.get("truncated")
    if isinstance(truncated, bool):
        metadata["truncated"] = truncated
    if isinstance(output_policy, dict):
        for key in (
            "ref_names_included",
            "stable_ref_hashes_included",
            "ref_ids_are_response_local",
        ):
            value = output_policy.get(key)
            if isinstance(value, bool):
                metadata[key] = value
    return metadata


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


def _optional_string_argument(arguments: JsonObject, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise PatchProposalError(f"{name} must be a non-empty string")
    return value


def _resource_scope_denial_reason(resource: JsonObject) -> str:
    scope_error = resource.get("scope_error")
    if isinstance(scope_error, str) and scope_error:
        return scope_error
    return "resource is outside the configured scope"
