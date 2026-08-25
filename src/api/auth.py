"""Configurable bearer-token authentication and role authorization."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer_scheme = HTTPBearer(auto_error=False)
ROLE_LEVEL = {"viewer": 1, "operator": 2, "admin": 3}


def _role_for_token(token: str, tokens: dict[str, str | None]) -> str | None:
    for role, configured in tokens.items():
        if configured and secrets.compare_digest(token, configured):
            return role
    return None


def require_role(required: str) -> Callable[..., Awaitable[str]]:
    if required not in ROLE_LEVEL:
        raise ValueError(f"unsupported role: {required}")

    async def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> str:
        settings = request.app.state.runtime.settings
        if not settings.auth_enabled:
            return "development"
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTHENTICATION_REQUIRED", "message": "bearer authentication is required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        role = _role_for_token(credentials.credentials, settings.role_tokens())
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "the bearer token is not recognized"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if ROLE_LEVEL[role] < ROLE_LEVEL[required]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INSUFFICIENT_ROLE", "message": f"{required} role is required"},
            )
        return role

    return dependency

