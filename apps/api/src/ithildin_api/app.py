"""FastAPI application factory for the Ithildin API service."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
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
    JsonValue,
    sha256_digest,
)
from pydantic import BaseModel, ValidationError

from ithildin_api.agent_runs import AgentRunError, AgentRunFilters, AgentRunStore
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
from ithildin_api.node_configuration import (
    NodeConfigurationAcknowledgmentPayload,
    NodeConfigurationAssignmentPayload,
    NodeConfigurationConflictError,
    NodeConfigurationNotFoundError,
    NodeConfigurationRequestPayload,
    NodeConfigurationRollbackPayload,
    NodeConfigurationSigner,
    NodeConfigurationSigningError,
    NodeConfigurationStore,
)
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionAcknowledgmentPayload,
    NodeConfigurationTrustTransitionAssignmentPayload,
    NodeConfigurationTrustTransitionConflictError,
    NodeConfigurationTrustTransitionNotFoundError,
    NodeConfigurationTrustTransitionRequestPayload,
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.node_versions import node_version_posture
from ithildin_api.nodes import (
    EnrollmentCodeIssuePayload,
    NodeAuthenticationError,
    NodeConflictError,
    NodeEnrollmentPayload,
    NodeHeartbeatPayload,
    NodeNotFoundError,
    NodeStore,
    enrollment_audit_metadata,
    node_audit_metadata,
)
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
from ithildin_api.sandbox_artifacts import SandboxArtifactWriteService
from ithildin_api.sandbox_descriptors import (
    SandboxDescriptorError,
    SandboxDescriptorPayload,
    SandboxDescriptorStore,
)
from ithildin_api.sandbox_descriptors import (
    safe_audit_metadata as sandbox_descriptor_audit_metadata,
)
from ithildin_api.security_status import (
    LOCAL_CORS_ORIGINS,
    security_status,
    validate_security_settings,
)
from ithildin_api.storage import storage_status, validate_storage_settings
from ithildin_api.telemetry import Telemetry, configure_telemetry, safe_span_attributes
from ithildin_api.trusted_host_promotions import (
    TRUSTED_HOST_PROMOTION_TOOL,
    TrustedHostPromotionError,
    TrustedHostPromotionProposalInput,
    TrustedHostPromotionService,
    TrustedHostPromotionStore,
)
from ithildin_api.workspaces import WorkspaceRegistry, WorkspaceRegistryError

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
            node_store = NodeStore(resolved_settings.db_path)
            node_store.initialize()
            app_instance.state.node_store = node_store
            node_configuration_store = NodeConfigurationStore(resolved_settings.db_path)
            node_configuration_store.initialize()
            app_instance.state.node_configuration_store = node_configuration_store
            node_configuration_trust_transition_store = (
                NodeConfigurationTrustTransitionStore(resolved_settings.db_path)
            )
            node_configuration_trust_transition_store.initialize()
            app_instance.state.node_configuration_trust_transition_store = (
                node_configuration_trust_transition_store
            )
            app_instance.state.node_configuration_signer = _load_node_configuration_signer(
                resolved_settings
            )
            sandbox_descriptor_store = SandboxDescriptorStore(resolved_settings.db_path)
            sandbox_descriptor_store.initialize()
            app_instance.state.sandbox_descriptor_store = sandbox_descriptor_store
            trusted_host_promotion_store = TrustedHostPromotionStore(resolved_settings.db_path)
            trusted_host_promotion_store.initialize()
            app_instance.state.trusted_host_promotion_store = trusted_host_promotion_store
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
            sandbox_artifact_service = SandboxArtifactWriteService.from_read_executor(
                read_tool_executor
            )
            app_instance.state.sandbox_artifact_service = sandbox_artifact_service
            app_instance.state.trusted_host_promotion_service = TrustedHostPromotionService(
                store=trusted_host_promotion_store,
                read_executor=read_tool_executor,
                descriptor_store=sandbox_descriptor_store,
                staging_root=resolved_settings.trusted_host_staging_root,
            )
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
                "sandbox_descriptors": cast(
                    SandboxDescriptorStore,
                    api.state.sandbox_descriptor_store,
                ).status(),
                "trusted_host_promotions": cast(
                    TrustedHostPromotionService,
                    api.state.trusted_host_promotion_service,
                ).diagnostics(cast(ApprovalService, api.state.approval_service))["status"],
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

    @api.post("/nodes/enrollment-codes", dependencies=[Depends(require_admin_token)])
    def issue_node_enrollment_code(payload: JsonObject) -> JsonObject:
        try:
            request_payload = EnrollmentCodeIssuePayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node enrollment-code request",
            ) from exc
        workspace_registry = cast(WorkspaceRegistry, api.state.workspace_registry)
        try:
            workspace_registry.resolve_active(request_payload.workspace_id)
        except WorkspaceRegistryError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unknown or disabled workspace",
            ) from exc
        settings_state = cast(Settings, api.state.settings)
        node_store = cast(NodeStore, api.state.node_store)
        issued = node_store.issue_enrollment_code(
            request_payload,
            expires_in_seconds=settings_state.node_enrollment_expiry_seconds,
        )
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_ENROLLMENT_CODE_ISSUED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local", "roles": ["Admin"]},
            metadata=enrollment_audit_metadata(issued),
        )
        node_store.mark_enrollment_code_evidence_complete(issued.code_id)
        return issued.response()

    @api.post("/nodes/enroll")
    def enroll_node(payload: JsonObject) -> JsonObject:
        try:
            request_payload = NodeEnrollmentPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node enrollment request",
            ) from exc
        signer = _require_node_configuration_signer(api)
        settings_state = cast(Settings, api.state.settings)
        try:
            manifest_lock_digest = _manifest_lock_digest(settings_state.manifest_lock_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="manifest lock is unavailable for Node enrollment",
            ) from exc
        node_store = cast(NodeStore, api.state.node_store)
        try:
            record = node_store.enroll(request_payload)
        except NodeAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except NodeConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_ENROLLED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": record.principal_id, "roles": []},
            metadata=node_audit_metadata(record),
        )
        record = node_store.mark_node_evidence_complete(record.node_id)
        response = record.summary()
        response["configuration_trust"] = signer.trust.summary()
        response["manifest_lock_digest"] = manifest_lock_digest
        return response

    @api.post("/nodes/{node_id}/heartbeat")
    def accept_node_heartbeat(node_id: str, request: Request, payload: JsonObject) -> JsonObject:
        try:
            heartbeat = NodeHeartbeatPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node heartbeat",
            ) from exc
        header_node_id = request.headers.get("X-Ithildin-Node", "")
        if header_node_id != node_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Node identity header mismatch",
            )
        settings_state = cast(Settings, api.state.settings)
        node_store = cast(NodeStore, api.state.node_store)
        try:
            record = node_store.accept_heartbeat(
                node_id=node_id,
                timestamp=request.headers.get("X-Ithildin-Timestamp", ""),
                nonce=request.headers.get("X-Ithildin-Nonce", ""),
                signature=request.headers.get("X-Ithildin-Signature", ""),
                payload=heartbeat,
                path=request.url.path,
                max_clock_skew_seconds=settings_state.node_max_clock_skew_seconds,
            )
        except (NodeAuthenticationError, NodeNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_HEARTBEAT_ACCEPTED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": record.principal_id, "roles": []},
            input_hash=record.last_heartbeat_hash,
            metadata=node_audit_metadata(record),
        )
        record = node_store.mark_node_evidence_complete(record.node_id)
        summary = record.summary(stale_after_seconds=settings_state.node_stale_after_seconds)
        _add_node_version_posture(
            summary,
            cast(NodeConfigurationStore, api.state.node_configuration_store),
        )
        return summary

    @api.get("/nodes", dependencies=[Depends(require_admin_token)])
    def list_nodes(request: Request) -> JsonObject:
        unexpected = sorted(set(request.query_params.keys()) - {"limit"})
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        limit = _bounded_query_limit(request.query_params.get("limit"), default=50, maximum=200)
        settings_state = cast(Settings, api.state.settings)
        records = cast(NodeStore, api.state.node_store).list(
            limit=limit,
            stale_after_seconds=settings_state.node_stale_after_seconds,
        )
        signer = cast(NodeConfigurationSigner | None, api.state.node_configuration_signer)
        for record in records:
            _add_node_version_posture(
                record,
                cast(NodeConfigurationStore, api.state.node_configuration_store),
            )
            record["configuration_signing_key_id"] = signer.trust.key_id if signer else None
            transitions = cast(
                NodeConfigurationTrustTransitionStore,
                api.state.node_configuration_trust_transition_store,
            ).list(str(record["node_id"]), limit=1)
            record["configuration_trust_transition"] = _configuration_trust_posture(
                transitions[0].summary() if transitions else None,
                gateway_key_id=signer.trust.key_id if signer else None,
                acknowledged_key_id=cast(
                    str | None,
                    record.get("acknowledged_active_configuration_signing_key_id"),
                ),
            )
        return {
            "nodes": cast(JsonValue, records),
            "count": len(records),
            "connectivity_source": "gateway_accepted_heartbeat",
            "stale_after_seconds": settings_state.node_stale_after_seconds,
            "runner_health_known": False,
        }

    @api.get("/nodes/{node_id}", dependencies=[Depends(require_admin_token)])
    def get_node(node_id: str) -> JsonObject:
        settings_state = cast(Settings, api.state.settings)
        try:
            record = cast(NodeStore, api.state.node_store).get(node_id)
        except NodeNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        summary = record.summary(stale_after_seconds=settings_state.node_stale_after_seconds)
        _add_node_version_posture(
            summary,
            cast(NodeConfigurationStore, api.state.node_configuration_store),
        )
        signer = cast(NodeConfigurationSigner | None, api.state.node_configuration_signer)
        summary["configuration_signing_key_id"] = signer.trust.key_id if signer else None
        transitions = cast(
            NodeConfigurationTrustTransitionStore,
            api.state.node_configuration_trust_transition_store,
        ).list(node_id, limit=1)
        summary["configuration_trust_transition"] = _configuration_trust_posture(
            transitions[0].summary() if transitions else None,
            gateway_key_id=signer.trust.key_id if signer else None,
            acknowledged_key_id=record.acknowledged_active_configuration_signing_key_id,
        )
        return summary

    @api.post("/nodes/{node_id}/revoke", dependencies=[Depends(require_admin_token)])
    def revoke_node(node_id: str) -> JsonObject:
        node_store = cast(NodeStore, api.state.node_store)
        try:
            record = node_store.revoke(node_id)
        except NodeNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_REVOKED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local", "roles": ["Admin"]},
            metadata=node_audit_metadata(record),
        )
        record = node_store.mark_node_evidence_complete(record.node_id)
        summary = record.summary()
        _add_node_version_posture(
            summary,
            cast(NodeConfigurationStore, api.state.node_configuration_store),
        )
        return summary

    @api.post(
        "/nodes/{node_id}/configurations",
        dependencies=[Depends(require_admin_token)],
    )
    def assign_node_configuration(node_id: str, payload: JsonObject) -> JsonObject:
        try:
            assignment = NodeConfigurationAssignmentPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration assignment",
            ) from exc
        signer = _require_node_configuration_signer(api)
        settings_state = cast(Settings, api.state.settings)
        policy_engine = cast(PolicyEngine, api.state.policy_evaluator)
        try:
            manifest_lock_digest = _manifest_lock_digest(settings_state.manifest_lock_path)
            record = cast(
                NodeConfigurationStore, api.state.node_configuration_store
            ).assign(
                node_id=node_id,
                payload=assignment,
                signer=signer,
                policy_version=policy_engine.document_version,
                policy_digest=policy_engine.policy_hash,
                manifest_lock_digest=manifest_lock_digest,
            )
        except NodeConfigurationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="manifest lock is unavailable for Node configuration",
            ) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_ASSIGNED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local", "roles": ["Admin"]},
            input_hash=record.configuration_digest,
            metadata={
                "node_id": node_id,
                "configuration_id": record.configuration_id,
                "generation": record.generation,
                "configuration_digest": record.configuration_digest,
                "evidence_status": record.evidence_status,
                "enforcement_status": "stored_not_enforced",
            },
        )
        record = cast(
            NodeConfigurationStore, api.state.node_configuration_store
        ).mark_assignment_evidence_complete(node_id, record.generation)
        return record.summary()

    @api.get(
        "/nodes/{node_id}/configurations",
        dependencies=[Depends(require_admin_token)],
    )
    def list_node_configurations(node_id: str, request: Request) -> JsonObject:
        unexpected = sorted(set(request.query_params.keys()) - {"limit"})
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        limit = _bounded_query_limit(request.query_params.get("limit"), default=20, maximum=100)
        try:
            node = cast(NodeStore, api.state.node_store).get(node_id)
        except NodeNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        records = cast(NodeConfigurationStore, api.state.node_configuration_store).list(
            node_id, limit=limit
        )
        configurations: list[JsonValue] = []
        for record in records:
            summary = record.summary()
            configuration = record.bundle.get("configuration")
            summary["configuration"] = configuration if isinstance(configuration, dict) else {}
            summary["is_desired"] = record.generation == node.desired_configuration_generation
            configurations.append(summary)
        return {
            "node_id": node_id,
            "configurations": configurations,
            "count": len(configurations),
            "rollback_semantics": "fresh_signed_generation",
            "enforcement_proven": False,
        }

    @api.post(
        "/nodes/{node_id}/configurations/rollback",
        dependencies=[Depends(require_admin_token)],
    )
    def rollback_node_configuration(node_id: str, payload: JsonObject) -> JsonObject:
        try:
            rollback = NodeConfigurationRollbackPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration rollback",
            ) from exc
        signer = _require_node_configuration_signer(api)
        store = cast(NodeConfigurationStore, api.state.node_configuration_store)
        try:
            record = store.rollback(node_id=node_id, payload=rollback, signer=signer)
        except NodeConfigurationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_ROLLBACK_ASSIGNED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local", "roles": ["Admin"]},
            input_hash=record.configuration_digest,
            metadata={
                "node_id": node_id,
                "configuration_id": record.configuration_id,
                "generation": record.generation,
                "configuration_digest": record.configuration_digest,
                "rollback_source_generation": rollback.source_generation,
                "replaced_desired_generation": rollback.expected_current_generation,
                "evidence_status": record.evidence_status,
                "enforcement_status": "stored_not_enforced",
                "automatic": False,
            },
        )
        record = store.mark_assignment_evidence_complete(node_id, record.generation)
        return record.summary()

    @api.post("/nodes/{node_id}/configuration")
    def retrieve_node_configuration(
        node_id: str, request: Request, payload: JsonObject
    ) -> JsonObject:
        try:
            configuration_request = NodeConfigurationRequestPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration request",
            ) from exc
        _require_header_node(request, node_id)
        settings_state = cast(Settings, api.state.settings)
        try:
            node = cast(NodeStore, api.state.node_store).authenticate_request(
                node_id=node_id,
                timestamp=request.headers.get("X-Ithildin-Timestamp", ""),
                nonce=request.headers.get("X-Ithildin-Nonce", ""),
                signature=request.headers.get("X-Ithildin-Signature", ""),
                body=configuration_request.safe_payload(),
                path=request.url.path,
                max_clock_skew_seconds=settings_state.node_max_clock_skew_seconds,
            )
            record = cast(
                NodeConfigurationStore, api.state.node_configuration_store
            ).desired(node_id)
        except NodeAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except NodeConfigurationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_RETRIEVED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": node.principal_id, "roles": []},
            input_hash=record.configuration_digest,
            metadata={
                "node_id": node_id,
                "configuration_id": record.configuration_id,
                "generation": record.generation,
                "configuration_digest": record.configuration_digest,
                "known_generation": configuration_request.known_generation,
                "enforcement_status": "stored_not_enforced",
            },
        )
        return record.bundle

    @api.post(
        "/nodes/{node_id}/configuration-trust-transitions",
        dependencies=[Depends(require_admin_token)],
    )
    def assign_node_configuration_trust_transition(
        node_id: str, payload: JsonObject
    ) -> JsonObject:
        try:
            assignment = NodeConfigurationTrustTransitionAssignmentPayload.model_validate(
                payload
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration trust transition assignment",
            ) from exc
        signer = _require_node_configuration_signer(api)
        store = cast(
            NodeConfigurationTrustTransitionStore,
            api.state.node_configuration_trust_transition_store,
        )
        try:
            record = store.assign(node_id=node_id, payload=assignment, signer=signer)
        except NodeConfigurationTrustTransitionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationTrustTransitionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_TRUST_TRANSITION_ASSIGNED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local", "roles": ["Admin"]},
            input_hash=record.transition_digest,
            metadata={
                "node_id": node_id,
                "transition_id": record.transition_id,
                "transition_digest": record.transition_digest,
                "current_key_id": record.current_key_id,
                "next_key_id": record.next_key_id,
                "expires_at": record.expires_at,
                "automatic": False,
                "activation_proven": False,
            },
        )
        return store.mark_assignment_evidence_complete(
            node_id, record.transition_id
        ).summary()

    @api.get(
        "/nodes/{node_id}/configuration-trust-transitions",
        dependencies=[Depends(require_admin_token)],
    )
    def list_node_configuration_trust_transitions(
        node_id: str, request: Request
    ) -> JsonObject:
        unexpected = sorted(set(request.query_params.keys()) - {"limit"})
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        try:
            cast(NodeStore, api.state.node_store).get(node_id)
        except NodeNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        limit = _bounded_query_limit(request.query_params.get("limit"), default=20, maximum=100)
        records = cast(
            NodeConfigurationTrustTransitionStore,
            api.state.node_configuration_trust_transition_store,
        ).list(node_id, limit=limit)
        return {
            "node_id": node_id,
            "configuration_trust_transitions": [record.summary() for record in records],
            "count": len(records),
            "activation_mode": "explicit_gateway_restart",
            "automatic": False,
            "activation_proven": False,
        }

    @api.post("/nodes/{node_id}/configuration-trust-transition")
    def retrieve_node_configuration_trust_transition(
        node_id: str, request: Request, payload: JsonObject
    ) -> JsonObject:
        try:
            transition_request = NodeConfigurationTrustTransitionRequestPayload.model_validate(
                payload
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration trust transition request",
            ) from exc
        _require_header_node(request, node_id)
        settings_state = cast(Settings, api.state.settings)
        store = cast(
            NodeConfigurationTrustTransitionStore,
            api.state.node_configuration_trust_transition_store,
        )
        try:
            node = cast(NodeStore, api.state.node_store).authenticate_request(
                node_id=node_id,
                timestamp=request.headers.get("X-Ithildin-Timestamp", ""),
                nonce=request.headers.get("X-Ithildin-Nonce", ""),
                signature=request.headers.get("X-Ithildin-Signature", ""),
                body=transition_request.safe_payload(),
                path=request.url.path,
                max_clock_skew_seconds=settings_state.node_max_clock_skew_seconds,
            )
            record = store.desired(node_id)
        except NodeAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except NodeConfigurationTrustTransitionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationTrustTransitionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_TRUST_TRANSITION_RETRIEVED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": node.principal_id, "roles": []},
            input_hash=record.transition_digest,
            metadata={
                "node_id": node_id,
                "transition_id": record.transition_id,
                "transition_digest": record.transition_digest,
                "known_transition_id": transition_request.known_transition_id,
                "activation_proven": False,
            },
        )
        return record.bundle

    @api.post("/nodes/{node_id}/configuration-trust-transition/acknowledgments")
    def acknowledge_node_configuration_trust_transition(
        node_id: str, request: Request, payload: JsonObject
    ) -> JsonObject:
        try:
            acknowledgment = (
                NodeConfigurationTrustTransitionAcknowledgmentPayload.model_validate(payload)
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration trust transition acknowledgment",
            ) from exc
        _require_header_node(request, node_id)
        settings_state = cast(Settings, api.state.settings)
        store = cast(
            NodeConfigurationTrustTransitionStore,
            api.state.node_configuration_trust_transition_store,
        )
        try:
            node = cast(NodeStore, api.state.node_store).authenticate_request(
                node_id=node_id,
                timestamp=request.headers.get("X-Ithildin-Timestamp", ""),
                nonce=request.headers.get("X-Ithildin-Nonce", ""),
                signature=request.headers.get("X-Ithildin-Signature", ""),
                body=acknowledgment.safe_payload(),
                path=request.url.path,
                max_clock_skew_seconds=settings_state.node_max_clock_skew_seconds,
            )
            store.acknowledge_pending(node_id=node_id, payload=acknowledgment)
        except NodeAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except NodeConfigurationTrustTransitionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationTrustTransitionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_TRUST_TRANSITION_ACKNOWLEDGED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": node.principal_id, "roles": []},
            input_hash=acknowledgment.transition_digest,
            metadata={
                "node_id": node_id,
                "transition_id": acknowledgment.transition_id,
                "transition_digest": acknowledgment.transition_digest,
                "status": acknowledgment.status,
                "activation_proven": False,
            },
        )
        return store.mark_acknowledgment_evidence_complete(
            node_id, acknowledgment.transition_id
        ).summary()

    @api.post("/nodes/{node_id}/configuration/acknowledgments")
    def acknowledge_node_configuration(
        node_id: str, request: Request, payload: JsonObject
    ) -> JsonObject:
        try:
            acknowledgment = NodeConfigurationAcknowledgmentPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid Node configuration acknowledgment",
            ) from exc
        _require_header_node(request, node_id)
        settings_state = cast(Settings, api.state.settings)
        node_store = cast(NodeStore, api.state.node_store)
        try:
            node = node_store.authenticate_request(
                node_id=node_id,
                timestamp=request.headers.get("X-Ithildin-Timestamp", ""),
                nonce=request.headers.get("X-Ithildin-Nonce", ""),
                signature=request.headers.get("X-Ithildin-Signature", ""),
                body=acknowledgment.safe_payload(),
                path=request.url.path,
                max_clock_skew_seconds=settings_state.node_max_clock_skew_seconds,
            )
            cast(NodeConfigurationStore, api.state.node_configuration_store).acknowledge_pending(
                node_id=node_id,
                payload=acknowledgment,
            )
        except NodeAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except NodeConfigurationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except NodeConfigurationConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        cast(AuditWriter, api.state.audit_writer).write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.NODE_CONFIGURATION_ACKNOWLEDGED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": node.principal_id, "roles": []},
            input_hash=acknowledgment.configuration_digest,
            metadata={
                "node_id": node_id,
                "generation": acknowledgment.generation,
                "configuration_digest": acknowledgment.configuration_digest,
                "configuration_signing_key_id": acknowledgment.configuration_signing_key_id,
                "active_configuration_signing_key_id": (
                    acknowledgment.active_configuration_signing_key_id
                ),
                "status": acknowledgment.status,
                "enforcement_proven": False,
            },
        )
        node = node_store.mark_node_evidence_complete(node_id)
        return node.summary(stale_after_seconds=settings_state.node_stale_after_seconds)

    @api.post("/sandbox-descriptors", dependencies=[Depends(require_admin_token)])
    def create_sandbox_descriptor(payload: JsonObject) -> JsonObject:
        try:
            descriptor_payload = SandboxDescriptorPayload.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid sandbox descriptor",
            ) from exc
        descriptor_store = cast(SandboxDescriptorStore, api.state.sandbox_descriptor_store)
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        record = descriptor_store.create(descriptor_payload)
        audit_writer.write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED,
            request_id=f"req_{uuid4().hex}",
            principal={
                "id": descriptor_payload.principal_id,
                "roles": [],
            },
            metadata=sandbox_descriptor_audit_metadata(record),
        )
        return record.detail()

    @api.get("/sandbox-descriptors", dependencies=[Depends(require_admin_token)])
    def list_sandbox_descriptors(request: Request) -> JsonObject:
        unexpected = sorted(set(request.query_params.keys()) - {"limit"})
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        limit = _bounded_query_limit(request.query_params.get("limit"), default=50, maximum=200)
        descriptor_store = cast(SandboxDescriptorStore, api.state.sandbox_descriptor_store)
        return {
            "sandbox_descriptors": cast(JsonValue, descriptor_store.list(limit=limit)),
            "summary": descriptor_store.status(),
        }

    @api.get("/sandbox-descriptors/{descriptor_id}", dependencies=[Depends(require_admin_token)])
    def get_sandbox_descriptor(descriptor_id: str) -> JsonObject:
        if not _valid_sandbox_descriptor_id(descriptor_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid sandbox descriptor id",
            )
        descriptor_store = cast(SandboxDescriptorStore, api.state.sandbox_descriptor_store)
        try:
            return descriptor_store.get(descriptor_id)
        except SandboxDescriptorError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @api.post("/trusted-host-promotions/proposals", dependencies=[Depends(require_admin_token)])
    def create_trusted_host_promotion_proposal(payload: JsonObject) -> JsonObject:
        try:
            proposal_payload = TrustedHostPromotionProposalInput.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid trusted-host promotion proposal",
            ) from exc
        promotion_service = cast(
            TrustedHostPromotionService,
            api.state.trusted_host_promotion_service,
        )
        approval_service = cast(ApprovalService, api.state.approval_service)
        try:
            return promotion_service.create_proposal(
                proposal_payload,
                approval_service=approval_service,
            )
        except (TrustedHostPromotionError, SandboxDescriptorError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @api.get("/trusted-host-promotions/proposals", dependencies=[Depends(require_admin_token)])
    def list_trusted_host_promotion_proposals() -> JsonObject:
        promotion_store = cast(
            TrustedHostPromotionStore,
            api.state.trusted_host_promotion_store,
        )
        return {
            "promotion_proposals": [
                proposal.summary() for proposal in promotion_store.list_proposals()
            ],
            "output_policy": {
                "file_contents_included": False,
                "raw_host_paths_included": False,
            },
        }

    @api.get(
        "/trusted-host-promotions/proposals/{proposal_id}",
        dependencies=[Depends(require_admin_token)],
    )
    def get_trusted_host_promotion_proposal(proposal_id: str) -> JsonObject:
        if not _valid_trusted_host_promotion_id(proposal_id, "thp_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid trusted-host promotion proposal id",
            )
        promotion_store = cast(
            TrustedHostPromotionStore,
            api.state.trusted_host_promotion_store,
        )
        try:
            return promotion_store.get_proposal(proposal_id).summary()
        except TrustedHostPromotionError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @api.post(
        "/trusted-host-promotions/proposals/{proposal_id}/apply",
        dependencies=[Depends(require_admin_token)],
    )
    def apply_trusted_host_promotion(proposal_id: str, payload: JsonObject) -> JsonObject:
        if not _valid_trusted_host_promotion_id(proposal_id, "thp_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid trusted-host promotion proposal id",
            )
        if sorted(payload.keys()) != ["approval_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported trusted-host promotion apply field",
            )
        approval_id = payload.get("approval_id")
        if not isinstance(approval_id, str) or not _valid_approval_id(approval_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid approval id",
            )
        promotion_service = cast(
            TrustedHostPromotionService,
            api.state.trusted_host_promotion_service,
        )
        approval_service = cast(ApprovalService, api.state.approval_service)
        audit_writer = cast(AuditWriter, api.state.audit_writer)
        input_hash = sha256_digest({"proposal_id": proposal_id, "approval_id": approval_id})
        audit_writer.write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.TOOL_EXECUTION_STARTED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local-api", "roles": ["Admin"]},
            tool_name=TRUSTED_HOST_PROMOTION_TOOL,
            resource={
                "type": "trusted_host_promotion",
                "promotion_proposal_id": proposal_id,
            },
            input_hash=input_hash,
            metadata={
                "executor": "trusted_host_promotion_stage",
                "approval_id": approval_id,
                "promotion_proposal_id": proposal_id,
                "staging_only": True,
            },
        )
        try:
            result = promotion_service.apply_approved(
                proposal_id=proposal_id,
                approval_id=approval_id,
                approval_service=approval_service,
            )
        except (ApprovalError, TrustedHostPromotionError) as exc:
            audit_writer.write_event(
                event_id=f"evt_{uuid4().hex}",
                event_type=AuditEventType.TOOL_EXECUTION_FAILED,
                request_id=f"req_{uuid4().hex}",
                principal={"id": "admin:local-api", "roles": ["Admin"]},
                tool_name=TRUSTED_HOST_PROMOTION_TOOL,
                resource={
                    "type": "trusted_host_promotion",
                    "promotion_proposal_id": proposal_id,
                },
                input_hash=input_hash,
                metadata={
                    "executor": "trusted_host_promotion_stage",
                    "approval_id": approval_id,
                    "promotion_proposal_id": proposal_id,
                    "reason": str(exc),
                    "staging_only": True,
                },
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        audit_writer.write_event(
            event_id=f"evt_{uuid4().hex}",
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            request_id=f"req_{uuid4().hex}",
            principal={"id": "admin:local-api", "roles": ["Admin"]},
            tool_name=TRUSTED_HOST_PROMOTION_TOOL,
            resource={
                "type": "trusted_host_promotion",
                "promotion_proposal_id": proposal_id,
            },
            input_hash=input_hash,
            metadata={
                "executor": "trusted_host_promotion_stage",
                "approval_id": approval_id,
                "promotion_proposal_id": proposal_id,
                "promotion_attempt_id": result.get("promotion_attempt_id"),
                "host_staging_label": result.get("host_staging_label"),
                "artifact_sha256": result.get("artifact_sha256"),
                "staged_sha256": result.get("staged_sha256"),
                "staging_only": True,
                "output_policy": result.get("output_policy"),
            },
        )
        return result

    @api.get("/trusted-host-promotions/diagnostics", dependencies=[Depends(require_admin_token)])
    def trusted_host_promotion_diagnostics() -> JsonObject:
        promotion_service = cast(
            TrustedHostPromotionService,
            api.state.trusted_host_promotion_service,
        )
        approval_service = cast(ApprovalService, api.state.approval_service)
        return promotion_service.diagnostics(approval_service)

    @api.get("/runs", dependencies=[Depends(require_admin_token)])
    def list_runs(request: Request) -> JsonObject:
        unexpected = sorted(
            set(request.query_params.keys())
            - {"principal_id", "workspace_id", "status", "tool_name", "session_id", "limit"}
        )
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        limit = _bounded_query_limit(request.query_params.get("limit"), default=50, maximum=200)
        filters = AgentRunFilters(
            principal_id=_safe_query_filter(request.query_params.get("principal_id")),
            workspace_id=_safe_query_filter(request.query_params.get("workspace_id")),
            status=_safe_query_filter(request.query_params.get("status")),
            tool_name=_safe_query_filter(request.query_params.get("tool_name")),
            session_id=_safe_query_filter(request.query_params.get("session_id")),
        )
        agent_run_store = cast(AgentRunStore, api.state.agent_run_store)
        return agent_run_store.query_runs(limit=limit, filters=filters)

    @api.get("/runs/{run_id}/evidence-export", dependencies=[Depends(require_admin_token)])
    def get_run_evidence_export(
        run_id: str,
        request: Request,
        timeline_limit: int = 200,
    ) -> JsonObject:
        unexpected = sorted(set(request.query_params.keys()) - {"timeline_limit"})
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported query parameter",
            )
        if not _valid_agent_run_id(run_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid run id")
        agent_run_store = cast(AgentRunStore, api.state.agent_run_store)
        approval_service = cast(ApprovalService, api.state.approval_service)
        patch_service = cast(PatchProposalService, api.state.patch_proposal_service)
        try:
            return agent_run_store.evidence_export(
                run_id,
                approvals=approval_service.list(),
                patch_diagnostics=patch_service.patch_apply_diagnostics(approval_service),
                timeline_limit=timeline_limit,
            )
        except AgentRunError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

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
            if approval.tool_name == TRUSTED_HOST_PROMOTION_TOOL:
                try:
                    review = _trusted_host_promotion_approval_review(api, approval)
                except TrustedHostPromotionError as exc:
                    raise ApprovalError(
                        "trusted-host promotion approval binding review failed"
                    ) from exc
                if review.get("valid") is not True:
                    raise ApprovalError(
                        "trusted-host promotion approval binding review failed"
                    )
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


def _load_node_configuration_signer(settings: Settings) -> NodeConfigurationSigner | None:
    private_path = settings.node_configuration_signing_private_key_path
    public_path = settings.node_configuration_signing_public_key_path
    if not private_path.exists() and not public_path.exists():
        return None
    if not private_path.exists() or not public_path.exists():
        raise NodeConfigurationSigningError("Node configuration signing keypair is incomplete")
    return NodeConfigurationSigner.load(private_path, public_path)


def _require_node_configuration_signer(api: FastAPI) -> NodeConfigurationSigner:
    signer = cast(NodeConfigurationSigner | None, api.state.node_configuration_signer)
    if signer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node configuration signing trust root is unavailable",
        )
    return signer


def _manifest_lock_digest(path: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("manifest lock must be an object")
    return sha256_digest(cast(JsonObject, document))


def _require_header_node(request: Request, node_id: str) -> None:
    if request.headers.get("X-Ithildin-Node", "") != node_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Node identity header mismatch",
        )


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


def _trusted_host_promotion_approval_review(
    api: FastAPI,
    approval: ApprovalRequest,
) -> JsonObject:
    promotion_service = cast(
        TrustedHostPromotionService,
        api.state.trusted_host_promotion_service,
    )
    return promotion_service.approval_review(approval)


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


def _valid_agent_run_id(run_id: str) -> bool:
    return run_id.startswith("run_") and len(run_id) == 36 and all(
        character in "0123456789abcdef" for character in run_id[4:]
    )


def _valid_sandbox_descriptor_id(descriptor_id: str) -> bool:
    return descriptor_id.startswith("sdesc_") and len(descriptor_id) == 38 and all(
        character in "0123456789abcdef" for character in descriptor_id[6:]
    )


def _valid_trusted_host_promotion_id(value: str, prefix: str) -> bool:
    return value.startswith(prefix) and len(value) == len(prefix) + 32 and all(
        character in "0123456789abcdef" for character in value[len(prefix) :]
    )


def _valid_approval_id(value: str) -> bool:
    return value.startswith("appr_") and len(value) == 37 and all(
        character in "0123456789abcdef" for character in value[5:]
    )


def _bounded_query_limit(value: str | None, *, default: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid limit",
        ) from exc
    if parsed < 1 or parsed > maximum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid limit",
        )
    return parsed


def _configuration_trust_posture(
    transition: JsonObject | None,
    *,
    gateway_key_id: str | None,
    acknowledged_key_id: str | None,
) -> JsonObject | None:
    if transition is None:
        return None
    next_key_id = transition.get("next_key_id")
    acknowledgment_evidence = transition.get("acknowledgment_evidence_status")
    expires_at = transition.get("expires_at")
    expired = False
    if isinstance(expires_at, str):
        try:
            parsed_expiry = datetime.fromisoformat(expires_at)
            expired = parsed_expiry.tzinfo is not None and parsed_expiry <= datetime.now(UTC)
        except ValueError:
            expired = True
    if acknowledged_key_id is not None and acknowledged_key_id == next_key_id:
        posture = "active_not_enforced"
        activation_proven = True
    elif gateway_key_id is not None and gateway_key_id == next_key_id:
        posture = "gateway_advanced_node_pending"
        activation_proven = False
    elif expired:
        posture = "transition_expired_not_activated"
        activation_proven = False
    elif acknowledgment_evidence == "complete":
        posture = "staged_not_active"
        activation_proven = False
    else:
        posture = "awaiting_node_stage"
        activation_proven = False
    return {
        **transition,
        "gateway_key_id": gateway_key_id,
        "node_acknowledged_key_id": acknowledged_key_id,
        "rotation_state": posture,
        "activation_proven": activation_proven,
        "enforcement_proven": False,
    }


def _add_node_version_posture(
    summary: JsonObject,
    configuration_store: NodeConfigurationStore,
) -> None:
    generation_value = summary.get("desired_configuration_generation")
    generation = (
        generation_value
        if isinstance(generation_value, int) and not isinstance(generation_value, bool)
        else None
    )
    desired_assigned = generation is not None
    minimum_version: str | None = None
    desired_evidence_complete = False
    desired_source = "none"
    if generation is not None:
        try:
            desired = configuration_store.get(str(summary["node_id"]), generation)
            configuration = desired.bundle.get("configuration")
            candidate = (
                configuration.get("minimum_node_version")
                if isinstance(configuration, dict)
                else None
            )
            minimum_version = candidate if isinstance(candidate, str) else None
            expires_at = datetime.fromisoformat(desired.expires_at)
            desired_evidence_complete = (
                desired.evidence_status == "complete"
                and expires_at.tzinfo is not None
                and expires_at > datetime.now(UTC)
            )
            desired_source = "signed_desired_configuration"
        except (NodeConfigurationNotFoundError, ValueError):
            desired_source = "invalid_or_missing_desired_configuration"
    observed = summary.get("last_observed_node_version")
    observed_version = observed if isinstance(observed, str) else None
    summary["minimum_node_version"] = minimum_version
    summary["version_posture"] = node_version_posture(
        node_status=str(summary.get("status", "")),
        node_evidence_status=str(summary.get("evidence_status", "")),
        desired_assigned=desired_assigned,
        desired_evidence_complete=desired_evidence_complete,
        observed_version=observed_version,
        minimum_version=minimum_version,
    )
    summary["version_desired_source"] = desired_source
    summary["version_observed_source"] = (
        "gateway_accepted_signed_heartbeat" if observed_version is not None else "none"
    )
    summary["maintenance_control_source"] = "operator_managed"
    summary["package_authenticity_known"] = False
    summary["self_update_allowed"] = False


def _safe_query_filter(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if len(value) > 128 or any(ord(character) < 32 for character in value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid filter value",
        )
    return value


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
