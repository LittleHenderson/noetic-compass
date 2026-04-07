"""JWT Bearer token authentication middleware."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings

# Paths that don't require authentication
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT Bearer tokens on protected endpoints."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid token: {e}"},
            )

        # Check expiry
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            return JSONResponse(
                status_code=401,
                content={"detail": "Token expired"},
            )

        # Attach user info to request state
        request.state.user = payload.get("sub", "anonymous")
        request.state.api_key = payload.get("api_key", "default")

        return await call_next(request)


def create_token(sub: str, api_key: str = "default", exp_minutes: int | None = None) -> str:
    """Create a JWT token (utility for testing)."""
    from datetime import timedelta

    expires = datetime.now(tz=timezone.utc) + timedelta(
        minutes=exp_minutes or settings.jwt_expiry_minutes
    )
    payload = {"sub": sub, "api_key": api_key, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
