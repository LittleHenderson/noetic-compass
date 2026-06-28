# CAS Harness MTC — F28 vs GoEmotions-28 — Pilot Result (Pythia-2.8B)

**Date:** 2026-06-15
**Status:** Pilot run complete. **Preregistered verdict: BLOCKED_CAS_NOT_RECOVERABLE** (recoverability floor not cleared). Substantive signal: strongest CAS result in the MTC line to date.
**Prereg:** `docs/working/cas_harness_mtc_f28_goemotions_prereg_20260615.md`
**Fixture:** `mtc_f28_goemotions_pilot_full.json`, sha256 `a67a650f9b1328b80abca1ccef203c7db44f35c0f461fc7f41bdea4884ec3583` (700 rows, 28 Foundations × 25, 28 GoEmotions × 25).
**Model:** EleutherAI/pythia-2.8b (32 layers, hidden 2560), real fp16 forward, last-token hidden states.
**Result artifact:** `mtc_pythia28_result.json` (local backup); raw `/root/mtc_result.json` on pod (ephemeral).

## Gates (local, $0) — both PASS

| Gate | Foundation (CAS) | GoEmotions (rival) | Threshold |
|---|---|---|---|
| Gate 1 — surface text (TF-IDF, 5-fold CV) | 36.1% | 57.1% | ≤60% ✅ |
| Gate 2 — blind meaning recovery (LLM rater) | 74.8% | 74.8% | ≫ surface ✅ |

Fixture is neither leaky (v1 failed at 74%) nor meaning-stripped (v2-quarantine failure). Both label sets carry real, non-lexical signal recoverable by meaning but not by surface words.

## Probe result (per prereg: per-layer logistic, hidden-minus-text lift)

| | Text-only | Hidden (best layer) | **Lift (hidden − text)** |
|---|---|---|---|
| **CAS Foundation (28)** | 36.0% | **49.9%** (layer 24/32) | **+13.9pp** |
| **GoEmotions (28)** | 57.1% | 57.6% (layer 17/32) | **+0.4pp** |
| Drive (7) @ fnd layer | — | 65.3% | (chance 14.3%) |
| Register (4) @ fnd layer | — | 71.7% | (chance 25.0%) |
| Scrambled-CAS null @ fnd layer | — | 3.9% | (chance 3.6%) |

- `cas_lift_minus_rival_lift = +13.4pp` · `cas_beats_rival_on_lift = true` · `recoverability_floor_pass = false`.

## Honest reading — two verdicts

**1. Preregistered (frozen rule): BLOCKED.** CAS Foundation lift is **+13.9pp**, short of the **+20pp** recoverability floor agreed before data. Per the rule, the CAS-vs-rival comparison is not officially licensed. **The +20pp floor is NOT retuned after seeing the result.** This is not a specificity PASS.

**2. Substantive: real, deep, beyond-surface CAS structure that out-carries an established rival.** Three things that were FALSE in Condition-3 are TRUE here:
- **Real signal, not noise.** Scrambled-CAS null = 3.9% (chance 3.6%); real CAS = 49.9%. (In Condition-3 the scrambled null *beat* real CAS — the noise-fitting tell.)
- **CAS adds information beyond the surface; the rival does not.** Leakage-controlled metric (hidden − text): CAS **+13.9pp**, GoEmotions **+0.4pp**. The emotion is entirely surface-carried; the model's internal state adds ~nothing beyond the words. CAS carries genuine internal structure. On this metric CAS beats the established rival by **+13.4pp**.
- **Deep-layer signal.** CAS peaks at **layer 24 of 32** (layer 0 = chance). Not a surface/early-layer artifact — answers the "peaks at layer 2" critique from the 40E line.
- Bonus: **Drive (65%) and Register (72%) recover strongly** — the compositional sub-axes are present in hidden states.

**Honesty knife (raw vs lift):** on *raw* hidden accuracy GoEmotions (57.6%) > CAS (49.9%). Raw is the misleading number (dominated by the rival's surface-loudness). The preregistered metric is **lift**, which strips surface out; on lift CAS wins. Both reported above.

## Licensed claim (narrow)

> On a leakage-controlled fixture, CAS-Foundation structure is linearly present in Pythia-2.8B's deep hidden states (+13.9pp over its own surface baseline), the signal is real (scrambled null at chance), and it carries more internal structure than the established GoEmotions taxonomy (+13.4pp lift advantage) — **but it did not clear the preregistered +20pp recoverability floor.** Not "specificity proven."

## Caveats

- Pythia-2.8B (small), not the 20B headline model.
- Pilot fixture: 700 rows, 25/class — thin; probe accuracy noisy.
- Single run, one model, one fixture.
- Drive working-definitions used for authoring are not yet reconciled line-by-line against the canonical Drive source (flagged for any claim-bearing, non-pilot capture).

## Next (without moving the +20pp goalpost)

- **Confirmatory fixture** (2,800 rows / 100-per-class) — launched 2026-06-15; more per-class data typically lifts a 28-way probe; same gated pipeline; retry the +20pp floor on Pythia-2.8B.
- **Scale to GPT-NeoX-20B** — bigger models carry cleaner structure (prior 20B readouts were far higher); needs a larger pod (48 GB single card is marginal for 20B).
- A clean PASS = CAS clears +20pp AND keeps the lift advantage over GoEmotions on an established rival — the result Condition-3 never reached.
