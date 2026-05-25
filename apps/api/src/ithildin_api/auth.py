"""Authentication dependencies for the Ithildin API service."""

from __future__ import annotations

from hmac import compare_digest
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ithildin_api.config import Settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are not configured")
    return settings


admin_credentials = Depends(bearer_scheme)
admin_settings = Depends(get_settings)


def require_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = admin_credentials,
    settings: Settings = admin_settings,
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not compare_digest(credentials.credentials, settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid bearer token",
        )
