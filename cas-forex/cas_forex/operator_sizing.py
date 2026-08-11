"""Broker-aware lot choices for autonomous Operator decisions.

The route builder supplies trade geometry and a tiny seed volume. This module
turns current broker contract, account, margin, portfolio, and stop-risk truth
into a small set of exact executable lot choices. The Operator chooses one
choice; it never invents a free-form volume. The final execution guard repeats
all money and portfolio checks immediately before a broker call.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from cas_forex.instruments import canonical_or_normalized_symbol
from cas_forex.pre_trade_money import build_pre_trade_money_estimate
from cas_forex.time_utils import utc_now


REPORT_KIND = "cas_forex_operator_sizing_plan"
PLAN_VERSION = "operator_sizing.v2"
SIZE_LEVELS: tuple[tuple[str, float], ...] = (
    ("PROBE", 0.25),
    ("STANDARD", 0.50),
    ("PRESS_EDGE", 0.75),
    ("MAX_WITHIN_ENVELOPE", 1.00),
)

CLAIM_BOUNDARY = (
    "The sizing planner computes exact broker-grid choices inside current risk, "
    "margin, position-count, and exposure caps. It does not select a choice, "
    "place an order, change owner limits, use a profit-target deficit as sizing "
    "authority, or replace the final action-time execution guard."
)


def build_operator_sizing_plan(
    *,
    symbol: str,
    direction: Any,
    entry_price: Any,
    stop_loss: Any,
    take_profit: Any,
    seed_lots: Any,
    bridge: Any,
    config: Any = None,
    proposed_intent: Mapping[str, Any] | None = None,
    account_snapshot: Mapping[str, Any] | None = None,
    purpose: str = "ENTRY",
    parent_position: Mapping[str, Any] | None = None,
    compound_slot_allowance: int = 0,
) -> dict[str, Any]:
    """Return exact lot choices derived from current broker/account evidence."""

    from cas_forex.execution_guard import caps_from_config

    seed = _positive(seed_lots) or 0.01
    proposed = dict(proposed_intent or {})
    proposed.update(
        {
            "symbol": str(symbol),
            "direction": _direction(direction),
            "lots": seed,
            "entry_price": _finite(entry_price),
            "stop_loss": _finite(stop_loss),
            "take_profit": _finite(take_profit),
            "sizing_purpose": str(purpose or "ENTRY").upper(),
        }
    )
    estimate = build_pre_trade_money_estimate(
        symbol=str(symbol),
        direction=direction,
        lots=seed,
        price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        proposed_intent=proposed,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )
    constraints = _mapping(estimate.get("broker_contract_constraints"))
    minimum = _positive(constraints.get("min_lot")) or _config_positive(
        config, "broker_min_lot", 0.01
    )
    step = _positive(constraints.get("lot_step")) or minimum
    broker_max = _positive(constraints.get("max_lot"))

    try:
        caps = caps_from_config(config)
    except Exception:
        caps = None
    cap_snapshot = {
        "max_risk_per_trade_pct": _finite(getattr(caps, "max_risk_per_trade_pct", None)),
        "max_total_exposure_lots": _finite(getattr(caps, "max_total_exposure_lots", None)),
        "max_margin_utilization_pct": _finite(
            getattr(caps, "max_margin_utilization_pct", None)
        ),
        "max_positions_per_symbol": _integer(
            getattr(caps, "max_positions_per_symbol", None)
        ),
        "max_open_position_count": _integer(
            getattr(caps, "max_open_position_count", None)
        ),
    }
    positions = _open_positions(bridge)
    portfolio = _portfolio_metrics(positions, symbol=str(symbol))
    account = _account_metrics(bridge, account_snapshot, estimate)
    purpose_value = str(purpose or "ENTRY").upper()
    try:
        reserved_compound_slots = max(0, int(compound_slot_allowance or 0))
    except (TypeError, ValueError):
        reserved_compound_slots = 0
    if purpose_value != "SCALE_IN":
        reserved_compound_slots = 0

    blockers: list[str] = []
    max_sources: list[tuple[str, float]] = []
    if broker_max is not None:
        max_sources.append(("broker_max_lot", broker_max))

    max_open = cap_snapshot["max_open_position_count"]
    if max_open is not None and portfolio["open_position_count"] >= max_open:
        blockers.append(
            f"open-position cap is already full ({portfolio['open_position_count']} / {max_open})"
        )
    max_symbol = cap_snapshot["max_positions_per_symbol"]
    effective_symbol_cap = (
        int(max_symbol) + reserved_compound_slots
        if max_symbol is not None
        else None
    )
    cap_snapshot["compound_slot_allowance"] = reserved_compound_slots
    cap_snapshot["effective_max_positions_per_symbol"] = effective_symbol_cap
    if (
        effective_symbol_cap is not None
        and portfolio["symbol_position_count"] >= effective_symbol_cap
    ):
        suffix = (
            f" plus {reserved_compound_slots} dedicated compound slot"
            f"{'s' if reserved_compound_slots != 1 else ''}"
            if reserved_compound_slots
            else ""
        )
        blockers.append(
            f"per-symbol position cap is already full "
            f"({portfolio['symbol_position_count']} / {effective_symbol_cap}; "
            f"base cap {max_symbol}{suffix})"
        )

    total_cap = _positive(cap_snapshot["max_total_exposure_lots"])
    if total_cap is not None:
        remaining = max(0.0, total_cap - portfolio["total_exposure_lots"])
        max_sources.append(("remaining_total_exposure_lots", remaining))

    seed_risk_pct = _positive(estimate.get("risk_at_stop_pct_equity"))
    risk_cap = _finite(cap_snapshot["max_risk_per_trade_pct"])
    if risk_cap is not None:
        if risk_cap <= 0:
            max_sources.append(("max_risk_per_trade_pct", 0.0))
        elif seed_risk_pct is not None:
            max_sources.append(("max_risk_per_trade_pct", seed * risk_cap / seed_risk_pct))

    seed_margin = _positive(estimate.get("estimated_margin_required_usd"))
    if seed_margin is not None:
        margin_per_lot = seed_margin / seed
        free_margin = _finite(account.get("free_margin_usd"))
        if free_margin is not None:
            max_sources.append(("free_margin", max(0.0, free_margin) / margin_per_lot))
        margin_cap_pct = _finite(cap_snapshot["max_margin_utilization_pct"])
        equity = _positive(account.get("equity_usd"))
        margin_used = _finite(account.get("margin_used_usd"))
        if margin_cap_pct is not None and equity is not None and margin_used is not None:
            margin_room = max(0.0, equity * margin_cap_pct / 100.0 - margin_used)
            max_sources.append(("max_margin_utilization_pct", margin_room / margin_per_lot))

    parent = dict(parent_position or {})
    if purpose_value == "SCALE_IN":
        parent_lots = _positive(parent.get("lot_size") or parent.get("volume") or parent.get("lots"))
        parent_multiple = _config_positive(config, "ai_scale_in_max_parent_multiple", 1.0)
        if parent_lots is not None:
            max_sources.append(("parent_position_multiple", parent_lots * parent_multiple))

    evidence_complete = seed_risk_pct is not None and bool(constraints)
    if not max_sources:
        max_sources.append(("seed_only_evidence_fallback", seed))
    elif not evidence_complete:
        # Unknown stop economics must never be converted into permission to size up.
        max_sources.append(("partial_evidence_seed_ceiling", seed))

    raw_max = min(value for _, value in max_sources)
    maximum = _quantize_down(raw_max, minimum=minimum, step=step)
    if maximum + 1e-12 < minimum:
        blockers.append(
            f"no compliant lot exists on the broker grid inside the current envelope; "
            f"maximum is {maximum:.8f}, minimum is {minimum:.8f}"
        )

    options = [] if blockers else _build_options(
        maximum=maximum,
        minimum=minimum,
        step=step,
        seed=seed,
        estimate=estimate,
    )
    if not options and not blockers:
        blockers.append("sizing evidence produced no positive broker-grid option")

    payload: dict[str, Any] = {
        "report_kind": REPORT_KIND,
        "plan_version": PLAN_VERSION,
        "generated_at": utc_now().isoformat(),
        "status": "OPTIONS_READY" if options else "NO_COMPLIANT_SIZE",
        "purpose": purpose_value,
        "symbol": str(symbol),
        "direction": _direction(direction),
        "entry_price": _finite(entry_price),
        "stop_loss": _finite(stop_loss),
        "take_profit": _finite(take_profit),
        "seed_lots": seed,
        "broker_min_lot": minimum,
        "broker_max_lot": broker_max,
        "broker_lot_step": step,
        "max_executable_lots": maximum,
        "max_lot_sources": [
            {"source": source, "max_lots": round(value, 8)}
            for source, value in max_sources
        ],
        "limiting_source": min(max_sources, key=lambda item: item[1])[0],
        "cap_snapshot": cap_snapshot,
        "compound_slot_allowance": reserved_compound_slots,
        "effective_max_positions_per_symbol": effective_symbol_cap,
        "portfolio_snapshot": portfolio,
        "account_snapshot": account,
        "seed_money_estimate": _compact_estimate(estimate),
        "options": options,
        "blockers": blockers,
        "daily_profit_target_used_for_sizing": False,
        "target_deficit_may_increase_size": False,
        "operator_must_select_exact_sizing_ref": bool(options),
        "final_execution_guard_authoritative": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["plan_hash"] = _hash_payload(
        {
            "plan_version": PLAN_VERSION,
            "purpose": payload["purpose"],
            "symbol": payload["symbol"],
            "direction": payload["direction"],
            "entry_price": payload["entry_price"],
            "stop_loss": payload["stop_loss"],
            "take_profit": payload["take_profit"],
            "cap_snapshot": cap_snapshot,
            "portfolio_snapshot": portfolio,
            "account_snapshot": account,
            "options": options,
        }
    )
    return payload


def option_for_ref(plan: Mapping[str, Any], sizing_ref: Any) -> dict[str, Any] | None:
    wanted = str(sizing_ref or "").strip()
    for row in plan.get("options") or []:
        if isinstance(row, Mapping) and str(row.get("sizing_ref") or "") == wanted:
            return dict(row)
    return None


def _build_options(
    *,
    maximum: float,
    minimum: float,
    step: float,
    seed: float,
    estimate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[tuple[str, float]] = [("BROKER_MINIMUM", minimum)]
    candidates.extend((label, maximum * fraction) for label, fraction in SIZE_LEVELS)
    seen: set[float] = set()
    rows: list[dict[str, Any]] = []
    for label, raw in candidates:
        lots = _quantize_down(raw, minimum=minimum, step=step)
        if lots <= 0 or lots > maximum + 1e-9:
            continue
        key = round(lots, 8)
        if key in seen:
            continue
        seen.add(key)
        ratio = lots / seed if seed > 0 else 0.0
        option = {
            "label": label,
            "lots": lots,
            "risk_at_stop_usd": _scaled(estimate.get("risk_at_stop_usd"), ratio, 2),
            "risk_at_stop_pct_equity": _scaled(
                estimate.get("risk_at_stop_pct_equity"), ratio, 4
            ),
            "reward_at_take_profit_usd": _scaled(
                estimate.get("reward_at_take_profit_usd"), ratio, 2
            ),
            "reward_risk_ratio": _finite(estimate.get("reward_risk_ratio")),
            "estimated_margin_required_usd": _scaled(
                estimate.get("estimated_margin_required_usd"), ratio, 2
            ),
            "spread_cost_estimate_usd": _scaled(
                estimate.get("spread_cost_estimate_usd"), ratio, 2
            ),
        }
        option["sizing_ref"] = (
            "size-"
            + _hash_payload(
                {
                    "label": label,
                    "lots": lots,
                    "risk": option["risk_at_stop_usd"],
                    "margin": option["estimated_margin_required_usd"],
                }
            )[:18]
        )
        rows.append(option)
    return sorted(rows, key=lambda row: float(row["lots"]))


def _compact_estimate(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "selected_broker_symbol",
        "entry_price",
        "stop_distance_units",
        "risk_at_stop_usd",
        "risk_at_stop_pct_equity",
        "reward_at_take_profit_usd",
        "reward_risk_ratio",
        "estimated_margin_required_usd",
        "estimated_free_margin_after_usd",
        "estimated_margin_utilization_after_pct",
        "account_equity_usd",
        "account_margin_used_usd",
        "account_free_margin_usd",
        "unit_value_source",
        "broker_contract_source",
    )
    return {key: value.get(key) for key in keys}


def _open_positions(bridge: Any) -> list[dict[str, Any]]:
    for name in ("get_open_positions_all", "get_open_positions"):
        getter = getattr(bridge, name, None)
        if not callable(getter):
            continue
        try:
            rows = list(getter() or [])
        except Exception:
            continue
        return [_mapping(row) for row in rows]
    return []


def _portfolio_metrics(rows: Sequence[Mapping[str, Any]], *, symbol: str) -> dict[str, Any]:
    target = _symbol_key(symbol)
    total_lots = 0.0
    symbol_lots = 0.0
    symbol_count = 0
    for row in rows:
        lots = _positive(row.get("volume") or row.get("lots") or row.get("lot_size")) or 0.0
        total_lots += lots
        if _symbol_key(row.get("symbol")) == target:
            symbol_lots += lots
            symbol_count += 1
    return {
        "open_position_count": len(rows),
        "symbol_position_count": symbol_count,
        "total_exposure_lots": round(total_lots, 8),
        "symbol_exposure_lots": round(symbol_lots, 8),
    }


def _account_metrics(
    bridge: Any,
    supplied: Mapping[str, Any] | None,
    estimate: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(supplied or {})
    getter = getattr(bridge, "get_account_info", None)
    if callable(getter):
        try:
            current = getter() or {}
            if isinstance(current, Mapping):
                raw = {**raw, **dict(current)}
        except Exception:
            pass
    return {
        "balance_usd": _first_finite(
            raw, "balance", "balance_usd", fallback=estimate.get("account_balance_usd")
        ),
        "equity_usd": _first_finite(
            raw, "equity", "equity_usd", fallback=estimate.get("account_equity_usd")
        ),
        "margin_used_usd": _first_finite(
            raw,
            "margin",
            "margin_used",
            "margin_used_usd",
            fallback=estimate.get("account_margin_used_usd"),
        ),
        "free_margin_usd": _first_finite(
            raw,
            "margin_free",
            "free_margin",
            "free_margin_usd",
            fallback=estimate.get("account_free_margin_usd"),
        ),
        "leverage": _first_finite(
            raw, "leverage", "account_leverage", fallback=estimate.get("account_leverage")
        ),
    }


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    return {
        key: getattr(value, key)
        for key in (
            "symbol",
            "volume",
            "lots",
            "lot_size",
            "side",
            "direction",
            "profit",
            "comment",
            "ticket",
        )
        if hasattr(value, key)
    }


def _quantize_down(raw: Any, *, minimum: float, step: float) -> float:
    value = max(0.0, _finite(raw) or 0.0)
    if value + 1e-12 < minimum:
        return 0.0
    units = math.floor(max(0.0, value - minimum + 1e-12) / step)
    return round(minimum + units * step, 8)


def _scaled(value: Any, ratio: float, digits: int) -> float | None:
    number = _finite(value)
    return None if number is None else round(number * ratio, digits)


def _direction(value: Any) -> str:
    raw = getattr(value, "value", value)
    text = str(raw or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text


def _symbol_key(value: Any) -> str:
    return canonical_or_normalized_symbol(value)


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _positive(value: Any) -> float | None:
    parsed = _finite(value)
    return parsed if parsed is not None and parsed > 0 else None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _config_positive(config: Any, key: str, default: float) -> float:
    return _positive(getattr(config, key, default)) or float(default)


def _first_finite(
    mapping: Mapping[str, Any],
    *keys: str,
    fallback: Any = None,
) -> float | None:
    for key in keys:
        value = _finite(mapping.get(key))
        if value is not None:
            return value
    return _finite(fallback)


def _hash_payload(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CLAIM_BOUNDARY",
    "PLAN_VERSION",
    "REPORT_KIND",
    "build_operator_sizing_plan",
    "option_for_ref",
]
