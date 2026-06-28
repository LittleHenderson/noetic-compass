"""Paper/demo real-time account and market movement snapshots for CAS Forex.

This is the live-readiness bridge after the owner investment ledger: it exposes
the same categories a live cockpit must track (account balance/equity/margin,
open-position P/L, bid/ask/spread, SL/TP distance, tick/candle hints) while the
runtime boundary still prevents real-money execution and payment movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from cas_forex.authority_boundary import NOT_LICENSED, OPEN
from cas_forex.instruments import pip_value_per_lot, price_unit_size, round_price, usd_notional
from cas_forex.time_utils import utc_now

CLAIM_BOUNDARY = (
    "Movement streams are paper/demo telemetry now. They track account/investment "
    "movement and market movement for active paper rows, but they do not place "
    "live orders, create broker ACCEPT, deposit, withdraw, move bank/card funds, "
    "or automate payouts. Live providers may replace the paper/demo sources only "
    "after owner-controlled runtime gates authorize those capabilities."
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
    quote_overrides = {**_mid_prices_from_snapshots(market_snapshots), **(quote_overrides or {})}

    positions = tuple(_position_movement(row, quote_overrides=quote_overrides, leverage=leverage) for row in rows)
    quote_by_symbol = {q.symbol: q for q in (_quote_from_position(pos, ts, market_snapshots.get(pos.symbol)) for pos in positions)}
    quotes = tuple(quote_by_symbol[symbol] for symbol in sorted(quote_by_symbol))
    floating = round(sum(pos.floating_pnl_usd for pos in positions), 2)
    balance = float(summary.get("balance_usd", 0.0) or 0.0)
    margin = round(sum(pos.margin_estimate_usd for pos in positions), 2)
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
    notes = (
        "Account movement is recomputed from paper/demo ledger rows and current paper/provider prices.",
        "Market movement uses configured-provider snapshots when supplied and deterministic paper-route fallback otherwise; broker tick/M1 provider data should replace fallback after provider verification.",
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
    )


def _position_movement(row: Mapping[str, Any], *, quote_overrides: Mapping[str, float], leverage: float) -> PositionMovement:
    symbol = str(row.get("symbol"))
    side = str(row.get("side") or "LONG")
    open_price = float(row.get("open_price", 0.0) or 0.0)
    current_price = float(quote_overrides.get(symbol, row.get("close_or_current_price") or open_price))
    lot_size = float(row.get("lot_size", 0.0) or 0.0)
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
        broker_ticket=row.get("broker_ticket"),
        simulator_ticket=str(row.get("simulator_ticket") or _stable_id("sim", symbol, open_price, lot_size)),
        evidence_packet_id=str(row.get("evidence_packet_id") or "unknown-evidence"),
        ai_action=str(row.get("ai_action") or "PAPER_SIGNAL"),
        status=str(row.get("status") or "PAPER_INTENT"),
    )


def _quote_from_position(position: PositionMovement, timestamp: str, snapshot: Any | None = None) -> MarketMovementQuote:
    unit = price_unit_size(position.symbol)
    if snapshot is not None:
        return _quote_from_snapshot(position, snapshot, timestamp)
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
        source="paper_route_snapshot",
        stale=False,
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


def _quote_from_snapshot(position: PositionMovement, snapshot: Any, timestamp: str) -> MarketMovementQuote:
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
    source_name = snapshot.__class__.__name__
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

def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


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
