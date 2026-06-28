"""HTTP routes for the owner-controlled MT4 EA mailbox route.

``GET /state`` reports whether the route is enabled, the mailbox folder, and the
EA heartbeat (present/fresh/stale). ``POST /update`` turns the route on/off and
points it at the MT4 terminal's mailbox folder. ``POST /reset`` reverts to
config/env defaults. ``GET /heartbeat`` is the live EA link status.

The MT4 file-mailbox is the stable real-order route. Enabling it writes PAPER_MT4
command intents the EA acknowledges; it does not authorize live money.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from cas_forex.mt4_control import (
    build_mt4_control_report,
    clear_mt4_control_overrides,
    read_ea_heartbeat,
    resolve_mt4_control,
    set_mt4_control_overrides,
)

router = APIRouter()


class MT4ControlUpdate(BaseModel):
    enabled: Optional[bool] = None
    mailbox_dir: Optional[str] = None


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Enable state + mailbox folder + EA heartbeat status."""
    return build_mt4_control_report()


@router.post("/update")
async def post_update(body: MT4ControlUpdate) -> dict[str, Any]:
    """Turn the MT4 route on/off and set the mailbox folder. Returns full state."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        try:
            set_mt4_control_overrides(**provided)
        except ValueError as exc:
            return {"report_kind": "cas_forex_mt4_control", "error": str(exc), **build_mt4_control_report()}
    return build_mt4_control_report()


@router.post("/reset")
async def post_reset() -> dict[str, Any]:
    """Revert MT4 route settings to config/env defaults."""
    clear_mt4_control_overrides()
    return build_mt4_control_report()


@router.get("/heartbeat")
async def get_heartbeat() -> dict[str, Any]:
    """Live EA heartbeat status (present / fresh / stale + last-seen age)."""
    ctrl = resolve_mt4_control()
    return {"report_kind": "cas_forex_mt4_heartbeat", "mailbox_dir": ctrl.mailbox_dir, **read_ea_heartbeat(ctrl.mailbox_dir)}
