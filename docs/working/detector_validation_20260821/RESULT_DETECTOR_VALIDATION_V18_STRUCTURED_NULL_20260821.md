# V18 — Structured non-CAS null (reading side, 160m): INCONCLUSIVE, and the design itself can't decide it

**Date:** 2026-08-21 · **Model:** `pythia-160m` (reserialized `d5861d32…`), attested engine, CPU, **$0**.
**Results file (co-located):** `detector_validation_v18_structured_null_results.json`, sha256 `d64b80f3a222478d…`
**Verified by a 2-lens adversarial pass (numbers SOUND; interpretation FLAWED, 2 BLOCKERs). The script's auto-verdict `CAS_NOT_PRIVILEGED_OVER_NONCAS` and my first reading ("CAS-specificity unsupported at 160m") are BOTH WITHDRAWN as confounded. Honest verdict: INCONCLUSIVE.**

## Why this test
The v17 verifier's demand: beating a char-ngram surface control does not show CAS-*specificity* — the CAS axis must out-read a **structured non-CAS** control. This runs it on the reading side. Fixed 32-sentence grid (8 topics × 4 CAS-Domains). Compare how well the model's activations separate the **CAS partition** (by Domain P/C/E/O) vs several **coherent non-CAS partitions** of the *same* sentences (three topic-pairings; sentence-length quartiles). R=20 random 24/8 splits, best-of-12-layer nearest-centroid + char-ngram surface, chance 0.25.

## Raw numbers (exact, confirmed)
| partition | activation | surface | act − surf | **(act−surf)/(1−surf)** |
|---|---|---|---|---|
| **CAS_domain** | **0.850** ± 0.122 | 0.662 | +0.188 | **0.556** |
| topicpair_A | 0.419 | 0.156 | +0.263 | 0.312 |
| topicpair_B | 0.369 | 0.069 | +0.300 | 0.322 |
| topicpair_C | 0.331 | 0.062 | +0.269 | 0.287 |
| sentence_length_quartile | 0.381 | 0.138 | +0.244 | 0.282 |

## Why it's INCONCLUSIVE (not a negative)

**The verdict flips with the metric:**
- **Raw above-surface gain (`act − surf`):** CAS `+0.188` is the *lowest* of all five → looks "not privileged."
- **Ceiling-normalized gain (`(act−surf)/(1−surf)`):** CAS `0.556` is the *highest* → looks "privileged."

Both cannot be right, and neither is decisive, because the raw comparison is **ceiling-confounded**: activation caps at 1.0, so CAS's maximum possible gain is only `1−0.662 = 0.338` while the non-CAS partitions' is `~0.93`. Subtracting a `0.662` floor from a bounded-at-1.0 score cannot produce a gain comparable to subtracting a `0.069` floor (Hake's normalized-gain problem). So the `+0.188 < +0.300` that drove the "not privileged" verdict is not a scale-legitimate comparison.

**Three further reasons the grid can't decide it:**
1. **No matched-surface comparison exists.** CAS's surface floor (`0.662`) lies *entirely outside* the non-CAS surface range (`0.062–0.156`) — zero overlap. There is no common surface-difficulty region at which to compare activation, so "privilege" is not cleanly testable on this grid regardless of metric.
2. **Construction confound.** The 32 sentences were hand-authored *on the CAS-domain axis* with stereotyped markers (deontic modals for P, superlatives for E, the fixed "First X, then Y" template for O). Both the high surface (`0.662`) AND the high raw separability (`0.850`) may be artifacts of the author's stereotyped writing, not the model's native representation. So the high raw separability neither supports nor refutes CAS — it is partly built in.
3. **Best-of-12-layer selection on test** inflates every activation figure vs its surface baseline (surface gets no such max-over-12 freedom). Uniform across partitions, so it doesn't break the cross-partition ranking, but the absolute act/act−surf values are optimistic.

## Verdict — INCONCLUSIVE at 160m; CAS-specificity stays `GREY`
This 160m run supports **neither** "CAS privileged" **nor** "CAS not privileged." The raw additive metric is confounded by ceiling asymmetry and points one way; a defensible normalized metric points the other; the surface floors don't overlap; and the grid was built on the CAS axis. **Logged as indeterminate — never as a negative against CAS.** The value of this run is methodological: **it shows how NOT to run the structured-null test.**

## The decisive design (what would actually settle it)
- Run at **6.9b**, where activation clears surface with an unambiguous margin (Domain-4 was `0.938` vs `0.438` there), so the ceiling confound is far smaller.
- Use partitions with **overlapping surface baselines**, or report an **activation-vs-surface curve** / matched-surface comparison, not a single additive number.
- Use stimuli **not hand-authored on the CAS axis** (or author matched non-CAS partitions with equally stereotyped markers) to remove the construction confound.

## Claim state
- **Real:** all numbers, real pythia-160m via attested engine. **Accepted:** none.
- **Not a result for or against CAS-specificity:** genuinely indeterminate; CAS-specificity remains `GREY`.
- **Not the attested-engine canary** (this used the attested engine locally, but it is detector research, not the canary, which is still `NOT RUN`).
