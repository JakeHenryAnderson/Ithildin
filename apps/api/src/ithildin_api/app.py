"""FastAPI application factory for the Ithildin API service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI
from ithildin_schemas import JsonObject

from ithildin_api.auth import require_admin_token
from ithildin_api.config import Settings, load_settings
from ithildin_api.database import initialize_database
from ithildin_api.logging import configure_logging
from ithildin_api.registry import ToolRegistry

SERVICE_NAME = "ithildin-api"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or load_settings()
        configure_logging(resolved_settings.log_level)
        app_instance.state.settings = resolved_settings
        initialize_database(resolved_settings.db_path)
        app_instance.state.registry = ToolRegistry.load(resolved_settings.manifest_dir)
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

    return api


app = create_app()
