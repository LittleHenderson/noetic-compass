# Forex Algo Review & Strategy Build — Project Brief (1-page)

## What this is
We have a working, well-tested **automated forex backtesting system** (Python). It pulls
real market data, runs trading strategies through a safety/risk-check pipeline, simulates
execution, and records a tamper-evident audit trail of every decision. The plumbing is
done and solid (217 automated tests pass). **We need an experienced quant/algo-trading
developer as an outside eye** to pressure-test our results and help us find a real,
cost-surviving trading edge.

## What we've already built and tested
- A full backtest engine + 5-stage risk/verification pipeline + evidence logging.
- Several strategies: trend-following (moving averages), breakout, mean-reversion, and an
  ML forecaster (Amazon Chronos).
- A **proprietary condition-analysis framework** (the owner's "CAS" method): it simulates
  many market conditions, maps which strategy works in which condition, **flags where we
  have no validated edge** (so the system can refuse to trade conditions it hasn't proven),
  and auto-switches strategy by detected condition. In standard terms: a regime-conditional
  performance matrix + an out-of-sample coverage map + a regime-switching selector.
- User-controllable risk budget (risk per trade, daily/weekly drawdown caps, position
  size) and a realistic trading-cost model (spread + commission + slippage).
- Tested on 5 years of real daily data and 2 years of hourly data across 5 major FX pairs.

## What we found (and need verified)
Across every strategy we tried, **simple strategies on major FX pairs did not beat
realistic trading costs** — the best was roughly break-even, going negative once normal
spread/commission is applied. We believe this is a *true result for what we tested*, but
we tested a narrow slice. We have **not** tested stock indices (e.g., NAS100/US30), which
trend much more strongly, nor a few key methodology choices.

## What we need you to do
1. **Audit our methodology** — especially our trading-cost and order-fill assumptions and
   our data quality (we use Yahoo Finance mid-prices; is that good enough, or do we need
   broker tick data?). Tell us if our results are fair or pessimistic.
2. **Port the system to stock indices** (NAS100/US30) and gold, and run trend/breakout
   strategies there. (Our position-value math is currently FX-specific and needs extending
   — flagged in the technical brief.)
3. **Add proper out-of-sample / walk-forward validation** (we've only done in-sample).
4. **Propose and backtest 1–2 strategy ideas** you believe have a genuine, cost-surviving
   edge, with honest results.

## Required skills
- Algorithmic / quantitative trading experience (real backtesting, not just indicators).
- Strong Python (numpy, pandas/pydantic). Comfortable reading an existing codebase.
- Understands transaction costs, slippage, overfitting, and out-of-sample validation.
- Forex **and** index/CFD trading knowledge a big plus.

## Deliverables
- A written review of our methodology (what's sound, what's flawed, what to fix).
- Working code to test indices + an out-of-sample validation harness.
- Backtested results for any proposed strategies, with honest, cost-included numbers.

## What we provide
- Full GitHub repo access + a detailed technical brief (setup, how to run everything,
  every experiment we ran with results, and a file-by-file map).
- Clear, documented code and a complete change log.

## Important notes (please read)
- This is **research/backtesting only**. The system is **not** connected to live money,
  and this job does **not** involve trading real money or handling funds.
- We do **not** want martingale, grid, or no-stop-loss "systems" — they show fake high
  win-rates and blow up accounts. Every strategy must use a hard stop loss.
- Honesty over hype: we want real, cost-included, out-of-sample numbers — not curve-fitted
  backtests. A clear "this doesn't work and here's why" is valuable to us.

*Full technical brief available on request: `docs/working/CAS_FOREX_HANDOFF_20260621.md`.*
