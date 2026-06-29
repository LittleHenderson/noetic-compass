# CAS Forex — Regime-Switching Edge: honest out-of-sample finding (2026-06-28)

## Verdict: NO EDGE

A leak-free, out-of-sample test of regime-switching on 5 years of real daily data
(US30, NAS100, EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD; 40 OOS windows, ~736
trades) shows **no demonstrable edge** from detecting the market regime and
switching strategies. Verdict: **NO_EDGE at every cost (1.0 / 2.0 / 3.0 points).**

| metric (cost sweep, 40 OOS windows) | 1.0p | 2.0p | 3.0p |
|---|---|---|---|
| SWITCH total OOS return | −2.7% | −2.7% | −2.7% |
| best single (chosen on train) | −6.1% | −6.2% | −6.2% |
| **random-routing null** | **−1.2%** | **−1.2%** | **−1.2%** |
| SWITCH beats the null, per window | **0%** | **0%** | **0%** |
| SWITCH positive-window rate | 20% | 20% | 20% |

**The core finding (robust): SWITCH never beats a random assignment of strategies
to regimes** — 0% of windows across all costs. The regime detector and its routing
add no value over chance.

A second, separate run on a *refetched* copy of the same "5y daily" data printed
SWITCH **+40%** (vs null +42%, still beaten in 98% of windows). The total return
flipping sign just from re-fetching the data is itself a no-edge signal — a real
edge is stable to a few bars of noise; this number is pure beta/path-noise. The
SWITCH-vs-null skill comparison, by contrast, is null-or-worse in every run. (For
a publishable claim the data must be frozen once; the verdict does not change.)

## Why this is the right answer, not a failure

The prior switching backtest (`run_switching_backtest.py`) and the walk-forward
harness both **leaked**: routing was hand-set from a synthetic sim and applied
in-sample, and the walk-forward labeled each test window's regime from the *whole
future* test segment. Those leaks make a fake edge look real. This test fixes all
of that:

- **Routing learned on train only** (`learn_routing_on_train`) — per-regime best
  strategy from a train grid, kept only if net-positive after cost.
- **Per-bar causal switch** drives the held-out test window; trades begin only in
  the test window and only ever see trailing closes.
- **Realistic cost** (2.0 points all-in; 1 pip = 1 index point for CFDs).
- **Random-routing null** + best-single + buy-hold baselines, so a positive return
  must beat *chance*, not just no-trade.

A measurement that says "no edge" honestly is worth more than one that says "edge"
by leaking. The 30-day paper-proof bar (net-positive after cost) would correctly
**fail** this strategy.

## The real bottleneck (where an edge could actually come from)

Every strategy in the menu is a fixed-threshold *rule* — it classifies the recent
past, it does not **forecast**. Switching only reallocates which edgeless rule
fires; it cannot manufacture forecast skill. The forecaster slot
(`forecast/models.py` Chronos/TimesFM) is an unwired stub. The honest path to a
real edge is:

1. Populate the forecaster with something that has **measurable next-bar directional
   skill out-of-sample** (calibrated, beats a no-skill baseline), then
2. let the regime layer gate *when to trust it* — not pick among rules that have no
   skill to begin with.

Until a component clears step 1 on broker-grade data, there is no edge to deploy,
and the NOT LICENSED / paper-only boundaries stay.

## Nested-lacunarity bias-state map (multi-timeframe, 2026-06-28)

The bias-state slider ("how well you know the 28 cells"), **measured** instead of
guessed, via `cas_forex/nested_lacunarity.py` on real data (US30 + EUR/USD, **H1
and D1**, all regimes), each cell decided by the unchanged leak-free OOS null:

> **BIAS-STATE: ALL_GAPS — 28 cells, 28 gaps, 0 non-gaps. Gap fraction 1.0000 at
> both H1 and D1. Fractal-coherent cells: 0.**

H1 was untested territory (finer bars, ~3.5k–12k of them, many more regime
transitions). It made no difference: no cell at any timeframe, symbol, or regime
clears the null. Multi-timeframe did not surface hidden edge — it confirmed the
no-edge result more robustly, across scales. The measured bias-state for price-only
signals is **≈ 0 everywhere**. In recipe terms: `Θ(Ω_profit) = a·price +
b·NEW_INFORMATION → profit` has its limiting reagent (NEW_INFORMATION) at ~0, so
theoretical yield is ~0 across all 28 cells — exactly what the map shows.

The discipline frame is built and verified (`cas_forex/cascade_forecast.py` +
`nested_lacunarity.py`, suite green 1212): it will trust, size, and route a *real*
signal honestly — but it confirms there is no price-only signal to route. The only
path to a non-zero bias-state is new information.

## Intraday macro-surprise — the last open door, now CLOSED (2026-06-28)

The daily macro test left one door: the real reaction happens in minutes, not days.
Tested it properly via `cas_forex/macro_intraday.py` + `scripts/run_macro_intraday_real.py`
on **real HistData M1 EUR/USD (5 years, 1.8M bars, 2020–2024)** + the Forex Factory
calendar, measuring the move **0–30 min after each release** at a news-realistic 2-pip
cost, through the same shuffled-surprise null.

> **PRIMARY (pre-registered) verdict: NO_SKILL.** 535 usable surprises, 214 test
> events, hit rate **0.509** (coin flip), net **−3.74%** (negative after cost), and
> the real signal is *worse* than the shuffled null's p95 (−1.31%). All four secondary
> windows (0–30/1pip, 0–30/3pip, 0–15/2pip, 5–30/2pip) agree: NO_SKILL. No single
> indicator rescues it (per-indicator raw hits cluster at ~0.50, mixed-sign means).

The faint *daily* tilt did **not** survive at the resolution where macro moves happen —
it went negative. And the test was generous (HistData M1 is interbank-ish, *tighter*
than retail; real news spreads blow out far wider, so a retail result would be worse).
Conclusion: **the macro-surprise → EUR/USD reaction has no tradeable edge for a retail
participant** — the consensus is priced in seconds, gone before a retail fill, and cost
eats the rest. The new-information channel (the one lever that could create edge) is,
for what's testable here, closed.

**Every lever is now tested and the answer is consistent: no demonstrated tradeable
edge.** Price-only (all scales) = all-gaps; assembly tools (PCBA/CJT/Fury/optimizer/
condition_lab) = no edge; CAS Harness = wrong domain; recipes/Foundations = organize-
not-predict; macro surprise daily = faint-but-not-significant; macro surprise intraday
= NO_SKILL. The null control caught every apparent edge along the way.

## Reproduce

`python scripts/run_edge_oos.py` (writes `evidence_runs/edge_oos/*-report.json`).
Code: `cas_forex/edge_oos.py`; anti-leakage tests: `tests/test_edge_oos.py`.
