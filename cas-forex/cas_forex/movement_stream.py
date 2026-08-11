"""Paper/demo account and market movement snapshots for CAS Forex.

This is the live-readiness bridge after the owner investment ledger: it exposes
the same categories a live cockpit must track (account balance/equity/margin,
open-position P/L, bid/ask/spread, SL/TP distance, tick/candle hints) while the
movement stream itself remains telemetry only. Autonomous order and money
actions belong to the separate guarded dispatch/provider paths.
"""

from __future__ import annotations
from cas_forex.account_ledger import money_sum

from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from cas_forex.authority_boundary import NOT_LICENSED, OPEN
from cas_forex.config import config
from cas_forex.instruments import pip_value_per_lot, price_unit_size, round_price, usd_notional
from cas_forex.time_utils import ensure_utc, utc_now

CLAIM_BOUNDARY = (
    "Movement streams are telemetry only. They track paper/demo account movement "
    "and market repricing for active proof rows, but this stream is not an "
    "execution surface: orders, take-profit/stop changes, broker ACCEPT, deposits, "
    "withdrawals, transfers, and payouts must use the guarded dispatch/provider "
    "paths after owner-delegated authority and runtime gates pass."
)

STATIC_SIMULATION_WARNING = (
    "Static simulator rows are not being moved by usable provider/MT5 quotes "
    "right now; prices and floating P&L can remain unchanged at entry."
)

MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS = max(
    1,
    int(getattr(config, "movement_snapshot_max_age_seconds", 900) or 900),
)


@dataclass(frozen=True)
class MarketMovementQuote:
    symbol: str
    timestamp: str
    bid: float
    ask: float
    mid: float
    spread_units: float
    price_unit_name: str
    price_unit_size: float
    session: str
    is_market_open: bool
    source: str
    stale: bool
    synthetic_candle: dict[str, float | str]
    atr_units: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PositionMovement:
    row_id: str
    symbol: str
    side: str
    lot_size: float
    open_price: float
    current_price: float
    stop_loss: float | None
    take_profit: float | None
    floating_pnl_usd: float
    floating_pnl_units: float
    distance_to_sl_units: float | None
    distance_to_tp_units: float | None
    distance_to_sl_pct: float | None
    distance_to_tp_pct: float | None
    margin_estimate_usd: float
    price_source: str
    price_stale: bool
    stale_reason: str | None
    opened_at: str | None
    age_seconds: int | None
    age_days: float | None
    position_source_label: str
    broker_ticket: str | None
    simulator_ticket: str
    evidence_packet_id: str
    ai_action: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AccountMovementSnapshot:
    timestamp: str
    balance_usd: float
    equity_usd: float
    realized_pnl_usd: float
    floating_pnl_usd: float
    swap_usd: float
    commission_usd: float
    broker_fees_usd: float
    margin_used_usd: float
    free_margin_usd: float
    drawdown_usd: float
    drawdown_pct: float
    deposit_usd: float
    withdrawals_usd: float
    payouts_usd: float
    open_position_count: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MovementStreamState:
    report_kind: str
    stream_id: str
    mode: str
    timestamp: str
    symbols: tuple[str, ...]
    account: AccountMovementSnapshot
    quotes: tuple[MarketMovementQuote, ...]
    positions: tuple[PositionMovement, ...]
    account_streams: tuple[str, ...]
    market_streams: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_boundary: str
    trading_edge_status: str
    live_trading_status: str
    broker_accept_status: str
    auto_deposit_status: str
    debit_card_bank_movement_status: str
    payout_automation_status: str
    live_money_authorized: bool
    payment_movement_authorized: bool
    notes: tuple[str, ...]
    static_simulation_active: bool = False
    price_source_label: str = "UNKNOWN"
    price_source_summary: str = ""
    price_source_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["account"] = self.account.to_dict()
        data["quotes"] = [quote.to_dict() for quote in self.quotes]
        data["positions"] = [position.to_dict() for position in self.positions]
        return data


def build_movement_stream_state(
    account_ledger: Mapping[str, Any],
    *,
    timestamp: str | None = None,
    leverage: float = 100.0,
    quote_overrides: Mapping[str, float] | None = None,
    market_snapshots: Mapping[str, Any] | None = None,
    market_snapshot_sources: Mapping[str, str] | None = None,
) -> MovementStreamState:
    """Build the paper/demo movement snapshot from the account ledger rows.

    ``market_snapshots`` lets the API inject configured-provider quotes
    (YFinance/OANDA/MT bridge later) while this module keeps a deterministic
    paper-route fallback. ``quote_overrides`` remains a test/operator override
    and wins over provider snapshots. None of these inputs authorize execution.
    """

    ts = timestamp or utc_now().isoformat()
    leverage = max(float(leverage), 1.0)
    summary = account_ledger.get("summary") or {}
    rows = list(account_ledger.get("positions") or [])
    market_snapshots = market_snapshots or {}
    market_snapshot_sources = {
        str(symbol): str(source)
        for symbol, source in (market_snapshot_sources or {}).items()
        if str(symbol or "").strip() and str(source or "").strip()
    }
    usable_snapshots = {
        str(symbol): snapshot
        for symbol, snapshot in market_snapshots.items()
        if movement_snapshot_usable_for_movement(snapshot, reference_time=ts)
    }
    provider_mid_prices = _mid_prices_from_snapshots(usable_snapshots)
    manual_overrides = quote_overrides or {}
    price_sources = {
        symbol: f"provider_snapshot:{market_snapshot_sources.get(symbol) or snapshot.__class__.__name__}"
        for symbol, snapshot in usable_snapshots.items()
    }
    price_sources.update({str(symbol): "operator_quote_override" for symbol in manual_overrides})
    quote_overrides = {**provider_mid_prices, **manual_overrides}

    positions = tuple(
        _position_movement(
            row,
            quote_overrides=quote_overrides,
            price_sources=price_sources,
            leverage=leverage,
            timestamp=ts,
        )
        for row in rows
    )
    quote_by_symbol = {
        q.symbol: q
        for q in (
            _quote_from_position(
                pos,
                ts,
                usable_snapshots.get(pos.symbol),
                market_snapshot_sources.get(pos.symbol),
            )
            for pos in positions
        )
    }
    quotes = tuple(quote_by_symbol[symbol] for symbol in sorted(quote_by_symbol))
    floating = money_sum(pos.floating_pnl_usd for pos in positions)
    balance = float(summary.get("balance_usd", 0.0) or 0.0)
    margin = money_sum(pos.margin_estimate_usd for pos in positions)
    equity = round(balance + floating, 2)
    free_margin = round(max(0.0, equity - margin), 2)
    initial = float(summary.get("initial_investment_usd", balance) or balance or 1.0)
    drawdown = round(max(0.0, initial - equity), 2)
    account = AccountMovementSnapshot(
        timestamp=ts,
        balance_usd=round(balance, 2),
        equity_usd=equity,
        realized_pnl_usd=round(float(summary.get("realized_pnl_usd", 0.0) or 0.0), 2),
        floating_pnl_usd=floating,
        swap_usd=round(float(summary.get("swap_usd", 0.0) or 0.0), 2),
        commission_usd=round(float(summary.get("commission_usd", 0.0) or 0.0), 2),
        broker_fees_usd=round(float(summary.get("broker_fees_usd", 0.0) or 0.0), 2),
        margin_used_usd=margin,
        free_margin_usd=free_margin,
        drawdown_usd=drawdown,
        drawdown_pct=round(drawdown / max(initial, 1e-9) * 100.0, 4),
        deposit_usd=round(float(summary.get("deposit_usd", 0.0) or 0.0), 2),
        withdrawals_usd=round(float(summary.get("withdrawals_usd", 0.0) or 0.0), 2),
        payouts_usd=round(float(summary.get("payouts_usd", 0.0) or 0.0), 2),
        open_position_count=len(positions),
        source="paper_demo_account_ledger",
    )
    symbols = tuple(sorted({pos.symbol for pos in positions}))
    stream_id = _stable_id("movement", account_ledger.get("plan_id"), ts, symbols, equity, floating)
    provider_symbols = tuple(symbol for symbol in symbols if symbol in usable_snapshots)
    fallback_symbols = tuple(symbol for symbol in symbols if symbol not in usable_snapshots)
    notes = (
        "Account movement is recomputed from paper/demo ledger rows and current paper/provider prices.",
        "Market movement uses configured-provider snapshots only when bid/ask data is usable and market-open; deterministic paper-route fallback remains clearly marked as static simulation.",
    )
    if provider_symbols:
        notes += (f"Provider-backed current prices used for: {', '.join(provider_symbols)}.",)
    if fallback_symbols:
        notes += (f"Static simulator fallback used for: {', '.join(fallback_symbols)}.",)
    static_simulation_active = bool(fallback_symbols)
    price_source_label = "STATIC SIM" if static_simulation_active else "PROVIDER"
    price_source_summary = (
        "Paper/demo movement is on static simulator fallback for one or more rows."
        if static_simulation_active
        else "Paper/demo movement is being repriced by provider or MT5 market snapshots."
    )
    return MovementStreamState(
        report_kind="cas_forex_movement_stream",
        stream_id=stream_id,
        mode="PAPER_DEMO_REALTIME_SCAFFOLD",
        timestamp=ts,
        symbols=symbols,
        account=account,
        quotes=quotes,
        positions=positions,
        account_streams=(
            "balance",
            "equity",
            "realized_pnl",
            "floating_pnl",
            "swap",
            "commission",
            "broker_fees",
            "margin",
            "free_margin",
            "drawdown",
            "deposit",
            "withdrawal",
            "payout",
            "open_position_count",
        ),
        market_streams=(
            "bid",
            "ask",
            "mid",
            "spread",
            "synthetic_candle",
            "atr",
            "sl_distance",
            "tp_distance",
            "floating_pnl",
            "margin_estimate",
            "market_open",
            "session",
            "source",
            "position_age",
            "stale_reason",
        ),
        evidence_refs=tuple(account_ledger.get("evidence_refs") or ()),
        claim_boundary=CLAIM_BOUNDARY,
        trading_edge_status=OPEN,
        live_trading_status=NOT_LICENSED,
        broker_accept_status=NOT_LICENSED,
        auto_deposit_status=NOT_LICENSED,
        debit_card_bank_movement_status=NOT_LICENSED,
        payout_automation_status=NOT_LICENSED,
        live_money_authorized=False,
        payment_movement_authorized=False,
        notes=notes,
        static_simulation_active=static_simulation_active,
        price_source_label=price_source_label,
        price_source_summary=price_source_summary,
        price_source_warning=STATIC_SIMULATION_WARNING if static_simulation_active else None,
    )


def _position_movement(
    row: Mapping[str, Any],
    *,
    quote_overrides: Mapping[str, float],
    price_sources: Mapping[str, str],
    leverage: float,
    timestamp: str,
) -> PositionMovement:
    symbol = str(row.get("symbol"))
    side = str(row.get("side") or "LONG")
    open_price = float(row.get("open_price", 0.0) or 0.0)
    current_price = float(quote_overrides.get(symbol, row.get("close_or_current_price") or open_price))
    price_source = str(price_sources.get(symbol) or "paper_route_snapshot:static_simulation")
    lot_size = float(row.get("lot_size", 0.0) or 0.0)
    broker_ticket = row.get("broker_ticket")
    opened_at = _nonempty_str(row.get("timestamp"))
    age_seconds = _age_seconds(opened_at, timestamp)
    position_source_label = _movement_position_source_label(
        broker_ticket=broker_ticket,
        price_source=price_source,
    )
    unit = price_unit_size(symbol)
    multiplier = 1.0 if side.upper() == "LONG" else -1.0
    movement_units = (current_price - open_price) / max(unit, 1e-9) * multiplier
    value_per_unit = pip_value_per_lot(symbol, max(current_price, 1e-9))
    floating = movement_units * value_per_unit * lot_size
    sl = _maybe_float(row.get("stop_loss"))
    tp = _maybe_float(row.get("take_profit"))
    distance_sl = None
    distance_tp = None
    if sl is not None:
        distance_sl = ((current_price - sl) / unit) if side.upper() == "LONG" else ((sl - current_price) / unit)
    if tp is not None:
        distance_tp = ((tp - current_price) / unit) if side.upper() == "LONG" else ((current_price - tp) / unit)
    margin = usd_notional(symbol, max(current_price, 1e-9), lot_size) / leverage
    price_stale = not price_source.startswith(("provider_snapshot:", "operator_quote_override"))
    stale_reason = (
        "Static paper-route snapshot: no usable provider or MT5 quote is pricing this simulator row."
        if price_stale
        else None
    )
    return PositionMovement(
        row_id=str(row.get("row_id") or _stable_id("row", symbol, open_price, lot_size)),
        symbol=symbol,
        side=side,
        lot_size=round(lot_size, 4),
        open_price=round_price(symbol, open_price),
        current_price=round_price(symbol, current_price),
        stop_loss=round_price(symbol, sl) if sl is not None else None,
        take_profit=round_price(symbol, tp) if tp is not None else None,
        floating_pnl_usd=round(floating, 2),
        floating_pnl_units=round(movement_units, 4),
        distance_to_sl_units=round(distance_sl, 4) if distance_sl is not None else None,
        distance_to_tp_units=round(distance_tp, 4) if distance_tp is not None else None,
        distance_to_sl_pct=round(distance_sl / max(abs(open_price / unit), 1e-9) * 100.0, 4) if distance_sl is not None else None,
        distance_to_tp_pct=round(distance_tp / max(abs(open_price / unit), 1e-9) * 100.0, 4) if distance_tp is not None else None,
        margin_estimate_usd=round(margin, 2),
        price_source=price_source,
        price_stale=price_stale,
        stale_reason=stale_reason,
        opened_at=opened_at,
        age_seconds=age_seconds,
        age_days=round(age_seconds / 86400.0, 2) if age_seconds is not None else None,
        position_source_label=position_source_label,
        broker_ticket=broker_ticket,
        simulator_ticket=str(row.get("simulator_ticket") or _stable_id("sim", symbol, open_price, lot_size)),
        evidence_packet_id=str(row.get("evidence_packet_id") or "unknown-evidence"),
        ai_action=str(row.get("ai_action") or "PAPER_SIGNAL"),
        status=str(row.get("status") or "PAPER_INTENT"),
    )


def _movement_position_source_label(
    *,
    broker_ticket: Any,
    price_source: str,
) -> str:
    has_broker_ticket = bool(str(broker_ticket or "").strip())
    if has_broker_ticket:
        if price_source.startswith("provider_snapshot:MT5TerminalMarketDataConnector"):
            return "PAPER_SIM_BROKER_TICKET_MT5_PRICED"
        if price_source.startswith(("provider_snapshot:", "operator_quote_override")):
            return "PAPER_SIM_BROKER_TICKET_PROVIDER_PRICED"
        if price_source.startswith("paper_route_snapshot"):
            return "PAPER_SIM_BROKER_TICKET_STATIC"
        return "PAPER_SIM_BROKER_TICKET"
    if price_source.startswith("provider_snapshot:MT5TerminalMarketDataConnector"):
        return "PAPER_SIM_MT5_PRICED"
    if price_source.startswith("paper_route_snapshot"):
        return "PAPER_SIM_STATIC"
    return "PAPER_SIM_PROVIDER_PRICED"


def _quote_from_position(
    position: PositionMovement,
    timestamp: str,
    snapshot: Any | None = None,
    snapshot_source_name: str | None = None,
) -> MarketMovementQuote:
    unit = price_unit_size(position.symbol)
    if snapshot is not None:
        return _quote_from_snapshot(position, snapshot, timestamp, snapshot_source_name)
    spread_units = 2.0
    half_spread = unit * spread_units / 2.0
    mid = position.current_price
    atr_units = max(
        1.0,
        abs((position.take_profit or mid) - mid) / max(unit, 1e-9) / 3.0,
        abs(mid - (position.stop_loss or mid)) / max(unit, 1e-9) / 3.0,
    )
    candle_low = min(mid, position.stop_loss or mid, position.open_price)
    candle_high = max(mid, position.take_profit or mid, position.open_price)
    return MarketMovementQuote(
        symbol=position.symbol,
        timestamp=timestamp,
        bid=round_price(position.symbol, mid - half_spread),
        ask=round_price(position.symbol, mid + half_spread),
        mid=round_price(position.symbol, mid),
        spread_units=spread_units,
        price_unit_name="point" if unit >= 1 else "pip",
        price_unit_size=unit,
        session="PAPER_DEMO",
        is_market_open=False,
        source="paper_route_snapshot:static_simulation",
        stale=True,
        synthetic_candle={
            "time": timestamp,
            "open": position.open_price,
            "high": round_price(position.symbol, candle_high),
            "low": round_price(position.symbol, candle_low),
            "close": position.current_price,
        },
        atr_units=round(atr_units, 4),
    )



def _mid_prices_from_snapshots(snapshots: Mapping[str, Any]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for symbol, snapshot in snapshots.items():
        try:
            bid = float(getattr(snapshot, "bid"))
            ask = float(getattr(snapshot, "ask"))
            close = getattr(snapshot, "close", None)
            prices[symbol] = float(close) if close is not None else (bid + ask) / 2.0
        except Exception:
            continue
    return prices


def movement_snapshot_age_seconds(
    snapshot: Any,
    *,
    reference_time: datetime | str | None = None,
) -> float | None:
    """Return snapshot age relative to the movement build time."""

    snapshot_time = _coerce_snapshot_datetime(getattr(snapshot, "timestamp", None) if snapshot is not None else None)
    if snapshot_time is None:
        return None
    reference = _coerce_snapshot_datetime(reference_time) or utc_now()
    return max(0.0, (reference - snapshot_time).total_seconds())


def movement_snapshot_usable_for_movement(
    snapshot: Any,
    *,
    reference_time: datetime | str | None = None,
    max_age_seconds: int | float | None = None,
) -> bool:
    """Only fresh real broker/provider snapshots may move rows.

    Fresh after-hours snapshots are allowed for observational repricing, but
    synthetic closed-market fallbacks are not.
    """
    if snapshot is None:
        return False
    try:
        bid = float(getattr(snapshot, "bid"))
        ask = float(getattr(snapshot, "ask"))
    except Exception:
        return False
    if bid <= 0 or ask <= 0:
        return False
    if bool(getattr(snapshot, "synthetic_fallback", False)):
        return False
    age = movement_snapshot_age_seconds(snapshot, reference_time=reference_time)
    if age is None:
        return False
    max_age = float(max_age_seconds or MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS)
    return age <= max_age


def movement_snapshot_issue_for_movement(
    source_name: str,
    snapshot: Any,
    *,
    reference_time: datetime | str | None = None,
    max_age_seconds: int | float | None = None,
) -> str:
    """Explain why a provider/MT5 snapshot cannot price movement rows."""

    if snapshot is None:
        return f"{source_name}: no snapshot returned"
    try:
        bid = float(getattr(snapshot, "bid"))
        ask = float(getattr(snapshot, "ask"))
    except Exception as exc:
        return f"{source_name}: unusable snapshot shape ({type(exc).__name__}: {exc})"
    if bid <= 0 or ask <= 0:
        return f"{source_name}: unusable bid/ask for movement pricing"
    if bool(getattr(snapshot, "synthetic_fallback", False)):
        return f"{source_name}: synthetic fallback snapshot, not a real provider/MT5 price"
    age = movement_snapshot_age_seconds(snapshot, reference_time=reference_time)
    if age is None:
        return f"{source_name}: snapshot timestamp missing or unparseable for movement pricing"
    max_age = float(max_age_seconds or MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS)
    if age > max_age:
        return f"{source_name}: stale snapshot for movement pricing ({age:.0f}s old > {max_age:.0f}s max)"
    return f"{source_name}: snapshot was not accepted for movement pricing"


def movement_snapshot_stale_for_movement(
    snapshot: Any,
    *,
    reference_time: datetime | str | None = None,
    max_age_seconds: int | float | None = None,
) -> bool:
    age = movement_snapshot_age_seconds(snapshot, reference_time=reference_time)
    if age is None:
        return True
    max_age = float(max_age_seconds or MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS)
    return age > max_age


def _snapshot_usable_for_movement(snapshot: Any) -> bool:
    return movement_snapshot_usable_for_movement(snapshot)


def _coerce_snapshot_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return _parse_iso_datetime(value)
    if hasattr(value, "isoformat"):
        return _parse_iso_datetime(str(value.isoformat()))
    return None


def _quote_from_snapshot(
    position: PositionMovement,
    snapshot: Any,
    timestamp: str,
    snapshot_source_name: str | None = None,
) -> MarketMovementQuote:
    unit = price_unit_size(position.symbol)
    bid = float(getattr(snapshot, "bid"))
    ask = float(getattr(snapshot, "ask"))
    mid = (bid + ask) / 2.0
    close = getattr(snapshot, "close", None)
    if close is not None:
        mid = float(close)
    spread_units = float(getattr(snapshot, "spread", (ask - bid) / max(unit, 1e-9)))
    high = getattr(snapshot, "high", None)
    low = getattr(snapshot, "low", None)
    candle_high = max(position.open_price, mid, float(high) if high is not None else mid)
    candle_low = min(position.open_price, mid, float(low) if low is not None else mid)
    atr_units = max(1.0, (candle_high - candle_low) / max(unit, 1e-9))
    source_name = str(snapshot_source_name or snapshot.__class__.__name__ or "MarketSnapshot")
    return MarketMovementQuote(
        symbol=position.symbol,
        timestamp=getattr(snapshot, "timestamp", timestamp).isoformat() if hasattr(getattr(snapshot, "timestamp", None), "isoformat") else str(getattr(snapshot, "timestamp", timestamp)),
        bid=round_price(position.symbol, bid),
        ask=round_price(position.symbol, ask),
        mid=round_price(position.symbol, mid),
        spread_units=round(spread_units, 4),
        price_unit_name="point" if unit >= 1 else "pip",
        price_unit_size=unit,
        session=str(getattr(snapshot, "session", "UNKNOWN")),
        is_market_open=bool(getattr(snapshot, "is_market_open", False)),
        source=f"provider_snapshot:{source_name}",
        stale=False,
        synthetic_candle={
            "time": timestamp,
            "open": position.open_price,
            "high": round_price(position.symbol, candle_high),
            "low": round_price(position.symbol, candle_low),
            "close": round_price(position.symbol, mid),
        },
        atr_units=round(atr_units, 4),
    )


def _nonempty_str(value: Any) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(opened_at: str | None, timestamp: str) -> int | None:
    opened = _parse_iso_datetime(opened_at)
    current = _parse_iso_datetime(timestamp)
    if opened is None or current is None:
        return None
    return max(0, int((current - opened).total_seconds()))


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def friendly_market_data_provider_name(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "provider"
    if text == "YFinanceConnector":
        return "Yahoo"
    if text == "OANDARestConnector":
        return "OANDA"
    if text == "MT5TerminalMarketDataConnector":
        return "MT5 terminal"
    return text


def build_movement_price_source_summary(
    *,
    price_source_status: str,
    market_data_provider_requested: bool,
    configured_market_data_provider: str | None,
    provider_usable_symbols: Sequence[str] | None,
    static_fallback_symbols: Sequence[str] | None,
    mt5_fallback_symbols: Sequence[str] | None,
    closed_market_symbols: Sequence[str] | None = None,
    unsupported_provider_symbols: Sequence[str] | None = None,
    provider_stale_symbols: Sequence[str] | None = None,
    provider_freshness_max_age_seconds: int | float | None = None,
) -> dict[str, Any]:
    provider_symbols = [str(symbol) for symbol in (provider_usable_symbols or []) if str(symbol or "").strip()]
    static_symbols = [str(symbol) for symbol in (static_fallback_symbols or []) if str(symbol or "").strip()]
    mt5_symbols = [str(symbol) for symbol in (mt5_fallback_symbols or []) if str(symbol or "").strip()]
    closed_symbols = [str(symbol) for symbol in (closed_market_symbols or []) if str(symbol or "").strip()]
    unsupported_symbols = [str(symbol) for symbol in (unsupported_provider_symbols or []) if str(symbol or "").strip()]
    stale_symbols = [str(symbol) for symbol in (provider_stale_symbols or []) if str(symbol or "").strip()]
    provider_name = friendly_market_data_provider_name(configured_market_data_provider)
    has_static = bool(static_symbols)
    status = str(price_source_status or "UNKNOWN").strip() or "UNKNOWN"
    freshness_max = int(float(provider_freshness_max_age_seconds or MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS))
    stale_suffix = (
        f" Stale provider/MT5 snapshots rejected for: {', '.join(stale_symbols)} "
        f"(max age {freshness_max}s)."
        if stale_symbols
        else ""
    )

    if status == "CACHE_WARMING":
        return {
            "static_simulation_active": False,
            "price_source_label": "WARMING",
            "price_source_summary": "Movement snapshot is warming; source truth is not ready yet.",
            "price_source_warning": None,
        }

    if status == "PROVIDER_ACTIVE":
        summary = "Provider/MT5-backed movement is repricing paper/demo rows where quotes are usable."
        if unsupported_symbols:
            summary += f" Configured provider {provider_name} does not support: {', '.join(unsupported_symbols)}."
        if mt5_symbols:
            summary += f" MT5 terminal fallback is active for: {', '.join(mt5_symbols)}."
        elif provider_symbols:
            summary += f" Provider-priced symbols: {', '.join(provider_symbols)}."
        if closed_symbols:
            summary += (
                f" Fresh closed-market last prices are being used for: {', '.join(closed_symbols)}; "
                "the venue is closed, so movement is observational until it reopens."
            )
        summary += stale_suffix
        return {
            "static_simulation_active": False,
            "price_source_label": "PROVIDER",
            "price_source_summary": summary,
            "price_source_warning": None,
        }

    if status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
        summary = (
            "Mixed movement source: some paper/demo rows are repriced by provider/MT5 quotes, "
            "but some rows still sit on static simulation fallback."
        )
        if unsupported_symbols:
            summary += f" Configured provider {provider_name} does not support: {', '.join(unsupported_symbols)}."
        if closed_symbols:
            summary += f" Closed-market last prices are still usable for: {', '.join(closed_symbols)}."
        if static_symbols:
            summary += f" Static fallback symbols: {', '.join(static_symbols)}."
        summary += stale_suffix
        return {
            "static_simulation_active": True,
            "price_source_label": "MIXED",
            "price_source_summary": summary,
            "price_source_warning": STATIC_SIMULATION_WARNING,
        }

    if status == "STATIC_SIMULATION_FALLBACK":
        summary = (
            "Static simulation only: paper/demo rows are not being repriced by usable "
            "provider or MT5 quotes right now."
        )
        if not market_data_provider_requested:
            summary += " Provider pricing was not requested for this snapshot."
        elif provider_name:
            summary += f" Requested provider: {provider_name}."
        if unsupported_symbols:
            summary += f" Unsupported on that provider/account: {', '.join(unsupported_symbols)}."
        if static_symbols:
            summary += f" Static fallback symbols: {', '.join(static_symbols)}."
        summary += stale_suffix
        return {
            "static_simulation_active": True,
            "price_source_label": "STATIC SIM",
            "price_source_summary": summary,
            "price_source_warning": STATIC_SIMULATION_WARNING,
        }

    return {
        "static_simulation_active": has_static,
        "price_source_label": status.replace("_", " "),
        "price_source_summary": "Movement source status is available, but no canonical summary was generated.",
        "price_source_warning": STATIC_SIMULATION_WARNING if has_static else None,
    }


def build_movement_position_feed_truth(
    *,
    positions: Sequence[Mapping[str, Any]] | None,
    quotes: Sequence[Mapping[str, Any]] | None,
    price_source_status: str,
    market_data_provider_requested: bool,
    configured_market_data_provider: str | None,
    provider_usable_symbols: Sequence[str] | None,
    static_fallback_symbols: Sequence[str] | None,
    mt5_fallback_symbols: Sequence[str] | None,
    closed_market_symbols: Sequence[str] | None = None,
    closed_market_quote_count: int | None = None,
    unsupported_provider_symbols: Sequence[str] | None = None,
    provider_stale_symbols: Sequence[str] | None = None,
    provider_freshness_max_age_seconds: int | float | None = None,
) -> dict[str, Any]:
    rows = [row for row in (positions or []) if isinstance(row, Mapping)]
    quote_rows = [row for row in (quotes or []) if isinstance(row, Mapping)]
    provider_symbols = [str(symbol) for symbol in (provider_usable_symbols or []) if str(symbol or "").strip()]
    static_symbols = [str(symbol) for symbol in (static_fallback_symbols or []) if str(symbol or "").strip()]
    mt5_symbols = [str(symbol) for symbol in (mt5_fallback_symbols or []) if str(symbol or "").strip()]
    closed_symbols = [str(symbol) for symbol in (closed_market_symbols or []) if str(symbol or "").strip()]
    unsupported_symbols = [str(symbol) for symbol in (unsupported_provider_symbols or []) if str(symbol or "").strip()]
    stale_symbols = [str(symbol) for symbol in (provider_stale_symbols or []) if str(symbol or "").strip()]
    provider_name = friendly_market_data_provider_name(configured_market_data_provider)
    status = str(price_source_status or "UNKNOWN").strip() or "UNKNOWN"
    freshness_max = int(float(provider_freshness_max_age_seconds or MOVEMENT_SNAPSHOT_MAX_AGE_SECONDS))
    total_rows = len(rows)
    broker_ticket_count = sum(
        1 for row in rows if str(row.get("broker_ticket") or "").strip()
    )
    static_position_count = sum(1 for row in rows if _is_static_position_row(row))
    static_quote_count = sum(1 for row in quote_rows if bool(row.get("stale")))
    closed_count = int(closed_market_quote_count or 0)
    executed_simulator_count = sum(
        1 for row in rows if row.get("status") == "PAPER_SIMULATOR_EXECUTED_OPEN"
    )
    durable_simulator_feed = bool(total_rows and executed_simulator_count == total_rows)

    detail = (
        "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
        "Use the MetaTrader 5 connected-account mirror for broker-side positions."
    )
    if durable_simulator_feed:
        detail = (
            "Rows in this snapshot are open positions from the durable internal paper "
            "broker, not approved-only plans and not MT5 broker positions."
        )
        if status == "PROVIDER_ACTIVE":
            detail += " Fresh provider/MT5 quotes are repricing current price and floating P&L."
        elif status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
            detail += " Some positions still use static fallback pricing."
        elif status == "STATIC_SIMULATION_FALLBACK":
            detail += " Current price remains static until a usable provider/MT5 quote arrives."
        if mt5_symbols:
            detail += f" MT5 quote fallback symbols: {', '.join(mt5_symbols)}."
    elif status == "CACHE_WARMING":
        detail = "Movement snapshot is warming; source truth for paper/demo proof rows is not ready yet."
    elif total_rows == 0:
        detail = (
            "This movement snapshot currently reports no paper/demo proof rows. "
            "When rows exist, they remain separate from MT5 broker-truth positions."
        )
    elif status == "STATIC_SIMULATION_FALLBACK":
        detail = (
            "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
            f"Static simulator fallback is active for {static_position_count}/{total_rows} row(s), "
            "so prices and floating P&L can remain at entry until usable provider or MT5 quotes arrive."
        )
        if not market_data_provider_requested:
            detail += " Provider pricing was not requested for this snapshot."
        elif provider_name:
            detail += f" Requested provider: {provider_name}."
        if unsupported_symbols:
            detail += f" That provider/account does not support: {', '.join(unsupported_symbols)}."
        if static_symbols:
            detail += f" Static fallback symbols: {', '.join(static_symbols)}."
    elif status == "MIXED_PROVIDER_AND_STATIC_FALLBACK":
        detail = (
            "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
            f"Provider/MT5 repricing is active, but {static_position_count}/{total_rows} row(s) still sit "
            "on static simulator fallback."
        )
        if closed_symbols:
            detail += (
                f" Fresh closed-market last prices are still usable for {closed_count or len(closed_symbols)}/{max(total_rows, 1)} row(s): "
                f"{', '.join(closed_symbols)}."
            )
        if unsupported_symbols:
            detail += f" Configured provider {provider_name} does not support: {', '.join(unsupported_symbols)}."
        if static_symbols:
            detail += f" Static fallback symbols: {', '.join(static_symbols)}."
    elif status == "PROVIDER_ACTIVE":
        detail = (
            "Rows in this snapshot are paper/demo proof rows, not MT5 broker-truth positions. "
            "Usable provider or MT5 quotes are repricing current prices and floating P&L."
        )
        if closed_symbols:
            detail += (
                f" Market-closed rows: {closed_count or len(closed_symbols)}/{max(total_rows, 1)} are using fresh last-known "
                f"provider/MT5 prices for {', '.join(closed_symbols)} until the venue reopens."
            )
        if unsupported_symbols:
            detail += f" Configured provider {provider_name} does not support: {', '.join(unsupported_symbols)}."
        if mt5_symbols:
            detail += f" MT5 fallback symbols: {', '.join(mt5_symbols)}."
        elif provider_symbols:
            detail += f" Provider-priced symbols: {', '.join(provider_symbols)}."
    if stale_symbols and status != "CACHE_WARMING":
        detail += (
            f" Stale provider/MT5 snapshots were rejected for: {', '.join(stale_symbols)} "
            f"(max age {freshness_max}s)."
        )
    if broker_ticket_count:
        detail += (
            f" Broker-ticket-backed proof rows: {broker_ticket_count}. "
            "Those rows are still part of this proof feed unless the live MT5 terminal verifier is the active source."
        )
    if static_quote_count and status != "CACHE_WARMING":
        detail += f" Static quote rows: {static_quote_count}."

    return {
        "position_feed_title": (
            "Paper Simulator Positions" if durable_simulator_feed else "Simulator Proof Rows"
        ),
        "position_feed_count_label": (
            "Open paper positions" if durable_simulator_feed else "Simulator rows"
        ),
        "position_feed_label": "PAPER SIM" if durable_simulator_feed else "SIM PROOF",
        "position_feed_detail": detail,
        "broker_ticket_position_count": broker_ticket_count,
        "durable_simulator_position_count": executed_simulator_count,
        "static_position_count": static_position_count,
        "static_quote_count": static_quote_count,
    }


def build_movement_source_truth_snapshot(
    movement_source: Mapping[str, Any] | None,
    *,
    telemetry_source: str = "movement_stream",
    telemetry_stale: bool = False,
    telemetry_last_update_iso: str | None = None,
    movement_stream_present: bool = True,
) -> dict[str, Any]:
    payload = movement_source if isinstance(movement_source, Mapping) else {}
    positions = [row for row in (payload.get("positions") or []) if isinstance(row, Mapping)]
    quotes = [row for row in (payload.get("quotes") or []) if isinstance(row, Mapping)]
    source_label_counts: dict[str, int] = {}
    broker_ticket_position_count = 0
    provider_priced_simulator_position_count = 0
    stale_price_position_count = 0
    static_position_count = 0
    for row in positions:
        if str(row.get("broker_ticket") or "").strip():
            broker_ticket_position_count += 1
        source_label = _nonempty_str(row.get("position_source_label"))
        if source_label:
            source_label_counts[source_label] = source_label_counts.get(source_label, 0) + 1
        price_source = str(row.get("price_source") or "")
        if price_source.startswith("provider_snapshot:") or price_source.startswith("operator_quote_override"):
            provider_priced_simulator_position_count += 1
        if bool(row.get("price_stale")):
            stale_price_position_count += 1
        if _is_static_position_row(row):
            static_position_count += 1
    static_quote_count = sum(1 for row in quotes if bool(row.get("stale")))
    closed_market_symbols = [str(symbol) for symbol in (payload.get("closed_market_symbols") or []) if str(symbol or "").strip()]
    unsupported_provider_symbols = [str(symbol) for symbol in (payload.get("unsupported_provider_symbols") or []) if str(symbol or "").strip()]
    price_source_status = _nonempty_str(payload.get("price_source_status"))
    if movement_stream_present and price_source_status == "STATIC_SIMULATION_FALLBACK" and positions:
        static_position_count = max(static_position_count, len(positions))
    detail = (
        _nonempty_str(payload.get("position_feed_detail"))
        or _nonempty_str(payload.get("detail"))
        or (
            "Movement snapshot is warming; source truth is not ready yet."
            if not movement_stream_present
            else "No paper/demo proof rows are currently reported by the movement stream."
        )
    )
    if not movement_stream_present:
        local_detail = detail
    elif static_position_count > 0:
        local_detail = (
            f"{static_position_count} open position row(s) are static or stale simulator telemetry; "
            "floating P&L may remain unchanged until provider/MT5 prices are usable."
        )
    elif positions:
        local_detail = "Open position rows are being repriced by provider or MT5 movement telemetry."
    else:
        local_detail = "No paper/demo proof rows are currently reported by the movement stream."
    provider_errors = payload.get("provider_errors") if isinstance(payload.get("provider_errors"), Mapping) else None
    provider_error_count = int(payload.get("provider_error_count") or 0)
    if provider_error_count <= 0 and isinstance(provider_errors, Mapping):
        provider_error_count = len(provider_errors)
    snapshot_age_seconds = (
        {
            str(symbol): (None if value is None else float(value))
            for symbol, value in payload.get("snapshot_age_seconds_by_symbol", {}).items()
            if str(symbol or "").strip()
        }
        if isinstance(payload.get("snapshot_age_seconds_by_symbol"), Mapping)
        else {}
    )
    return {
        "movement_stream_present": movement_stream_present,
        "telemetry_source": telemetry_source,
        "telemetry_stale": telemetry_stale,
        "telemetry_last_update_iso": telemetry_last_update_iso,
        "market_data_provider_requested": bool(payload.get("market_data_provider_requested")),
        "market_data_provider": _nonempty_str(payload.get("market_data_provider")),
        "price_source_status": price_source_status,
        "price_source_label": _nonempty_str(payload.get("price_source_label")),
        "price_source_summary": _nonempty_str(payload.get("price_source_summary")),
        "price_source_warning": _nonempty_str(payload.get("price_source_warning")),
        "position_feed_title": _nonempty_str(payload.get("position_feed_title")),
        "position_feed_count_label": _nonempty_str(payload.get("position_feed_count_label")),
        "position_feed_label": _nonempty_str(payload.get("position_feed_label")) or ("SIM PROOF" if movement_stream_present else "NONE"),
        "position_feed_detail": detail,
        "static_simulation_active": bool(payload.get("static_simulation_active")) or static_position_count > 0,
        "open_position_count": len(positions),
        "broker_ticket_position_count": broker_ticket_position_count,
        "simulator_position_count": max(0, len(positions) - broker_ticket_position_count),
        "provider_priced_simulator_position_count": provider_priced_simulator_position_count,
        "static_simulator_position_count": static_position_count,
        "stale_price_position_count": stale_price_position_count,
        "static_position_count": static_position_count,
        "static_quote_count": static_quote_count,
        "source_label_counts": source_label_counts,
        "configured_market_data_provider": (
            _nonempty_str(payload.get("configured_market_data_provider"))
            or _nonempty_str(payload.get("market_data_provider"))
        ),
        "provider_usable_symbols": [str(symbol) for symbol in (payload.get("provider_usable_symbols") or []) if str(symbol or "").strip()],
        "static_fallback_symbols": [str(symbol) for symbol in (payload.get("static_fallback_symbols") or []) if str(symbol or "").strip()],
        "mt5_fallback_symbols": [str(symbol) for symbol in (payload.get("mt5_fallback_symbols") or []) if str(symbol or "").strip()],
        "provider_stale_symbols": [str(symbol) for symbol in (payload.get("provider_stale_symbols") or []) if str(symbol or "").strip()],
        "closed_market_symbols": closed_market_symbols,
        "closed_market_quote_count": int(payload.get("closed_market_quote_count") or 0),
        "unsupported_provider_symbols": unsupported_provider_symbols,
        "provider_freshness_max_age_seconds": payload.get("provider_freshness_max_age_seconds"),
        "snapshot_age_seconds_by_symbol": snapshot_age_seconds,
        "provider_error_count": provider_error_count,
        "attention_required": bool(payload.get("attention_required")) or telemetry_stale or static_position_count > 0 or price_source_status == "CACHE_WARMING",
        "detail": detail,
        "local_detail": local_detail,
    }


def _is_static_position_row(row: Mapping[str, Any]) -> bool:
    price_source = str(row.get("price_source") or "")
    return bool(
        row.get("price_stale")
        or price_source.startswith("paper_route_snapshot")
        or row.get("position_source_label") in {"PAPER_SIM_STATIC", "PAPER_SIM_BROKER_TICKET_STATIC"}
    )


def assert_movement_stream_boundary(state: MovementStreamState) -> None:
    if state.live_money_authorized or state.payment_movement_authorized:
        raise ValueError("movement stream cannot authorize live money or payment movement")
    statuses = {
        state.live_trading_status,
        state.broker_accept_status,
        state.auto_deposit_status,
        state.debit_card_bank_movement_status,
        state.payout_automation_status,
    }
    if any(status != NOT_LICENSED for status in statuses):
        raise ValueError("paper/demo movement stream must keep real-money statuses NOT LICENSED")
    if state.trading_edge_status != OPEN:
        raise ValueError("movement stream must preserve trading edge status OPEN")
