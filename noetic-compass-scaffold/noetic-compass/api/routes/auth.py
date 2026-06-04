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
from fastapi import APIRouter, HTTPException, Request

from api.middleware.auth import create_token

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    username: str = "dashboard-user"
    # Phase-1 shared mint credential. Optional in the model so it can also be
    # supplied via the X-Auth-Mint-Secret header; the route enforces presence.
    mint_secret: str | None = None


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
async def generate_token(body: TokenRequest, request: Request) -> TokenResponse:
    """Issue a JWT signed with the server's secret.

    Two postures, selected by ``settings.accounts_enabled`` (default OFF):

    * **accounts_enabled=False (default).** Byte-for-byte the historical behaviour: the Phase-1
      mint lock (:func:`_authorize_mint`) gates the request, then a ``dashboard:<username>`` token
      is minted for the supplied username. The shared-secret/debug-open path is untouched, so the
      current internal smoke flow keeps working exactly as before.

    * **accounts_enabled=True.** The Phase-1 mint lock STILL runs first (preserved unchanged as the
      credential gate), and THEN identity is enforced against the durable account store: the
      supplied username/email must resolve to an EXISTING, ACTIVE account, or the mint is refused
      (401). When it resolves, the token is bound to that account's SERVER-DERIVED
      ``account_id``/``tenant_id``/``role`` -- never to anything from the request body. An unknown
      identity cannot log in; a disabled account cannot log in.
    """
    from api.config import settings

    # Phase-1 mint lock: PRESERVED unchanged, and it runs in BOTH postures. With accounts off this
    # is the whole gate; with accounts on it is the outer credential gate before the identity check.
    _authorize_mint(request, body)

    normalized = body.username.strip() or "dashboard-user"

    if settings.accounts_enabled:
        return _mint_for_account(request, normalized)

    # Default posture: unchanged shared-secret mint.
    api_key = f"dashboard:{normalized.lower()}"
    token = create_token(sub=normalized, api_key=api_key, exp_minutes=settings.jwt_expiry_minutes)
    return TokenResponse(token=token, expires_in_minutes=settings.jwt_expiry_minutes)


def _mint_for_account(request: Request, identity: str) -> TokenResponse:
    """Identity-login branch (accounts_enabled=True): bind the token to a real account.

    Fails closed: an identity with no account, or a disabled account, is refused with 401 -- an
    unknown or disabled user cannot obtain a token. On success the token carries the account's
    SERVER-DERIVED ``account_id``/``tenant_id``/``role`` claims (from the stored record), so a
    client can neither choose its own tenant/role nor mint an identity that does not exist.
    """
    from api.config import settings

    store = getattr(request.app.state, "account_store", None)
    if store is None:
        # accounts_enabled=True but no durable store installed -> honest failure, not a silent
        # fall-through to the open mint (which would defeat the identity gate). Startup is meant to
        # fail loud in this case; if we still reach here, refuse rather than mint unbound.
        raise HTTPException(
            status_code=503,
            detail="Account login is enabled but the account store is unavailable.",
        )

    account = store.get_account_by_email(identity)
    if account is None:
        # Unknown identity: no account exists for it. Fail closed.
        raise HTTPException(status_code=401, detail="No account exists for the supplied identity.")
    if not account.is_active:
        # Disabled account: locked out at login.
        raise HTTPException(status_code=401, detail="This account is disabled.")

    token = create_token(
        sub=account.email_or_username,
        api_key=f"account:{account.account_id}",
        exp_minutes=settings.jwt_expiry_minutes,
        account_id=account.account_id,
        tenant_id=account.tenant_id,
        role=account.role,
    )
    return TokenResponse(token=token, expires_in_minutes=settings.jwt_expiry_minutes)
