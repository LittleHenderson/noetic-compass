"""Token generation endpoint for dashboard login.

CAS Harness scoped-beta Phase 1 — mint lock.
---------------------------------------------
Historically ``POST /auth/token`` minted a valid JWT for ANY username with no
credential at all (it sits in PUBLIC_PATHS), so anyone who could reach the API
could mint a token for any identity. That is fine for purely local dev but is a
blocking hole for any external exposure.

This module closes that hole with a *shared* mint credential (Phase 1):

* ``NC_AUTH_MINT_SECRET`` set  -> the secret is REQUIRED in every environment.
  A request must present it (``X-Auth-Mint-Secret`` header or ``mint_secret``
  body field) or it is refused with HTTP 401.
* ``NC_AUTH_MINT_SECRET`` unset -> the legacy open mint (any username, no
  credential) is allowed ONLY when ``settings.debug`` is True, so local work is
  unaffected. In non-debug (production) an unset secret refuses the mint
  entirely — production is never an open mint.

PHASE-2 SEAM: this is a single shared credential, NOT per-account auth. The next
step is per-account issued API keys — each account holds its own key and the
minted token is scoped to that account — replacing this shared-secret gate with
a real identity lookup. When that lands, the credential check below becomes a
per-key verification and the debug-gated open path should be removed.
"""

import hmac

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.dependencies.authz import require_role
from api.services.accounts.models import can_manage_role
from api.middleware.auth import create_token

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    username: str = "dashboard-user"
    # Phase-1 shared mint credential. Optional in the model so it can also be
    # supplied via the X-Auth-Mint-Secret header; the route enforces presence.
    mint_secret: str | None = None
    api_credential: str | None = None


class TokenResponse(BaseModel):
    token: str
    expires_in_minutes: int


def _authorize_mint(request: Request, body: TokenRequest) -> None:
    """Enforce the Phase-1 mint lock. Raises HTTP 401 when the mint is not authorized.

    Decision (debug-gated-open + secret-in-prod): when no shared secret is
    configured we keep the frictionless open mint for local dev only (debug
    True) and fail closed in production (debug False). When a secret IS
    configured it is required everywhere. This keeps local work unbroken while
    guaranteeing production is never an open mint.
    """
    from api.config import settings

    configured = settings.auth_mint_secret

    if not configured:
        # No shared secret set: open mint allowed for local dev only.
        if settings.debug:
            return
        raise HTTPException(
            status_code=401,
            detail=(
                "Token minting is disabled: no NC_AUTH_MINT_SECRET is configured and the "
                "server is not in debug mode."
            ),
        )

    # A shared secret is configured -> it must be presented and must match.
    presented = request.headers.get("X-Auth-Mint-Secret") or body.mint_secret or ""
    # Constant-time comparison; encode to bytes so non-ASCII secrets compare safely.
    if not hmac.compare_digest(presented.encode("utf-8"), configured.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing mint credential.",
        )


@router.post("/auth/token", response_model=TokenResponse)
async def generate_token(
    body: TokenRequest, request: Request, response: Response
) -> TokenResponse:
    """Issue a JWT signed with the server's secret.

    Two postures, selected by ``settings.accounts_enabled`` (default OFF):

    * **accounts_enabled=False (default).** Byte-for-byte the historical behaviour: the Phase-1
      mint lock (:func:`_authorize_mint`) gates the request, then a ``dashboard:<username>`` token
      is minted for the supplied username. The shared-secret/debug-open path is untouched, so the
      current internal smoke flow keeps working exactly as before.

    * **accounts_enabled=True.** The deployment-global mint secret is disabled. The supplied
      username/email and per-account credential must authenticate an EXISTING, ACTIVE account,
      or the mint is refused (401). When it resolves, the token is bound to that account's
      SERVER-DERIVED
      ``account_id``/``tenant_id``/``role`` -- never to anything from the request body. An unknown
      identity cannot log in; a disabled account cannot log in.
    """
    from api.config import settings
    response.headers["Cache-Control"] = "no-store"

    normalized = body.username.strip() or "dashboard-user"
    if settings.accounts_enabled:
        # Account mode never accepts the deployment-global mint secret. Authentication is bound to
        # the individual account credential issued by invite redemption or first-owner bootstrap.
        return _mint_for_account(request, normalized, body.api_credential)

    # Phase-1 mint lock: PRESERVED unchanged, and it runs in BOTH postures. With accounts off this
    # is the whole gate; with accounts on it is the outer credential gate before the identity check.
    _authorize_mint(request, body)

    # Default posture: unchanged shared-secret mint.
    api_key = f"dashboard:{normalized.lower()}"
    token = create_token(sub=normalized, api_key=api_key, exp_minutes=settings.jwt_expiry_minutes)
    return TokenResponse(token=token, expires_in_minutes=settings.jwt_expiry_minutes)


def _mint_for_account(
    request: Request, identity: str, api_credential: str | None
) -> TokenResponse:
    """Identity-login branch (accounts_enabled=True): bind the token to a real account + session.

    Fails closed: an identity with no account, or a disabled account, is refused with 401 -- an
    unknown or disabled user cannot obtain a token. On success the login OPENS A DURABLE SESSION and
    the token carries the account's SERVER-DERIVED ``account_id``/``tenant_id``/``role`` claims plus
    the session id as ``jti`` (from the stored records), so a client can neither choose its own
    tenant/role nor mint an identity that does not exist. The ``jti`` is what makes this token
    revocable + chokepoint-expirable: the dispatch middleware looks the session up on every request
    and rejects a revoked/expired one (see ``api/middleware/auth.py``).
    """
    from datetime import timedelta

    from api.config import settings
    from api.services.production.state_substrate import utc_now

    store = getattr(request.app.state, "account_store", None)
    if store is None:
        # accounts_enabled=True but no durable store installed -> honest failure, not a silent
        # fall-through to the open mint (which would defeat the identity gate). Startup is meant to
        # fail loud in this case; if we still reach here, refuse rather than mint unbound.
        raise HTTPException(
            status_code=503,
            detail="Account login is enabled but the account store is unavailable.",
        )

    account = store.authenticate_account(identity, api_credential)
    if account is None:
        # Unknown identity, wrong/missing credential, and disabled account deliberately share one
        # response so the public login endpoint cannot enumerate account existence or state.
        raise HTTPException(status_code=401, detail="Invalid account credentials.")

    # Open a durable session. Its id becomes the token ``jti``; its expiry mirrors the token's so a
    # session never outlives the credential it backs. The session is what the chokepoint revokes
    # against -- without it the token would only be checkable at issue time.
    session_store = getattr(request.app.state, "session_store", None)
    if session_store is None:
        # accounts_enabled=True but no session store -> the token could not be revoked at the
        # chokepoint, defeating logout/disable enforcement. Refuse rather than mint an
        # unrevokable account-mode token. (Startup fails loud in this case; this is the backstop.)
        raise HTTPException(
            status_code=503,
            detail="Account login is enabled but the session store is unavailable.",
        )

    expiry_minutes = settings.jwt_expiry_minutes
    session_expires_at = (utc_now() + timedelta(minutes=expiry_minutes)).isoformat()
    session = session_store.create_session(
        account_id=account.account_id,
        tenant_id=account.tenant_id,
        role=account.role,
        auth_epoch=account.auth_epoch,
        expires_at=session_expires_at,
    )

    token = create_token(
        sub=account.email_or_username,
        api_key=f"account:{account.account_id}",
        exp_minutes=expiry_minutes,
        account_id=account.account_id,
        tenant_id=account.tenant_id,
        role=account.role,
        jti=session.session_id,
    )
    return TokenResponse(token=token, expires_in_minutes=expiry_minutes)


# --- logout / revoke -------------------------------------------------------


class LogoutResponse(BaseModel):
    revoked: bool


def _session_store(request: Request):
    """Return the installed durable session store, or 503.

    Mirrors the accounts route's fail-closed durability posture: session state is never served from
    an ephemeral fallback. A missing store means account-mode is not enabled/installed, and the
    honest response is "unavailable", not a fabricated success.
    """
    store = getattr(request.app.state, "session_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Sessions are not enabled on this deployment.",
        )
    return store


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(request: Request) -> LogoutResponse:
    """Revoke the caller's CURRENT session (the one its bearer token names).

    The session id is taken from ``request.state.session_id`` -- set by the dispatch middleware from
    the verified token's ``jti``, NEVER from the request body -- so a caller can only ever log
    *itself* out, not someone else. After this returns, the next request bearing the same token is
    rejected at the dispatch chokepoint (the session is now revoked). Idempotent: logging out an
    already-revoked (or unknown) session still returns ``revoked: true`` -- the post-condition (this
    token's session is dead) holds.

    This endpoint is NOT public: it sits behind the JWT middleware, and only an account-mode token
    (one carrying a ``jti``) establishes a ``session_id`` to revoke. A token with no session id (a
    legacy shared-secret token) has no server-side session to revoke and gets a 400.
    """
    store = _session_store(request)
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        # Authenticated by the middleware, but this token has no session to revoke (not an
        # account-mode token). Nothing to do; tell the caller plainly rather than pretend.
        raise HTTPException(
            status_code=400,
            detail="This token has no server-side session to revoke.",
        )
    store.revoke_session(str(session_id))
    return LogoutResponse(revoked=True)


@router.post("/auth/sessions/{session_id}/revoke", response_model=LogoutResponse)
async def revoke_session_admin(
    session_id: str,
    request: Request,
    _role: str = Depends(require_role("admin", "owner", "operator")),
) -> LogoutResponse:
    """Revoke ANY session by id -- a privileged admin/operator action (role-gated).

    Gated by :func:`require_role`: a member-role token is refused with 403; an unauthenticated
    request is 401. The role is read from the SERVER-SET ``request.state.role`` (never the body).
    Idempotent -- revoking an unknown or already-revoked session returns ``revoked: true``.

    The target session and its backing account must both belong to the caller's tenant, and the
    caller must outrank the target role. Cross-tenant ids fail as indistinguishable 404s.
    """
    store = _session_store(request)
    target = store.get_session(session_id)
    if target is None:
        return LogoutResponse(revoked=True)
    actor_tenant = str(getattr(request.state, "tenant_id", "") or "")
    if not actor_tenant or target.tenant_id != actor_tenant:
        raise HTTPException(status_code=404, detail="Session not found.")
    account_store = getattr(request.app.state, "account_store", None)
    target_account = (
        account_store.get_account_by_id(target.account_id)
        if account_store is not None
        else None
    )
    if target_account is None or target_account.tenant_id != actor_tenant:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not can_manage_role(_role, target_account.role):
        raise HTTPException(status_code=403, detail="Role escalation is not permitted.")
    store.revoke_session(session_id)
    return LogoutResponse(revoked=True)
