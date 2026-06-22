# CAS Forex — Changelog

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
