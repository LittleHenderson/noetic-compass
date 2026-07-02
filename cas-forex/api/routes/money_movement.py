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

from ..live_money_cache import invalidate_live_money_gate_caches
from ..route_cache import cache_first_payload
from cas_forex import runtime_gates
from cas_forex.money_movement import MovementEngine
from cas_forex.payout_recovery import (
    CLAIM_BOUNDARY as PAYOUT_RECOVERY_CLAIM_BOUNDARY,
    DEFAULT_ATTEMPT_PATH,
    DEFAULT_AUDIT_PATH as DEFAULT_PAYOUT_RECOVERY_AUDIT_PATH,
    PayoutAttemptStore,
    PayoutRecoveryError,
)
from cas_forex.time_utils import utc_now
from cas_forex.verified_profit_sweep import (
    DEFAULT_SWEEP_AUDIT_PATH,
    DEFAULT_SWEEP_POLICY_PATH,
    ProfitSweepAuditLog,
    ProfitSweepPolicyStore,
    ProfitSweepSettings,
    build_sweep_preview,
    request_verified_profit_sweep,
)

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


class VerifiedSweepPolicyUpdate(BaseModel):
    sweep_pct: Optional[float] = Field(default=None, ge=0, le=100)
    tax_reserve_pct: Optional[float] = Field(default=None, ge=0, le=100)
    min_sweep_usd: Optional[float] = Field(default=None, ge=0)
    destination_id: Optional[str] = Field(default=None)
    allow_principal_sweep: Optional[bool] = Field(default=None)


class VerifiedSweepLedgerRequest(BaseModel):
    account_ledger: dict[str, Any]
    settings: Optional[VerifiedSweepPolicyUpdate] = None
    destination_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class PayoutAttemptResolveRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1)
    owner_status: str = Field(..., description="SETTLED, FAILED, or BLOCKED after owner/provider review.")
    provider_reference: Optional[str] = None
    notes: Optional[str] = None


def _engine() -> MovementEngine:
    return MovementEngine.from_config()


def _policy_store() -> ProfitSweepPolicyStore:
    return ProfitSweepPolicyStore(DEFAULT_SWEEP_POLICY_PATH)


def _audit_log() -> ProfitSweepAuditLog:
    return ProfitSweepAuditLog(DEFAULT_SWEEP_AUDIT_PATH)


def _attempt_store() -> PayoutAttemptStore:
    return PayoutAttemptStore(DEFAULT_ATTEMPT_PATH, DEFAULT_PAYOUT_RECOVERY_AUDIT_PATH)


def _live_recovery_report() -> dict[str, Any]:
    from cas_forex.live_recovery import build_live_recovery_report

    return build_live_recovery_report()


def _settings_with_overrides(body: Optional[VerifiedSweepPolicyUpdate]) -> ProfitSweepSettings:
    settings = _policy_store().load()
    if body is None:
        return settings
    changes = {}
    for key in body.model_fields_set:
        value = getattr(body, key)
        if value is not None or key == "destination_id":
            changes[key] = value
    if not changes:
        return settings
    return ProfitSweepSettings(**{**settings.__dict__, **changes}).normalized()


def _verified_profit_sweep_policy_payload() -> dict[str, Any]:
    settings = _policy_store().load()
    return {
        "report_kind": "cas_forex_verified_profit_sweep_policy",
        "settings": settings.__dict__,
        "latest_audit": _audit_log().latest(),
        "note": "Sweep applies only to live broker-confirmed net winnings, after tax reserve.",
    }


def _verified_profit_sweep_policy_warming() -> dict[str, Any]:
    settings = _policy_store().load()
    return {
        "report_kind": "cas_forex_verified_profit_sweep_policy",
        "settings": settings.__dict__,
        "latest_audit": None,
        "note": "Verified-profit sweep policy cache is warming; no money movement is authorized.",
    }


def _verified_profit_sweep_state_payload() -> dict[str, Any]:
    from api.data import verified_profit_account_ledger

    preview = build_sweep_preview(verified_profit_account_ledger(), _policy_store().load())
    return preview.to_dict()


def _verified_profit_sweep_state_warming() -> dict[str, Any]:
    preview = build_sweep_preview(
        {
            "mode": "PAPER",
            "live_money_authorized": False,
            "cashflow_events": [],
            "deals": [],
            "summary": {},
        },
        _policy_store().load(),
    ).to_dict()
    preview.update(
        {
            "status": "WARMING",
            "reason": "Verified-profit sweep evidence is warming; no live winnings are sweepable.",
        }
    )
    return preview


def _payout_recovery_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_payout_recovery",
        "generated_at": utc_now().isoformat(),
        "status": "WARMING",
        "attempt_count": 0,
        "pending_count": 0,
        "has_pending_recovery": False,
        "latest_attempt": None,
        "pending_attempts": [],
        "claim_boundary": PAYOUT_RECOVERY_CLAIM_BOUNDARY,
        "next_action": "Payout recovery cache is warming; do not retry a sweep until refreshed.",
    }


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


@router.get("/verified-profit-sweep/policy")
async def get_verified_profit_sweep_policy() -> dict[str, Any]:
    """Owner sweep settings plus the latest audit row.

    These settings only define how verified net winnings would be split; they do
    not move money by themselves.
    """
    return cache_first_payload(
        "verified_profit_sweep_policy",
        builder=_verified_profit_sweep_policy_payload,
        fallback=_verified_profit_sweep_policy_warming,
        ttl_seconds=10.0,
    )


@router.post("/verified-profit-sweep/policy")
async def post_verified_profit_sweep_policy(body: VerifiedSweepPolicyUpdate) -> dict[str, Any]:
    changes = {}
    for key in body.model_fields_set:
        value = getattr(body, key)
        if value is not None or key == "destination_id":
            changes[key] = value
    try:
        settings = _policy_store().update(**changes) if changes else _policy_store().load()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    invalidate_live_money_gate_caches()
    audit = _audit_log().append("SWEEP_POLICY_UPDATE", {"settings": settings.__dict__})
    return {
        "report_kind": "cas_forex_verified_profit_sweep_policy",
        "settings": settings.__dict__,
        "audit": audit,
    }


@router.get("/verified-profit-sweep/state")
async def get_verified_profit_sweep_state() -> dict[str, Any]:
    """Preview sweep state from the current account ledger.

    Today the current ledger is paper/demo, so this honestly reports zero
    sweepable real winnings until a live broker-confirmed ledger exists.
    """
    return cache_first_payload(
        "verified_profit_sweep_state",
        builder=_verified_profit_sweep_state_payload,
        fallback=_verified_profit_sweep_state_warming,
        ttl_seconds=10.0,
    )


@router.get("/verified-profit-sweep/payout-recovery")
async def get_verified_profit_sweep_payout_recovery() -> dict[str, Any]:
    """Return idempotent payout-attempt recovery state."""
    return cache_first_payload(
        "verified_profit_sweep_payout_recovery",
        builder=lambda: _attempt_store().build_status(),
        fallback=_payout_recovery_warming,
        ttl_seconds=10.0,
    )


@router.post("/verified-profit-sweep/payout-recovery/resolve")
async def post_verified_profit_sweep_payout_recovery_resolve(
    body: PayoutAttemptResolveRequest,
) -> dict[str, Any]:
    """Owner-resolve a pending payout attempt after checking provider/bank evidence."""
    try:
        attempt = _attempt_store().resolve(
            body.idempotency_key,
            owner_status=body.owner_status,
            provider_reference=body.provider_reference or "",
            notes=body.notes or "",
        )
    except PayoutRecoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    invalidate_live_money_gate_caches()
    return {
        "report_kind": "cas_forex_payout_recovery_resolution",
        "attempt": attempt,
        "status": attempt.get("status"),
    }


@router.post("/verified-profit-sweep/preview")
async def post_verified_profit_sweep_preview(body: VerifiedSweepLedgerRequest) -> dict[str, Any]:
    """Preview sweepable verified net winnings from a supplied account ledger."""
    try:
        settings = _settings_with_overrides(body.settings)
        preview = build_sweep_preview(body.account_ledger, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return preview.to_dict()


@router.post("/verified-profit-sweep/request")
async def post_verified_profit_sweep_request(
    body: VerifiedSweepLedgerRequest,
    confirm: bool = Query(default=False),
) -> dict[str, Any]:
    """Request payout of the verified sweep amount.

    Requires ``?confirm=true`` before a payout is attempted. The payout engine
    then re-checks payout_automation and provider gates before touching any
    payment provider.
    """
    try:
        settings = _settings_with_overrides(body.settings)
        return request_verified_profit_sweep(
            body.account_ledger,
            settings,
            confirm=confirm,
            destination_id=body.destination_id,
            audit=_audit_log(),
            attempt_store=_attempt_store(),
            idempotency_key=body.idempotency_key,
            live_recovery_report=_live_recovery_report(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/verified-profit-sweep/request-current")
async def post_verified_profit_sweep_request_current(
    body: Optional[VerifiedSweepPolicyUpdate] = None,
    confirm: bool = Query(default=False),
) -> dict[str, Any]:
    """Request payout of the verified sweep amount from the current ledger.

    This is the dashboard-safe companion to ``/request``: the server chooses the
    same current ledger used by ``/state``, then the sweep layer still requires
    ``confirm=true`` and the movement engine still enforces payout gates before
    any provider can be touched.
    """
    from api.data import verified_profit_account_ledger

    try:
        settings = _settings_with_overrides(body)
        return request_verified_profit_sweep(
            verified_profit_account_ledger(),
            settings,
            confirm=confirm,
            audit=_audit_log(),
            attempt_store=_attempt_store(),
            live_recovery_report=_live_recovery_report(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
