"""Backtest Engine — runs historical data through the full CAS Forex pipeline.

Simulates: Market Data → Forecast → CAS Compiler → Auditor → Execution → P&L tracking.
Supports: pure simulation (candles only) and paper trading (MT5 demo).

Tracks: trades, P&L, drawdown, win rate, Sharpe ratio, Evidence Packets.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from cas_forex.config import config
from cas_forex.evidence_store import EvidenceStore
from cas_forex.instruments import (
    pip_value_per_lot,
    price_unit_size,
    round_price,
    usd_notional,
)
from cas_forex.schemas.decision import CASDecision, Verdict
from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.forecast import (
    ForecastProposal,
    Direction,
    ModelSource,
    pip_multiplier,
)
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.schemas.order import BrokerOrderRequest, OrderOutcome, OrderStatus, OrderType
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.schemas.sweep import SweepTransaction, SweepStatus
from cas_forex.time_utils import ensure_utc, utc_now
from cas_forex.verifier.auditor import CASForexAuditor


STANDARD_LOT_UNITS = 100_000


class TradeRecord:
    """Complete record of a single trade through the pipeline."""

    def __init__(
        self,
        proposal: ForecastProposal,
        decision: CASDecision,
        order: Optional[BrokerOrderRequest] = None,
        outcome: Optional[OrderOutcome] = None,
    ):
        self.proposal = proposal
        self.decision = decision
        self.order = order
        self.outcome = outcome
        self.entry_price: float = 0.0
        self.exit_price: float = 0.0
        self.profit_pips: float = 0.0
        self.profit_account: float = 0.0
        self.closed: bool = False
        self.close_time: Optional[datetime] = None
        self.packet: Optional[ForexEvidencePacket] = None

    @property
    def is_winner(self) -> bool:
        return self.profit_pips > 0

    @property
    def direction(self) -> str:
        return self.proposal.direction.value


class BacktestResult:
    """Aggregate statistics from a backtest run."""

    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.starting_balance: float = 0.0
        self.ending_balance: float = 0.0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.suppressed_trades: int = 0
        self.win_rate: float = 0.0
        self.total_profit_pips: float = 0.0
        self.total_profit_account: float = 0.0
        self.max_drawdown_pct: float = 0.0
        self.max_daily_drawdown_pct: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.profit_factor: float = 0.0
        self.avg_winner_pips: float = 0.0
        self.avg_loser_pips: float = 0.0
        self.avg_rr_ratio: float = 0.0
        self.equity_curve: List[float] = []
        self.packet_count: int = 0
        self.evidence_chain_verified: bool = False
        self.evidence_write_failed: bool = False

    def compute(self):
        self.total_trades = len(self.trades)
        self.winning_trades = sum(1 for t in self.trades if t.is_winner)
        self.losing_trades = self.total_trades - self.winning_trades
        self.win_rate = self.winning_trades / max(self.total_trades, 1)
        self.total_profit_pips = sum(t.profit_pips for t in self.trades)
        self.total_profit_account = sum(t.profit_account for t in self.trades)

        winners = [t for t in self.trades if t.is_winner]
        losers = [t for t in self.trades if not t.is_winner]
        self.avg_winner_pips = np.mean([t.profit_pips for t in winners]) if winners else 0
        self.avg_loser_pips = np.mean([t.profit_pips for t in losers]) if losers else 0

        gross_profit = sum(t.profit_pips for t in winners) if winners else 0
        gross_loss = abs(sum(t.profit_pips for t in losers)) if losers else 1
        self.profit_factor = gross_profit / max(gross_loss, 1)

        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / np.array(self.equity_curve[:-1])
            if len(returns) > 1 and returns.std() > 0:
                self.sharpe_ratio = float(returns.mean() / returns.std() * np.sqrt(252))
            peak = np.maximum.accumulate(self.equity_curve)
            dd = (peak - self.equity_curve) / peak * 100
            self.max_drawdown_pct = float(dd.max()) if len(dd) > 0 else 0

    def summary(self) -> dict:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "suppressed_trades": self.suppressed_trades,
            "win_rate": round(self.win_rate, 4),
            "total_profit_pips": round(self.total_profit_pips, 2),
            "total_profit_account": round(self.total_profit_account, 2),
            "avg_winner_pips": round(self.avg_winner_pips, 2),
            "avg_loser_pips": round(self.avg_loser_pips, 2),
            "profit_factor": round(self.profit_factor, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "starting_balance": round(self.starting_balance, 2),
            "ending_balance": round(self.ending_balance, 2),
            "packet_count": self.packet_count,
            "evidence_chain_verified": self.evidence_chain_verified,
            "evidence_write_failed": self.evidence_write_failed,
        }


class BacktestEngine:
    """Runs the full CAS Forex pipeline against historical candle data."""

    def __init__(
        self,
        auditor: Optional[CASForexAuditor] = None,
        initial_balance: float = 10000.0,
        position_size_lots: float = 0.05,
        spread_pips: float = 1.0,
        extra_cost_pips: float = 0.0,
        evidence_store: Optional[EvidenceStore] = None,
        run_id: str = "backtest",
        signal_fn=None,
        signal_model_source: ModelSource = ModelSource.TECHNICAL,
        signal_rationale: str = "external signal",
    ):
        # Optional injected directional signal. When provided, it replaces the
        # built-in SMA trend signal but SL/TP stay ATR-based and identical, so
        # the directional signal is the only variable under comparison.
        self.signal_fn = signal_fn
        self.signal_model_source = signal_model_source
        self.signal_rationale = signal_rationale
        self.auditor = auditor or CASForexAuditor()
        self.initial_balance = initial_balance
        self.position_size = position_size_lots
        self.spread_pips = spread_pips
        # Additional round-trip cost beyond the modeled spread: commission +
        # slippage, expressed in pips. Real all-in majors cost ~1.5-2.5 pips.
        self.extra_cost_pips = extra_cost_pips
        self.evidence_store = evidence_store
        self.run_id = run_id
        self.evidence_write_failed = False
        self.balance = initial_balance
        self.equity = initial_balance
        self.day_start_balance = initial_balance
        self.week_start_balance = initial_balance
        self.current_day: Optional[int] = None
        self.current_week: Optional[int] = None
        self.open_positions: List[TradeRecord] = []
        self.closed_trades: List[TradeRecord] = []
        self.equity_history: List[float] = []
        self.sweep_transactions: List[SweepTransaction] = []
        self.packets: List[ForexEvidencePacket] = []

    def run(
        self,
        candles: List[dict],
        symbol: str = "EUR/USD",
        lot_size_pips: float = 0.10,
        horizon: int = 60,
        warmup_bars: int = 50,
    ) -> BacktestResult:
        """Run backtest over historical candles.

        For each candle after warmup:
          1. Build MarketSnapshot
          2. Build RiskAssessment from current state
          3. Generate ForecastProposal
          4. Run through Auditor (includes compiler gate)
          5. If ACCEPT, simulate execution
          6. Check for closes (stop-loss / take-profit hits)
          7. Track P&L and equity

        Args:
            candles: List of OHLCV dicts with keys: timestamp, open, high, low, close.
            symbol: Forex pair.
            lot_size_pips: Value of 1 pip per lot in account currency.
            horizon: Forecast horizon in minutes.
            warmup_bars: Minimum bars before first trade.
        """
        result = BacktestResult()
        result.starting_balance = self.initial_balance

        for i in range(warmup_bars, len(candles)):
            c = candles[i]
            timestamp = c.get("timestamp")
            dt = self._parse_time(timestamp)
            atr = self._compute_atr(candles[: i + 1])

            # Update day/week tracking
            self._update_period(dt)

            # Build snapshot
            pip_size = price_unit_size(symbol)
            half_spread = self.spread_pips * pip_size / 2.0
            snapshot = MarketSnapshot(
                symbol=symbol,
                timestamp=utc_now(),
                bid=round_price(symbol, c["close"] - half_spread),
                ask=round_price(symbol, c["close"] + half_spread),
                spread=self.spread_pips,
                high=c.get("high", c["close"]),
                low=c.get("low", c["close"]),
                close=c["close"],
                timeframe="M5",
                session=self._detect_session(dt),
                is_market_open=True,
            )

            # Check closes on open positions
            for trade in list(self.open_positions):
                if self._check_close(trade, c):
                    self._close_trade(trade, c, lot_size_pips)

            # Build risk assessment
            risk = self._build_risk_assessment(symbol=symbol, price=c["close"])
            if risk is None:
                continue

            # Build forecast from simple trend detection
            proposal = self._generate_proposal(symbol, candles[: i + 1], horizon, atr)
            if proposal is None:
                continue
            trace_id = proposal.proposal_id
            self._emit_packet(
                PacketStatus.PROPOSED,
                trace_id=trace_id,
                proposal=proposal,
                snapshot=snapshot,
                risk=risk,
            )

            # Run through auditor (5-gate pipeline including compiler)
            decision = self.auditor.evaluate(proposal, snapshot, risk)

            if decision.verdict == Verdict.SUPPRESS:
                result.suppressed_trades += 1
                self._emit_packet(
                    PacketStatus.SUPPRESSED,
                    trace_id=trace_id,
                    proposal=proposal,
                    snapshot=snapshot,
                    risk=risk,
                    decision=decision,
                )
                continue

            if decision.verdict != Verdict.ACCEPT:
                self._emit_packet(
                    PacketStatus.FLAG_FOR_HUMAN_REVIEW,
                    trace_id=trace_id,
                    proposal=proposal,
                    snapshot=snapshot,
                    risk=risk,
                    decision=decision,
                )
                continue
            self._emit_packet(
                PacketStatus.ACCEPTED,
                trace_id=trace_id,
                proposal=proposal,
                snapshot=snapshot,
                risk=risk,
                decision=decision,
            )

            # Build order and simulate execution
            order = self.auditor.build_order(proposal, risk, decision_ref=decision.decision_id)
            outcome = self._simulate_execution(order, c, lot_size_pips)
            self._emit_packet(
                PacketStatus.EXECUTED if outcome.status == OrderStatus.EXECUTED else PacketStatus.REJECTED,
                trace_id=trace_id,
                proposal=proposal,
                snapshot=snapshot,
                risk=risk,
                decision=decision,
                order=order,
                outcome=outcome,
            )

            trade = TradeRecord(proposal, decision, order, outcome)
            trade.entry_price = outcome.filled_price or c["close"]
            self.open_positions.append(trade)

            # Track equity
            self.equity_history.append(self.balance)

        # Close any remaining positions at last price
        last = candles[-1]
        for trade in list(self.open_positions):
            self._close_trade(trade, last, lot_size_pips, forced=True)

        # Finalize
        self.closed_trades.sort(
            key=lambda t: ensure_utc(t.close_time) if t.close_time else ensure_utc(datetime.min)
        )
        result.trades = self.closed_trades
        result.ending_balance = self.balance
        result.equity_curve = self.equity_history
        result.packet_count = len(self.packets)
        result.evidence_write_failed = self.evidence_write_failed
        result.evidence_chain_verified = (
            self.evidence_store.verify_chain()
            if self.evidence_store is not None and not self.evidence_write_failed
            else not self.evidence_write_failed
        )
        result.compute()

        return result

    def _generate_proposal(
        self, symbol: str, candles: List[dict], horizon: int, atr: float,
    ) -> Optional[ForecastProposal]:
        """Generate a trade proposal.

        Uses an injected directional signal (e.g. Chronos) when one was provided
        to the engine; otherwise falls back to the built-in SMA5/20/50 trend
        signal. SL/TP are ATR-based and identical regardless of signal source.
        """
        if len(candles) < 20:
            return None

        closes = [c["close"] for c in candles]
        current = closes[-1]

        sl_mult, tp_mult = 1.5, 2.0  # default ATR stop/target multiples
        if self.signal_fn is not None:
            sig = self.signal_fn(closes)
            if sig is None:
                return None
            # Signal may return (dir, conf) or (dir, conf, sl_mult, tp_mult).
            direction, confidence = sig[0], sig[1]
            if len(sig) >= 4:
                sl_mult, tp_mult = float(sig[2]), float(sig[3])
            model_source = self.signal_model_source
            rationale = self.signal_rationale
        else:
            sma20 = np.mean(closes[-20:])
            sma5 = np.mean(closes[-5:])
            sma50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma20
            if sma5 > sma20 > sma50:
                direction = Direction.LONG
            elif sma5 < sma20 < sma50:
                direction = Direction.SHORT
            else:
                return None
            confidence = min(abs(sma5 - sma20) / current * 500, 0.75)
            model_source = ModelSource.TECHNICAL
            rationale = f"SMA5={sma5:.5f} vs SMA20={sma20:.5f}"

        if confidence < 0.3:
            return None

        if direction == Direction.LONG:
            sl = current - atr * sl_mult
            tp = current + atr * tp_mult
        else:
            sl = current + atr * sl_mult
            tp = current - atr * tp_mult

        # Guard the ForecastProposal SL/TP validators when ATR is degenerate.
        if not (sl > 0 and tp > 0 and sl != current and tp != current):
            return None

        return ForecastProposal(
            proposal_id=str(uuid.uuid4()),
            symbol=symbol,
            direction=direction,
            entry_price=round_price(symbol, current),
            stop_loss=round_price(symbol, sl),
            take_profit=round_price(symbol, tp),
            confidence=round(confidence, 4),
            model_source=model_source,
            horizon_minutes=horizon,
            rationale=rationale,
        )

    def _check_close(self, trade: TradeRecord, candle: dict) -> bool:
        """Check if stop-loss or take-profit is hit."""
        high, low = candle.get("high", 0), candle.get("low", 0)
        if trade.direction == "LONG":
            if low <= trade.proposal.stop_loss:
                trade.exit_price = trade.proposal.stop_loss
                return True
            if high >= trade.proposal.take_profit:
                trade.exit_price = trade.proposal.take_profit
                return True
        else:
            if high >= trade.proposal.stop_loss:
                trade.exit_price = trade.proposal.stop_loss
                return True
            if low <= trade.proposal.take_profit:
                trade.exit_price = trade.proposal.take_profit
                return True
        return False

    def _close_trade(
        self, trade: TradeRecord, candle: dict, lot_pips: float, forced: bool = False,
    ):
        """Close a trade and book P&L."""
        if forced:
            trade.exit_price = candle["close"]
            trade.close_time = self._parse_time(candle.get("timestamp")) or utc_now()
        else:
            trade.close_time = self._parse_time(candle.get("timestamp")) or utc_now()

        # Calculate P&L
        mult = pip_multiplier(trade.proposal.symbol)
        if trade.direction == "LONG":
            trade.profit_pips = (trade.exit_price - trade.entry_price) * mult
        else:
            trade.profit_pips = (trade.entry_price - trade.exit_price) * mult

        # Account for round-trip trading cost: spread + commission + slippage
        trade.profit_pips -= (self.spread_pips + self.extra_cost_pips)
        pip_value = self._pip_value_per_standard_lot(
            trade.proposal.symbol, trade.exit_price or trade.entry_price
        )
        trade.profit_account = trade.profit_pips * pip_value * self.position_size

        self.balance += trade.profit_account
        trade.closed = True
        status = PacketStatus.CLOSED_WIN if trade.profit_account > 0 else PacketStatus.CLOSED_LOSS
        self._emit_packet(
            status,
            trace_id=trade.proposal.proposal_id,
            proposal=trade.proposal,
            decision=trade.decision,
            order=trade.order,
            outcome=trade.outcome,
            close_outcome={
                "exit_price": trade.exit_price,
                "profit_pips": round(trade.profit_pips, 2),
                "profit_account": round(trade.profit_account, 2),
                "forced": forced,
                "closed_at": trade.close_time.isoformat() if trade.close_time else None,
            },
        )

        self.open_positions.remove(trade)
        self.closed_trades.append(trade)

    def _build_risk_assessment(
        self, symbol: Optional[str] = None, price: Optional[float] = None,
    ) -> Optional[RiskAssessment]:
        """Build risk assessment from current account state."""
        # Account blown (balance gone): stop trading. You can't risk what you
        # don't have, and the schema requires balance/equity > 0. This makes the
        # backtest robust when an ungated arm detonates the account.
        if self.balance <= 0:
            return None
        margin_used = sum(
            self._usd_notional(t.proposal.symbol, t.entry_price, self.position_size) * 0.01
            for t in self.open_positions
        )
        margin_free = self.balance - margin_used
        if margin_free <= 0:
            return None

        daily_dd = (
            (self.day_start_balance - self.balance) / self.day_start_balance * 100
            if self.day_start_balance > 0 else 0
        )
        weekly_dd = (
            (self.week_start_balance - self.balance) / self.week_start_balance * 100
            if self.week_start_balance > 0 else 0
        )

        risk_notional = (
            np.mean([
                self._usd_notional(t.proposal.symbol, t.entry_price, self.position_size)
                for t in self.open_positions
            ])
            if self.open_positions
            else self._usd_notional(symbol, price or 1.0, self.position_size)
            if symbol is not None
            else self.position_size * STANDARD_LOT_UNITS
        )
        # Cap at 100%: in deep drawdown the raw notional ratio can exceed the
        # account; the schema bounds this field at 100 and the risk gate only
        # cares that it is over the (much smaller) max_risk_per_trade_pct.
        risk_per_trade = min((risk_notional * 0.005) / max(self.balance, 1) * 100, 100.0)

        return RiskAssessment(
            assessment_id=str(uuid.uuid4()),
            account_balance=self.balance,
            account_equity=self.balance,
            margin_used=margin_used,
            margin_free=margin_free,
            margin_level_pct=(self.balance / max(margin_used, 1) * 100),
            daily_drawdown_pct=daily_dd,
            weekly_drawdown_pct=weekly_dd,
            max_daily_drawdown_pct=config.max_daily_drawdown_pct,
            max_weekly_drawdown_pct=config.max_weekly_drawdown_pct,
            proposed_position_size_lots=self.position_size,
            max_position_size_lots=config.max_position_lots,
            risk_per_trade_pct=risk_per_trade,
            max_risk_per_trade_pct=config.max_risk_per_trade_pct,
            open_positions_count=len(self.open_positions),
            max_open_positions=config.max_open_positions,
            total_exposure_lots=self.position_size * len(self.open_positions),
            max_total_exposure_lots=config.max_total_exposure_lots,
            correlated_exposure_lots=self.position_size * len(self.open_positions),
            max_correlated_exposure_lots=config.max_correlated_exposure_lots,
        )

    def _simulate_execution(
        self, order: BrokerOrderRequest, candle: dict, lot_pips: float,
    ) -> OrderOutcome:
        fill = candle["close"]
        slippage = abs(fill - (order.price or fill)) * pip_multiplier(order.symbol)
        return OrderOutcome(
            order_ref=order.order_id,
            broker_ticket=hash(order.order_id) % 100000000,
            status=OrderStatus.EXECUTED,
            filled_price=fill,
            slippage_pips=round(slippage, 2),
            timestamp=utc_now(),
        )

    def _emit_packet(
        self,
        status: PacketStatus,
        trace_id: str,
        proposal: Optional[ForecastProposal] = None,
        snapshot: Optional[MarketSnapshot] = None,
        risk: Optional[RiskAssessment] = None,
        decision: Optional[CASDecision] = None,
        order: Optional[BrokerOrderRequest] = None,
        outcome: Optional[OrderOutcome] = None,
        close_outcome: Optional[dict] = None,
    ) -> ForexEvidencePacket:
        packet = ForexEvidencePacket(
            packet_id=str(uuid.uuid4()),
            trace_id=trace_id,
            status=status,
            proposal=proposal.model_dump(mode="json") if proposal else None,
            market_snapshot=snapshot.model_dump(mode="json") if snapshot else None,
            cas_decision=decision.model_dump(mode="json") if decision else None,
            risk_assessment=risk.model_dump(mode="json") if risk else None,
            order_request=order.model_dump(mode="json") if order else None,
            order_outcome=outcome.model_dump(mode="json") if outcome else None,
            close_outcome=close_outcome,
            profit_loss_account=close_outcome.get("profit_account") if close_outcome else None,
            profit_loss_pips=close_outcome.get("profit_pips") if close_outcome else None,
        )
        packet.finalize()
        self.packets.append(packet)
        if self.evidence_store is not None:
            try:
                self.evidence_store.append(packet, source="backtest")
            except Exception as exc:
                self.evidence_write_failed = True
                failure_packet = ForexEvidencePacket(
                    packet_id=str(uuid.uuid4()),
                    trace_id=trace_id,
                    status=PacketStatus.WRITE_FAILED,
                    notes=[f"Evidence write failure: {exc}"],
                )
                failure_packet.finalize()
                self.packets.append(failure_packet)
        return packet

    @staticmethod
    def _pip_value_per_standard_lot(symbol: str, price: float) -> float:
        """Approximate USD value of one pip for one standard lot."""
        return pip_value_per_lot(symbol, price)

    @staticmethod
    def _usd_notional(symbol: str, price: float, lots: float) -> float:
        return usd_notional(symbol, price, lots)

    def _update_period(self, dt: Optional[datetime]):
        if dt is None:
            return
        if self.current_day != dt.day:
            self.day_start_balance = self.balance
            self.current_day = dt.day
        week_num = dt.isocalendar()[1]
        if self.current_week != week_num:
            self.week_start_balance = self.balance
            self.current_week = week_num

    @staticmethod
    def _compute_atr(candles: List[dict], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.001
        trs = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return float(np.mean(trs[-period:]))

    @staticmethod
    def _parse_time(ts):
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ensure_utc(ts)
        try:
            return ensure_utc(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
        except Exception:
            return None

    @staticmethod
    def _detect_session(dt: Optional[datetime]) -> str:
        if dt is None:
            return "UNKNOWN"
        h = dt.hour
        if 0 <= h < 8:
            return "ASIAN"
        elif 8 <= h < 13:
            return "LONDON"
        elif 13 <= h < 17:
            return "OVERLAP"
        elif 17 <= h < 22:
            return "NEW_YORK"
        return "ASIAN"
