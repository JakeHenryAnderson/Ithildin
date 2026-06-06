"""FastAPI application factory for the Ithildin API service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from ithildin_audit_core import (
    AuditSigningError,
    AuditWriteError,
    AuditWriter,
    audit_signing_status,
    signed_audit_export_bundle,
)
from ithildin_policy_core import PolicyEngine
from ithildin_schemas import (
    ApprovalDecisionValue,
    ApprovalRequest,
    ApprovalStatus,
    AuditEventType,
    JsonObject,
    sha256_digest,
)
from pydantic import BaseModel

from ithildin_api.agent_runs import AgentRunError, AgentRunStore
from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_api.auth import require_admin_token
from ithildin_api.config import Settings, load_settings
from ithildin_api.database import initialize_database
from ithildin_api.filesystem_contract import collect_filesystem_contract_status
from ithildin_api.http_tools import HttpFetchExecutor
from ithildin_api.identity import (
    PrincipalRegistry,
    PrincipalRegistryError,
    filter_tools_for_principal,
)
from ithildin_api.logging import configure_logging
from ithildin_api.manifest_lock import ManifestLockError, manifest_lock_signature_status
from ithildin_api.patches import (
    PATCH_APPLY_TOOL,
    PatchProposalError,
    PatchProposalService,
    PatchProposalStore,
)
from ithildin_api.policy import load_policy_engine
from ithildin_api.policy_impact import PolicyImpactError, PolicyImpactService
from ithildin_api.policy_preview import (
    DEFAULT_PREVIEW_SESSION_ID,
    PolicyPreviewService,
)
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.redaction import RedactionService
from ithildin_api.registry import ToolRegistry, ToolRegistryError
from ithildin_api.security_status import (
    LOCAL_CORS_ORIGINS,
    security_status,
    validate_security_settings,
)
from ithildin_api.storage import storage_status, validate_storage_settings
from ithildin_api.telemetry import Telemetry, configure_telemetry, safe_span_attributes
from ithildin_api.workspaces import WorkspaceRegistry

SERVICE_NAME = "ithildin-api"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or load_settings()
        configure_logging(resolved_settings.log_level)
        validate_security_settings(resolved_settings)
        validate_storage_settings(resolved_settings)
        telemetry = configure_telemetry(resolved_settings)
        app_instance.state.settings = resolved_settings
        app_instance.state.telemetry = telemetry
        with telemetry.start_span(
            "ithildin.api.startup",
            safe_span_attributes(storage_backend=resolved_settings.storage_backend),
        ):
            initialize_database(resolved_settings.db_path)
            audit_writer = AuditWriter(resolved_settings.db_path, resolved_settings.audit_log_path)
            audit_writer.initialize()
            app_instance.state.audit_writer = audit_writer
            agent_run_store = AgentRunStore(resolved_settings.db_path)
            agent_run_store.initialize()
            app_instance.state.agent_run_store = agent_run_store
            approval_store = ApprovalStore(resolved_settings.db_path)
            approval_store.initialize()
            app_instance.state.approval_service = ApprovalService(
                approval_store,
                audit_writer,
                timedelta(seconds=resolved_settings.approval_expiry_seconds),
            )
            registry = ToolRegistry.load(
                resolved_settings.manifest_dir,
                lock_path=resolved_settings.manifest_lock_path,
                require_lock=resolved_settings.require_manifest_lock,
                signature_path=resolved_settings.manifest_lock_signature_path,
                signature_public_key_path=resolved_settings.manifest_lock_signing_public_key_path,
                require_signed_lock=resolved_settings.require_signed_manifest_lock,
            )
            app_instance.state.manifest_lock_signature_startup = manifest_lock_signature_status(
                lock_path=resolved_settings.manifest_lock_path,
                signature_path=resolved_settings.manifest_lock_signature_path,
                public_key_path=resolved_settings.manifest_lock_signing_public_key_path,
                required=resolved_settings.require_signed_manifest_lock,
            )
            principal_registry = PrincipalRegistry.load(
                resolved_settings.principal_registry_path,
                require_registry=resolved_settings.require_known_principals,
            )
            workspace_registry = WorkspaceRegistry.load(
                resolved_settings.workspace_registry_path,
                require_registry=resolved_settings.require_known_workspaces,
                fallback_root=resolved_settings.workspace_root,
                default_workspace_id=resolved_settings.default_workspace_id,
            )
            policy_evaluator = load_policy_engine(resolved_settings)
            app_instance.state.registry = registry
            app_instance.state.principal_registry = principal_registry
            app_instance.state.workspace_registry = workspace_registry
            app_instance.state.policy_evaluator = policy_evaluator
            http_fetch_executor = HttpFetchExecutor.from_settings(
                http_allowlist=resolved_settings.http_allowlist,
                timeout_seconds=resolved_settings.http_timeout_seconds,
                max_response_bytes=resolved_settings.http_max_response_bytes,
                max_redirects=resolved_settings.http_max_redirects,
            )
            app_instance.state.http_fetch_executor = http_fetch_executor
            redaction_service = RedactionService.from_settings(
                extra_keys=resolved_settings.redaction_extra_keys,
                extra_patterns=resolved_settings.redaction_extra_patterns,
            )
            app_instance.state.redaction_service = redaction_service
            app_instance.state.policy_impact_service = PolicyImpactService(
                current_policy_path=resolved_settings.policy_path,
                tests_path=resolved_settings.policy_tests_path,
            )
            read_tool_executor = ReadToolExecutor.from_settings(
                workspace_root=resolved_settings.workspace_root,
                max_read_bytes=resolved_settings.max_read_bytes,
                search_result_limit=resolved_settings.search_result_limit,
                git_log_limit=resolved_settings.git_log_limit,
                workspace_registry=workspace_registry,
            )
            app_instance.state.read_tool_executor = read_tool_executor
            app_instance.state.policy_preview_service = PolicyPreviewService(
                registry,
                policy_evaluator,
                http_fetch_executor.allowlist,
                principal_registry,
                read_tool_executor,
            )
            patch_store = PatchProposalStore(resolved_settings.db_path)
            patch_store.initialize()
            app_instance.state.patch_proposal_service = PatchProposalService(
                patch_store,
                read_tool_executor.filesystem,
                resolved_settings.max_patch_bytes,
                read_tool_executor.filesystems,
                read_tool_executor.default_workspace_id,
            )
            app_instance.state.tool_call_telemetry = telemetry
        logging.getLogger(__name__).info("api service started")
        yield

    api = FastAPI(title="Ithildin API", lifespan=lifespan)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_CORS_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @api.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @api.get("/admin/status", dependencies=[Depends(require_admin_token)])
    def admin_status() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME, "admin": "authenticated"}

    @api.get("/system/status", dependencies=[Depends(require_admin_token)])
    def system_status() -> JsonObject:
        settings_state = cast(Settings, api.state.settings)
        registry = cast(ToolRegistry, api.state.registry)
        principal_registry = cast(PrincipalRegistry, api.state.principal_registry)
        workspace_registry = cast(WorkspaceRegistry, api.state.workspace_registry)
        policy_evaluator = cast(PolicyEngine, api.state.policy_evaluator)
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        telemetry = cast(Telemetry, api.state.telemetry)
        redaction_service = cast(RedactionService, api.state.redaction_service)
        agent_run_store = cast(AgentRunStore, api.state.agent_run_store)
        tools = registry.list_tools()
        verification = audit_writer.verify_chain().as_dict()
        current_manifest_lock_signature = manifest_lock_signature_status(
            lock_path=settings_state.manifest_lock_path,
            signature_path=settings_state.manifest_lock_signature_path,
            public_key_path=settings_state.manifest_lock_signing_public_key_path,
            required=settings_state.require_signed_manifest_lock,
        )
        startup_manifest_lock_signature = cast(
            JsonObject,
            getattr(api.state, "manifest_lock_signature_startup", current_manifest_lock_signature),
        )
        current_manifest_lock = _current_manifest_lock_status(settings_state)
        with telemetry.start_span("ithildin.api.system_status"):
            return {
                "status": "ok",
                "service": SERVICE_NAME,
                "tool_count": len(tools),
                "manifest_lock": {
                    "required": settings_state.require_manifest_lock,
                    "path": settings_state.manifest_lock_path.as_posix(),
                    "current": current_manifest_lock,
                    "signature": current_manifest_lock_signature,
                    "signature_startup": startup_manifest_lock_signature,
                    "signature_drift": current_manifest_lock_signature
                    != startup_manifest_lock_signature,
                },
                "principals": {
                    **principal_registry.status(),
                    "required": settings_state.require_known_principals,
                },
                "workspaces": workspace_registry.status(),
                "filesystem": collect_filesystem_contract_status(),
                "storage": storage_status(settings_state),
                "security": security_status(settings_state),
                "telemetry": telemetry.status(),
                "policy": policy_evaluator.status(),
                "audit": {
                    "valid": verification["valid"],
                    "event_count": verification["event_count"],
                    "head_hash": verification["head_hash"],
                },
                "agent_runs": {
                    "enabled": True,
                    "count": len(agent_run_store.list_runs(limit=200)),
                    "status": "read_only_observability",
                },
                "audit_signing": audit_signing_status(
                    settings_state.audit_signing_private_key_path,
                    settings_state.audit_signing_public_key_path,
                ),
                "redaction": redaction_service.status(),
                "limits": {
                    "approval_expiry_seconds": settings_state.approval_expiry_seconds,
                    "max_read_bytes": settings_state.max_read_bytes,
                    "max_patch_bytes": settings_state.max_patch_bytes,
                    "search_result_limit": settings_state.search_result_limit,
                    "git_log_limit": settings_state.git_log_limit,
                    "http_allowlist_configured": bool(settings_state.http_allowlist.strip()),
                    "http_timeout_seconds": settings_state.http_timeout_seconds,
                    "http_max_response_bytes": settings_state.http_max_response_bytes,
                    "http_max_redirects": settings_state.http_max_redirects,
                },
            }

    @api.get("/tools", dependencies=[Depends(require_admin_token)])
    def list_tools(principal: Optional[str] = None) -> dict[str, list[JsonObject]]:
        registry = cast(ToolRegistry, api.state.registry)
        registered_tools = registry.list_tools()
        if principal is not None:
            principal_registry = cast(PrincipalRegistry, api.state.principal_registry)
            try:
                principal_record = principal_registry.resolve_active(principal)
            except PrincipalRegistryError:
                registered_tools = []
            else:
                registered_tools = filter_tools_for_principal(
                    registered_tools,
                    principal_record,
                    lambda tool: tool.manifest.risk,
                )
        tools = [tool.summary() for tool in registered_tools]
        return {"tools": tools}

    @api.get("/principals", dependencies=[Depends(require_admin_token)])
    def list_principals() -> dict[str, list[JsonObject]]:
        principal_registry = cast(PrincipalRegistry, api.state.principal_registry)
        return {
            "principals": [
                principal.safe_summary() for principal in principal_registry.list_principals()
            ]
        }

    @api.get("/principals/{principal_id}", dependencies=[Depends(require_admin_token)])
    def get_principal(principal_id: str) -> JsonObject:
        principal_registry = cast(PrincipalRegistry, api.state.principal_registry)
        try:
            return principal_registry.get(principal_id).safe_summary()
        except PrincipalRegistryError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @api.get("/workspaces", dependencies=[Depends(require_admin_token)])
    def list_workspaces() -> dict[str, list[JsonObject]]:
        workspace_registry = cast(WorkspaceRegistry, api.state.workspace_registry)
        return {
            "workspaces": [
                workspace.safe_summary() for workspace in workspace_registry.list_workspaces()
            ]
        }

    @api.get("/runs", dependencies=[Depends(require_admin_token)])
    def list_runs(limit: int = 50) -> dict[str, list[JsonObject]]:
        agent_run_store = cast(AgentRunStore, api.state.agent_run_store)
        return {"runs": agent_run_store.list_runs(limit=limit)}

    @api.get("/runs/{run_id}", dependencies=[Depends(require_admin_token)])
    def get_run(run_id: str, timeline_limit: int = 200) -> JsonObject:
        agent_run_store = cast(AgentRunStore, api.state.agent_run_store)
        try:
            return agent_run_store.detail(run_id, timeline_limit=timeline_limit)
        except AgentRunError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @api.post("/policy/preview", dependencies=[Depends(require_admin_token)])
    def preview_policy(payload: PolicyPreviewPayload) -> JsonObject:
        preview_service = cast(PolicyPreviewService, api.state.policy_preview_service)
        return preview_service.preview(
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            principal=payload.principal,
            session_id=payload.session_id,
        )

    @api.get("/policy/status", dependencies=[Depends(require_admin_token)])
    def policy_status() -> JsonObject:
        policy_evaluator = cast(PolicyEngine, api.state.policy_evaluator)
        return policy_evaluator.status()

    @api.post("/policy/impact-preview", dependencies=[Depends(require_admin_token)])
    def preview_policy_impact(payload: PolicyImpactPreviewPayload) -> JsonObject:
        impact_service = cast(PolicyImpactService, api.state.policy_impact_service)
        try:
            return impact_service.preview_candidate_yaml(payload.candidate_policy_yaml)
        except PolicyImpactError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @api.get("/patch-proposals", dependencies=[Depends(require_admin_token)])
    def list_patch_proposals() -> dict[str, list[JsonObject]]:
        patch_service = cast(PatchProposalService, api.state.patch_proposal_service)
        proposals = [
            {**proposal.summary(), "review": patch_service.proposal_review(proposal)}
            for proposal in patch_service.list_proposals()
        ]
        return {"patch_proposals": proposals}

    @api.get("/patch-proposals/{proposal_id}", dependencies=[Depends(require_admin_token)])
    def get_patch_proposal(proposal_id: str) -> JsonObject:
        patch_service = cast(PatchProposalService, api.state.patch_proposal_service)
        try:
            proposal = patch_service.get_proposal(proposal_id)
            return {**proposal.detail(), "review": patch_service.proposal_review(proposal)}
        except PatchProposalError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @api.get("/patch-apply-diagnostics", dependencies=[Depends(require_admin_token)])
    def patch_apply_diagnostics() -> JsonObject:
        patch_service = cast(PatchProposalService, api.state.patch_proposal_service)
        approval_service = cast(ApprovalService, api.state.approval_service)
        return patch_service.patch_apply_diagnostics(approval_service)

    @api.get("/approvals", dependencies=[Depends(require_admin_token)])
    def list_approvals(status: Optional[ApprovalStatus] = None) -> dict[str, list[ApprovalRequest]]:
        approval_service = cast(ApprovalService, api.state.approval_service)
        return {"approvals": approval_service.list(status=status)}

    @api.get("/approvals/review", dependencies=[Depends(require_admin_token)])
    def list_approval_reviews(status: Optional[ApprovalStatus] = None) -> JsonObject:
        approval_service = cast(ApprovalService, api.state.approval_service)
        return {
            "approvals": [
                {
                    "approval": approval.model_dump(mode="json"),
                    "review": _patch_apply_approval_review(api, approval),
                }
                for approval in approval_service.list(status=status)
            ]
        }

    @api.post("/approvals", dependencies=[Depends(require_admin_token)])
    def create_approval(payload: CreateApprovalPayload) -> ApprovalRequest:
        approval_service = cast(ApprovalService, api.state.approval_service)
        return approval_service.create_pending(
            CreateApprovalInput(
                principal=payload.principal,
                tool_name=payload.tool_name,
                resource=payload.resource,
                summary=payload.summary,
                one_time_scope=payload.one_time_scope,
                request_id=payload.request_id,
                request_hash=payload.request_hash,
                expires_at=payload.expires_at,
                metadata=payload.metadata,
            )
        )

    @api.get("/approvals/{approval_id}", dependencies=[Depends(require_admin_token)])
    def get_approval(approval_id: str) -> ApprovalRequest:
        approval_service = cast(ApprovalService, api.state.approval_service)
        return _approval_or_404(approval_service, approval_id)

    @api.post("/approvals/{approval_id}/approve", dependencies=[Depends(require_admin_token)])
    def approve_approval(approval_id: str, payload: ApprovalDecisionPayload) -> ApprovalRequest:
        _require_route_decision(payload.decision, ApprovalDecisionValue.APPROVE)
        approval_service = cast(ApprovalService, api.state.approval_service)
        try:
            approval = approval_service.get(approval_id)
            if approval.tool_name == PATCH_APPLY_TOOL:
                try:
                    review = _patch_apply_approval_review(api, approval)
                except PatchProposalError as exc:
                    raise ApprovalError(
                        "patch apply approval binding review failed"
                    ) from exc
                if review.get("valid") is not True:
                    raise ApprovalError("patch apply approval binding review failed")
            return approval_service.approve(
                approval_id,
                decided_by=payload.decided_by,
                reason=payload.reason,
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @api.post("/approvals/{approval_id}/deny", dependencies=[Depends(require_admin_token)])
    def deny_approval(approval_id: str, payload: ApprovalDecisionPayload) -> ApprovalRequest:
        _require_route_decision(payload.decision, ApprovalDecisionValue.DENY)
        approval_service = cast(ApprovalService, api.state.approval_service)
        try:
            return approval_service.deny(
                approval_id,
                decided_by=payload.decided_by,
                reason=payload.reason,
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @api.get("/audit-events", dependencies=[Depends(require_admin_token)])
    def list_audit_events(
        limit: int = 100,
        event_type: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, list[JsonObject]]:
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        try:
            return {
                "audit_events": audit_writer.list_events(
                    limit=limit,
                    event_type=event_type,
                    request_id=request_id,
                )
            }
        except AuditWriteError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @api.get("/audit-events/verify", dependencies=[Depends(require_admin_token)])
    def verify_audit_events() -> JsonObject:
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        return audit_writer.verify_chain().as_dict()

    @api.get("/audit-events/diagnostics", dependencies=[Depends(require_admin_token)])
    def audit_diagnostics() -> JsonObject:
        settings_state = cast(Settings, api.state.settings)
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        return {
            **audit_writer.diagnostics(),
            "signing": audit_signing_status(
                settings_state.audit_signing_private_key_path,
                settings_state.audit_signing_public_key_path,
            ),
        }

    @api.get("/audit-events/export", dependencies=[Depends(require_admin_token)])
    def export_audit_events() -> Response:
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        try:
            _write_audit_export_event(audit_writer, signed=False)
            return Response(
                content=audit_writer.export_jsonl_bundle(),
                media_type="application/x-ndjson",
                headers={
                    "Content-Disposition": 'attachment; filename="ithildin-audit-export.jsonl"'
                },
            )
        except AuditWriteError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @api.get("/audit-events/export/signed", dependencies=[Depends(require_admin_token)])
    def export_signed_audit_events() -> JsonObject:
        settings_state = cast(Settings, api.state.settings)
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        try:
            preflight_jsonl_bundle = audit_writer.export_jsonl_bundle(require_clean_lifecycle=True)
            signed_audit_export_bundle(
                jsonl_bundle=preflight_jsonl_bundle,
                private_key_path=settings_state.audit_signing_private_key_path,
                public_key_path=settings_state.audit_signing_public_key_path,
            )
            _write_audit_export_event(audit_writer, signed=True)
            return signed_audit_export_bundle(
                jsonl_bundle=audit_writer.export_jsonl_bundle(require_clean_lifecycle=True),
                private_key_path=settings_state.audit_signing_private_key_path,
                public_key_path=settings_state.audit_signing_public_key_path,
            )
        except (AuditSigningError, AuditWriteError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return api


def _write_audit_export_event(audit_writer: AuditWriter, *, signed: bool) -> None:
    audit_writer.write_event(
        event_id=f"evt_{uuid4().hex}",
        event_type=AuditEventType.AUDIT_EXPORTED,
        request_id=f"req_{uuid4().hex}",
        principal={"id": "admin:local-api", "roles": ["Admin"]},
        metadata={
            "export_format": "signed_json" if signed else "jsonl",
            "signed": signed,
            "contents": "audit export metadata and events",
        },
    )


def _approval_expected_policy_version(
    approval: ApprovalRequest,
    fallback_policy_hash: str,
) -> str:
    value = approval.metadata.get("policy_version")
    return value if isinstance(value, str) and value else fallback_policy_hash


def _approval_expected_matched_rules(approval: ApprovalRequest) -> list[str]:
    value = approval.metadata.get("matched_rules")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return cast(list[str], value)
    scope_value = approval.one_time_scope.get("matched_rules")
    if isinstance(scope_value, list) and all(isinstance(item, str) for item in scope_value):
        return cast(list[str], scope_value)
    return []


def _patch_apply_approval_review(api: FastAPI, approval: ApprovalRequest) -> JsonObject:
    patch_service = cast(PatchProposalService, api.state.patch_proposal_service)
    registry = cast(ToolRegistry, api.state.registry)
    policy_evaluator = cast(PolicyEngine, api.state.policy_evaluator)
    tool = registry.get_tool(PATCH_APPLY_TOOL)
    return patch_service.approval_review(
        approval,
        expected_manifest_hash=tool.manifest_hash,
        expected_manifest_version=tool.manifest.version,
        expected_tool_input_schema_hash=sha256_digest(tool.manifest.input_schema),
        expected_policy_engine=policy_evaluator.engine_name,
        expected_policy_hash=policy_evaluator.policy_hash,
        expected_policy_version=_approval_expected_policy_version(
            approval,
            policy_evaluator.policy_hash,
        ),
        expected_policy_document_version=policy_evaluator.document_version,
        expected_matched_rules=_approval_expected_matched_rules(approval),
        expected_principal=approval.principal,
    )


def _current_manifest_lock_status(settings: Settings) -> JsonObject:
    if not settings.require_manifest_lock:
        return {"verified": False, "required": False, "error": None}
    try:
        ToolRegistry.load(
            settings.manifest_dir,
            lock_path=settings.manifest_lock_path,
            require_lock=True,
            signature_path=settings.manifest_lock_signature_path,
            signature_public_key_path=settings.manifest_lock_signing_public_key_path,
            require_signed_lock=settings.require_signed_manifest_lock,
        )
    except (ToolRegistryError, ManifestLockError) as exc:
        return {
            "verified": False,
            "required": True,
            "error": str(exc),
        }
    return {
        "verified": True,
        "required": True,
        "error": None,
    }


def _require_route_decision(
    actual: ApprovalDecisionValue,
    expected: ApprovalDecisionValue,
) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"decision must be {expected.value}",
        )


class CreateApprovalPayload(BaseModel):
    principal: JsonObject
    tool_name: str
    resource: JsonObject
    summary: str
    one_time_scope: JsonObject
    request_id: Optional[str] = None
    request_hash: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[JsonObject] = None


class ApprovalDecisionPayload(BaseModel):
    decision: ApprovalDecisionValue
    decided_by: str
    reason: Optional[str] = None


class PolicyPreviewPayload(BaseModel):
    tool_name: str
    arguments: JsonObject
    principal: Optional[JsonObject] = None
    session_id: str = DEFAULT_PREVIEW_SESSION_ID


class PolicyImpactPreviewPayload(BaseModel):
    candidate_policy_yaml: str


def _approval_or_404(approval_service: ApprovalService, approval_id: str) -> ApprovalRequest:
    try:
        return approval_service.get(approval_id)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


app = create_app()
