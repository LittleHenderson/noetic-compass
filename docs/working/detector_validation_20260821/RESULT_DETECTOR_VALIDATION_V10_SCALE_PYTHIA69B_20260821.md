# V10 — SCALE TEST: the CAS detector suite on pythia-6.9b (real weights, PAID GPU)

**Date:** 2026-08-21
**Model:** `EleutherAI/pythia-6.9b` — 32 layers, hidden 4096 (≈43× the parameters of the pythia-160m used in v1–v9)
**Hardware:** rented RunPod **A40** (Secure Cloud, non-interruptible, `$0.44/hr`, hard 22-minute wall, independent stop-watchdog). Owner-authorized paid run.
**Stack on the pod:** `transformers 5.15.1`, `torch 2.8.0+cu128`, fp16 on CUDA.
**Capture method:** **direct `transformers` forward hooks** on `model.gpt_neox.layers[i]`, last-token residual per layer — **NOT** the attested-engine wrapper. This is a **research data run, labeled as such**; it does **not** satisfy, and makes no claim about, the frozen A40/Pythia **canary** (the attested-engine plumbing proof), which remains **NOT RUN** (§4.7).
**Results file (co-located):** `detector_validation_v10_scale_pythia69b_results.json`, sha256 `ea5940972ef1e8a4ec1cde45caf91647d2cea309a33d0dee486281a35a485ad4`
**Cost discipline:** exactly one A40 created, watchdog armed at create, pod verified `EXITED` after retrieval. Two earlier create attempts this session failed on plumbing (scp arg bug; then PEP-668 blocking the `transformers` install) — both cheap, no science. Total exposure ≈ $0.30–0.40.

> **This write-up was revised after a 3-lens adversarial verification pass (numbers / overclaim / discipline).** The overclaim lens raised two BLOCKERs against the first draft — a noise result bundled into a plural "scale hardens" headline, and an invalid "apples-to-apples" defense. Both are fixed below. The first-draft headline is **withdrawn**; this is the corrected, evidence-bounded version.

---

## 1. The question

At pythia-160m the mandatory **char-ngram surface control** was a **load-bearing negative** (v6): trained on explicit valence/causality and tested on an implicit set that removes the giveaway vocabulary, the activation detectors could not beat a bag-of-character-ngrams baseline. v7 confirmed the valence signal was real but **bounded**. v8 showed the valence direction is nonetheless **causally load-bearing** at 160m. v9 showed Operator-10 is **surface-robust** and Domain-4 only **weakly** beats surface.

**V10 asks: does a 43× bigger model change any verdict?** Same detector logic, same stimulus constructs, same surface control.

## 2. The selection caveat that governs every number below

For the activation figures, the detector **picks its single best layer by accuracy on the test set itself** — over **32 layers** at 6.9b, vs only **12 layers** at 160m. The char-ngram surface baseline has no layers and gets **no** such selection. Two consequences, both load-bearing:

1. **Best-of-N selection inflates the activation figure**, and the inflation **grows with N** — so the 6.9b activation numbers get ~2.7× more "layer-lottery tickets" than the 160m numbers they are compared against. **Verdict-changes vs 160m therefore cannot be cleanly attributed to scale** rather than to the larger selection denominator.
2. A result only counts if it **survives a best-of-32 noise test**: is the best-layer accuracy above what selecting the max over 32 layers would give under the chance null? This kills one axis outright (see cause-effect).

## 3. Results (exact, real pythia-6.9b weights)

All "surface control" rows train on the **explicit** register and test on a **held-out implicit** set (the v6/v7 protocol — the test that failed at 160m). "act" = best-layer test accuracy; "surf" = char-ngram (n=2,3,4) on the same split.

| Axis | test n | chance | 6.9b act | surf | best-of-32 noise test | honest verdict |
|------|--------|--------|----------|------|-----------------------|----------------|
| `^2`/`^3` valence (implicit) | 16 (8+8) | 0.500 | **0.938** (L6) = 15/16 | 0.500 | **SURVIVES** — P(≥15/16 over 32 layers) ≈ `0.008` | **REAL: beats surface (+0.438) and chance** |
| `^8`/`^9` cause-effect (connective-stripped) | 12 (6+6) | 0.500 | 0.750 (L18) = 9/12 | 0.583 | **FAILS** — P(≥9/12 over 32 layers) ≈ `0.91` | **NOT DISTINGUISHED FROM NOISE — withdrawn** |
| Domain-4 P/C/E/O (cross-topic) | 8 (2×4) | 0.250 | **1.000** (L11) = 8/8 | 0.875 | beats chance (P≈`5e-4`) | **READABLE but surface-lexical: only +0.125 over surface (1 item), unchanged from 160m** |
| Operator-10 `^0`..`^9` | 20 (2×10) | 0.100 | **0.800** (L12) = 16/20 | 0.250 | **SURVIVES** — 16/20 at chance 0.10 is ~10σ | **REAL and robust: beats surface (+0.550) and chance** |

**160m reference (same protocol):** valence 0.562 vs surf 0.438 (v6, NOT HARDENED); cause-effect 0.562 vs surf 0.625 (v6, surface won); Domain-4 1.000 vs surf 0.875 (v9, BEATS_SURFACE_WEAK); Operator-10 0.550 vs surf 0.250 (v5/v9, SURFACE_ROBUST).

Causal steering (v8 protocol, additive `±w`, `w` = mean(explicit-pos) − mean(explicit-neg) normalized to α=6.0, at valence best-layer L6, vs a K=12 random norm-matched null):

| | 6.9b | 160m (v8) |
|---|------|-----------|
| swing (mean over 4 neutral prompts) | **0.040** | +5.656 |
| per-prompt swings | [0.14, 0.01, 0.01, 0.0] — **only 1 of 4 exceeds null** | all strongly positive |
| null mean / null max\|·\| | 0.012 / 0.057 | 0.176 / 1.188 |
| z over null | **1.05** | ≈9.3σ |
| verdict | **NOT DISTINGUISHED FROM RANDOM** | CAUSALLY_LOAD_BEARING |

## 4. What it means — the honest, bounded reading

**Two axes are genuinely real at 6.9b and beat their surface baseline; one is noise; one is surface-lexical.**

- **REAL (2):** **valence** (0.938 = 15/16, survives best-of-32 at p≈0.008, surface sits at chance 0.500) and **Operator-10** (0.800 = 16/20, ~10σ over chance 0.10, surface pinned at 0.250). Operator-10 is the strongest and cleanest axis on the board. These two clearly beat a bag-of-character-ngrams — i.e. they are **not** just reading giveaway words.
- **NOISE (1):** **cause-effect** at n=12 with best-of-32-layer selection scores 0.750 about 91% of the time under the pure coin-flip null. **The v6 "surface won" negative is not overturned** — the 6.9b number is not distinguishable from noise. Withdrawn as a verdict-change.
- **SURFACE-LEXICAL (1):** **Domain-4** reads perfectly (8/8) but the char-ngram baseline is also 0.875 — margin +0.125 (one item), **unchanged from 160m**. The P/C/E/O framings carry lexical signatures; scale did not separate the detector from surface here.
- **CAUSAL: negative.** At fixed α=6.0 the steer is not distinguished from random (z=1.05); only 1 of 4 prompts moved beyond the null band. **Untested hypothesis** (not a conclusion): α=6.0 was tuned for 160m's 768-dim residual and is likely proportionally too small at 4096-dim — an α-rescaled re-run is the follow-up. Recorded as a null at fixed α, **not** as a causal positive and **not** as a refutation of v8.

**What I will NOT say:** that "scale hardens the axes" as a general claim (it rests on the two real axes, against a selection asymmetry that itself favors the bigger model), that the cause-effect axis improved, or that Operator-10's 0.55→0.80 delta is *caused by* scale (two single runs at different layer counts — the 6.9b result stands on its own; the delta is not cleanly attributable).

**What I WILL say:** on real pythia-6.9b weights, the valence and Operator-10 axes are readable well above chance and above a char-ngram surface control at their best layer — the two strongest same-protocol results the detector track has produced, on a model 43× larger than the 160m baseline.

## 5. Claim-state separation

- **Real:** every activation/surface/causal number above, on real `pythia-6.9b` weights via direct transformers on a rented A40.
- **Simulated:** none.
- **Accepted:** none — research-grade, not a customer `ACCEPT`.
- **Not the attested engine / not the canary:** direct transformers, not `load_open_weight_runtime`/`capture_greedy_trajectory`. The frozen A40/Pythia **canary** is still **NOT RUN**; §4.7 and §5.2 items 30/32 unchanged.
- **Open:** cause-effect needs a held-out layer-selection split + cross-seed nulls before any verdict; causal steering needs α rescaled to the 6.9b residual; Domain-4 needs a framing-matched control; Element-40 rung; larger n; replication through the attested engine.

## 6. Honest scope / caveats (superset)

- Small n throughout (16 / 12 / 8 / 20). Research-grade, not significance testing.
- Best-layer selected on the test set; 32 layers at 6.9b vs 12 at 160m — the comparison is **not** symmetric in the one dimension that drives verdict-changes (see §2).
- One model, one run, one seed per null.
- Direct-transformers capture differs from the attested engine; numbers are not interchangeable with attested-engine runs.
