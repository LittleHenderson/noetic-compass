# CAS Forex — Changelog

## 2026-06-21 — Detector tuning + intraday switching: cost drag is the wall, no config beats break-even

Followed the switching test with (A) detector-threshold tuning on daily and (B)
intraday H1. Added detector CLI args (`--er-trend/--detect-window/--hi-vol/--lo-vol/
--shock-z`) to `run_switching_backtest.py`.

(A) Daily er_trend sweep — MORE trend detection = WORSE switching (monotonic):
  er 0.15 -$7,360 | 0.20 -$6,479 | 0.25 -$5,631 | 0.35 -$2,040.
  Every "trend" call routes to breakout/trend, which lose on daily, so seeing more
  trends destroys value. Can't tune a daily edge into existence; meanrev_tf (~+$9) wins.

(B) Intraday H1 (real 2y, ~12,300 bars/pair, cost 1.5p): EVERYTHING loses —
  trend_sma -$10,404 | breakout -$6,196 | meanrev -$4,862 | SWITCH -$4,715 |
  meanrev_tf -$4,123 (best). SWITCH again ~= meanrev (detector still 91.6% range at H1).
  The killer is COST DRAG: meanrev_tf made +$3.72 on daily (286 trades) but loses
  -$4,123 on H1 (4,654 trades) — same strategy, ~16x more trades x cost. ~85% of the
  H1 loss is trading cost.

Synthesis after a thorough search (4 strategy families, 2 forecasters incl. Chronos,
regime sim, detection, hard switching, detector tuning, daily + H1): NO configuration
produces a cost-surviving edge. The ceiling is daily mean-rev+filter at literal
break-even (+$3.72), which evaporates at realistic costs. The wall is cost drag eating
thin edges, worse at higher frequency.

Genuinely untested (tied to user's real 2020 success): the user's OWN discretionary
entry rules encoded, and NAS30 / index instruments (indices trend more strongly than FX
majors; we have only tested FX majors, which mean-revert). Live trading remains NOT
LICENSED. 217 tests pass.

## 2026-06-21 — Regime detector + switching on REAL data: switching does NOT beat the best single strategy (on daily)

Built the live regime detector + RPM switching and tested it on real 5y daily data
against every single strategy.

- `forecast/strategies.py` — `make_sma_trend_signal` (composable SMA, routable).
- `regime_sim.py` — `detect_regime` (Kaufman efficiency ratio + vol-vs-baseline +
  shock z-score + vol-of-vol), `DEFAULT_ROUTING` (sim's RPM seed), and
  `make_regime_switching_signal` (detect each bar -> route -> sit out on lacuna).
- `scripts/run_switching_backtest.py` — SWITCH vs each single strategy on real data.

Result (real 5y daily, cost 1.5p, $50k):
  trend_sma  -$15,055 | meanrev -$729 | meanrev_tf +$3.72 | breakout -$8,144 |
  SWITCH     -$2,048
Best = meanrev_tf (+$3.72). SWITCH did NOT beat it (-$2,048).

Why (the mechanism): the detector classifies **97% of real daily bars as "range"**,
so SWITCH ~= plain meanrev, plus rare trend/breakout detours that lost money. Daily
bars are too coarse/homogeneous for hard switching to add value — there isn't enough
regime variety, and the trend calls aren't reliable/timely on daily.

Honest read: the regime-switching MACHINERY works end-to-end, but on daily data the
useful "regime intelligence" is the lightweight trend FILTER already baked into
meanrev_tf (a soft regime-awareness), not a separate hard switch. Switching's real
shot is INTRADAY, where regimes vary and change more (ties to the multi-timeframe
requirement). meanrev_tf remains the incumbent (break-even). NOT LICENSED. 217 tests pass.

## 2026-06-21 — Strategy-condition simulator (CAS-SDG for regimes): CJT + nested lacunarity + RPM routing

Built the user's idea: a market-REGIME simulator that plays every strategy across
every condition and uses the CAS machinery to map where edge lives. Working v0.

- `cas_forex/regime_sim.py` — seeded synthetic OHLC generator for 7 regimes
  (trend_up/down, range, high_vol, low_vol, vol_cluster, shock); CJT operating-region
  classifier (cutoff/active/saturation/breakdown + gain beta); nested lacunarity
  (gap map across strategy x regime x volatility); best-strategy-per-regime (RPM seed).
- `scripts/run_strategy_simulator.py` — sweeps strategies x regimes x vol x seeds,
  prints the matrix + nested lacunarity + RPM routing seed, writes a JSON report.

First run (4 strategies x 7 regimes x 3 vol x 5 seeds, cost 1.5p) cleanly recovers
known structure — which validates the simulator:
- Trend/breakout WIN in trends (breakout +13.2%/+12.2% up/down) and LOSE in range.
- Mean-reversion WINS in range (+0.9%) and loses in trends.
- No single strategy wins everywhere (overall lacunarity 0.58 — 58% of cells are gaps).

RPM routing seed (regime -> best validated strategy):
  trend_up/down/high_vol -> breakout; range/shock -> meanrev; low_vol -> trend_sma;
  vol_cluster -> NONE (honest lacuna, do not trade).

Reframe (the productive insight): the edge — if any — is in REGIME DETECTION +
SWITCHING, not one magic strategy. The honest next frontier is detecting the live
regime reliably on REAL data and validating the routing out-of-sample (the RPM
prerequisite question). Synthetic regimes characterize behavior, not live edge.
Live trading remains NOT LICENSED. 217 tests pass.

## 2026-06-21 — Realistic-cost test: the thin edge does NOT survive normal costs

Added a configurable round-trip cost knob (`extra_cost_pips` = commission + slippage
on top of spread; `--spread-pips` / `--extra-cost-pips`) and swept the trend-filtered
mean-reversion (the only positive strategy) across realistic cost levels.

5y portfolio P&L (gated, $50k):
- 1.0 pip total cost (very optimistic):  +$91   PASS
- 1.5 pips (optimistic ECN+commission):  +$28   PASS
- 2.0 pips (normal retail):              -$31   FAIL
- 2.5 pips (standard account):           -$95   FAIL

Verdict: the edge breaks even at ~1.5-2.0 pips and is negative at realistic retail
all-in costs (majors typically 1.5-2.5 pips spread+commission+slippage). So the
trend-filtered mean-reversion is NOT a deployable, cost-surviving strategy — it is
positive only under optimistic cost assumptions, and even then ~$0 over 5 years on
$50k. This is the honest make-or-break result: no deployable edge yet across 4
strategy families tested (trend SMA, Chronos, mean-rev, mean-rev+filter).

Implication for the $5-12k/month target: not reachable. Best strategy made ~$0 over
5y on $50k; $5-12k/month on a $2-5k seed is +100-600%/month (martingale-blowup
territory), not a real return. A realistic 2-5%/month would need a ~$100-250k account
to clear $5k/month — and even that is exceptional and not guaranteed.

Added/changed:
- `backtest/engine.py` — `extra_cost_pips` (round-trip commission+slippage), deducted
  with spread on close. Default 0.0 (tests unchanged).
- `scripts/run_real_backtest.py` — `--spread-pips`, `--extra-cost-pips`.
- 217 tests pass.

## 2026-06-21 — Strategy pivot: mean-reversion + trend filter = first POSITIVE backtest (thin)

Acted on the research insight that FX majors range 70-80% of the time, so our
trend-follower was the wrong strategy class (it lost most on the most mean-reverting
pair, USD/CAD). Added rule-based strategies + user-controllable risk budget and
re-ran the same real-data harness (5y daily, 5 majors).

Progression (portfolio P&L on $50k, gated):
- Trend SMA:               -$15,098   (avg max DD 41%)
- Chronos:                 -$15,574   (avg max DD 49%)
- Mean-reversion (z-fade):    -$523    (avg max DD 6%)   <- ~30x less bad, ~break-even
- Mean-reversion + trend filter: +$105.62 (avg max DD 3.5%)  <- FIRST passed=True

The trend filter (skip fades that fight a >150bps move over 60 bars — a theory-backed
fix, not curve-fitting) made it net positive: 3/5 pairs clearly positive (EUR/USD
+1.56%, GBP/USD +3.47%, AUD/USD +3.26%), beating buy-and-hold on every ranging pair.
Only USD/CAD (-6.1%) still loses (it trended up). Evidence chains verified.

CRITICAL honesty caveat — the edge is razor-thin and NOT yet deployable:
- +$105.62 over 286 gated trades = ~$0.37/trade = ~0.74 pip/trade edge.
- The backtest already charges a 1-pip spread; ONE more pip of real cost
  (commission + slippage) is ~$143 across 286 trades and FLIPS IT NEGATIVE.
- So this is positive-after-1-pip-spread, NOT positive-after-realistic-costs.
- One parameter set, one dataset, in-sample. Needs out-of-sample / walk-forward
  validation + realistic cost modeling before ANY capital. report.passed is a
  research signal, not a license. Live trading remains NOT LICENSED.

Real progress nonetheless: we moved from "definitely loses" to "plausibly
break-even with low drawdown," and confirmed the lever is strategy class + regime
filter, not forecaster sophistication.

Added/changed:
- `forecast/strategies.py` — mean-reversion (z-fade, optional trend filter) and
  Donchian breakout signals; no martingale / grid / no-stop modes (real money).
- `backtest/engine.py` — signals may set ATR stop/target multiples; risk limits now
  all sourced from config (single source of truth for the risk budget).
- `scripts/run_real_backtest.py` — `--model meanrev|breakout`, mean-rev params, and
  RISK BUDGET flags (`--starting-balance --position-lots --risk-per-trade-pct
  --max-daily-dd --max-weekly-dd --max-open-positions --max-position-lots`).
- 217 tests pass throughout.

## 2026-06-21 — Chronos-Bolt re-run confirms NO edge across TWO forecasters

Wired Amazon Chronos-Bolt (`forecast/chronos_signal.py`) as a pluggable directional
signal and re-ran the exact same real-data harness (5y daily Yahoo, 5 majors), with
SL/TP held identical so only the forecaster changed (SMA → ML model). Evidence chain
verified: 19,660 hash-chained packets across 5 files, all re-verified.

Result (REAL): Chronos also **loses** — portfolio **-$15,574 gated / -$17,007 raw**
on $50k, vs the SMA run's -$15,098 / -$16,296. Per pair (gated%): EUR/USD -22.0,
GBP/USD -81.1, USD/JPY +38.6, AUD/USD -101.6 (account wiped), USD/CAD +10.2.
Buy-and-hold beat the strategy on every pair, including the two "winners" (USD/JPY
b&h +46.3 vs +38.6; USD/CAD b&h +14.6 vs +10.2).

Decisive read: swapping a simple moving average for a real ML forecaster moved the
needle by ~$0.5k on -$15k — i.e. **the edge problem is NOT a forecaster-quality
problem.** Two structurally different models both lose on majors over 5 years.

Consistent finding across BOTH models: the **CAS gating layer reduces loss and
drawdown** (gated beat raw on P&L and avg max DD in both runs; suppressed 1,118
Chronos trades) and the new blow-up guard prevented crashes when the ungated AUD/USD
and GBP/USD arms hit ~100% loss / ~100% drawdown. Honest nuance: on the two
profitable pairs the gates slightly REDUCED gains (USD/CAD gated +10.2 vs raw +19.5)
— the gates cut both tails; net-positive only because losers dominate.

Strategic implication: the validated, sellable asset is the safety/audit chassis, not
a profitable bot. A trading edge remains OPEN and is the hard, unsolved part; next
lever is a different strategy class or timeframe (per the user multi-timeframe
requirement), NOT a bigger model. Live trading remains NOT LICENSED.

Added/changed:
- `forecast/chronos_signal.py` — cached CPU Chronos-Bolt → (Direction, confidence).
- `backtest/engine.py` — optional `signal_fn` hook (SMA default unchanged); blow-up
  guard (stop trading when balance <= 0; clamp risk_per_trade_pct at 100%).
- `scripts/run_real_backtest.py` — `--model {sma,chronos}`.
- Artifacts: `evidence_runs/real_backtest/real-chronos-20260622003352-report.json`.
- 217 tests pass throughout.

## 2026-06-21 — First REAL-data comparative backtest: safety layer works, strategy has NO edge

Ran the first backtest on REAL market data instead of synthetic candles. Pulled 5
years of daily candles from Yahoo Finance (1,300 bars/pair, 2021-06-22 → 2026-06-22,
no API key, no GPU) for EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD and ran the full
CAS Forex pipeline three ways: `cas_gated` (SMA proposals through the 5-gate auditor),
`raw_model` (same proposals, gates removed), and `buy_hold` / `no_trade` baselines.

Result (REAL, evidence-chain verified): the built-in SMA5/20/50 daily strategy **LOSES
money** with or without CAS gating — portfolio P&L **-$15,097.88 gated vs -$16,296.32
raw** on $50,000 starting capital (5 × $10k), avg max drawdown 41.5% gated / 46.0% raw.
Buy-and-hold beat the strategy on most pairs (e.g. USD/JPY b&h +46.3% vs gated +9.3%).

Honest read:
- The **CAS safety/gating layer does its job**: it suppressed 695 trades, lost ~$1,198
  (~7.4%) less than the ungated arm, and lowered average max drawdown (41.5% vs 46.0%).
  It reduces damage — it cannot turn a losing strategy into a winning one.
- The **trading edge does not exist** with the current model. `report.passed = False`
  (no positive edge vs no-trade). This confirms live trading SHOULD remain NOT LICENSED:
  trading this model live would lose money.
- Evidence is real and verifiable: 13,554 hash-chained Evidence Packets across 5 files,
  all chains independently re-verified. 217 tests still pass (additive change only).

Next lever for an actual edge (in priority order): wire a real forecaster (Chronos stub
at `forecast/models.py:112`, or a TimeGPT key), then re-run this exact harness; the
strategy — not the safety chassis — is the bottleneck.

Added:
- `scripts/run_real_backtest.py` — real-data (Yahoo) comparative backtest:
  cas_gated vs raw_model vs buy_hold vs no_trade, writes a real BacktestEvidenceReport
  + verifiable hash-chain, with an explicit research-signal (not license) pass criterion.
- Run artifact: `evidence_runs/real_backtest/real-20260621234945-report.json`.

Known caveat (follow-up): the macro gate is evaluated at wall-clock now, not at the
candle's historical timestamp, so macro blackouts are effectively inert in backtests
(`backtest/engine.py` builds the snapshot with `timestamp=utc_now()`).

## 2026-06-19 — Closed-book KWIK hallucination probe: measured ceiling, NOT LICENSED

Ran the decisive pre-answer hidden-state hallucination experiment in the one framing where
text controls are structurally weak — closed-book "knows-what-it-knows" (TriviaQA no-context,
hidden state captured at the last prompt token before any answer is emitted, label = did the
model's own greedy answer match). This is the literature SOTA direction (SAPLMA / semantic
entropy) and the only honest route to a real +0.15 margin.

Result (REAL, leakage-safe, N=2500 each): the framing **works** — residual signal climbed off
the chance floor (grounded 0.45 → KWIK 0.68), proving the hidden state carries genuine
text-independent "do I know this" information. But it **plateaus below the license gate**:
hidden BA ≈ 0.75, margin ≈ +0.12 over text, residual 0.68 — short of +0.15 / 0.75. The wall is
flat: 7B → 14B moved the margin +0.000, and a nonlinear MLP + layer ensemble land on the same
~0.75. This matches the published ceiling (~0.7–0.85 AUROC) for pre-answer hidden-state probes.

Then, per user request, COUPLED the hidden-state probe with semantic entropy (10× sampling on
14B, leakage-safe stacking). Result: coupled BA 0.7345 vs hidden-only 0.732 — a +0.002 gain. The
two signals are **redundant, not complementary** (the 14B is often confidently wrong: mean
entropy 0.379 nats), so entropy adds almost nothing. Held-out generalization flipped to PASS
(0.757), proving an information ceiling rather than overfitting; floor/margin/residual still fail.

Verdict: hallucination detection remains **OPEN / NOT LICENSED** at the specified bars — now a
*measured* ceiling confirmed from five independent angles (framing, scale, readout, probe,
method-coupling), not an untested assumption. No fabrication.

Added:
- `closedbook_kwik_capture.py` — KWIK capture (last-token + mean-pool hidden, greedy label).
- `lic_eval_closedbook.py` — leakage-safe gate (readout×layer selection, residual, held-out,
  selection-aware 1000-perm).
- `kwik_enhanced_probe.py` — ceiling check (ensemble + MLP) confirming the plateau.
- `kwik_semantic_entropy.py` — batched 10× sampling + discrete semantic entropy.
- `lic_eval_coupled.py` — coupled (hidden + semantic entropy) leakage-safe gate.
- `docs/working/hallucination_kwik_ceiling_findings_20260619.md` — full findings + A/B/C fork.

## 2026-06-17 — CJT/PCBA Tier-B/C research code + honest gates

Built the research-tier and gated CJT/PCBA work: real, runnable code plus honest
readiness gates. No higher-authority claim was flipped to LICENSED — those need
GPU traces, external red-team, or legal review (all still OPEN / NOT LICENSED).

Added:
- `cas_forex/cjt_compiler.py` (B) — compiles one `CJT<>` statement: runs embedded
  CAS literals through the real CAS compiler bridge and emits E-CJT-001..008
  validation findings. `is_production_cjt_syntax_enabled()` stays False.
- `cas_forex/cjt_analysis.py` (B) — analytical β (large/small-signal), gm, and
  operating-region classification via Fisher-Rao geometry. `validated` is always
  False — analytical estimate, not measured against real traces (Q-002).
- `cas_forex/ccb_designs.py` (B) — the 5 Cognitive Circuit Boards (CSB, COB,
  CDAB, CMB, CPMB) encoded as executable `CrcCircuit` specs that pass CRC
  ERROR-free. Well-formed designs, NOT runtime-safety guarantees.
- `cas_forex/ccb_readiness.py` (C) — readiness gates that report each CCB safety
  claim, governance proof, and the CjtPredictionHead as NOT LICENSED / OPEN with
  required external evidence missing.
- `docs/working/cjt_w0_labeled_readout_experiment_design_20260617.md` (C) —
  design for the failed-Qwen-W0-gate follow-up (CJT labels + controls + pass
  criteria). Research design only; not run.
- `tests/test_cjt_tier_bc.py` — 17 tests incl. negative claim-boundary proofs.

Tests: `python -m pytest tests -q` → 217 passed (zero regressions).

## 2026-06-17 — CJT/PCBA Tier-A evidence + visualization layer

Built the buildable-now ("Tier A") CJT/PCBA stack recommended in
`docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`. All
additive, evidence-only, claim-bounded (no path to live trading or broker
ACCEPT).

Added:
- `cas_forex/cas_state_utils.py` — surface parser for CAS state literals
  (`^k^D_{Fd}|R`): Noetic/Domain/Drive/Register extraction, domain precedence,
  involution-pair check. Not the compiler — surface only.
- `cas_forex/cjt_diagnostics.py` (A-1) — maps forex conditions (weak edge,
  forecast disagreement, single-model overconfidence, macro shock, drawdown,
  broker mismatch, beta drift) into `CjtCircuitDiagnostic` sidecars with
  claim-ceiling routing (SUPPRESS / FLAG_FOR_HUMAN_REVIEW / LIVE_LOCKED).
- `cas_forex/crc_linter.py` (A-3) — Cognitive Rule Check: static design-time
  linter (CRC-001..008) over CJT/via/fuse circuit specs. Flags invalid bias
  domain, short circuits, reverse-flow bypass, push-pull gain divergence,
  cascade depth, gain firewall, and fuse-after-protected. Static only; a
  well-formed circuit is NOT a runtime-safety guarantee.
- `cas_forex/cjt_circuit_view.py` (A-2) — deterministic markdown/ASCII renderer
  for diagnostics and CRC reports (Cause→[Bias]→Effect, region, β, gate).
- `cas_forex/cjt_differential.py` (A-4) — differential-pair matched-control via
  Fisher-Rao geodesic distance on the open simplex; emits FLAG_FOR_HUMAN_REVIEW
  above threshold. Heuristic, not proof.
- `tests/test_cjt_pcba_tier_a.py` — 23 tests covering all of the above.

Tests: `python -m pytest tests -q` → 200 passed (zero regressions).
