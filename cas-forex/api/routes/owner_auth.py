"""Owner-auth routes: pair a device, turn LAN access on/off, rotate the token.

The sensitive actions here — reading the full token, enabling LAN access,
rotating — are LOOPBACK-ONLY: they can only be called from the PC running CAS
Forex, never from a paired phone over the network. That keeps "arm network
access" a physical-owner action. ``/state`` is safe (no full token) and is
reachable by any already-admitted caller.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cas_forex import owner_auth

router = APIRouter()


def _require_loopback(request: Request) -> JSONResponse | None:
    host = request.client.host if request.client else None
    if owner_auth.request_is_loopback(host):
        return None
    return JSONResponse(
        status_code=403,
        content={
            "error": "loopback_only",
            "detail": "This action can only be performed on the PC running CAS Forex.",
        },
    )


class LanMode(BaseModel):
    enabled: bool


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Safe status — presence + hint only, never the full token."""
    token = owner_auth.current_token()
    return {
        "report_kind": "cas_forex_owner_auth",
        "token_present": bool(token),
        "token_hint": owner_auth.mask_token(token),
        "lan_mode_enabled": owner_auth.lan_mode_enabled(),
        "claim_boundary": owner_auth.CLAIM_BOUNDARY,
    }


@router.get("/pairing")
async def get_pairing(request: Request):
    """The full token + how-to-pair. LOOPBACK ONLY (served on the owner's PC)."""
    blocked = _require_loopback(request)
    if blocked is not None:
        return blocked
    return owner_auth.pairing_payload()


@router.post("/lan-mode")
async def post_lan_mode(body: LanMode, request: Request):
    """Turn authenticated LAN access on/off. LOOPBACK ONLY."""
    blocked = _require_loopback(request)
    if blocked is not None:
        return blocked
    result = owner_auth.set_lan_mode(body.enabled)
    return {"report_kind": "cas_forex_owner_auth", **result}


@router.post("/rotate")
async def post_rotate(request: Request):
    """Generate a fresh token (unpairs every device). LOOPBACK ONLY."""
    blocked = _require_loopback(request)
    if blocked is not None:
        return blocked
    owner_auth.rotate_token()
    return {"report_kind": "cas_forex_owner_auth", "rotated": True, "token_hint": owner_auth.mask_token(owner_auth.current_token())}
