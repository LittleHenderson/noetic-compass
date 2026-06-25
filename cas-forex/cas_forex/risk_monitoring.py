"""Pure portfolio risk monitoring primitives.

This module is strictly OBSERVATIONAL. It aggregates live telemetry and the
latest broker account snapshot into a single risk shape: per-symbol
exposure, total exposure (in lots), concentration, floating P/L envelope,
margin utilization. It NEVER recommends an action ("close X", "scale back",
"reduce exposure"). The operator decides.

Inputs are intentionally loose Mappings so the same function works against
the live-telemetry route payload, raw MT5 verifier reports, and the
movement-stream paper snapshot. Anything missing collapses to a safe zero
or ``None``; the module never fabricates numbers.

The companion route `api/routes/risk_monitoring.py` wires the disk loader.
Tests pin the forbidden-phrase list — see `tests/test_risk_monitoring.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


# Phrases that imply an action recommendation. The plain-English summary and
# diagnostic hints MUST NEVER contain any of these substrings. Tests pin
# this list; do not weaken without updating the tests.
FORBIDDEN_ADVISORY_PHRASES: tuple[str, ...] = (
    "you should close",
    "consider closing",
    "scale back",
    "exit position",
    "take profit now",
    "cut your losses",
    "reduce exposure",
    "buy more",
    "add to position",
)


@dataclass(frozen=True)
class SymbolRiskExposure:
    symbol: str
    direction: str  # "BUY" | "SELL" | "MIXED"
    open_position_count: int
    total_lots: float
    total_floating_pnl: float
    largest_position_lots: float


@dataclass(frozen=True)
class PortfolioRiskSnapshot:
    snapshot_at_iso: str
    open_position_count: int
    total_floating_pnl: float
    total_exposure_lots: float
    largest_symbol_exposure: Optional[SymbolRiskExposure]
    largest_floating_pnl_loss: float
    largest_floating_pnl_gain: float
    by_symbol: tuple[SymbolRiskExposure, ...]
    concentration_pct: float
    account_balance: Optional[float]
    account_equity: Optional[float]
    account_margin: Optional[float]
    account_free_margin: Optional[float]
    margin_utilization_pct: Optional[float]
    plain_english_summary: str
    diagnostic_hints: tuple[str, ...]


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


def _normalize_direction(raw: Any) -> str:
    if isinstance(raw, str):
        token = raw.strip().upper()
        if token in {"BUY", "LONG", "0"}:
            return "BUY"
        if token in {"SELL", "SHORT", "1"}:
            return "SELL"
        if token == "MIXED":
            return "MIXED"
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return "BUY" if int(raw) == 0 else "SELL"
    return "BUY"


def _extract_positions(live_telemetry: Optional[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Pull a normalized list of {symbol, direction, lots, floating_pnl}
    from a live-telemetry payload. Tolerant of the route's own shape and of
    raw MT5/paper position lists."""
    if not isinstance(live_telemetry, Mapping):
        return []
    raw = live_telemetry.get("open_positions")
    if not isinstance(raw, list):
        # Allow callers to pass a bare list under a different wrapper.
        raw = live_telemetry.get("positions")
        if not isinstance(raw, list):
            return []
    out: list[dict[str, Any]] = []
    for p in raw:
        if not isinstance(p, Mapping):
            continue
        symbol = p.get("symbol")
        if not symbol:
            continue
        lots = _as_float_or_zero(p.get("lots") or p.get("volume") or p.get("lot_size"))
        pnl = _as_float_or_zero(
            p.get("floating_pnl")
            if p.get("floating_pnl") is not None
            else (p.get("profit") if p.get("profit") is not None else p.get("floating_pnl_usd"))
        )
        direction = _normalize_direction(p.get("direction") or p.get("side") or p.get("type"))
        out.append({
            "symbol": str(symbol).upper(),
            "direction": direction,
            "lots": abs(lots),
            "floating_pnl": pnl,
        })
    return out


def _extract_account(account_snapshot: Optional[Mapping[str, Any]]) -> dict[str, Optional[float]]:
    """Pull balance/equity/margin/free-margin from either a raw verifier
    report or a flat account snapshot dict."""
    result: dict[str, Optional[float]] = {
        "balance": None,
        "equity": None,
        "margin": None,
        "free_margin": None,
    }
    if not isinstance(account_snapshot, Mapping):
        return result

    # Walk the typical nesting shapes:
    #   verifier report -> probe.receipt.account_snapshot
    #   movement_stream -> account
    #   flat dict       -> as-is
    candidates: list[Mapping[str, Any]] = []
    candidates.append(account_snapshot)
    probe = account_snapshot.get("probe")
    if isinstance(probe, Mapping):
        receipt = probe.get("receipt")
        if isinstance(receipt, Mapping):
            snap = receipt.get("account_snapshot")
            if isinstance(snap, Mapping):
                candidates.append(snap)
    acct = account_snapshot.get("account")
    if isinstance(acct, Mapping):
        candidates.append(acct)

    for src in candidates:
        if result["balance"] is None:
            result["balance"] = _as_float(src.get("balance"))
        if result["equity"] is None:
            result["equity"] = _as_float(src.get("equity"))
        if result["margin"] is None:
            result["margin"] = _as_float(src.get("margin"))
        if result["free_margin"] is None:
            # MT5 calls it `margin_free`; movement-stream sometimes `free_margin`.
            result["free_margin"] = _as_float(
                src.get("margin_free") if src.get("margin_free") is not None else src.get("free_margin")
            )
    return result


def _aggregate_by_symbol(positions: list[dict[str, Any]]) -> list[SymbolRiskExposure]:
    bucket: dict[str, dict[str, Any]] = {}
    for p in positions:
        sym = p["symbol"]
        slot = bucket.setdefault(
            sym,
            {
                "directions": set(),
                "count": 0,
                "lots": 0.0,
                "pnl": 0.0,
                "largest": 0.0,
            },
        )
        slot["directions"].add(p["direction"])
        slot["count"] += 1
        slot["lots"] += p["lots"]
        slot["pnl"] += p["floating_pnl"]
        if p["lots"] > slot["largest"]:
            slot["largest"] = p["lots"]

    out: list[SymbolRiskExposure] = []
    for sym, slot in bucket.items():
        dirs = slot["directions"]
        if len(dirs) > 1:
            direction = "MIXED"
        else:
            direction = next(iter(dirs))
        out.append(
            SymbolRiskExposure(
                symbol=sym,
                direction=direction,
                open_position_count=int(slot["count"]),
                total_lots=round(slot["lots"], 4),
                total_floating_pnl=round(slot["pnl"], 2),
                largest_position_lots=round(slot["largest"], 4),
            )
        )
    out.sort(key=lambda s: (-s.total_lots, s.symbol))
    return out


def _format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _compose_summary(
    open_count: int,
    by_symbol: tuple[SymbolRiskExposure, ...],
    total_lots: float,
    total_pnl: float,
    largest: Optional[SymbolRiskExposure],
    concentration_pct: float,
    equity: Optional[float],
    free_margin: Optional[float],
    margin_utilization_pct: Optional[float],
) -> str:
    sentences: list[str] = []
    if open_count == 0:
        sentences.append("Portfolio holds no open positions.")
    else:
        sentences.append(
            f"Portfolio holds {open_count} open position"
            f"{'s' if open_count != 1 else ''} across {len(by_symbol)} symbol"
            f"{'s' if len(by_symbol) != 1 else ''} "
            f"(total exposure {total_lots:.2f} lots; floating P/L {_format_money(total_pnl)})."
        )
    if largest is not None and total_lots > 0:
        sentences.append(
            f"Largest single-symbol exposure: {largest.symbol} at "
            f"{largest.total_lots:.2f} lots ({concentration_pct:.0f}% of total)."
        )
    if equity is not None and free_margin is not None and margin_utilization_pct is not None:
        sentences.append(
            f"Account equity {_format_money(equity)}, free margin "
            f"{_format_money(free_margin)}, margin utilization "
            f"{margin_utilization_pct:.0f}%."
        )
    return " ".join(sentences)


def _compose_hints(
    by_symbol: tuple[SymbolRiskExposure, ...],
    open_count: int,
    concentration_pct: float,
    largest: Optional[SymbolRiskExposure],
    margin_utilization_pct: Optional[float],
) -> tuple[str, ...]:
    hints: list[str] = []
    if largest is not None and concentration_pct > 60:
        hints.append(f"Concentration above 60% in {largest.symbol}.")
    if margin_utilization_pct is not None and margin_utilization_pct > 50:
        hints.append("Margin utilization above 50%.")
    if len(by_symbol) == 1 and open_count > 1:
        hints.append("All positions on one symbol.")
    return tuple(hints)


def compose_portfolio_risk_snapshot(
    *,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> PortfolioRiskSnapshot:
    """Build a `PortfolioRiskSnapshot` from optional live telemetry and an
    optional account snapshot. Pure function; safe with all-`None` inputs.
    """
    positions = _extract_positions(live_telemetry)
    by_symbol_list = _aggregate_by_symbol(positions)
    by_symbol = tuple(by_symbol_list)

    open_position_count = sum(s.open_position_count for s in by_symbol)
    total_exposure_lots = round(sum(s.total_lots for s in by_symbol), 4)
    total_floating_pnl = round(sum(s.total_floating_pnl for s in by_symbol), 2)

    largest_symbol_exposure: Optional[SymbolRiskExposure] = (
        by_symbol[0] if by_symbol else None
    )

    if positions:
        pnls = [p["floating_pnl"] for p in positions]
        largest_loss = round(min(min(pnls), 0.0), 2)
        largest_gain = round(max(max(pnls), 0.0), 2)
    else:
        largest_loss = 0.0
        largest_gain = 0.0

    if total_exposure_lots > 0 and largest_symbol_exposure is not None:
        concentration_pct = round(
            (largest_symbol_exposure.total_lots / total_exposure_lots) * 100.0, 2
        )
    else:
        concentration_pct = 0.0

    account = _extract_account(account_snapshot)
    balance = account["balance"]
    equity = account["equity"]
    margin = account["margin"]
    free_margin = account["free_margin"]

    if equity is not None and free_margin is not None and equity > 0:
        margin_utilization_pct: Optional[float] = round(
            (1.0 - (free_margin / equity)) * 100.0, 2
        )
    else:
        margin_utilization_pct = None

    summary = _compose_summary(
        open_count=open_position_count,
        by_symbol=by_symbol,
        total_lots=total_exposure_lots,
        total_pnl=total_floating_pnl,
        largest=largest_symbol_exposure,
        concentration_pct=concentration_pct,
        equity=equity,
        free_margin=free_margin,
        margin_utilization_pct=margin_utilization_pct,
    )
    hints = _compose_hints(
        by_symbol=by_symbol,
        open_count=open_position_count,
        concentration_pct=concentration_pct,
        largest=largest_symbol_exposure,
        margin_utilization_pct=margin_utilization_pct,
    )

    return PortfolioRiskSnapshot(
        snapshot_at_iso=_now_iso(now),
        open_position_count=open_position_count,
        total_floating_pnl=total_floating_pnl,
        total_exposure_lots=total_exposure_lots,
        largest_symbol_exposure=largest_symbol_exposure,
        largest_floating_pnl_loss=largest_loss,
        largest_floating_pnl_gain=largest_gain,
        by_symbol=by_symbol,
        concentration_pct=concentration_pct,
        account_balance=balance,
        account_equity=equity,
        account_margin=margin,
        account_free_margin=free_margin,
        margin_utilization_pct=margin_utilization_pct,
        plain_english_summary=summary,
        diagnostic_hints=hints,
    )


def snapshot_to_payload(snapshot: PortfolioRiskSnapshot) -> dict[str, Any]:
    """JSON-serializable form. Tuples become lists; nested dataclasses
    become dicts."""
    payload = asdict(snapshot)
    if snapshot.largest_symbol_exposure is None:
        payload["largest_symbol_exposure"] = None
    payload["by_symbol"] = [asdict(s) for s in snapshot.by_symbol]
    payload["diagnostic_hints"] = list(snapshot.diagnostic_hints)
    return payload
