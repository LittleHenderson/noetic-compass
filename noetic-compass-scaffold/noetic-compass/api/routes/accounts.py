"""Account routes -- invite redemption (public, fail-closed) + invite creation (gated).

Two endpoints over :class:`~api.services.accounts.store.AccountStore` (built once at startup and
stashed on ``app.state.account_store`` -- see ``api/main.py``):

* ``POST /accounts/invite/redeem`` -- **public** (a brand-new user has no token yet). Redeems an
  invite code into EXACTLY ONE durable account, fail-closed. The store does the atomic work; the
  route maps every redemption failure to a single 400 shape so the endpoint is non-enumerable (a
  caller cannot tell "no such code" from "used code" from "expired code"). It returns the account's
  PUBLIC projection only -- no secret, and it never mints a token here (login is ``/auth/token``).

* ``POST /accounts/invite`` -- **gated**. Creates an invite. Full RBAC (an operator/admin role
  check) is a LATER PR; for now this is restricted to debug OR a presented operator secret
  (the existing shared mint secret, reused as a coarse operator gate). See the TODO below.

Durability is NON-NEGOTIABLE for account state: unlike the CRM route, this endpoint does NOT fall
back to an in-memory store. If no durable account store was installed (``accounts_enabled`` off, or
a misconfigured deployment), the endpoints return 503 rather than fabricate ephemeral account
state. Account/invite records must be durable or absent -- never silently in-memory.
"""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.config import settings
from api.services.accounts.models import DEFAULT_INVITE_ROLE, ROLE_VALUES, Role
from api.services.accounts.store import AccountStore, InviteRedemptionError

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _account_store(request: Request) -> AccountStore:
    """Return the installed durable account store, or 503.

    Fail-closed on durability: account state is never served from an ephemeral fallback. A missing
    store means the spine was not enabled/installed, and the honest response is "unavailable", not
    a silently in-memory account.
    """
    store = getattr(request.app.state, "account_store", None)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Accounts are not enabled on this deployment.",
        )
    return store


# --- redeem (public, fail-closed) -----------------------------------------


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=512)
    email_or_username: str = Field(..., min_length=1, max_length=320)
    display_name: Optional[str] = Field(default=None, max_length=200)
    # NOTE: there is deliberately NO role / tenant_id / account_id field here. Those are
    # SERVER-DERIVED from the invite record; accepting them from the body would let a client
    # escalate its own privilege. Any such field a client sends is simply not part of this model
    # and is ignored.


class AccountResponse(BaseModel):
    account_id: str
    email_or_username: str
    role: str
    tenant_id: str
    status: str
    display_name: Optional[str] = None
    created_at: str
    updated_at: str


@router.post("/invite/redeem", response_model=AccountResponse)
async def redeem_invite(body: RedeemRequest, request: Request) -> AccountResponse:
    """Redeem an invite into exactly one account. Fail-closed on any invalid/used/expired code."""
    store = _account_store(request)
    try:
        account = store.redeem_invite(
            code=body.code,
            email_or_username=body.email_or_username,
            display_name=body.display_name,
        )
    except InviteRedemptionError as exc:
        # Every redemption failure collapses to ONE identical 400 shape -- same status, same body,
        # regardless of whether the code was unknown / used / expired / mismatched / email-taken.
        # The coarse ``exc.reason`` is kept server-side (the exception carries it for logging) and
        # deliberately NOT surfaced to the client, so redemption stays non-enumerable: a caller
        # cannot probe which codes exist or which emails are taken.
        raise HTTPException(
            status_code=400,
            detail="Invite code could not be redeemed.",
        ) from exc
    return AccountResponse(**account.to_dict())


# --- invite creation (gated; full RBAC is a later PR) ---------------------


class CreateInviteRequest(BaseModel):
    role: Role = DEFAULT_INVITE_ROLE
    target_email: Optional[str] = Field(default=None, max_length=320)
    tenant_id: Optional[str] = Field(default=None, max_length=200)
    expires_at: Optional[str] = Field(default=None, max_length=64)
    max_uses: int = Field(default=1, ge=1, le=10_000)


class CreateInviteResponse(BaseModel):
    code: str
    role: str
    tenant_id: str
    target_email: Optional[str] = None
    expires_at: Optional[str] = None
    max_uses: int
    uses: int
    created_at: str


def _authorize_invite_create(request: Request) -> None:
    """Coarse gate for invite creation until real RBAC lands.

    TODO(Phase 5 / RBAC): replace this with a ``require_role("operator"|"admin")`` dependency once
    the role-claim + central authz dependency exist. For now, restrict invite creation to:
      * a debug deployment (local dev/demo), OR
      * a request presenting the operator secret (the shared ``NC_AUTH_MINT_SECRET``, reused here
        purely as a coarse operator credential) via ``X-Auth-Mint-Secret``.
    With no operator secret configured and debug off, invite creation is refused (fail closed).
    """
    if settings.debug:
        return
    configured = settings.auth_mint_secret
    presented = request.headers.get("X-Auth-Mint-Secret", "")
    if configured and hmac.compare_digest(
        presented.encode("utf-8"), configured.encode("utf-8")
    ):
        return
    raise HTTPException(
        status_code=403,
        detail="Invite creation requires operator authorization.",
    )


@router.post("/invite", response_model=CreateInviteResponse)
async def create_invite(body: CreateInviteRequest, request: Request) -> CreateInviteResponse:
    """Create an invite code. Gated (debug or operator secret) until RBAC lands."""
    _authorize_invite_create(request)
    store = _account_store(request)
    if body.role not in ROLE_VALUES:
        raise HTTPException(status_code=422, detail=f"invalid role {body.role!r}")
    invite = store.create_invite(
        role=body.role,
        target_email=body.target_email,
        tenant_id=body.tenant_id,
        expires_at=body.expires_at,
        max_uses=body.max_uses,
    )
    return CreateInviteResponse(
        code=invite.code,
        role=invite.role,
        tenant_id=invite.tenant_id,
        target_email=invite.target_email,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses=invite.uses,
        created_at=invite.created_at,
    )
