# V20 — Shortest-rule audit of every STILL-STANDING result ($0, no model, no GPU)

**Date:** 2026-08-21 · **Cost:** `$0` (pure text analysis, no model loaded).
**Results file (co-located):** `audit_all_stimuli_results.json`, sha256 `dcca0c994ebcb6cb…`
**Why:** v19 proved the char-ngram control **understates the surface ceiling**. That flaw may invalidate the session's *remaining* wins too. This audits them — before any further GPU spend, and before anything else rests on them.

**Method.** Rather than hand-crafting regexes (subjective, and biased by knowing the answer), search **automatically** for the shortest rule that solves each stimulus set: (1) best single **word** per class; (2) best **structural** feature (length-quantile / comma-count / internal-period bins), scored as a **genuine multi-class predictor**, fit maximally generously on the same items.

> **Self-correction recorded:** the first version of this audit scored structural features **one-vs-rest**, so on the 10-class Operator set the degenerate rule "nothing is `^8`" scored `18/20 = 0.90` and appeared to beat the model's 10-way `0.800`. That is not a comparable statistic. Caught and fixed before reporting; the numbers below are from the fixed multi-class version.

## Results

| stimulus set (published result) | chance | published activation | char-ngram | **best word rule** | **best structural rule** | **shortest rule** | verdict |
|---|---|---|---|---|---|---|---|
| **Valence `^2`/`^3`** (v10 `0.938`; v16 causal) | 0.500 | **0.938** | 0.500 | 0.625 | 0.625 | **0.625** | **SURVIVES** — model leads by **+0.313** |
| **Operator-10 fresh** (v14 `0.800`) | 0.100 | **0.800** | 0.550 | 0.650 | 0.500 | **0.650** | **SURVIVES, NARROWED** — model leads by **+0.150** (not +0.250) |
| **`^8`/`^9` construct-correct** (v14 `0.917`) | 0.500 | 0.917 | 0.833 | 0.833 | **0.917** | **0.917** | **KILLED** — a **comma-count rule ties the model exactly** |
| Domain-4 framing-stripped (v19, known fail — positive control) | 0.250 | 0.963 | 0.688 | 0.562 | 0.688 | 0.688 | (hand-written 3-regex = **1.000**, see below) |

## What this establishes

1. **`^8`/`^9` cause-effect is WITHDRAWN.** A trivial **comma-count** rule scores `0.917` — *exactly* the model's `0.917`. The model has **zero** advantage over counting commas on this set. The v14 "marginal crossover" is dead. (`^8` scene-setting clauses carry commas; `^9` arrival sentences do too — my "fresh, giveaway-free" rewrite introduced a punctuation tell.) **This was already the weakest axis (P=0.097); it is now a negative.**
2. **Valence SURVIVES cleanly.** Model `0.938` vs best trivial rule `0.625` — a **+0.313** margin no short rule reaches. This is now the **only** axis to survive both the char-ngram control *and* a shortest-rule audit, and it is also the axis with the causal result (v16). **Valence is the strongest thing the harness has.**
3. **Operator-10 SURVIVES but its margin shrinks.** Model `0.800` vs shortest rule `0.650` → the honest margin is **+0.150**, not the `+0.250` measured against char-ngrams. Real, but weaker than published.
4. **The char-ngram baseline is systematically too weak — now demonstrated on 4 of 4 sets.** In every case a simple word or structural rule **beat the char-ngram control** (valence `0.625` vs `0.500`; Operator `0.650` vs `0.550`; `^8`/`^9` `0.917` vs `0.833`; Domain hand-regex `1.000` vs `0.688`). **Every margin ever reported against char-ngrams in this track is overstated.** The shortest-rule audit must become the standard control.
5. **Automated rule search is a LOWER bound, not an upper bound.** On the v19 Domain grid the automated search found only `0.688`, while a **hand-written 3-regex rule reaches `1.000`**. So a "SURVIVES" verdict here means *"no trivial rule was found"*, **not** *"no trivial rule exists"*. Corrects the audit script's original docstring claim of an "objective upper bound."

## Revised standing of the session's results

| result | status after audit |
|---|---|
| Valence reading (v10) `0.938` | **STANDS** — margin +0.313 over shortest rule |
| Valence causal steering (v16) z=`11.18` | **STANDS** (stimuli survive; steering claim already bounded by v17 to "direction-specific vs random") |
| Operator-10 (v14) `0.800` | **STANDS, NARROWED** to +0.150 |
| `^8`/`^9` (v14) `0.917` | **WITHDRAWN** — tied by a comma-count rule |
| Domain-4 (v11/v15/v19) | **WITHDRAWN** as specificity (v19) |

## Claim state
- **Real:** all audit numbers (pure text analysis, deterministic, `$0`). **Accepted:** none.
- **CAS-specificity:** `GREY`, tending negative — but **valence is now the cleanest surviving candidate** for a real, non-surface, causally-active axis.
- **Binding methodological rule going forward:** run `template_audit.py` **and** this shortest-rule search as a **blocking pre-registration gate** on any stimulus set, before GPU spend; report margins against the **shortest rule**, not against char-ngrams.
- **Next (both `$0`):** hand-adversarial rule search on the valence and Operator-10 sets (automated search under-finds); permutation null over 1000+ random partitions.
