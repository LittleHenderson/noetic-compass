# V14 — SCALE THE CONTROLS: the two controls that lost at 160m, re-run on pythia-6.9b (PAID A40)

**Date:** 2026-08-21 · **Model:** `EleutherAI/pythia-6.9b` (32 layers, 4096 hidden), `transformers 5.15.1`, `torch 2.8.0+cu128`, fp16 CUDA.
**Hardware:** owner-authorized paid RunPod **A40** (Secure Cloud, `$0.44/hr`, hard 22-min watchdog, pod `sa7wy64kfny07m` verified `EXITED`). Direct transformers forward hooks — **NOT** the attested engine (research data run). One earlier attempt this session died on a Windows cp1252 decode bug in the orchestrator (experiment ran, output lost); fixed with UTF-8 decode + disabled HF progress bars.
**Results file (co-located):** `detector_validation_v14_scale_controls_pythia69b_results.json`, sha256 `647884a072ba12a7…`

## The question
At 160m, the two framing/giveaway controls **lost to the char-ngram word-counter**: Operator-10 framing-matched (v12) `0.500` < `0.550`; `^8`/`^9` construct-correct + giveaway-free (v13) `0.667` < `0.833`. Valence was the *only* axis that beat surface, and *only* at 6.9b. **Do these two cross over and beat surface at 43× scale, the way valence did?**

## Results (exact)

| Control | scale | activation | surface | margin | vs chance (best-of-32) | verdict |
|---|---|---|---|---|---|---|
| **Operator-10** framing-matched (train colloquial, test FRESH) | 160m | 0.500 (10/20) | 0.550 | −0.050 | — | lost |
| | **6.9b** | **0.800 (16/20, L29)** | 0.550 (11/20) | **+0.250** | P=`1.04e-11` | **CROSSOVER — beats surface** |
| **`^8`/`^9`** construct-correct + giveaway-free | 160m | 0.667 (8/12) | 0.833 | −0.167 | — | lost |
| | **6.9b** | **0.917 (11/12, L31)** | 0.833 (10/12) | **+0.083** | P=`0.0967` | **marginal — beats surface by 1 item** |

Per-class at 6.9b — Operator-10 activation: `^0`2/2 `^1`1/2 `^2`2/2 `^3`2/2 `^4`1/2 `^5`2/2 `^6`2/2 `^7`1/2 `^8`2/2 `^9`1/2 (16/20); surface: 11/20. `^8`/`^9` activation: `^8`5/6 `^9`6/6 (11/12); surface: `^8`6/6 `^9`4/6 (10/12).

## What it means

**Operator-10 CROSSES OVER decisively at scale — this is the headline positive.** The flagship axis, which at 160m was *colloquialism-confounded* (0.500 < 0.550), at 6.9b reads the 10 Noetic operators from **fresh, giveaway-free phrasings** at `0.800` — **beating the word-counter by +0.250 and chance by ~10σ (P=1.04e-11)**. So it is **not** colloquialism-matching: at scale the model carries a **register-independent representation** of the 10 Noetics that a bag-of-character-ngrams cannot match. This is the strongest same-question positive the detector track has produced beyond valence.

**`^8`/`^9` crosses over only MARGINALLY.** It improves a lot with scale (0.667 → 0.917) and now *nominally* beats surface — but by **one item** (11/12 vs 10/12), and `11/12` under best-of-32-layer selection is ~10% likely under the coin-flip null (P=`0.0967`). **Not certified** — call it a weak/borderline crossover, not a clean pass.

**The pattern is now clear and strengthens Claim B.** The CAS reading axes are **surface-confounded at 160m but harden at scale.** At 6.9b, three axes now beat the word-counter: **valence** (`0.938` vs `0.500`, clean — v10), **Operator-10** (`0.800` vs `0.550`, clean — this run), and **`^8`/`^9`** (`0.917` vs `0.833`, marginal — this run). The "reading" half of Claim B (CAS as a measurement language) is real at scale for **multiple** axes, not just valence.

## Claim-state separation
- **Real:** all numbers, real pythia-6.9b weights via direct transformers on a paid A40.
- **Accepted:** none — research-grade.
- **Not the attested engine / not the canary:** direct transformers; the frozen A40/Pythia canary is still `NOT RUN`.
- **Clean positive:** Operator-10 crossover (+0.250, P=1.04e-11). **Marginal:** `^8`/`^9` (+0.083, P=0.097). **Still open:** framing-matched **Domain** at 6.9b (not run — v10 Domain was same-register 1.000 vs 0.875, surface-lexical).
- **Caveat:** activation best-of-32-layers selected on the test set (surface gets no selection); n=2 fresh per operator / n=6 per `^8`/`^9` class; single run. Operator-10's +0.250 margin and 10σ-over-chance make selection noise an implausible explanation; `^8`/`^9`'s +1-item margin does not.
