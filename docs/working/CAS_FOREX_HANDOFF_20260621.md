# CAS Forex — Engineering Handoff & Outside-Review Brief

**Date:** 2026-06-21
**Prepared for:** external reviewers (Fiverr quant/engineering team) as an outside eye
**Status:** research / backtest only — **live trading is NOT LICENSED**, paper/sim only

---

## 0. TL;DR for the reviewer

CAS Forex is an automated, gated forex-trading system: forecasting strategies propose
trades, a 5-gate "CAS" auditor verifies each one, a simulated/MT5 broker executes, and
every step is recorded in a tamper-evident evidence chain. The **safety/audit machinery
is solid and tested (217 passing tests).** The **trading edge is the open problem.**

We tested many strategies on **real** market data (Yahoo) and found: simple, well-known
strategies on **FX majors** do **not** produce an edge that survives realistic trading
costs. The best result is daily mean-reversion-with-trend-filter at **literal break-even**,
which goes negative at ~2 pips round-trip cost. We have **not** tested the instruments the
owner actually traded profitably in 2020 (NAS30 / indices), nor his own discretionary
entry rules — those are the top untested avenues.

**What we want from you:** an independent audit of (a) the **execution/cost/fill model**
(are our assumptions fair or too harsh?), (b) the **data quality** (Yahoo mid-price vs
broker tick data), (c) whether our **strategy/validation methodology** is sound, and
(d) concrete ideas for an edge — especially on indices and with out-of-sample validation.

---

## 1. Repository & access

- **GitHub:** https://github.com/LittleHenderson/noetic-compass
- **Branch:** `codex/cascompass-legal-live-source`
- **Commit at handoff:** `0275368539ccb5115cd32af08adde6deaf9a4560`
- **Project root in repo:** `cas-forex/`
- **This document:** `docs/working/CAS_FOREX_HANDOFF_20260621.md`
- **Full change log (read this for the play-by-play):** `cas-forex/CHANGELOG.md`

```bash
git clone https://github.com/LittleHenderson/noetic-compass.git
cd noetic-compass
git checkout codex/cascompass-legal-live-source
cd cas-forex
```

## 2. Environment

- **Python 3.14** (Windows; should work on Linux/Mac).
- Dependencies: `numpy`, `pydantic` (v2), `yfinance`, `requests`, `pytest`,
  and for the ML forecaster `torch` (CPU is fine) + `chronos-forecasting`.

```bash
pip install numpy pydantic yfinance requests pytest torch chronos-forecasting
# from cas-forex/:
python -m pytest tests -q          # expect: 217 passed
```

No API keys required for the core work — market data comes from Yahoo Finance
(`yfinance`). OANDA / TimeGPT / MT5 are optional and key-gated.

## 3. How to reproduce every result

All runners live in `cas-forex/scripts/` and write JSON + (some) hash-chained evidence
to `cas-forex/evidence_runs/`. Run from `cas-forex/`.

```bash
# Real-data comparative backtest (one strategy vs ungated vs buy&hold vs no-trade)
python scripts/run_real_backtest.py --model sma      --period 5y --interval 1d
python scripts/run_real_backtest.py --model chronos  --period 5y --interval 1d
python scripts/run_real_backtest.py --model meanrev  --period 5y --interval 1d
python scripts/run_real_backtest.py --model meanrev  --mr-trend-filter --period 5y --interval 1d

# Risk-budget control (all overridable):
python scripts/run_real_backtest.py --model meanrev --mr-trend-filter \
  --starting-balance 3000 --position-lots 0.02 --risk-per-trade-pct 0.5 \
  --max-daily-dd 2 --max-weekly-dd 5 --spread-pips 1.0 --extra-cost-pips 0.5

# Cost sensitivity (find where the edge dies):
python scripts/run_real_backtest.py --model meanrev --mr-trend-filter --extra-cost-pips 1.0

# Strategy x regime simulator (CJT regions + nested lacunarity + RPM routing seed):
python scripts/run_strategy_simulator.py

# Regime detector + switching vs every single strategy (real data):
python scripts/run_switching_backtest.py                       # daily
python scripts/run_switching_backtest.py --er-trend 0.20       # tune the detector
python scripts/run_switching_backtest.py --period 2y --interval 1h   # intraday H1
```

## 4. Architecture (the pipeline)

```
Market Data ─► Forecast/Strategy ─► CAS Auditor (5 gates) ─► Broker ─► Post-Trade ─► Evidence
                                     │
       Gate 0 CAS compiler ─ Gate 1 Risk ─ Gate 2 Macro ─ Gate 3 Market ─ Gate 4 Execution
       (only ACCEPT reaches the broker; SUPPRESS / FLAG_FOR_HUMAN_REVIEW / LIVE_LOCKED otherwise)
```

A trade only executes if it passes **all five gates**. Risk/drawdown breaches and shocks
force `LIVE_LOCKED` (needs signed human unlock). Everything is written to a local
SHA-256 hash-chain (`evidence_store.py`) so tampering/deletion is detectable.

## 5. File map (addresses)

**Core engine & pipeline**
- `cas-forex/cas_forex/backtest/engine.py` — backtest engine; runs candles through the
  full pipeline; pluggable `signal_fn`; ATR stops; cost model; P&L/DD/Sharpe.
- `cas-forex/cas_forex/verifier/auditor.py` — the 5-gate CAS auditor (the decision core).
- `cas-forex/cas_forex/verifier/{risk_gate,macro_gate,market_gate,execution_gate,live_lock}.py`
- `cas-forex/cas_forex/evidence_store.py` — tamper-evident hash-chain.
- `cas-forex/cas_forex/config.py` — all settings (risk budget, broker, sweep, symbols).

**Strategies / forecasting (where the edge would live)**
- `cas-forex/cas_forex/forecast/strategies.py` — mean-reversion (z-fade + trend filter),
  Donchian breakout, composable SMA trend. **No martingale/grid/no-stop modes (by policy).**
- `cas-forex/cas_forex/forecast/chronos_signal.py` — Amazon Chronos-Bolt ML directional signal.
- `cas-forex/cas_forex/forecast/models.py` — TimeGPT (API), TechnicalModel, Chronos stub.
- `cas-forex/cas_forex/forecast/harness.py` — suppresses weak/disagreeing model signals.
- `cas-forex/cas_forex/regime_sim.py` — synthetic regime generator, CJT operating-region
  classifier, nested lacunarity, `detect_regime`, regime-switching signal.
- `cas-forex/cas_forex/mtfa.py` — multi-timeframe analysis (4 trading styles).

**Data / broker / money**
- `cas-forex/cas_forex/market_data/connector.py` — Yahoo (no key) + OANDA connectors.
- `cas-forex/cas_forex/broker/mt5_bridge.py` — MT5 real bridge + simulated bridge; live
  execution gated behind account-boundary acks (NOT LICENSED).
- `cas-forex/cas_forex/sweep/sweeper.py` — profit sweep (reinvest/withdraw split);
  AUTO bank/card transfer is NOT LICENSED.
- `cas-forex/cas_forex/post_trade.py` — broker reconciliation; can trigger LIVE_LOCKED.

**Schemas** — `cas-forex/cas_forex/schemas/*.py` (market, forecast, decision, risk, order,
evidence, sweep, cjt, etc.). Pydantic v2 models; strict validators.

**Runners** — `cas-forex/scripts/run_real_backtest.py`, `run_strategy_simulator.py`,
`run_switching_backtest.py`, plus `run_paper_trading_session.py`.

**Tests** — `cas-forex/tests/` (217 tests). **Plan/spec** —
`docs/working/cas_harness_forex_trading_execution_plan.md`. **UI plan** —
`docs/working/cas_forex_pwa_ui_ux_plan_revised_20260617.md`.

## 6. What we tried, in order, with results

All figures are **real market data** (Yahoo), portfolio = 5 FX majors (EUR/USD, GBP/USD,
USD/JPY, AUD/USD, USD/CAD), $10,000/symbol ($50,000 total), evidence chains verified.
"gated" = through the 5 CAS gates; "raw" = same strategy, gates removed.

| # | Experiment | Setup | Result (portfolio P&L) | Takeaway |
|---|---|---|---|---|
| 1 | Trend SMA | 5y daily, ~1pip cost | gated **-$15,098** (DD 41%) | trend-follow bleeds on majors |
| 2 | Chronos ML | 5y daily | gated **-$15,574** (DD 49%) | advanced model ≈ same loss; edge isn't a model problem |
| 3 | Mean-reversion | 5y daily | **-$523** (DD 6%) | right regime: ~break-even, low DD |
| 4 | Mean-rev + trend filter | 5y daily, 1pip | **+$105.62** (DD 3.5%) | first positive; skip fades vs strong trends |
| 5 | Cost sweep (#4) | vary cost | +$91@1.0p, +$28@1.5p, **-$31@2.0p**, -$95@2.5p | edge dies at realistic cost |
| 6 | Regime simulator | synthetic regimes | lacunarity 0.58; routing seed | each strategy wins only in its regime |
| 7 | Regime switching | 5y daily, 1.5p | SWITCH **-$2,048** vs best single +$3.72 | switching doesn't beat best single |
| 8 | Detector tuning | daily, vary threshold | more trends ⇒ worse (−$7.4k…−$2.0k) | can't tune a daily edge into existence |
| 9 | Intraday switching | 2y **H1**, 1.5p | all lose; best −$4,123; SWITCH −$4,715 | cost drag (≈16× trades) kills intraday |

Small run-to-run variation (±a few hundred $) occurs because the Yahoo "5y/2y" window and
warmup shift slightly between runs; qualitative conclusions are stable.

**Also built (controls the owner asked for):** user-controllable **risk budget**
(per-trade %, daily/weekly DD, max open, lots, starting balance) via CLI/config; a
realistic **cost knob** (spread + commission + slippage in pips); the **CAS-SDG regime
simulator**; **CJT** operating-region tagging; **nested lacunarity** gap map; **RPM**
routing seed.

## 6A. The CAS methodology layer (what makes this more than a textbook bot)

The distinctive part of this project is **not** the individual strategies (those are
standard) — it is the **condition-analysis and strategy-selection framework** layered on
top of them. It is proprietary (part of the owner's "CAS" framework) but maps cleanly onto
standard quant concepts, given here so an outside reviewer can evaluate and extend it.
Code: `cas-forex/cas_forex/regime_sim.py` (+ `cjt_*` modules); runners
`scripts/run_strategy_simulator.py` and `scripts/run_switching_backtest.py`.

- **Regime simulator (CAS-SDG):** generates many synthetic market *conditions* — trend
  up/down, range, high-vol, low-vol, volatility-clustering, shock — and runs every strategy
  across all of them. (Standard-quant analog: a regime-conditional performance matrix /
  Monte-Carlo scenario stress test.)
- **CJT operating regions:** each (strategy × condition) cell is classified into one of four
  *behavioral* states — `cutoff` (signal barely fired), `active` (working as designed),
  `saturation` (overtrading without converting to return), `breakdown` (deep drawdown /
  blow-up) — with a gain (β) estimate. (Analog: behavioral regime classification + a
  risk-adjusted gain metric, i.e. return per unit of drawdown taken.)
- **Nested lacunarity (the gap map):** across the whole matrix, measure where we have **no
  validated positive edge** — and nest it (gaps *within* gaps) across a second axis
  (volatility level). A strategy may "cover" normal vol but be all-gaps at high vol. The
  point is *honesty about coverage*: the system can refuse to trade conditions it has not
  validated rather than over-generalizing from a thin backtest. (Analog: an out-of-sample
  coverage / capability map; an anti-overfitting guardrail.)
- **RPM routing (prerequisite-based switching):** each strategy has *prerequisites* — the
  conditions under which it has edge. Detect the live condition → route to the strategy
  whose prerequisites are met → if **none** qualifies (a lacuna), **sit out**. (Analog: a
  regime-switching / strategy-selection meta-model with an explicit "no-trade" state.)

**How they combine:** simulator measures each strategy's CJT region + return per condition →
nested-lacunarity coverage map → RPM derives "best strategy per condition (or don't trade)"
→ a live detector (`detect_regime`, Kaufman efficiency ratio + vol-vs-baseline + shock
z-score + vol-of-vol) applies that routing bar-by-bar.

**Honest status (important — do not oversell to candidates):** this framework is **built
and works end-to-end**, and it correctly recovers known structure (trend/breakout win
trending regimes; mean-reversion wins ranges; overall lacunarity 0.58 — most
strategy×condition cells are gaps). **But on FX majors it did NOT beat the best single
strategy** (experiments 7–9): the live detector reads daily majors as ~97% "range," and the
trend strategies it would switch to have no edge on majors anyway. The framework's value is
strongest where conditions genuinely vary **and** where several strategies each own a real
regime — which is precisely the case for **stock indices vs ranging FX**, and the main
reason indices are the top recommended test (Section 8).

## 7. The self-audit — "what went wrong?" (honest)

**What is SOLID (not the problem):**
- Real data, verified evidence chains, standard pip/P&L math, 217 passing tests.
- The negative result is **consistent across 9 independent methods** — strong evidence
  it's a true finding for what we tested, not a single bug.
- The cost-break-even (~1.5–2 pips) and "FX majors mean-revert" findings match the
  published literature.

**Genuine LIMITATIONS that an outside eye should scrutinize (could move the answer):**
1. **Strategy universe is textbook-simple** (SMA, z-score fade, Donchian). These are the
   most-arbitraged ideas in retail trading — by design they should have little edge left.
2. **Only FX majors were tested.** We never tested **NAS30 / indices** (which the owner
   actually traded profitably) — indices *trend* far more than majors, so trend/breakout
   strategies that lose here could behave very differently there.
3. **Execution/fill model is idealized.** Fills at candle close; intrabar stop/target
   checked in a fixed order (stop-before-target for longs) which can bias a bar that spans
   both; flat per-trade pip cost; no partial fills, requotes, or liquidity model.
4. **Macro gate is inert in backtests** — it checks wall-clock now, not the candle's
   historical time, so macro intelligence does not actually contribute in backtests.
5. **In-sample, single window, single vendor.** No walk-forward / out-of-sample; one data
   source (Yahoo mid-price, not broker bid/ask tick data; volume often 0; weekend quirks).
6. **Chronos used naively** (single last-step point forecast → direction; not quantiles,
   multi-horizon, regime-conditioned, or fine-tuned).
7. **One-size-fits-all ATR stops; fixed-lot sizing.** No trailing/partial/time exits, no
   vol-targeting or Kelly sizing, no per-instrument tuning.
8. **Leverage is not modeled in P&L** (it affects margin/ruin, not per-trade P&L in our
   model), so 1:100 account dynamics have not actually been simulated.
9. **Regime routing came from synthetic data**, not fitted to real data — a hypothesis,
   not a trained model.

**Honest verdict:** nothing is "broken." The build is sound and the negative result is
**true but narrow** — we rigorously proved that *simple mechanical strategies on FX majors
don't clear realistic costs*. That is **not** the same as proving "no edge exists." The
biggest gap is **scope**: we never tested the owner's actual market (indices) or his own
rules. The two methodology points most worth your scrutiny are the **cost/fill model** and
**data quality** — if either is too pessimistic, the break-even threshold shifts.

## 8. Open questions / where to point the review

1. **Indices (NAS30/US30/SPX35) + commodities (XAU/USD):** wire them into the same harness
   and run trend/breakout. Indices trend; this is the top untested avenue. (Note: our pip
   math in `schemas/forecast.py::pip_multiplier` is FX-specific — indices need a contract/
   point-value model. This is a required code change, flagged for you.)
2. **Owner's 2020 discretionary rules:** encode his actual NAS30/GBP-USD entry/exit logic
   and test it — the one input we never had.
3. **Cost & fill realism:** replace the flat pip cost with broker-specific spread +
   commission + modeled slippage; validate against real Hugo's Way spreads.
4. **Data quality:** swap Yahoo for broker tick/m1 data (Dukascopy, broker export) and
   re-run; check whether mid-price vs bid/ask changes the cost picture.
5. **Out-of-sample / walk-forward:** none done yet. Build a proper train/validate/test split.
6. **Session scalper (ForexFury-style) with a real stop:** never built; test on intraday.
7. **Position sizing / risk model:** vol-targeting or fractional-Kelly on top of any edge.

## 9. Hard boundaries (do not cross without separate review)

- **Live trading = NOT LICENSED.** `live_mode=False`, `paper_trading=True`. Live execution
  is blocked in `broker/mt5_bridge.py` behind account-boundary acknowledgments.
- **AUTO bank/card transfer = NOT LICENSED** (`sweep/sweeper.py`). DRY_RUN / MANUAL only.
- **No martingale, grid-averaging, or no-stop-loss modes.** Every strategy must have a hard
  stop. (These are the patterns that show fake high win-rates and then blow up accounts.)
- Backtest results are **research signals, not promotions.** `report.passed=True` means a
  positive in-sample signal, **not** a validated, deployable, or licensed strategy.

## 10. Contact / ownership

- Owner: Little Henderson (a.k.a. Wakil). Project: Noetic Compass / CAS ecosystem.
- The full session play-by-play (every experiment, every number, every commit) is in
  `cas-forex/CHANGELOG.md` — newest entries at the top.
```
