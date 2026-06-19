# CAS Forex — Changelog

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

Verdict: hallucination detection remains **OPEN / NOT LICENSED** at the specified bars — now a
*measured* ceiling, not an untested assumption. No fabrication.

Added:
- `closedbook_kwik_capture.py` — KWIK capture (last-token + mean-pool hidden, greedy label).
- `lic_eval_closedbook.py` — leakage-safe gate (readout×layer selection, residual, held-out,
  selection-aware 1000-perm).
- `kwik_enhanced_probe.py` — ceiling check (ensemble + MLP) confirming the plateau.
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
