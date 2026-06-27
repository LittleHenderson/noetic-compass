"""HTTP routes for the gated money-movement engine.

Thin wrappers around ``cas_forex.money_movement.MovementEngine``. Each POST runs
the matching capability gate FIRST and only touches the configured payment
provider if it is owner-authorized. With default config every money gate is
NOT LICENSED, so each call returns a ``BLOCKED`` result listing the exact
missing requirements and no money moves. The engine uses the config-selected
provider (``MovementEngine.from_config``), so a real provider moves real money
only when both the gate authorizes it and the owner has configured that provider.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from cas_forex import runtime_gates
from cas_forex.money_movement import MovementEngine

router = APIRouter()

_MONEY_CAPABILITIES = ("auto_deposit", "bank_card_movement", "payout_automation")


def _confirm_required(capability: str, confirm: bool) -> Optional[dict[str, Any]]:
    """Second layer for real-money POSTs: when the capability is owner-authorized
    (so a real transfer WOULD execute), require an explicit ``?confirm=true``.

    Returns a CONFIRM_REQUIRED payload to short-circuit the route, or ``None`` to
    proceed. When the capability is NOT authorized this returns ``None`` so the
    engine still runs and reports BLOCKED + the missing requirements.
    """
    if confirm:
        return None
    if runtime_gates.is_authorized(capability):
        return {
            "status": "CONFIRM_REQUIRED",
            "capability": capability,
            "detail": (
                f"{capability} is owner-authorized; this would move real money. "
                "Re-POST with ?confirm=true to execute."
            ),
        }
    return None


class DepositRequest(BaseModel):
    amount_usd: float = Field(..., gt=0, description="Amount to deposit, USD.")
    source_id: Optional[str] = Field(default=None, description="Funding source id.")


class WithdrawRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)
    destination_id: Optional[str] = Field(default=None)


class PayoutRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)
    destination_id: Optional[str] = Field(default=None)


class ReinvestSplitRequest(BaseModel):
    realized_profit_usd: float = Field(..., gt=0)
    reinvest_pct: float = Field(..., ge=0, le=100)
    savings_pct: float = Field(..., ge=0, le=100)
    tax_reserve_pct: float = Field(..., ge=0, le=100)
    destination_id: Optional[str] = Field(default=None)


def _engine() -> MovementEngine:
    return MovementEngine.from_config()


@router.get("/gates")
async def get_money_movement_gates() -> dict[str, Any]:
    """Return the money-movement capability gates (deposit / bank-card / payout).

    Each gate reports authorized vs pending owner enable and exactly what is
    still required to authorize it.
    """
    decisions = {
        cap: runtime_gates.evaluate_capability(cap).to_dict() for cap in _MONEY_CAPABILITIES
    }
    return {
        "report_kind": "cas_forex_money_movement_gates",
        "gates": decisions,
        "all_authorized": all(d["authorized"] for d in decisions.values()),
    }


@router.post("/deposit")
async def post_deposit(body: DepositRequest, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Deposit funds (gated by auto_deposit). BLOCKED + missing requirements
    when not owner-authorized; when authorized, requires ``?confirm=true`` to
    actually move money. No real money moves without both the gate and confirm."""
    pending = _confirm_required("auto_deposit", confirm)
    if pending is not None:
        return pending
    return _engine().deposit(body.amount_usd, source_id=body.source_id).to_dict()


@router.post("/withdraw")
async def post_withdraw(body: WithdrawRequest, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Withdraw funds to the owner-allowlisted destination (gated by
    bank_card_movement; requires ``?confirm=true`` when authorized). A
    destination that does not match the allowlisted one is rejected."""
    pending = _confirm_required("bank_card_movement", confirm)
    if pending is not None:
        return pending
    return _engine().withdraw(body.amount_usd, destination_id=body.destination_id).to_dict()


@router.post("/payout")
async def post_payout(body: PayoutRequest, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Pay realized profit to the owner's allowlisted destination (gated by
    payout_automation; requires ``?confirm=true`` when authorized). A
    destination that is not the allowlisted one is rejected even when authorized."""
    pending = _confirm_required("payout_automation", confirm)
    if pending is not None:
        return pending
    return _engine().payout(body.amount_usd, destination_id=body.destination_id).to_dict()


@router.post("/reinvest-split")
async def post_reinvest_split(body: ReinvestSplitRequest, confirm: bool = Query(default=False)) -> dict[str, Any]:
    """Split realized profit into a retained reinvest leg + gated payout legs
    (requires ``?confirm=true`` when payout is authorized)."""
    pending = _confirm_required("payout_automation", confirm)
    if pending is not None:
        return pending
    try:
        split = _engine().reinvest_split(
            body.realized_profit_usd,
            reinvest_pct=body.reinvest_pct,
            savings_pct=body.savings_pct,
            tax_reserve_pct=body.tax_reserve_pct,
            destination_id=body.destination_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return split.to_dict()
