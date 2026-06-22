"""Real-data comparative backtest for CAS Forex.

Pulls REAL historical daily candles from Yahoo Finance (no API key, no GPU) and
runs the full CAS Forex pipeline so we can answer the only question that matters:
is there any edge, and does the CAS gating layer help or hurt?

Three honest comparisons per symbol:
  - cas_gated : the engine's SMA proposals run through the full 5-gate auditor.
  - raw_model : the SAME SMA proposals with the CAS gates removed (pass-through
                auditor that ACCEPTs everything). Isolates what CAS gating adds.
  - buy_hold  : underlying price return, long, unleveraged (did we beat holding?).
  - no_trade  : zero (did we beat doing nothing?).

This writes a real BacktestEvidenceReport plus a verifiable local hash-chain.

Honesty boundaries (do not overstate):
  - In-sample, single strategy (SMA5/20/50), daily bars, ONE data vendor (Yahoo).
  - The macro gate is evaluated at wall-clock now, not at historical event times,
    so macro blackouts are effectively inert in this run (known follow-up).
  - A positive result here is a RESEARCH SIGNAL to continue, NOT a license to
    trade live. Live trading remains NOT LICENSED.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.backtest.engine import BacktestEngine, BacktestResult
from cas_forex.evidence_store import EvidenceStore
from cas_forex.schemas.decision import CASDecision, Verdict
from cas_forex.schemas.evidence import BacktestEvidenceReport
from cas_forex.schemas.forecast import ModelSource, pip_multiplier
from cas_forex.time_utils import utc_now
from cas_forex.verifier.auditor import CASForexAuditor


SYMBOLS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"]


class PassThroughAuditor(CASForexAuditor):
    """Auditor with the CAS gates removed: every proposal is ACCEPTed.

    Used to build the `raw_model` arm so we can measure exactly what the CAS
    gating layer changes versus the same model with no gates at all.
    """

    def evaluate(self, proposal, snapshot, risk, current_price=None, forecast_report=None) -> CASDecision:
        return CASDecision(
            decision_id=str(uuid.uuid4()),
            proposal_ref=proposal.proposal_id,
            symbol=proposal.symbol,
            verdict=Verdict.ACCEPT,
            gate_results=[],
            summary="RAW (ungated): proposal accepted with no CAS gates",
        )


def fetch_real_candles(symbol: str, period: str, interval: str) -> List[dict]:
    """Fetch real OHLCV candles from Yahoo Finance for a forex pair."""
    import yfinance as yf

    ticker_str = f"{symbol.replace('/', '')}=X"
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return []
    candles: List[dict] = []
    for idx, row in df.iterrows():
        close = float(row["Close"])
        if close <= 0:
            continue
        candles.append({
            "timestamp": idx.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": close,
            "volume": int(row.get("Volume", 0) or 0),
        })
    return candles


def buy_hold_metrics(candles: List[dict], symbol: str) -> Dict[str, float]:
    """Underlying long buy-and-hold over the window (unleveraged, no sizing)."""
    if len(candles) < 2:
        return {"return_pct": 0.0, "profit_pips": 0.0, "bars": len(candles)}
    first = candles[0]["close"]
    last = candles[-1]["close"]
    return {
        "return_pct": round((last / first - 1.0) * 100, 4),
        "profit_pips": round((last - first) * pip_multiplier(symbol), 2),
        "bars": len(candles),
    }


def run_variant(candles: List[dict], symbol: str, store: Optional[EvidenceStore],
                run_id: str, gated: bool, signal_fn=None,
                model_source: ModelSource = ModelSource.TECHNICAL) -> BacktestResult:
    auditor = CASForexAuditor() if gated else PassThroughAuditor()
    engine = BacktestEngine(
        auditor=auditor, evidence_store=store, run_id=run_id,
        signal_fn=signal_fn, signal_model_source=model_source,
        signal_rationale=f"{model_source.value} next-step directional forecast",
    )
    warmup = min(60, max(50, len(candles) // 10))
    return engine.run(candles, symbol=symbol, warmup_bars=warmup)


def account_return_pct(result: BacktestResult) -> float:
    if result.starting_balance <= 0:
        return 0.0
    return round((result.ending_balance - result.starting_balance) / result.starting_balance * 100, 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="5y", help="yfinance period (1y, 2y, 5y, 10y, max)")
    parser.add_argument("--interval", default="1d", help="yfinance interval (1d recommended for multi-year)")
    parser.add_argument("--symbols", nargs="*", default=SYMBOLS)
    parser.add_argument("--output-dir", default="evidence_runs/real_backtest")
    parser.add_argument("--model", default="sma", choices=["sma", "chronos"],
                        help="directional signal: built-in SMA or Chronos-Bolt")
    parser.add_argument("--chronos-model", default="amazon/chronos-bolt-tiny")
    parser.add_argument("--min-move-bps", type=float, default=2.0,
                        help="Chronos: ignore predicted moves smaller than this (bps)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"real-{args.model}-{utc_now().strftime('%Y%m%d%H%M%S')}"

    signal_fn = None
    model_source = ModelSource.TECHNICAL
    if args.model == "chronos":
        from cas_forex.forecast.chronos_signal import make_chronos_signal_fn
        print(f"[chronos] loading {args.chronos_model} (one-time) ...", flush=True)
        signal_fn = make_chronos_signal_fn(
            model_id=args.chronos_model, min_move_bps=args.min_move_bps,
        )
        model_source = ModelSource.CHRONOS
        print("[chronos] ready", flush=True)

    report = BacktestEvidenceReport(
        report_id=f"report-{run_id}",
        run_id=run_id,
        symbols=list(args.symbols),
        variants=["cas_gated", "raw_model", "buy_hold", "no_trade"],
    )

    rows: List[dict] = []
    chain_ok = True
    any_data = False

    for symbol in args.symbols:
        print(f"[fetch] {symbol} period={args.period} interval={args.interval} ...", flush=True)
        try:
            candles = fetch_real_candles(symbol, args.period, args.interval)
        except Exception as exc:  # network / parsing
            print(f"  ! fetch failed: {exc}", flush=True)
            report.failure_reasons.append(f"{symbol}: fetch failed: {exc}")
            continue

        if len(candles) < 80:
            print(f"  ! only {len(candles)} bars returned; skipping (need >=80)", flush=True)
            report.failure_reasons.append(f"{symbol}: insufficient real bars ({len(candles)})")
            continue

        any_data = True
        first_ts = candles[0]["timestamp"][:10]
        last_ts = candles[-1]["timestamp"][:10]
        print(f"  {len(candles)} real bars {first_ts} -> {last_ts}", flush=True)

        gated_store = EvidenceStore(out_dir / f"{run_id}-{symbol.replace('/', '')}-gated.jsonl", run_id=run_id)
        gated = run_variant(candles, symbol, gated_store, run_id, gated=True,
                            signal_fn=signal_fn, model_source=model_source)
        raw = run_variant(candles, symbol, None, run_id, gated=False,
                          signal_fn=signal_fn, model_source=model_source)
        bh = buy_hold_metrics(candles, symbol)

        chain_ok = chain_ok and gated.evidence_chain_verified
        report.packet_count += gated.packet_count

        gated_sum = gated.summary()
        raw_sum = raw.summary()
        report.metrics_by_symbol[symbol] = {
            "bars": len(candles),
            "first": first_ts,
            "last": last_ts,
            "cas_gated": gated_sum,
            "raw_model": raw_sum,
            "buy_hold": bh,
        }
        report.variant_metrics[f"{symbol}:cas_gated"] = gated_sum
        report.variant_metrics[f"{symbol}:raw_model"] = raw_sum
        report.variant_metrics[f"{symbol}:buy_hold"] = bh
        report.variant_metrics[f"{symbol}:no_trade"] = {"total_profit_account": 0.0, "return_pct": 0.0}

        rows.append({
            "symbol": symbol,
            "gated_ret": account_return_pct(gated),
            "raw_ret": account_return_pct(raw),
            "bh_ret": bh["return_pct"],
            "gated_trades": gated_sum["total_trades"],
            "gated_suppressed": gated_sum["suppressed_trades"],
            "raw_trades": raw_sum["total_trades"],
            "gated_dd": gated_sum["max_drawdown_pct"],
            "raw_dd": raw_sum["max_drawdown_pct"],
            "gated_pf": gated_sum["profit_factor"],
            "raw_pf": raw_sum["profit_factor"],
            "gated_pnl": gated_sum["total_profit_account"],
            "raw_pnl": raw_sum["total_profit_account"],
        })

    # ---- Portfolio aggregate ----
    port = {
        "gated_pnl": round(sum(r["gated_pnl"] for r in rows), 2),
        "raw_pnl": round(sum(r["raw_pnl"] for r in rows), 2),
        "gated_trades": sum(r["gated_trades"] for r in rows),
        "raw_trades": sum(r["raw_trades"] for r in rows),
        "gated_suppressed": sum(r["gated_suppressed"] for r in rows),
        "gated_dd_avg": round(sum(r["gated_dd"] for r in rows) / max(len(rows), 1), 2),
        "raw_dd_avg": round(sum(r["raw_dd"] for r in rows) / max(len(rows), 1), 2),
    }

    # ---- Honest research-signal criterion (NOT a license) ----
    edge_vs_no_trade = port["gated_pnl"] > 0
    cas_beats_raw_pnl = port["gated_pnl"] > port["raw_pnl"]
    cas_lowers_dd = port["gated_dd_avg"] < port["raw_dd_avg"]
    cas_helps = cas_beats_raw_pnl or cas_lowers_dd

    report.chain_verified = chain_ok and any_data
    report.completed_at = utc_now()
    # `passed` here means: real data, chain verified, positive edge, and CAS gating
    # helped (more P&L or less drawdown) vs the ungated arm. It is a research
    # signal to continue, explicitly NOT a promotion or a license to trade live.
    report.passed = bool(report.chain_verified and edge_vs_no_trade and cas_helps)
    if not any_data:
        report.failure_reasons.append("No real data fetched for any symbol (network?).")
    if not edge_vs_no_trade:
        report.failure_reasons.append("CAS-gated portfolio P&L did not beat no-trade (<= 0).")
    if not cas_helps:
        report.failure_reasons.append("CAS gating did not improve P&L or drawdown vs ungated raw model.")
    if not report.chain_verified:
        report.failure_reasons.append("Evidence chain did not verify.")
    report.failure_reasons.append(
        "Research signal only: in-sample, single SMA strategy, daily bars, one vendor (Yahoo). "
        "Live trading remains NOT LICENSED."
    )

    report_path = out_dir / f"{run_id}-report.json"
    report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")

    # ---- Human-readable table ----
    print("\n" + "=" * 78)
    print(f"CAS FOREX REAL-DATA BACKTEST  model={args.model}  run_id={run_id}")
    print("=" * 78)
    hdr = f"{'symbol':9} {'gated%':>8} {'raw%':>8} {'b&h%':>8} {'gTr':>4} {'gSup':>5} {'rTr':>4} {'gDD%':>6} {'rDD%':>6}"
    print(hdr)
    print("-" * 78)
    for r in rows:
        print(f"{r['symbol']:9} {r['gated_ret']:>8.2f} {r['raw_ret']:>8.2f} {r['bh_ret']:>8.2f} "
              f"{r['gated_trades']:>4} {r['gated_suppressed']:>5} {r['raw_trades']:>4} "
              f"{r['gated_dd']:>6.2f} {r['raw_dd']:>6.2f}")
    print("-" * 78)
    print(f"PORTFOLIO  gated P&L ${port['gated_pnl']:>10}  raw P&L ${port['raw_pnl']:>10}  "
          f"(start $10,000/symbol)")
    print(f"           gated trades {port['gated_trades']} (suppressed {port['gated_suppressed']})  "
          f"raw trades {port['raw_trades']}")
    print(f"           avg max DD: gated {port['gated_dd_avg']}%  raw {port['raw_dd_avg']}%")
    print("-" * 78)
    print(f"chain_verified : {report.chain_verified}")
    print(f"edge_vs_no_trade (gated P&L > 0)        : {edge_vs_no_trade}")
    print(f"cas_beats_raw_pnl                       : {cas_beats_raw_pnl}")
    print(f"cas_lowers_drawdown                     : {cas_lowers_dd}")
    print(f"report.passed (RESEARCH SIGNAL, not a license) : {report.passed}")
    print(f"\nreport written: {report_path}")
    print("NOTE: live trading remains NOT LICENSED regardless of this result.")
    return 0 if any_data else 1


if __name__ == "__main__":
    raise SystemExit(main())
