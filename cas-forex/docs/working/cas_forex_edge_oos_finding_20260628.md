# CAS Forex — Regime-Switching Edge: honest out-of-sample finding (2026-06-28)

## Verdict: NO EDGE

A leak-free, out-of-sample test of regime-switching on 5 years of real daily data
(US30, NAS100, EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD) shows **no demonstrable
edge** from detecting the market regime and switching strategies.

| metric (40 OOS windows, 736 trades, 2.0pt all-in cost) | value |
|---|---|
| SWITCH total OOS return | **+40.2%** |
| best single strategy (chosen on train) | +20.5% |
| **random-routing null** (shuffle regime→strategy) | **+42.3%** |
| SWITCH beats the random null, per window | **2%** |
| SWITCH positive-window rate | 55% |
| SWITCH max drawdown | 16.7% |

The headline `+40%` is **beta, not alpha**: a *random* assignment of strategies to
regimes does just as well (+42%) and beats the "smart" switch in 98% of windows.
The regime detector and its routing add no value over chance. The positive number
is simply from being long-biased instruments during a 2021–2026 up-period, not from
the switching logic.

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

## Reproduce

`python scripts/run_edge_oos.py` (writes `evidence_runs/edge_oos/*-report.json`).
Code: `cas_forex/edge_oos.py`; anti-leakage tests: `tests/test_edge_oos.py`.
