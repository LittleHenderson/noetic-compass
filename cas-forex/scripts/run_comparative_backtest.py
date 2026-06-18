"""Offline comparative backtest runner for CAS Forex proof collection.

This runner is deterministic by default. It produces a BacktestEvidenceReport
and local hash-chain evidence, but it does not claim broker-grade 12-month proof
until real historical data is supplied and the evidence chain is preserved.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.backtest.engine import BacktestEngine
from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.evidence import BacktestEvidenceReport
from cas_forex.time_utils import utc_now


SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]
VARIANTS = [
    "raw_model",
    "cas_gated",
    "last_price",
    "moving_average",
    "breakout",
    "volatility_filter",
    "no_trade",
]


def generate_candles(symbol: str, bars: int = 360) -> List[dict]:
    base = 145.0 if symbol == "USD/JPY" else 1.10
    drift = 0.006 if symbol != "USD/CAD" else -0.004
    candles = []
    start = datetime(2026, 1, 1, 0, 0)
    for i in range(bars):
        wave = math.sin(i / 11.0) * (0.12 if symbol == "USD/JPY" else 0.0012)
        trend = drift * (i / max(bars, 1))
        close = base + wave + trend
        span = 0.08 if symbol == "USD/JPY" else 0.0008
        candles.append({
            "timestamp": (start + timedelta(minutes=5 * i)).isoformat(),
            "open": close - span / 4,
            "high": close + span,
            "low": close - span,
            "close": close,
            "volume": 1000 + i,
        })
    return candles


def baseline_metrics(candles: List[dict], variant: str) -> Dict[str, float]:
    if variant == "no_trade":
        return {"total_trades": 0, "total_profit_pips": 0.0, "win_rate": 0.0}
    closes = [c["close"] for c in candles]
    if len(closes) < 2:
        return {"total_trades": 0, "total_profit_pips": 0.0, "win_rate": 0.0}
    moves = [b - a for a, b in zip(closes, closes[1:])]
    winners = sum(1 for move in moves if move > 0)
    score = sum(moves)
    if variant == "moving_average":
        score *= 0.6
    elif variant == "breakout":
        score *= 0.8
    elif variant == "volatility_filter":
        score *= 0.4
    return {
        "total_trades": len(moves),
        "total_profit_pips": round(score * 10000, 2),
        "win_rate": round(winners / len(moves), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--bars", type=int, default=360)
    parser.add_argument("--output-dir", default="evidence_runs/comparative_backtest")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"comparative-{utc_now().strftime('%Y%m%d%H%M%S')}"
    report = BacktestEvidenceReport(
        report_id=f"report-{run_id}",
        run_id=run_id,
        symbols=SYMBOLS,
        variants=VARIANTS,
    )

    for symbol in SYMBOLS:
        candles = generate_candles(symbol, args.bars)
        store = EvidenceStore(out_dir / f"{run_id}-{symbol.replace('/', '')}.jsonl", run_id=run_id)
        engine = BacktestEngine(evidence_store=store, run_id=run_id)
        result = engine.run(candles, symbol=symbol, warmup_bars=min(60, max(20, args.bars // 4)))
        report.metrics_by_symbol[symbol] = result.summary()
        report.packet_count += result.packet_count
        report.chain_verified = report.chain_verified or result.evidence_chain_verified
        report.variant_metrics[f"{symbol}:cas_gated"] = result.summary()
        report.variant_metrics[f"{symbol}:raw_model"] = baseline_metrics(candles, "raw_model")
        for variant in VARIANTS[2:]:
            report.variant_metrics[f"{symbol}:{variant}"] = baseline_metrics(candles, variant)

    report.completed_at = utc_now()
    report.passed = False
    report.failure_reasons.append(
        "Synthetic generated candles verify runner mechanics only; this is not broker-grade 12-month evidence."
    )
    if args.months < 12:
        report.failure_reasons.append("Runner invoked with less than 12 months.")
    if not report.chain_verified:
        report.failure_reasons.append("Evidence chain did not verify.")

    report_path = out_dir / f"{run_id}-report.json"
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), **report.model_dump(mode="json")}, indent=2))
    return 0 if report.chain_verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
