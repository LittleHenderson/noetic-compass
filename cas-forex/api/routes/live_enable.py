"""HTTP routes for owner live-enable control: turn the live-trading flags ON.

``GET /state`` reports the resolved flags + the live-trading gate readout (what
is still missing); ``POST /update`` flips one or more toggles; ``POST /reset``
reverts to config/env defaults. Only flags present in the request body change.

Every response re-evaluates ``runtime_gates`` so the UI always shows exactly
what is still required to actually go live.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..live_money_cache import invalidate_live_money_gate_caches
from ..route_cache import cache_first_payload
from cas_forex.live_enable_control import (
    LIVE_ENABLE_KEYS,
    build_authorization_report,
    build_live_enable_report,
    clear_live_enable_overrides,
    resolve_live_enable,
    set_live_enable_overrides,
)

router = APIRouter()
_LIVE_ENABLE_CACHE_TTL_SECONDS = 30.0


class LiveEnableUpdate(BaseModel):
    # Each flag: true/false to set; omit (or null) to leave unchanged.
    personal_account_ack: Optional[bool] = None
    no_pooled_capital_ack: Optional[bool] = None
    live_mode: Optional[bool] = None
    prefer_mt5: Optional[bool] = None
    owner_enable_live_trading: Optional[bool] = None
    live_trading_licensed: Optional[bool] = None


class AuthorizationUpdate(BaseModel):
    # Core live-owner flags also accepted here so Trade/Proof can offer one
    # owner switch surface instead of forcing the owner to hunt through Settings.
    personal_account_ack: Optional[bool] = None
    no_pooled_capital_ack: Optional[bool] = None
    live_mode: Optional[bool] = None
    prefer_mt5: Optional[bool] = None
    # Downstream capability owner-enable toggles (booleans).
    owner_enable_live_trading: Optional[bool] = None
    live_trading_licensed: Optional[bool] = None
    owner_enable_broker_accept: Optional[bool] = None
    owner_enable_auto_deposit: Optional[bool] = None
    owner_enable_bank_card_movement: Optional[bool] = None
    owner_enable_payout_automation: Optional[bool] = None
    payout_destination_allowlisted: Optional[bool] = None
    # Shared payment-provider config. payment_api_key is a secret the owner sets;
    # it is stored but never returned by any report.
    payment_provider: Optional[str] = None
    payment_api_key: Optional[str] = None
    payout_destination_id: Optional[str] = None


@router.get("/state")
async def get_live_enable() -> dict[str, Any]:
    """Resolved live-enable flags + the live-trading gate readout."""
    return cache_first_payload(
        "live_enable_state_report",
        builder=build_live_enable_report,
        fallback=_live_enable_warming,
        ttl_seconds=_LIVE_ENABLE_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.post("/update")
async def post_live_enable(body: LiveEnableUpdate) -> dict[str, Any]:
    """Flip toggles. Field present = set; omitted = unchanged. Returns the full
    report (incl. runtime_gates) so the UI shows what is still missing."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        set_live_enable_overrides(**provided)
        invalidate_live_money_gate_caches()
    return build_live_enable_report()


@router.get("/authorization")
async def get_authorization() -> dict[str, Any]:
    """Unified report for all 5 owner-controlled capabilities + provider config."""
    return cache_first_payload(
        "live_enable_authorization_report",
        builder=build_authorization_report,
        fallback=_authorization_warming,
        ttl_seconds=_LIVE_ENABLE_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.post("/authorization/update")
async def post_authorization(body: AuthorizationUpdate) -> dict[str, Any]:
    """Set any capability toggle / provider field. Returns the full authorization
    report (per-capability gate status + what is still missing)."""
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    if provided:
        set_live_enable_overrides(**provided)
        invalidate_live_money_gate_caches()
    return build_authorization_report()


@router.post("/reset")
async def post_reset_live_enable() -> dict[str, Any]:
    """Clear all owner authorization overrides (revert to config / env defaults)."""
    clear_live_enable_overrides()
    invalidate_live_money_gate_caches()
    return build_live_enable_report()


_FLAG_LABELS: dict[str, tuple[str, str]] = {
    "personal_account_ack": (
        "Personal-account acknowledgment",
        "Confirms this is the owner's own personal trading account.",
    ),
    "no_pooled_capital_ack": (
        "No-pooled-capital acknowledgment",
        "Confirms no pooled, client, or third-party capital is traded here.",
    ),
    "live_mode": ("Live mode", "Switches the broker layer from paper/demo to live mode."),
    "prefer_mt5": ("Prefer MT5", "Routes the live broker bridge through MT5 when configured."),
    "owner_enable_live_trading": (
        "Owner enable live trading",
        "Owner allows the live-trading capability gate to evaluate as enabled.",
    ),
    "live_trading_licensed": (
        "Owner ACCEPT live authority",
        "Owner authorizes live trading to proceed from this cockpit.",
    ),
}

_CAPABILITY_FALLBACKS: tuple[dict[str, Any], ...] = (
    {
        "capability": "live_trading",
        "title": "Live Trading",
        "toggles": ("owner_enable_live_trading", "live_trading_licensed"),
        "note": "Also requires owner account acknowledgments, broker credentials, owner ACCEPT reviews, edge authorization, and order-time risk checks.",
    },
    {
        "capability": "broker_accept",
        "title": "Broker ACCEPT",
        "toggles": ("owner_enable_broker_accept",),
        "note": "Also requires owner broker-reality review.",
    },
    {
        "capability": "auto_deposit",
        "title": "Auto-Deposit",
        "toggles": ("owner_enable_auto_deposit",),
        "note": "Also requires the payment provider.",
    },
    {
        "capability": "bank_card_movement",
        "title": "Bank / Card Movement",
        "toggles": ("owner_enable_bank_card_movement",),
        "note": "Also requires the payment provider.",
    },
    {
        "capability": "payout_automation",
        "title": "Payout Automation (Sweep Ledger)",
        "toggles": ("owner_enable_payout_automation",),
        "note": "Also requires the payment provider and allowlisted payout destination.",
    },
)


def _owner_authority_model_warming() -> dict[str, Any]:
    return {
        "authority": "OWNER",
        "authority_controls": ["owner switches", "Owner ACCEPT buttons"],
        "owner_controls_are_final_authority": True,
        "metrics_and_ai_are_advisory_only": True,
        "metrics_and_ai_can_veto_owner_authority": False,
        "technical_action_time_checks_still_required": True,
        "advisory_inputs": [
            "paper-proof day count",
            "12-month / multi-symbol evidence",
            "strategy win-rate / profit metrics",
            "AI confidence or agent recommendation",
            "daily/monthly profit pace",
        ],
        "action_time_requirements": [
            "owner switches / Owner ACCEPT are ON for the capability",
            "broker or payment-provider credentials are configured",
            "broker/feed/provider bridge is reachable for the requested action",
            "fresh edge authorization exists when the dispatch path requires it",
            "risk checks, emergency-stop checks, and explicit action confirmation pass",
        ],
        "statement": (
            "The owner is the live-trading authority. Metrics and AI are advisory; "
            "broker/provider/edge/risk checks still run at action time."
        ),
    }


def _gate_warming_decision(capability: str) -> dict[str, Any]:
    return {
        "capability": capability,
        "authorized": False,
        "status": "CURRENTLY NOT LICENSED",
        "missing_requirements": ["Detailed runtime gate audit is warming."],
        "satisfied_requirements": [],
        "advisory_requirements": [],
        "next_action": "Wait for the cached live-enable report to refresh.",
    }


def _live_enable_flags_warming() -> list[dict[str, Any]]:
    resolved = resolve_live_enable()
    flags = []
    for key in LIVE_ENABLE_KEYS:
        label, consequence = _FLAG_LABELS[key]
        flags.append(
            {
                "key": key,
                "label": label,
                "consequence": consequence,
                "enabled": bool(resolved.get(key, False)),
                "overridden": False,
            }
        )
    return flags


def _live_enable_warming() -> dict[str, Any]:
    resolved = resolve_live_enable()
    live = _gate_warming_decision("live_trading")
    return {
        "report_kind": "cas_forex_live_enable",
        "flags": _live_enable_flags_warming(),
        "resolved": {key: bool(resolved.get(key, False)) for key in LIVE_ENABLE_KEYS},
        "override_state_path": None,
        "override_count": 0,
        "persisted": True,
        "runtime_gates": {
            "report_kind": "cas_forex_runtime_gates",
            "decisions": {"live_trading": live},
            "all_real_money_authorized": False,
            "summary": "Live-enable gate audit is warming and remains fail-closed.",
            "owner_authority_boundary": _owner_authority_model_warming()["statement"],
            "advisory_only_inputs": _owner_authority_model_warming()["advisory_inputs"],
            "action_time_requirements": _owner_authority_model_warming()["action_time_requirements"],
            "owner_controls_are_final_authority": True,
            "metrics_and_ai_can_veto_owner_authority": False,
        },
        "owner_authority_model": _owner_authority_model_warming(),
        "live_trading": live,
        "live_authorized": False,
        "still_missing": list(live["missing_requirements"]),
        "caveats": [
            "This warming packet is fail-closed and does not place orders.",
            "The cached live-enable report will replace it when the runtime-gate audit finishes.",
        ],
    }


def _authorization_warming() -> dict[str, Any]:
    capabilities = []
    for capability in _CAPABILITY_FALLBACKS:
        decision = _gate_warming_decision(str(capability["capability"]))
        toggles = [
            {
                "key": key,
                "label": _FLAG_LABELS.get(key, (key, ""))[0],
                "consequence": _FLAG_LABELS.get(key, ("", "Owner-controlled capability toggle."))[1],
                "enabled": False,
                "overridden": False,
            }
            for key in capability["toggles"]
        ]
        capabilities.append({**capability, **decision, "toggles": toggles})
    return {
        "report_kind": "cas_forex_authorization",
        "capabilities": capabilities,
        "provider": {
            "payment_provider": "",
            "payment_api_key_set": False,
            "payout_destination_id": "",
            "payout_destination_allowlisted": False,
            "allowlist_label": "Payout destination allowlisted",
        },
        "all_real_money_authorized": False,
        "summary": "Owner-controlled capability audit is warming and remains fail-closed.",
        "owner_authority_model": _owner_authority_model_warming(),
        "override_state_path": None,
        "override_count": 0,
        "persisted": True,
        "caveats": [
            "This warming packet does not move money, place orders, or expose payment secrets.",
            "The cached authorization report will replace it when the runtime-gate audit finishes.",
        ],
    }
