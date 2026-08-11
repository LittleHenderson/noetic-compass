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

import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..live_money_cache import invalidate_live_money_gate_caches
from ..route_cache import cache_first_payload
from cas_forex import runtime_gates
from cas_forex.account_ledger import money
from cas_forex.money_movement import MovementEngine
from cas_forex.money_movement_dispatch import dispatch_money_movement
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
MONEY_MOVEMENT_CONFIRM_PHRASE = "CONFIRM MONEY MOVEMENT"
AUTONOMOUS_SWEEP_ARM_PHRASE = "ARM AUTONOMOUS PROFIT SWEEP"


def _confirmation_matches(confirm_phrase: str) -> bool:
    return (confirm_phrase or "").strip() == MONEY_MOVEMENT_CONFIRM_PHRASE


def _confirm_required(
    capability: str,
    confirm: bool,
    confirm_phrase: str = "",
) -> Optional[dict[str, Any]]:
    """Second layer for real-money POSTs: when the capability is owner-authorized
    (so a real transfer WOULD execute), require an explicit confirmation phrase.

    Returns a CONFIRM_REQUIRED payload to short-circuit the route, or ``None`` to
    proceed. When the capability is NOT authorized this returns ``None`` so the
    engine still runs and reports BLOCKED + the missing requirements.
    """
    if not runtime_gates.is_authorized(capability):
        return None
    if confirm and _confirmation_matches(confirm_phrase):
        return None
    return {
        "status": "CONFIRM_REQUIRED",
        "capability": capability,
        "need_confirmation": MONEY_MOVEMENT_CONFIRM_PHRASE,
        "confirm_phrase": MONEY_MOVEMENT_CONFIRM_PHRASE,
        "detail": (
            f"{capability} is owner-authorized; this would move real money. "
            f'Re-POST with ?confirm=true and confirm_phrase="{MONEY_MOVEMENT_CONFIRM_PHRASE}" to execute.'
        ),
    }


class DepositRequest(BaseModel):
    amount_usd: float = Field(..., gt=0, description="Amount to deposit, USD.")
    source_id: Optional[str] = Field(default=None, description="Funding source id.")
    idempotency_key: Optional[str] = Field(default=None)


class WithdrawRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)
    destination_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class PayoutRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)
    destination_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class ReinvestSplitRequest(BaseModel):
    realized_profit_usd: float = Field(..., gt=0)
    reinvest_pct: float = Field(..., ge=0, le=100)
    savings_pct: float = Field(..., ge=0, le=100)
    tax_reserve_pct: float = Field(..., ge=0, le=100)
    destination_id: Optional[str] = Field(default=None)
    idempotency_key: Optional[str] = Field(default=None)


class VerifiedSweepPolicyUpdate(BaseModel):
    sweep_pct: Optional[float] = Field(default=None, ge=0, le=100)
    tax_reserve_pct: Optional[float] = Field(default=None, ge=0, le=100)
    min_sweep_usd: Optional[float] = Field(default=None, ge=0)
    destination_id: Optional[str] = Field(default=None)
    allow_principal_sweep: Optional[bool] = Field(default=None)
    autonomous_enabled: Optional[bool] = Field(default=None)
    max_daily_sweep_usd: Optional[float] = Field(default=None, ge=0)


class VerifiedSweepLedgerRequest(BaseModel):
    account_ledger: dict[str, Any]
    settings: Optional[VerifiedSweepPolicyUpdate] = None
    destination_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class PayoutAttemptResolveRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1)
    owner_status: str = Field(
        ...,
        description=(
            "FAILED or BLOCKED after owner/provider review. SETTLED can only be "
            "recorded from complete provider reconciliation evidence."
        ),
    )
    provider_reference: Optional[str] = None
    notes: Optional[str] = None


def _engine() -> MovementEngine:
    return MovementEngine.from_config()


def _manual_movement_dispatch(
    *,
    kind: str,
    amount_usd: float,
    source_id: str | None = None,
    destination_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    engine = _engine()
    provider_is_real = bool(getattr(engine.provider, "is_real", False))
    if provider_is_real and not str(idempotency_key or "").strip():
        return {
            "kind": kind,
            "status": "IDEMPOTENCY_KEY_REQUIRED",
            "requested_amount_usd": amount_usd,
            "authorized": False,
            "reason": (
                "A caller-supplied idempotency_key is required for every real-provider "
                "movement so an HTTP retry cannot create a second transfer."
            ),
            "provider_touched": False,
            "provider_receipt": None,
            "ledger_event": None,
            "ledger_entry": None,
            "event_hash": None,
            "before_after_balance_snapshot": None,
            "idempotency_key": None,
        }
    key = str(idempotency_key or f"manual-api-{uuid.uuid4().hex}")
    dispatch = dispatch_money_movement(
        kind=kind,
        amount_usd=amount_usd,
        idempotency_key=key,
        source_id=source_id,
        destination_id=destination_id,
        purpose=f"manual_api_{kind}",
        authority_mode="MANUAL",
        require_real_provider=provider_is_real,
        engine=engine,
        attempt_store=_attempt_store(),
    )
    movement = dispatch.get("movement")
    if isinstance(movement, dict):
        payload = dict(movement)
    else:
        authority = next(
            (
                item.get("evidence") or {}
                for item in (dispatch.get("anomaly_checks") or {}).get("checks") or []
                if item.get("check_id") == "authority_gate"
            ),
            {},
        )
        payload = {
            "kind": kind,
            "status": dispatch.get("status"),
            "requested_amount_usd": amount_usd,
            "capability": authority.get("capability"),
            "authorized": bool(authority.get("authorized", False)),
            "reason": dispatch.get("detail"),
            "missing_requirements": list(authority.get("missing_requirements") or []),
            "is_real_money": False,
            "provider_touched": False,
            "provider_receipt": None,
            "ledger_event": None,
            "ledger_entry": None,
            "event_hash": None,
            "before_after_balance_snapshot": None,
        }
    payload["idempotency_key"] = key
    payload["money_movement_dispatch"] = dispatch
    payload["movement_attempt"] = dispatch.get("movement_attempt")
    return payload


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

    settings = _policy_store().load()
    preview = _build_current_sweep_preview(verified_profit_account_ledger(), settings)
    return preview.to_dict()


def _build_current_sweep_preview(
    account_ledger: dict[str, Any],
    settings: ProfitSweepSettings,
) -> Any:
    already_swept = _attempt_store().settled_total_usd(
        purpose="verified_profit_sweep",
        policy_id=settings.policy_id,
    )
    return build_sweep_preview(
        account_ledger,
        settings,
        already_swept_usd=already_swept,
    )


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
    report = runtime_gates.build_runtime_gates_report()
    decisions = {
        cap: runtime_gates.evaluate_capability(cap).to_dict() for cap in _MONEY_CAPABILITIES
    }
    provider_runtime = dict(report.payment_provider_runtime or {})
    runtime_ready = bool(provider_runtime.get("real_money_provider_ready", False))
    from cas_forex.broker_funding_conformance import latest_broker_funding_conformance

    return {
        "report_kind": "cas_forex_money_movement_gates",
        "gates": decisions,
        "payment_provider_runtime": provider_runtime,
        "real_money_provider_ready": runtime_ready,
        "runtime_scaffolded": not runtime_ready,
        "sandbox_conformance": latest_broker_funding_conformance(),
        "detail": (
            str(provider_runtime.get("detail") or "")
            if provider_runtime
            else "Money-movement runtime is unreadable; keep payout/deposit surfaces fail-closed."
        ),
        "all_authorized": all(d["authorized"] for d in decisions.values()),
    }


@router.post("/deposit")
async def post_deposit(
    body: DepositRequest,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Deposit funds (gated by auto_deposit). BLOCKED + missing requirements
    when not owner-authorized; when authorized, requires typed confirmation to
    actually move money. No real money moves without both the gate and confirm."""
    pending = _confirm_required("auto_deposit", confirm, confirm_phrase)
    if pending is not None:
        return pending
    return _manual_movement_dispatch(
        kind="deposit",
        amount_usd=body.amount_usd,
        source_id=body.source_id,
        idempotency_key=body.idempotency_key,
    )


@router.post("/withdraw")
async def post_withdraw(
    body: WithdrawRequest,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Withdraw funds to the owner-allowlisted destination (gated by
    bank_card_movement; requires typed confirmation when authorized). A
    destination that does not match the allowlisted one is rejected."""
    pending = _confirm_required("bank_card_movement", confirm, confirm_phrase)
    if pending is not None:
        return pending
    return _manual_movement_dispatch(
        kind="withdrawal",
        amount_usd=body.amount_usd,
        destination_id=body.destination_id,
        idempotency_key=body.idempotency_key,
    )


@router.post("/payout")
async def post_payout(
    body: PayoutRequest,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Pay realized profit to the owner's allowlisted destination (gated by
    payout_automation; requires typed confirmation when authorized). A
    destination that is not the allowlisted one is rejected even when authorized."""
    pending = _confirm_required("payout_automation", confirm, confirm_phrase)
    if pending is not None:
        return pending
    return _manual_movement_dispatch(
        kind="payout",
        amount_usd=body.amount_usd,
        destination_id=body.destination_id,
        idempotency_key=body.idempotency_key,
    )


@router.post("/reinvest-split")
async def post_reinvest_split(
    body: ReinvestSplitRequest,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Split realized profit into a retained reinvest leg + gated payout legs
    (requires typed confirmation when payout is authorized)."""
    pending = _confirm_required("payout_automation", confirm, confirm_phrase)
    if pending is not None:
        return pending
    total_pct = body.reinvest_pct + body.savings_pct + body.tax_reserve_pct
    if abs(total_pct - 100.0) > 1e-6:
        raise HTTPException(
            status_code=422,
            detail="reinvest_pct + savings_pct + tax_reserve_pct must equal 100",
        )
    base_key = str(body.idempotency_key or f"manual-api-split-{uuid.uuid4().hex}")
    reinvest_usd = money(body.realized_profit_usd * body.reinvest_pct / 100.0)
    savings_usd = money(body.realized_profit_usd * body.savings_pct / 100.0)
    tax_reserve_usd = money(body.realized_profit_usd * body.tax_reserve_pct / 100.0)
    reinvest_leg = {
        "kind": "reinvest",
        "status": "RETAINED",
        "requested_amount_usd": reinvest_usd,
        "capability": "none",
        "authorized": True,
        "reason": "Reinvest portion retained in the trading account; no transfer.",
        "provider_touched": False,
    }
    savings_leg = (
        _manual_movement_dispatch(
            kind="payout",
            amount_usd=savings_usd,
            destination_id=body.destination_id,
            idempotency_key=f"{base_key}:savings",
        )
        if savings_usd > 0
        else {"kind": "payout", "status": "RETAINED", "requested_amount_usd": 0.0}
    )
    tax_leg = (
        _manual_movement_dispatch(
            kind="payout",
            amount_usd=tax_reserve_usd,
            destination_id=body.destination_id,
            idempotency_key=f"{base_key}:tax-reserve",
        )
        if tax_reserve_usd > 0
        else {"kind": "payout", "status": "RETAINED", "requested_amount_usd": 0.0}
    )
    return {
        "realized_profit_usd": money(body.realized_profit_usd),
        "reinvest_usd": reinvest_usd,
        "savings_usd": savings_usd,
        "tax_reserve_usd": tax_reserve_usd,
        "idempotency_key": base_key,
        "legs": [reinvest_leg, savings_leg, tax_leg],
        "external_movement_settled": all(
            leg.get("status") in {"SETTLED", "RETAINED"}
            for leg in (savings_leg, tax_leg)
        ),
        "claim_boundary": (
            "Each external reinvest-split leg uses the durable money-movement "
            "provider chokepoint with its own derived idempotency key."
        ),
    }


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
async def post_verified_profit_sweep_policy(
    body: VerifiedSweepPolicyUpdate,
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    current = _policy_store().load()
    if (
        body.autonomous_enabled is True
        and not current.autonomous_enabled
        and confirm_phrase.strip() != AUTONOMOUS_SWEEP_ARM_PHRASE
    ):
        return {
            "report_kind": "cas_forex_verified_profit_sweep_policy",
            "status": "CONFIRM_REQUIRED",
            "need_confirmation": AUTONOMOUS_SWEEP_ARM_PHRASE,
            "settings": current.__dict__,
            "detail": (
                "This grants standing AI authority for in-envelope verified-profit "
                "payouts. Confirm once to arm; individual sweeps will not ask again."
            ),
        }
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


@router.get("/verified-profit-sweep/autonomy")
async def get_verified_profit_sweep_autonomy() -> dict[str, Any]:
    from cas_forex.autonomous_money_movement import autonomous_money_movement_status

    return autonomous_money_movement_status(
        settings=_policy_store().load(),
        attempt_store=_attempt_store(),
    )


@router.post("/verified-profit-sweep/autonomy/run-once")
async def post_verified_profit_sweep_autonomy_run_once() -> dict[str, Any]:
    """Run one owner-armed autonomous sweep cycle without per-transfer approval."""

    from cas_forex.autonomous_money_movement import (
        run_autonomous_verified_profit_sweep_cycle,
    )

    return run_autonomous_verified_profit_sweep_cycle(
        trigger="OWNER_REQUESTED_AUTONOMOUS_RUN_ONCE",
        settings=_policy_store().load(),
        attempt_store=_attempt_store(),
        audit=_audit_log(),
    )


@router.post("/verified-profit-sweep/payout-recovery/resolve")
async def post_verified_profit_sweep_payout_recovery_resolve(
    body: PayoutAttemptResolveRequest,
) -> dict[str, Any]:
    """Close an attempt as FAILED/BLOCKED after review; never invent settlement."""
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
        preview = _build_current_sweep_preview(body.account_ledger, settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return preview.to_dict()


@router.post("/verified-profit-sweep/request")
async def post_verified_profit_sweep_request(
    body: VerifiedSweepLedgerRequest,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Request payout of the verified sweep amount.

    Requires typed confirmation before a payout is attempted. The payout engine
    then re-checks payout_automation and provider gates before touching any
    payment provider.
    """
    try:
        settings = _settings_with_overrides(body.settings)
        preview = _build_current_sweep_preview(body.account_ledger, settings)
        if confirm:
            pending = _confirm_required("payout_automation", confirm, confirm_phrase) if preview.status == "READY" else None
            if pending is not None:
                pending["preview"] = preview.to_dict()
                return pending
        return request_verified_profit_sweep(
            body.account_ledger,
            settings,
            confirm=confirm,
            destination_id=body.destination_id,
            audit=_audit_log(),
            attempt_store=_attempt_store(),
            idempotency_key=body.idempotency_key,
            live_recovery_report=_live_recovery_report(),
            preview=preview,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/verified-profit-sweep/request-current")
async def post_verified_profit_sweep_request_current(
    body: Optional[VerifiedSweepPolicyUpdate] = None,
    confirm: bool = Query(default=False),
    confirm_phrase: str = Query(default=""),
) -> dict[str, Any]:
    """Request payout of the verified sweep amount from the current ledger.

    This is the dashboard-safe companion to ``/request``: the server chooses the
    same current ledger used by ``/state``, then the sweep layer still requires
    typed confirmation and the movement engine still enforces payout gates
    before any provider can be touched.
    """
    from api.data import verified_profit_account_ledger

    try:
        settings = _settings_with_overrides(body)
        account_ledger = verified_profit_account_ledger()
        preview = _build_current_sweep_preview(account_ledger, settings)
        if confirm:
            pending = _confirm_required("payout_automation", confirm, confirm_phrase) if preview.status == "READY" else None
            if pending is not None:
                pending["preview"] = preview.to_dict()
                return pending
        return request_verified_profit_sweep(
            account_ledger,
            settings,
            confirm=confirm,
            audit=_audit_log(),
            attempt_store=_attempt_store(),
            live_recovery_report=_live_recovery_report(),
            preview=preview,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
