"""JWT Bearer token authentication middleware."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings

# Paths that don't require JWT authentication. Atlas LIVE has its own
# invite-code/session-token gate because the alpha does not have the full
# licensing auth flow yet. CAS Harness audit beta keeps only the reference
# demo/session lifecycle public. Distributed/fleet endpoints are protected
# because they can register workers, lease jobs, and submit evidence receipts.
PUBLIC_PATHS = {
    "/health",
    "/health/db",
    "/health/ready",
    "/auth/token",
    # Invite redemption is public: a brand-new user has no token yet, so the redeem endpoint must
    # be reachable unauthenticated. It is fail-closed on the invite code itself (the store rejects
    # any invalid/used/expired code), and creates only a single account. Invite CREATION
    # (/accounts/invite) is deliberately NOT public — it stays behind the JWT + operator gate.
    "/accounts/invite/redeem",
    "/docs",
    "/openapi.json",
    "/redoc",
}
PUBLIC_PATH_PREFIXES = (
    "/atlas/live",
    "/api/cas-harness/audit/target/verify",
    "/api/cas-harness/audit/scale-plan",
    "/api/cas-harness/audit/session",
    "/api/cas-harness/audit/sessions",
    "/api/cas-harness/live-worker/health",
    # Public lead capture: an anonymous prospect's form posts here. Only the /public subtree is
    # open; the authed sales views (/api/crm/leads...) stay protected by JWT.
    "/api/crm/public",
)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT Bearer tokens on protected endpoints."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if is_public_path(request.url.path) or request.method == "OPTIONS":
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


def create_token(
    sub: str,
    api_key: str = "default",
    exp_minutes: int | None = None,
    *,
    account_id: str | None = None,
    tenant_id: str | None = None,
    role: str | None = None,
) -> str:
    """Create a JWT token.

    Backward-compatible by construction: with no ``account_id``/``tenant_id``/``role`` supplied the
    payload is exactly the historical ``{sub, api_key, exp}`` and every existing caller/token is
    unchanged. When the identity-login path (``api/routes/auth.py``) supplies SERVER-DERIVED
    account claims, they are embedded ADDITIVELY as ``account_id``/``tenant_id``/``role``.

    These claims are only ever passed in by the server after an account lookup; they are never read
    from a request body. The dispatch-side enforcement that *consumes* them (session/jti checks,
    disabled-account lockout at the chokepoint, ``require_role``) is deferred to the NEXT spine PR
    -- this PR only mints the claims so the account they describe is recorded in the token.
    """
    from datetime import timedelta

    expires = datetime.now(tz=timezone.utc) + timedelta(
        minutes=exp_minutes or settings.jwt_expiry_minutes
    )
    payload: dict[str, object] = {"sub": sub, "api_key": api_key, "exp": expires}
    # Additive, optional claims. Only present when the server derived them from an account record.
    if account_id is not None:
        payload["account_id"] = account_id
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
