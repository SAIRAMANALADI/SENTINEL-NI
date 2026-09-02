"""Configurable bearer-token authentication and role authorization."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer_scheme = HTTPBearer(auto_error=False)
ROLE_LEVEL = {"viewer": 1, "operator": 2, "admin": 3}


def _security_event(request: Request, *, result: str, reason: str) -> None:
    """Record authentication failures without retaining the presented token."""

    try:
        request.app.state.runtime.audit.record(
            event_type="authentication_failed" if result != "forbidden" else "authorization_denied",
            model_version="security-v1",
            policy_version="security-policy-v1",
            result=result,
            reason=reason,
            request_id=getattr(request.state, "request_id", None),
            source_ip=request.client.host if request.client else None,
        )
    except Exception:
        # Security telemetry must never turn an authentication decision into an
        # availability failure or expose details in the response.
        return


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
            _security_event(request, result="missing", reason="bearer credential missing")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTHENTICATION_REQUIRED", "message": "bearer authentication is required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        role = _role_for_token(credentials.credentials, settings.role_tokens())
        if role is None:
            _security_event(request, result="invalid", reason="bearer credential not recognized")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "the bearer token is not recognized"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if ROLE_LEVEL[role] < ROLE_LEVEL[required]:
            _security_event(request, result="forbidden", reason=f"{required} role required")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INSUFFICIENT_ROLE", "message": f"{required} role is required"},
            )
        return role

    return dependency
