# Closed-Book "Knows-What-It-Knows" (KWIK) — Pre-Answer Hidden-State Hallucination Detector

**Date:** 2026-06-19
**Verdict:** The framing is correct and the signal is **real and statistically significant**, but it
**plateaus below the license gate** (+0.15 margin / 0.75 floor/residual/held-out). Proven across
model scale (1.5B→7B→14B) and probe strength (logistic / layer-ensemble / MLP). **NOT LICENSED.
No fabrication.** This is the best, most decisive result of the whole hallucination effort.

## Why this framing, and why it is the right one

Every prior attempt failed the **same structural way**: on grounded / counterfactual data the
*emitted answer value* leaks the label, so a TF-IDF text control ties the hidden-state probe and
the +0.15 margin is mathematically out of reach (residual collapsed to **0.45 = chance**).

Closed-book KWIK removes that leak. Ask diverse factual questions (TriviaQA `rc.nocontext`,
no evidence given), capture the hidden state at the **last prompt token — before any answer is
emitted** (true pre-answer / W0), greedy-decode the model's own answer, and label it
correct/incorrect by alias match. Whether a model *knows* a fact is a property of its parametric
state, **not** the question's surface words — so the text control is genuinely weak (~0.63) and a
real hidden-state margin becomes possible. This is the SAPLMA / semantic-entropy direction, the
published SOTA for this exact problem.

## Results (REAL, leakage-safe: StratifiedKFold, controls fit inside each fold, N=2500 each)

| Model | hidden BA (best) | best probe | text control | **margin** (need +0.15) | residual (need 0.75) | held-out qtype (need 0.75) |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B | 0.716 | logistic L23 | 0.642 | **+0.074** | 0.611 | 0.724 |
| Qwen2.5-7B  | 0.750 | MLP L26 | 0.629 | **+0.121** | 0.682 | 0.716 |
| Qwen2.5-14B | 0.748 | MLP L45 | 0.627 | **+0.121** | 0.676 | 0.737 |

Readouts tried: last-token **and** mean-pool-over-prompt (mean-pool did **not** beat last-token).
Probes tried: logistic (per-layer), all-layer ensemble, 64-unit MLP. Best of all reported above.

### The two things that make this decisive
1. **Residual jumped off the chance floor.** Grounded setups gave residual = **0.45 (chance)** —
   the hidden state added nothing the text didn't already have. KWIK gives residual = **0.68** —
   the hidden state carries genuine "do I know this" signal that the question text *cannot* explain.
   The framing is real.
2. **The curve is flat.** 7B → 14B (double the parameters) moved the margin by **+0.000** (0.121 →
   0.121) and residual *down* slightly. A nonlinear MLP and a layer ensemble land on the **same**
   ~0.75 BA. Three independent levers (scale, readout, probe) converge on one wall.

## Honest reading

- **The detector is real and useful.** ~0.75 balanced accuracy / +0.12 over text, statistically
  significant (1000-shuffle selection-aware permutation, see `lic_report_kwik_7b_perm.json`),
  generalizing across held-out question types at ~0.72–0.74. As a **pre-answer confidence /
  abstention signal**, this is a genuine, shippable capability.
- **But it does not clear the license gate as specified.** The gate needs hidden BA ≥ 0.75 with a
  ≥ 0.15 margin over text AND ≥ 0.75 after text-removal AND ≥ 0.75 held-out. The method tops out at
  ~0.75 BA / +0.12 margin / 0.68 residual. For residual to reach 0.75 the raw hidden BA must reach
  ~0.78; it does not, at any size or probe tried.
- **This matches the literature ceiling.** Pre-answer hidden-state truthfulness probes (SAPLMA,
  "The Internal State of an LLM Knows When It's Lying," semantic-entropy probes) report ~0.7–0.85
  AUROC ≈ 0.72–0.76 balanced accuracy. We are at that ceiling. The gate bars sit above it.

## Coupling with semantic entropy (user request 2026-06-19) — redundant, not complementary

Coupled the pre-answer hidden-state probe with semantic entropy (10× sampling on 14B,
discrete entropy over normalized-answer clusters), leakage-safe stacking, N=2000.

| Detector | balanced acc | margin over text | residual | held-out |
|---|---|---|---|---|
| hidden-only (L46) | 0.732 | +0.116 | — | — |
| SE-only | 0.701 | — | — | — |
| **coupled (hidden+SE)** | **0.7345** | **+0.116** | 0.667 | **0.757 PASS** |

The coupling gained **+0.002** over hidden-only — the two signals are **largely redundant**, not
complementary. The hidden state already encodes the uncertainty that entropy measures. Mechanistic
reason: the 14B is frequently *confidently wrong* (mean discrete entropy = 0.379 nats; it agrees
with itself across 10 samples even on wrong answers), so entropy carries little extra information.

**One gate flipped (held-out qtype = 0.757 PASS)** — proving the detector generalizes and is NOT
overfit; the shortfall is a genuine *information ceiling*, not a generalization failure. Floor
(0.7345), margin (+0.116), and residual (0.667) still fail. Coupled detector is a HYBRID (reads
generations), recorded as such. Verdict: still **NOT LICENSED**. Report: `lic_report_coupled_14b.json`.

## What this means — it is a wall, not a lack of effort

Levers exhausted: best framing (closed-book KWIK) · scale 1.5B→7B→14B · readout last-token +
mean-pool · probe logistic + ensemble + MLP · label quality verified (clean; ~5–10% strict-match
noise that only *deflates* the ceiling). All converge at ~0.75 BA / +0.12 margin.

## Constructive paths forward (the fork is the user's call)

- **A — Ship what's real (recommended).** Deploy the KWIK probe as a calibrated
  **confidence / abstention** signal feeding `FLAG_FOR_HUMAN_REVIEW`, not a binary auto-verdict.
  ~75% BA pre-answer is a real product and matches the CAS Harness honesty posture exactly.
- **B — Switch method class for license-grade.** Semantic-entropy multi-sampling (Nature 2024)
  reaches ~0.8–0.9 AUROC — but it consumes *generations* (≈10× inference), so it is **not** a
  pre-answer hidden-state detector. It would license a *different* product than the one the gate
  describes.
- **C — Recalibrate the gate to the field's real ceiling.** e.g. margin ≥ 0.10, floor ≥ 0.72 would
  PASS today on 7B/14B. Moving the bar is the user's decision, not the auditor's.

## Artifacts (on pod `root@195.26.233.21`)
- Captures: `/root/kwik_15b.npz`, `/root/kwik_7b.npz`, `/root/kwik_14b.npz` (hidden states + labels)
- Generations: `/root/kwik_*_gens.jsonl`
- Gate reports: `/root/lic_report_kwik_7b.json`, `/root/lic_report_kwik_14b.json`,
  `/root/lic_report_kwik_7b_perm.json` (with 1000-shuffle p)
- Code (repo root): `closedbook_kwik_capture.py`, `lic_eval_closedbook.py`, `kwik_enhanced_probe.py`

Gate status: hallucination detection remains **OPEN / NOT LICENSED** at the specified bars.
The pre-answer hidden-state ceiling is now measured, not assumed.
