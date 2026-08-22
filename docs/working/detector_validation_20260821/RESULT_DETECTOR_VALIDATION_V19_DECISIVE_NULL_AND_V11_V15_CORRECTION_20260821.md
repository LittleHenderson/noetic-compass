# V19 — Decisive null: NOT a positive. And a CORRECTION that bounds V11 and V15.

**Date:** 2026-08-21 · **Model:** `EleutherAI/pythia-6.9b`, direct transformers. Paid A40 (`$0.44/hr`, pod `6c7ml3ejpw66jb` verified `EXITED`). **NOT** the attested engine (canary still `NOT RUN`).
**Results file (co-located):** `detector_validation_v19_decisive_null_pythia69b_results.json`, sha256 `1c17cdcc21a904a0…`
**Verified by a 2-lens adversarial pass. My draft — "CAS-domain is PRIVILEGED at 6.9b; first positive evidence for CAS-specificity" — is WITHDRAWN. The script's auto-verdict `CAS_PRIVILEGED_NORMALIZED` is WITHDRAWN.**

## 1. The raw numbers (all arithmetically correct, verified)
Framing-stripped 8 topics × 4 CAS-Domains = 32 sentences; R=20 splits; best-of-32-layer nearest-centroid vs char-ngram surface; chance 0.25.

| partition | activation | surface | act−surf | normalized (act−surf)/(1−surf) |
|---|---|---|---|---|
| CAS_domain | **0.963** (±0.057) | 0.688 | +0.275 | **0.880** |
| topicpair_A | 0.275 | 0.050 | +0.225 | 0.237 |
| topicpair_B | 0.338 | 0.044 | **+0.294** | 0.307 |
| topicpair_C | 0.375 | 0.212 | +0.163 | 0.206 |
| sentence_length_quartile | 0.444 | 0.319 | +0.125 | 0.183 |

## 2. Why this is NOT evidence for CAS-specificity — the decisive fact

**Three hand-written regexes classify all 32 sentences by CAS-Domain at `32/32 = 1.000`** — no model, no training, better than the 6.9b probe's `0.963`. **Verified directly by me on my own grid:**
- `P`: contains `rather than | instead of | even though` — **in-class 8/8, out-of-class 0/24**
- `O`: contains an internal period (the three-imperative structure) — **8/8, 0/24**
- `E`: contains `looked forward to | pleasure | at ease | looked after | satisfying | not soon forget` — **8/8, 0/24**
- `C`: the residue — 8/8.

**The true surface ceiling for this partition is `1.000`, not the char-ngram's `0.688`.** Under an honest surface control, CAS act−surf = `0.963 − 1.000 = −0.037`, and normalized gain is **undefined** (`0/0`). The entire claimed "+0.275 gain" fits inside the gap between what char-ngrams happen to catch and what the text actually determines.

**Three more failures, all conceded:**
1. **The framing-strip manipulation FAILED its own check.** Surface is a property of the text alone, so v18 `0.662` → v19 `0.688` is a clean text-to-text comparison: my intervention meant to *lower* CAS surface **raised** it. I substituted markers (modals → contrastive connectives; "first/then" → bare imperatives with periods) rather than removing them.
2. **"Both metrics agree" was false.** CAS leads on raw activation (`0.963`) and normalized gain (`0.880`) but **not** on raw act−surf (`0.275` vs topicpair_B `0.294`). The metric disagreement that made v18 unusable **persists**; I manufactured agreement by quietly promoting raw activation, the metric with *no* surface control at all.
3. **The normalized lead is an arithmetic artifact of the unfixed surface non-overlap.** The `1/(1−surf)` multiplier is `3.205×` for CAS vs `1.046×` for topicpair_B. Surfaces still span `0.044–0.688` — the v18 "no matched-surface comparison" objection applies in **full force**.
4. **Comparator denominators are weak**: several non-CAS surfaces sit *below* chance (`0.044–0.212 < 0.25`) because averaging two unrelated topics into one centroid is systematically anti-correct — so the normalized metric divides CAS by a real ceiling and the comparators by broken ones.
5. **Chance is not `0.25`** for the reported statistic: activation is max-over-32-layers scored on the test split (selection on test), while surface is a single estimator. v18 maxed over 12 layers, v19 over 32 — part of the `0.850 → 0.963` rise is simply more candidates to max over.

**Verdict: `NOT_LICENSED` — no evidence about CAS-specific representation. CAS-specificity remains `GREY`, now tending negative.** v18 and v19 are both retained.

## 3. THE CORRECTION — this bounds V11 and V15 (previously recorded as positives)

**The v11 and v15 Domain test sentences are literally identical to 16 of the v19 grid sentences (verified: `identical sentences: 16/16`), and the same three regexes classify them at `16/16 = 1.000`.**

Therefore:
- **V15 ("SCALE DOMAIN — Domain-4 hardens decisively at 6.9b: activation `0.938` vs char-ngram `0.438`, `+0.500`, P recovers `1/4`→`3/4`, reads principle from meaning not modals") is BOUNDED.** The char-ngram baseline `0.438` **understated the true surface ceiling of `1.000`**. The claim "reads principle from meaning, not modal words" is **not supported** — the P sentences simply traded modal markers for contrastive-connective markers, which are equally lexical. **The `+0.500` margin is withdrawn as a specificity claim.**
- **V11 (160m framing-matched Domain, PARTIAL) is bounded identically** — same test sentences, same regex recoverability.
- **The general methodological lesson (the most valuable output of this run): the char-ngram surface control UNDERSTATES the surface ceiling.** Passing it is necessary, **not sufficient**. Every stimulus set in the detector track needs a **template/regex audit** — "can a short hand-written rule solve this?" — *before* GPU spend, as a blocking pre-registered manipulation check.

**Explicitly NOT corrected by this finding** (different stimuli, not audited here): v10 valence (implicit-scenario stimuli), v14 Operator-10 (fresh non-colloquial phrasings), v16 valence causal steering. Those stand as previously recorded — **but they have not had a regex audit either, and should get one before any further claim rests on them.**

## 4. What would actually test CAS-specificity (pre-registered, in order)
1. **Blocking manipulation check, before any GPU:** regenerate the grid under a hard constraint that no lexical/punctuation rule beats `≤0.35` on the CAS axis. Gate the run on it.
2. **Author the sentences blind to the CAS axis** (author does not know the partition), then label independently — so the CAS axis is not the authorship axis.
3. **Permutation null:** instead of 4 hand-picked comparators, score CAS's percentile against **1000+ random balanced 4-way partitions** of the same items. That is the literal claim ("privileged over arbitrary partitions") and it is CPU-only with cached residuals — **`$0`**.
4. **Nest layer selection inside CV** (pick layer on train, score on test), or pre-register one layer, and give the surface baseline the same best-of-L freedom.

## 5. Claim state
- **Real:** all numbers, real pythia-6.9b weights. **Accepted:** none.
- **NOT LICENSED:** "CAS-domain is privileged"; "first positive evidence for CAS-specificity"; and (now) V15's "Domain-4 reads principle from meaning not modals."
- **`GREY`, tending negative:** CAS-specificity.
- **Kept:** v18 and v19 both retained as load-bearing negatives; no number altered.
