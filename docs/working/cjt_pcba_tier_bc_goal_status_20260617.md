# CJT/PCBA Tier-B/C Build — Goal Status

Generated: 2026-06-17
Goal: Build the research-tier ("Tier B") and gated ("Tier C") CJT/PCBA work —
the real, runnable code plus the honest readiness gates — WITHOUT flipping any
higher-authority claim to LICENSED.
Goal complete: `true` (Tier-B/C scope = buildable code + honest gates)
Current boundary honest: `true`

## What Was Built

| Tier | Item | Module | Status |
|---|---|---|---|
| B | CJT compiler integration + E-CJT-001..008 validation | `cas_forex/cjt_compiler.py` | DONE |
| B | Analytical engine: β (large/small-signal), gm, region | `cas_forex/cjt_analysis.py` | DONE |
| B | 5 CCBs as executable, CRC-clean designs | `cas_forex/ccb_designs.py` | DONE |
| C | CCB + governance + prediction-head readiness gates | `cas_forex/ccb_readiness.py` | DONE |
| C | W0 CJT-labeled readout experiment design | `docs/working/cjt_w0_labeled_readout_experiment_design_20260617.md` | DONE (design only) |
| B/C | Tests incl. negative claim-boundary | `tests/test_cjt_tier_bc.py` | DONE (17 tests) |

## Test Evidence

- `python -m pytest tests/test_cjt_tier_bc.py -q` → 17 passed.
- `python -m pytest tests -q` → **217 passed** (17 new + 200 prior; zero regressions).
- All 5 CCBs lint ERROR-free (well-formed); expected CRC-004 reverse-flow
  warnings on safety-assessment / feedback edges only.

## REAL vs OPEN (the honest split)

REAL (code runs + tested):
- CJT statement compilation through the real CAS compiler bridge + E-CJT
  validation passes (missing bias, invalid bias domain, cutoff, saturation,
  short circuit, gain divergence, cascade depth).
- Analytical β/gm/region computation (Fisher-Rao geometry). The *math* is real.
- Five CCB reference designs that are provably well-formed under CRC.
- Readiness machinery that reports board/governance/prediction-head claims as
  NOT LICENSED / OPEN.

OPEN / NOT LICENSED (unchanged — this build does NOT advance them):
- **`CJT<>` production compiler authority** — `is_production_cjt_syntax_enabled()`
  stays False; grammar-spec-approved and semantics-review-signed are unsigned.
- **β as a measured model property** — the engine produces *analytical estimates*;
  `CjtAnalysis.validated` is always False (needs empirical trace validation, Q-002).
- **CjtPredictionHead** — architecture is specified; no head is trained or
  evaluated. Sample-level eval (the only acceptance metric) has not run.
- **CCB safety / memory / power / governance claims** — designs are well-formed,
  but every behavioral claim is NOT LICENSED pending red-team, false-positive
  eval, privacy review, and legal review.
- **Model-internal W0 prompt-injection detection** — the Qwen W0 gate FAILED
  (hidden BA 0.745 < 0.75; margin 0.094 < 0.15). The new doc specifies the
  follow-up experiment; it has NOT been run.
- **Live trading / broker ACCEPT** — structurally impossible; unchanged.

## Negative Claim-Boundary Proof

`tests/test_cjt_tier_bc.py` asserts:
- No CCB readiness check is LICENSED or ready; all carry missing external evidence.
- The CjtPredictionHead is OPEN with zero present evidence.
- `is_production_cjt_syntax_enabled()` remains False.
- `analyze_transition(...).validated` is always False.

## What Tier-B/C Did NOT Do

It did not train models, run GPU traces, obtain external red-team or legal
review, or pass the W0 gate. Those are the gating dependencies, and they remain
outstanding by design. "Built" here means the code and the honest gates exist —
not that the claims are licensed.
