"""FastAPI application factory for the Ithildin API service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, cast

from fastapi import Depends, FastAPI, HTTPException, status
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import ApprovalDecisionValue, ApprovalRequest, JsonObject
from pydantic import BaseModel

from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_api.auth import require_admin_token
from ithildin_api.config import Settings, load_settings
from ithildin_api.database import initialize_database
from ithildin_api.logging import configure_logging
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry

SERVICE_NAME = "ithildin-api"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or load_settings()
        configure_logging(resolved_settings.log_level)
        app_instance.state.settings = resolved_settings
        initialize_database(resolved_settings.db_path)
        audit_writer = AuditWriter(resolved_settings.db_path, resolved_settings.audit_log_path)
        audit_writer.initialize()
        app_instance.state.audit_writer = audit_writer
        approval_store = ApprovalStore(resolved_settings.db_path)
        approval_store.initialize()
        app_instance.state.approval_service = ApprovalService(
            approval_store,
            audit_writer,
            timedelta(seconds=resolved_settings.approval_expiry_seconds),
        )
        app_instance.state.registry = ToolRegistry.load(resolved_settings.manifest_dir)
        app_instance.state.policy_evaluator = PolicyEvaluator.load(resolved_settings.policy_path)
        app_instance.state.read_tool_executor = ReadToolExecutor.from_settings(
            workspace_root=resolved_settings.workspace_root,
            max_read_bytes=resolved_settings.max_read_bytes,
            search_result_limit=resolved_settings.search_result_limit,
            git_log_limit=resolved_settings.git_log_limit,
        )
        logging.getLogger(__name__).info("api service started")
        yield

    api = FastAPI(title="Ithildin API", lifespan=lifespan)

    @api.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @api.get("/admin/status", dependencies=[Depends(require_admin_token)])
    def admin_status() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME, "admin": "authenticated"}

    @api.get("/tools", dependencies=[Depends(require_admin_token)])
    def list_tools(principal: Optional[str] = None) -> dict[str, list[JsonObject]]:
        registry = api.state.registry
        tools = [tool.summary() for tool in registry.list_tools(principal=principal)]
        return {"tools": tools}

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
        approval_service = cast(ApprovalService, api.state.approval_service)
        try:
            return approval_service.approve(
                approval_id,
                decided_by=payload.decided_by,
                reason=payload.reason,
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @api.post("/approvals/{approval_id}/deny", dependencies=[Depends(require_admin_token)])
    def deny_approval(approval_id: str, payload: ApprovalDecisionPayload) -> ApprovalRequest:
        approval_service = cast(ApprovalService, api.state.approval_service)
        try:
            return approval_service.deny(
                approval_id,
                decided_by=payload.decided_by,
                reason=payload.reason,
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return api


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


def _approval_or_404(approval_service: ApprovalService, approval_id: str) -> ApprovalRequest:
    try:
        return approval_service.get(approval_id)
    except ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


app = create_app()
