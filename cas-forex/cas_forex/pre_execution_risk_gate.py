"""Pre-execution risk gate primitive.

This module evaluates a *proposed* RouteIntent against the current
portfolio risk snapshot (from `cas_forex.risk_monitoring`) and the
operator's configured risk caps. It returns a structured decision that
the dispatch chokepoint consults BEFORE touching the broker bridge.

CRITICAL framing: this gate is strictly OBSERVATIONAL.  It REJECTS or
APPROVES a proposed intent based on whether the would-be portfolio
metrics breach the operator's caps.  It NEVER advises trade picks,
NEVER tells the operator what to buy or sell, NEVER suggests scaling
back, closing, taking profit, or any other trade action.  The plain-
English reason explains *which cap fired* and *what the would-be value
was*, nothing more.

Inputs are loose Mappings so the same function works against the
risk_monitoring `snapshot_to_payload` shape and any equivalent dict.
Anything missing collapses to a safe default; the module never raises.

Tests pin the forbidden-phrase list — see
`tests/test_pre_execution_risk_gate.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


# Phrases that imply an action recommendation. The plain-English reason
# MUST NEVER contain any of these substrings, in either PASS or REJECT
# branches. Tests pin this list; do not weaken without updating tests.
FORBIDDEN_ADVISORY_PHRASES: tuple[str, ...] = (
    "you should sell",
    "consider closing",
    "scale back",
    "exit position",
    "take profit",
    "cut your losses",
    "buy more",
    "add to position",
    "is a good entry",
    "we recommend",
)


@dataclass(frozen=True)
class RiskCapConfig:
    """Operator-configured risk caps. ``None`` means "no cap" on that
    dimension. All other values are treated as hard ceilings (a strict
    breach blocks the proposed intent)."""

    max_total_exposure_lots: Optional[float]
    max_concentration_pct: Optional[float]
    max_margin_utilization_pct: Optional[float]
    max_positions_per_symbol: Optional[int]
    max_open_position_count: Optional[int]
    max_drawdown_pct_from_equity_peak: Optional[float]
    max_floating_loss_usd: Optional[float]
    max_risk_per_trade_pct: Optional[float] = None
    max_compound_units: Optional[int] = 0


@dataclass(frozen=True)
class RiskGateDecision:
    accepted: bool
    decision: str  # "PASS" | "REJECT"
    blocking_caps: tuple[str, ...]
    proposed_intent_summary: str
    plain_english_reason: str
    evaluated_at_iso: str
    cap_snapshot: Mapping[str, Any]
    portfolio_snapshot_summary: Mapping[str, Any]


DEFAULT_CAPS = RiskCapConfig(
    max_total_exposure_lots=10.0,
    max_concentration_pct=70.0,
    max_margin_utilization_pct=70.0,
    max_positions_per_symbol=5,
    max_open_position_count=20,
    max_drawdown_pct_from_equity_peak=15.0,
    max_floating_loss_usd=None,
    max_risk_per_trade_pct=None,
    max_compound_units=0,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso(now: Optional[datetime]) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.isoformat()


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_float_or_zero(value: Any) -> float:
    f = _as_float(value)
    return 0.0 if f is None else f


def _first_float(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[Optional[float], Optional[str]]:
    for key in keys:
        value = _as_float(mapping.get(key))
        if value is not None:
            return value, key
    return None, None


def _normalize_symbol(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    token = value.strip().upper()
    return token or None


def _normalize_direction(raw: Any) -> Optional[str]:
    if isinstance(raw, str):
        token = raw.strip().upper()
        if token in {"BUY", "LONG"}:
            return "BUY"
        if token in {"SELL", "SHORT"}:
            return "SELL"
    return None


def _format_lots(value: float) -> str:
    return f"{value:.2f}"


def _format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _extract_by_symbol(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("by_symbol")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            continue
        sym = _normalize_symbol(entry.get("symbol"))
        if sym is None:
            continue
        out.append(
            {
                "symbol": sym,
                "total_lots": _as_float_or_zero(entry.get("total_lots")),
                "open_position_count": int(
                    _as_float_or_zero(entry.get("open_position_count"))
                ),
                "total_floating_pnl": _as_float_or_zero(
                    entry.get("total_floating_pnl")
                ),
            }
        )
    return out


def _proposed_margin_impact(
    proposed_intent: Mapping[str, Any],
    portfolio_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return best-effort proposed margin facts for the risk decision.

    The dispatcher attaches the pre-trade estimate when it has one. If an
    upstream caller supplies only required margin, this derives would-be margin
    utilization from the current account snapshot.
    """

    explicit_util, explicit_key = _first_float(
        proposed_intent,
        (
            "estimated_margin_utilization_after_pct",
            "margin_utilization_after_pct",
            "would_be_margin_utilization_pct",
        ),
    )
    required_margin, required_key = _first_float(
        proposed_intent,
        (
            "estimated_margin_required_usd",
            "margin_required_usd",
            "required_margin_usd",
            "margin_required",
        ),
    )
    margin_after, margin_after_key = _first_float(
        proposed_intent,
        (
            "estimated_margin_after_usd",
            "margin_after_usd",
            "would_be_margin_used_usd",
        ),
    )
    free_margin_after, free_margin_after_key = _first_float(
        proposed_intent,
        (
            "estimated_free_margin_after_usd",
            "free_margin_after_usd",
            "would_be_free_margin_usd",
        ),
    )
    equity = _as_float(portfolio_snapshot.get("account_equity"))
    current_margin = _as_float(portfolio_snapshot.get("account_margin"))
    current_free_margin = _as_float(portfolio_snapshot.get("account_free_margin"))

    if explicit_util is not None:
        util_after = explicit_util
        source = f"proposed_intent.{explicit_key}"
    elif margin_after is not None and equity is not None and equity > 0:
        util_after = (margin_after / equity) * 100.0
        source = f"proposed_intent.{margin_after_key}/portfolio.account_equity"
    elif (
        required_margin is not None
        and current_margin is not None
        and equity is not None
        and equity > 0
    ):
        util_after = ((current_margin + required_margin) / equity) * 100.0
        source = f"portfolio.account_margin+proposed_intent.{required_key}/portfolio.account_equity"
    else:
        util_after = _as_float(portfolio_snapshot.get("margin_utilization_pct"))
        source = "portfolio.margin_utilization_pct" if util_after is not None else None

    return {
        "estimated_margin_required_usd": required_margin,
        "estimated_margin_after_usd": margin_after,
        "estimated_free_margin_after_usd": free_margin_after,
        "would_be_margin_utilization_pct": round(util_after, 4) if util_after is not None else None,
        "margin_utilization_source": source,
        "current_free_margin_usd": current_free_margin,
        "free_margin_after_source": (
            f"proposed_intent.{free_margin_after_key}" if free_margin_after_key is not None else None
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_proposed_intent(
    *,
    proposed_intent: Mapping[str, Any],
    portfolio_snapshot: Mapping[str, Any],
    caps: RiskCapConfig,
    equity_peak: Optional[float] = None,
    now: Optional[datetime] = None,
    compound_slot_authorized: bool = False,
) -> RiskGateDecision:
    """Evaluate a proposed RouteIntent against a portfolio snapshot and
    risk caps. Pure. Returns a `RiskGateDecision`. Never raises.

    `proposed_intent` is expected to carry `symbol`, `direction` and
    `lots` at minimum; optional `expected_loss_usd` is consulted for the
    floating-loss cap.

    `portfolio_snapshot` is the shape produced by
    `cas_forex.risk_monitoring.snapshot_to_payload`.
    """
    evaluated_at_iso = _now_iso(now)
    cap_snapshot = asdict(caps)

    # ---- 1. Parse the proposed intent defensively -----------------------
    if not isinstance(proposed_intent, Mapping):
        proposed_intent = {}
    if not isinstance(portfolio_snapshot, Mapping):
        portfolio_snapshot = {}

    symbol = _normalize_symbol(proposed_intent.get("symbol"))
    direction = _normalize_direction(
        proposed_intent.get("direction")
        if proposed_intent.get("direction") is not None
        else proposed_intent.get("side")
    )
    lots_raw = proposed_intent.get("lots")
    if lots_raw is None:
        lots_raw = proposed_intent.get("volume")
    lots_value = _as_float(lots_raw)
    if lots_value is not None:
        lots_value = abs(lots_value)

    portfolio_summary = _summarize_snapshot(portfolio_snapshot)

    missing: list[str] = []
    if symbol is None:
        missing.append("symbol")
    if direction is None:
        missing.append("direction")
    if lots_value is None or lots_value <= 0:
        missing.append("lots")

    if missing:
        summary_text = _format_intent_summary(
            symbol=symbol, direction=direction, lots=lots_value
        )
        reason = (
            "Proposed intent rejected: missing required field"
            f"{'s' if len(missing) > 1 else ''}: {', '.join(missing)}."
        )
        return RiskGateDecision(
            accepted=False,
            decision="REJECT",
            blocking_caps=("missing_required_fields",),
            proposed_intent_summary=summary_text,
            plain_english_reason=reason,
            evaluated_at_iso=evaluated_at_iso,
            cap_snapshot=cap_snapshot,
            portfolio_snapshot_summary=portfolio_summary,
        )

    # ---- 2. Pull metrics from the snapshot ------------------------------
    by_symbol = _extract_by_symbol(portfolio_snapshot)
    current_total_lots = _as_float_or_zero(
        portfolio_snapshot.get("total_exposure_lots")
    )
    current_open_count = int(
        _as_float_or_zero(portfolio_snapshot.get("open_position_count"))
    )
    current_floating_pnl = _as_float_or_zero(
        portfolio_snapshot.get("total_floating_pnl")
    )
    equity = _as_float(portfolio_snapshot.get("account_equity"))
    free_margin = _as_float(portfolio_snapshot.get("account_free_margin"))

    # Per-symbol bucket for the proposed symbol (may be absent).
    symbol_bucket = next(
        (b for b in by_symbol if b["symbol"] == symbol), None
    )
    symbol_existing_lots = (
        symbol_bucket["total_lots"] if symbol_bucket is not None else 0.0
    )
    symbol_existing_positions = (
        symbol_bucket["open_position_count"]
        if symbol_bucket is not None
        else 0
    )

    # ---- 3. Compute would-be metrics after the proposed intent ----------
    # Exposure is summed as |lots|, regardless of direction. This matches
    # how risk_monitoring aggregates: an opposing-direction position on
    # an existing symbol still adds to total notional exposure.
    would_be_total_lots = round(current_total_lots + lots_value, 4)
    would_be_symbol_lots = round(symbol_existing_lots + lots_value, 4)
    would_be_open_count = current_open_count + 1
    would_be_symbol_positions = symbol_existing_positions + 1
    compound_add_requested = bool(
        proposed_intent.get("is_compound_add")
        or proposed_intent.get("compound_add")
    )
    compound_slot_allowance = 0
    if compound_slot_authorized and compound_add_requested:
        try:
            compound_slot_allowance = max(0, int(caps.max_compound_units or 0))
        except (TypeError, ValueError):
            compound_slot_allowance = 0
    effective_symbol_position_cap = caps.max_positions_per_symbol
    if effective_symbol_position_cap is not None:
        effective_symbol_position_cap += compound_slot_allowance
    if isinstance(portfolio_summary, dict):
        portfolio_summary.update(
            {
                "compound_add_requested": compound_add_requested,
                "compound_slot_authorized": bool(compound_slot_authorized),
                "compound_slot_allowance": compound_slot_allowance,
                "base_max_positions_per_symbol": caps.max_positions_per_symbol,
                "effective_max_positions_per_symbol": effective_symbol_position_cap,
            }
        )

    # The "would-be" concentration is the max symbol concentration after
    # adding the proposed lots. The proposed symbol gets +lots_value;
    # every other symbol stays where it is.
    if would_be_total_lots > 0:
        proposed_symbol_pct = (would_be_symbol_lots / would_be_total_lots) * 100.0
        other_max_pct = 0.0
        for bucket in by_symbol:
            if bucket["symbol"] == symbol:
                continue
            pct = (bucket["total_lots"] / would_be_total_lots) * 100.0
            if pct > other_max_pct:
                other_max_pct = pct
        would_be_concentration_pct = round(
            max(proposed_symbol_pct, other_max_pct), 2
        )
        # Track which symbol holds the would-be peak so the reason is
        # honest (rejection on an existing symbol's concentration is
        # still observational — it explains the structural ratio, not
        # what to do about it).
        if proposed_symbol_pct >= other_max_pct:
            would_be_peak_symbol = symbol
        else:
            would_be_peak_symbol = next(
                b["symbol"]
                for b in by_symbol
                if b["symbol"] != symbol
                and round((b["total_lots"] / would_be_total_lots) * 100.0, 2)
                == round(other_max_pct, 2)
            )
    else:
        would_be_concentration_pct = 0.0
        would_be_peak_symbol = symbol

    # Margin utilization can come from the dispatcher-attached pre-trade
    # estimate when broker/account metadata is available, otherwise it
    # degrades to the current snapshot fields.
    margin_impact = _proposed_margin_impact(proposed_intent, portfolio_snapshot)
    current_margin_util = _as_float(portfolio_snapshot.get("margin_utilization_pct"))
    would_be_margin_util = _as_float(margin_impact.get("would_be_margin_utilization_pct"))
    proposed_free_margin_after = _as_float(margin_impact.get("estimated_free_margin_after_usd"))
    if isinstance(portfolio_summary, dict):
        portfolio_summary.update(
            {
                "proposed_margin_required_usd": margin_impact.get("estimated_margin_required_usd"),
                "proposed_free_margin_after_usd": margin_impact.get("estimated_free_margin_after_usd"),
                "would_be_margin_utilization_pct": margin_impact.get("would_be_margin_utilization_pct"),
                "margin_utilization_source": margin_impact.get("margin_utilization_source"),
            }
        )

    # Drawdown from equity peak.
    drawdown_pct: Optional[float] = None
    if equity_peak is not None and equity is not None and equity_peak > 0:
        drawdown_pct = round(
            max(0.0, (equity_peak - equity) / equity_peak * 100.0), 2
        )

    expected_loss_usd, expected_loss_key = _first_float(
        proposed_intent,
        ("risk_at_stop_usd", "expected_loss_usd"),
    )
    if expected_loss_usd is not None:
        expected_loss_usd = abs(expected_loss_usd)
    explicit_risk_at_stop_pct, risk_pct_key = _first_float(
        proposed_intent,
        ("risk_at_stop_pct_equity", "risk_per_trade_pct"),
    )
    if explicit_risk_at_stop_pct is not None:
        explicit_risk_at_stop_pct = abs(explicit_risk_at_stop_pct)
    derived_risk_at_stop_pct = None
    derived_risk_source = None
    if expected_loss_usd is not None and equity is not None and equity > 0:
        derived_risk_at_stop_pct = (expected_loss_usd / equity) * 100.0
        derived_risk_source = (
            f"proposed_intent.{expected_loss_key}/portfolio.account_equity"
            if expected_loss_key
            else "proposed_intent.stop_risk/portfolio.account_equity"
        )
    risk_pct_candidates = [
        (explicit_risk_at_stop_pct, f"proposed_intent.{risk_pct_key}" if risk_pct_key else None),
        (derived_risk_at_stop_pct, derived_risk_source),
    ]
    risk_pct_candidates = [item for item in risk_pct_candidates if item[0] is not None]
    risk_at_stop_pct = max((value for value, _ in risk_pct_candidates), default=None)
    risk_pct_source = None
    if risk_at_stop_pct is not None:
        risk_pct_source = next(
            (source for value, source in risk_pct_candidates if value == risk_at_stop_pct),
            None,
        )
    if isinstance(portfolio_summary, dict):
        portfolio_summary.update(
            {
                "proposed_risk_at_stop_usd": (
                    round(expected_loss_usd, 2) if expected_loss_usd is not None else None
                ),
                "proposed_risk_at_stop_pct_equity": (
                    round(risk_at_stop_pct, 4) if risk_at_stop_pct is not None else None
                ),
                "proposed_risk_at_stop_source": risk_pct_source,
            }
        )

    # ---- 4. Check each cap ----------------------------------------------
    blocking: list[str] = []
    headline_parts: list[str] = []

    if caps.max_total_exposure_lots is not None:
        if would_be_total_lots > caps.max_total_exposure_lots:
            blocking.append("max_total_exposure_lots")
            headline_parts.append(
                f"total exposure would become "
                f"{_format_lots(would_be_total_lots)} lots "
                f"(cap {_format_lots(caps.max_total_exposure_lots)})"
            )

    if caps.max_concentration_pct is not None:
        if would_be_concentration_pct > caps.max_concentration_pct:
            blocking.append("max_concentration_pct")
            headline_parts.append(
                f"concentration in {would_be_peak_symbol} would be "
                f"{would_be_concentration_pct:.0f}% "
                f"(cap {caps.max_concentration_pct:.0f}%)"
            )

    if caps.max_margin_utilization_pct is not None:
        if (
            would_be_margin_util is not None
            and would_be_margin_util > caps.max_margin_utilization_pct
        ):
            blocking.append("max_margin_utilization_pct")
            if current_margin_util is not None and abs(would_be_margin_util - current_margin_util) > 0.01:
                headline_parts.append(
                    f"margin utilization would become {would_be_margin_util:.0f}% "
                    f"from {current_margin_util:.0f}% "
                    f"(cap {caps.max_margin_utilization_pct:.0f}%)"
                )
            else:
                headline_parts.append(
                    f"margin utilization {would_be_margin_util:.0f}% "
                    f"(cap {caps.max_margin_utilization_pct:.0f}%)"
                )

    if proposed_free_margin_after is not None and proposed_free_margin_after < 0:
        blocking.append("insufficient_free_margin")
        if free_margin is not None:
            headline_parts.append(
                f"free margin would become {_format_money(proposed_free_margin_after)} "
                f"from {_format_money(free_margin)}"
            )
        else:
            headline_parts.append(
                f"free margin would become {_format_money(proposed_free_margin_after)}"
            )

    if effective_symbol_position_cap is not None:
        if would_be_symbol_positions > effective_symbol_position_cap:
            blocking.append("max_positions_per_symbol")
            if compound_slot_allowance:
                headline_parts.append(
                    f"positions on {symbol} would become {would_be_symbol_positions} "
                    f"(base cap {caps.max_positions_per_symbol} plus "
                    f"{compound_slot_allowance} authorized compound slot"
                    f"{'s' if compound_slot_allowance != 1 else ''})"
                )
            else:
                headline_parts.append(
                    f"positions on {symbol} would become "
                    f"{would_be_symbol_positions} "
                    f"(cap {effective_symbol_position_cap})"
                )

    if caps.max_open_position_count is not None:
        if would_be_open_count > caps.max_open_position_count:
            blocking.append("max_open_position_count")
            headline_parts.append(
                f"open position count would become "
                f"{would_be_open_count} "
                f"(cap {caps.max_open_position_count})"
            )

    if caps.max_drawdown_pct_from_equity_peak is not None:
        if (
            drawdown_pct is not None
            and drawdown_pct > caps.max_drawdown_pct_from_equity_peak
        ):
            blocking.append("max_drawdown_pct_from_equity_peak")
            headline_parts.append(
                f"drawdown from equity peak {drawdown_pct:.1f}% "
                f"(cap {caps.max_drawdown_pct_from_equity_peak:.1f}%)"
            )

    if caps.max_floating_loss_usd is not None:
        # would-be worst-case floating loss = current floating P/L
        # minus the expected loss the intent could add.
        prospective_loss = current_floating_pnl
        if expected_loss_usd is not None:
            prospective_loss = current_floating_pnl - abs(expected_loss_usd)
        if prospective_loss < -abs(caps.max_floating_loss_usd):
            blocking.append("max_floating_loss_usd")
            headline_parts.append(
                f"floating loss could reach "
                f"{_format_money(prospective_loss)} "
                f"(cap {_format_money(-abs(caps.max_floating_loss_usd))})"
            )

    if caps.max_risk_per_trade_pct is not None and risk_at_stop_pct is not None:
        if risk_at_stop_pct > caps.max_risk_per_trade_pct:
            blocking.append("max_risk_per_trade_pct")
            headline_parts.append(
                f"risk at the protective stop would be {risk_at_stop_pct:.3f}% of equity "
                f"(cap {caps.max_risk_per_trade_pct:.3f}%)"
            )

    proposed_intent_summary = _format_intent_summary(
        symbol=symbol, direction=direction, lots=lots_value
    )

    if blocking:
        headline = headline_parts[0] if headline_parts else "cap breach"
        reason = (
            f"Proposed intent rejected by {len(blocking)} cap"
            f"{'s' if len(blocking) != 1 else ''}: "
            f"{', '.join(blocking)}. Headline: {headline}."
        )
        return RiskGateDecision(
            accepted=False,
            decision="REJECT",
            blocking_caps=tuple(blocking),
            proposed_intent_summary=proposed_intent_summary,
            plain_english_reason=reason,
            evaluated_at_iso=evaluated_at_iso,
            cap_snapshot=cap_snapshot,
            portfolio_snapshot_summary=portfolio_summary,
        )

    # ---- 5. PASS branch -------------------------------------------------
    pass_reason = (
        "Within configured caps. "
        f"Total exposure would become {_format_lots(would_be_total_lots)} lots; "
        f"concentration in {would_be_peak_symbol} would be "
        f"{would_be_concentration_pct:.0f}%; "
    )
    if would_be_margin_util is not None:
        if current_margin_util is not None and abs(would_be_margin_util - current_margin_util) > 0.01:
            pass_reason += f"margin utilization would become {would_be_margin_util:.0f}% from {current_margin_util:.0f}%."
        else:
            pass_reason += f"margin utilization {would_be_margin_util:.0f}%."
    else:
        pass_reason += "margin utilization not reported."
    if risk_at_stop_pct is not None:
        pass_reason += f" Risk at the protective stop is {risk_at_stop_pct:.3f}% of equity."

    return RiskGateDecision(
        accepted=True,
        decision="PASS",
        blocking_caps=(),
        proposed_intent_summary=proposed_intent_summary,
        plain_english_reason=pass_reason,
        evaluated_at_iso=evaluated_at_iso,
        cap_snapshot=cap_snapshot,
        portfolio_snapshot_summary=portfolio_summary,
    )


def _format_intent_summary(
    *, symbol: Optional[str], direction: Optional[str], lots: Optional[float]
) -> str:
    sym_text = symbol if symbol else "?"
    dir_text = direction if direction else "?"
    lots_text = f"{lots:.2f}" if lots is not None else "?"
    return f"{dir_text} {sym_text} {lots_text} lots"


def _summarize_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "open_position_count": int(
            _as_float_or_zero(snapshot.get("open_position_count"))
        ),
        "total_exposure_lots": _as_float_or_zero(
            snapshot.get("total_exposure_lots")
        ),
        "total_floating_pnl": _as_float_or_zero(
            snapshot.get("total_floating_pnl")
        ),
        "concentration_pct": _as_float_or_zero(
            snapshot.get("concentration_pct")
        ),
        "margin_utilization_pct": _as_float(
            snapshot.get("margin_utilization_pct")
        ),
        "account_equity": _as_float(snapshot.get("account_equity")),
        "account_free_margin": _as_float(
            snapshot.get("account_free_margin")
        ),
    }


def decision_to_payload(decision: RiskGateDecision) -> dict[str, Any]:
    """JSON-serializable form of a `RiskGateDecision`."""
    payload = asdict(decision)
    payload["blocking_caps"] = list(decision.blocking_caps)
    return payload
