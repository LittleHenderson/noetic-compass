"""JWT Bearer token authentication middleware."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from api.acceptance_authority_contract import ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
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
    "/accounts/bootstrap",
    "/platform/tenants",
    # Stripe verifies this endpoint with the raw-body signature, not a CAS JWT.
    "/billing/webhook/stripe",
    # Platform-only route; its separate 32-byte admin secret is verified in-route.
    "/platform/billing/manual-comped-subscription",
    # Exact public support-intake route. Do not use a broad prefix: ticket
    # listing and lifecycle transitions remain authenticated operator actions.
    "/api/support/public/tickets",
    "/docs",
    "/openapi.json",
    "/redoc",
}

PUBLIC_ACCOUNT_CAPABILITIES_PATH = "/public/capabilities"
PUBLIC_SUPPORT_PRIVACY_NOTICE_PATH = "/api/support/public/privacy-notice"
# ALWAYS public, in EVERY posture: these never carry per-tenant evidence ownership, so identity is
# never required for them. Atlas LIVE has its own invite-code/session-token gate; target/verify and
# scale-plan are stateless validators/planners; live-worker/health is a liveness probe; /api/crm/public
# is anonymous lead capture (only the /public subtree is open — the authed sales views
# /api/crm/leads... stay protected by JWT).
ALWAYS_PUBLIC_PREFIXES = (
    "/atlas/live",
    "/api/cas-harness/audit/target/verify",
    "/api/cas-harness/audit/scale-plan",
    "/api/cas-harness/live-worker/health",
    "/api/crm/public",
)
# Backwards-compatible alias: external code (and older imports) referenced PUBLIC_PATH_PREFIXES as the
# always-public tuple. It now names exactly the always-public set, so any startswith check over it is
# unchanged for these prefixes.
PUBLIC_PATH_PREFIXES = ALWAYS_PUBLIC_PREFIXES
# Account-GATED public prefixes: the audit-session create/run/get/list routes. Public ONLY in the
# legacy/dark posture (accounts OFF — the live production default), so the deployed console keeps
# calling them without a login exactly as today. Once accounts are enabled they leave the allowlist
# and require identity, so the auth middleware decodes the jti token and sets
# request.state.tenant_id/account_id — the seam the per-tenant evidence-ownership write consumes.
ACCOUNT_GATED_PUBLIC_PREFIXES = (
    "/api/cas-harness/audit/session",
    "/api/cas-harness/audit/sessions",
)

# The anonymous Evidence Packet share has exactly one public GET-shaped path.
# Keep this as a full match rather than a broad prefix so no future management
# route below /evidence can accidentally inherit anonymous access.
_ANONYMOUS_EVIDENCE_SHARE_PATTERN = re.compile(
    r"^/evidence/shared/shr_[A-Za-z0-9_-]{20,64}$"
)


def is_public_path(path: str) -> bool:
    if (
        path in PUBLIC_PATHS
        or any(path.startswith(p) for p in ALWAYS_PUBLIC_PREFIXES)
        or _ANONYMOUS_EVIDENCE_SHARE_PATTERN.fullmatch(path) is not None
    ):
        return True
    # The audit-session routes are public ONLY in the legacy/dark posture. Once accounts are
    # enabled they require identity so the middleware sets request.state.tenant_id (the seam the
    # ownership write below consumes). Read settings.accounts_enabled at call time.
    if not settings.accounts_enabled:
        return any(path.startswith(p) for p in ACCOUNT_GATED_PUBLIC_PREFIXES)
    return False


def is_public_account_capability_request(
    path: str, method: str, query: str = ""
) -> bool:
    """Allow only the exact, query-free Atlas startup handshake GET.

    This deliberately cannot live in ``PUBLIC_PATHS``: that path-only set
    would also make every other HTTP method anonymous.  Keeping the method and
    query checks at the authentication chokepoint prevents a future route with
    the same path from silently inheriting broader public access.
    """

    return (
        method.upper() == "GET"
        and not query
        and path == PUBLIC_ACCOUNT_CAPABILITIES_PATH
    )


def is_public_support_privacy_notice_request(
    path: str, method: str, query: str = ""
) -> bool:
    """Allow only the exact, query-free public support notice metadata GET."""

    return (
        method.upper() == "GET"
        and not query
        and path == PUBLIC_SUPPORT_PRIVACY_NOTICE_PATH
    )


def is_public_acceptance_authority_request(
    path: str, method: str, query: str = ""
) -> bool:
    """Allow only exact, query-free GETs to the public authority documents.

    These paths cannot live in ``PUBLIC_PATHS`` because that path-only helper
    would also make POST/PUT/DELETE anonymous.  Keeping the method check here is
    the authentication boundary for this deliberately secret-free read surface.
    """

    return (
        method.upper() == "GET"
        and not query
        and path in ACCEPTANCE_AUTHORITY_PUBLIC_PATHS
    )


ACCOUNT_MODE_ALLOWED_PREFIXES = (
    "/auth/",
    "/accounts/",
    "/billing/",
    "/api/cas-harness/audit/session",
    "/api/cas-harness/audit/sessions",
    "/evidence",
    "/health",
    "/notation",
    "/api/support/tickets",
)

_FLEET_SERVICE_CALLBACK_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^/api/cas-harness/audit/distributed/fleet/worker/register$",
        r"^/api/cas-harness/audit/distributed/fleet/worker/[^/]+/heartbeat$",
        r"^/api/cas-harness/audit/distributed/session/[^/]+/worker/[^/]+/(?:running|evidence)$",
        r"^/api/cas-harness/audit/distributed/session/[^/]+/merge$",
        r"^/api/cas-harness/audit/distributed/session/[^/]+/fleet/job/lease$",
        r"^/api/cas-harness/audit/distributed/session/[^/]+/fleet/job/[^/]+/receipt$",
        r"^/api/cas-harness/audit/distributed/session/[^/]+/fleet/(?:merge|verifier)$",
    )
)


def is_fleet_service_callback_path(path: str) -> bool:
    """Return whether ``path`` is a callback guarded by fleet service auth at its route."""
    return any(pattern.fullmatch(path) for pattern in _FLEET_SERVICE_CALLBACK_PATTERNS)


def is_account_mode_allowed_path(path: str) -> bool:
    """Customer tokens may reach only routes with an explicit tenant/account boundary."""
    if settings.fleet_service_auth_enabled and path.startswith(
        "/api/cas-harness/audit/distributed"
    ):
        return True
    return any(path.startswith(prefix) for prefix in ACCOUNT_MODE_ALLOWED_PREFIXES)




class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT Bearer tokens on protected endpoints."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if (
            is_public_path(request.url.path)
            or is_public_account_capability_request(
                request.url.path, request.method, request.url.query
            )
            or is_public_support_privacy_notice_request(
                request.url.path, request.method, request.url.query
            )
            or is_public_acceptance_authority_request(
                request.url.path, request.method, request.url.query
            )
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # Worker/merger/verifier callbacks use a separate tenant-bound credential.  Let the
        # matched route perform capability/scope/nonce verification; customer Bearer JWTs are
        # deliberately not accepted for these machine-to-machine actions.
        if settings.fleet_service_auth_enabled and is_fleet_service_callback_path(
            request.url.path
        ):
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


        # --- account-mode enforcement (session + account-status) ---------------------------------
        # A token MINTED by the identity-login path carries a ``jti`` (its session id) and the
        # SERVER-DERIVED account_id/tenant_id/role claims. ONLY such tokens get the extra checks
        # below. A token with NO ``jti`` is a legacy shared-secret token (minted when accounts are
        # off); it MUST flow exactly as before this PR -- no session lookup, no new failure mode --
        # which is what preserves the default-off smoke flow byte-for-byte.
        jti = payload.get("jti")
        session_store = getattr(request.app.state, "session_store", None)
        account_store = getattr(request.app.state, "account_store", None)
        if settings.accounts_enabled:
            # Account mode is all-or-nothing. Legacy no-jti tokens and unavailable stores must
            # never fall through as authenticated legacy callers because that bypasses revocation.
            if jti is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Account session is required"},
                )
            if session_store is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Session verification is unavailable"},
                )
            if account_store is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Account verification is unavailable"},
                )

            # Session must exist and be live (not revoked, not expired). A revoked session (logout /
            # admin revoke) or an expired one fails the NEXT request here -- enforcement at the
            # chokepoint, not merely at login.
            session = session_store.get_session(str(jti))
            if session is None or not session.is_live():
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Session is no longer valid"},
                )
            # Re-check account status so a DISABLE takes effect on the next request, even though the
            # role/tenant were copied into the session at login. A missing account store while
            # account-mode is on is an honest failure, not a silent pass.
            account = account_store.get_account_by_id(session.account_id)
            if account is None or not account.is_active:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Account is disabled"},
                )
            if (
                session.auth_epoch != account.auth_epoch
                or session.tenant_id != account.tenant_id
            ):
                return JSONResponse(
                    status_code=401, content={"detail": "Session credential is stale"}
                )
            # Attach SERVER-DERIVED identity for the central authz dependency. Sourced from the
            # session/account records, never from the request body -- ``require_role`` reads exactly
            # these. Role comes from the live account record (authoritative now), tenant from the
            # session (the granted tenant fixed at login).
            request.state.account_id = session.account_id
            request.state.tenant_id = session.tenant_id
            request.state.role = account.role
            request.state.session_id = session.session_id
            # Best-effort last-seen; never blocks or fails the request.
            session_store.touch_session(session.session_id)

        if settings.accounts_enabled and not is_account_mode_allowed_path(
            request.url.path
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Route is unavailable to customer account credentials."},
            )

        return await call_next(request)


def create_token(
    sub: str,
    api_key: str = "default",
    exp_minutes: int | None = None,
    *,
    account_id: str | None = None,
    tenant_id: str | None = None,
    role: str | None = None,
    jti: str | None = None,
) -> str:
    """Create a JWT token.

    Backward-compatible by construction: with no ``account_id``/``tenant_id``/``role``/``jti``
    supplied the payload is exactly the historical ``{sub, api_key, exp}`` and every existing
    caller/token is unchanged. When the identity-login path (``api/routes/auth.py``) supplies
    SERVER-DERIVED account claims, they are embedded ADDITIVELY as ``account_id``/``tenant_id``/
    ``role``, and the session it opened is embedded as ``jti``.

    ``jti`` is the session id the login created (see ``api/services/sessions``). Its PRESENCE is the
    signal the dispatch path uses to tell an account-mode token from a legacy shared-secret token: a
    token with a ``jti`` gets the session-live + account-not-disabled checks at the chokepoint; a
    token with NO ``jti`` (the legacy ``dashboard:<user>`` mint used when accounts are off) flows
    exactly as before, with no session lookup. This is what keeps the default-off smoke flow
    byte-for-byte unchanged.

    All of these claims are only ever passed in by the server after an account lookup; they are never
    read from a request body.
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
    # Session id (== session record id). Its presence marks the token as account-mode at dispatch.
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
