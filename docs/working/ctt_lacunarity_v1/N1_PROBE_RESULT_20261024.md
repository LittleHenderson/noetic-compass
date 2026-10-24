# N1 probe result — per-cell measurement works, but this set measures fit, not generalisation (2026-10-24)

Status: **exploratory fit measurement.** It does not test the Noetic hypothesis. Numbers `REAL`; nothing here is
claim-bearing. Predeclaration: `PREREGISTRATION_N1_NOETIC_GAPS_20261024.md`; data limit: `N1_OUTCOME_DATA_LIMIT_20261024.md`.

## 1. What was run

The 2,034 notation rows that carry a Noetic address were taken from `cas_keep.jsonl` (a subset of training data, the
only such rows available) and scored on all 18 checkpoints with teacher-forced per-token error. Exposure per cell is
the count of those rows whose target contains the cell.

**Stated before the numbers: these rows were trained on.** This is a fit measurement. It cannot show generalisation,
and the predeclared overfit/neglect comparison was framed for held-out error, so it cannot decide those hypotheses
either.

## 2. Result, per seed (error falls in every cell)

| Seed | Overall row error, step 1,000 | step 6,000 | Change | Λ(error vector) |
|---|---|---|---|---|
| A4-s1 | 0.006552 | 0.000624 | −0.005928 | 0.011667 → 0.015832 |
| A4-s2 | 0.008036 | 0.000635 | −0.007401 | 0.054442 → 0.023438 |
| A4-s3 | 0.005599 | 0.000598 | −0.005001 | 0.016491 → 0.039908 |

Per cell, all ten improve. The largest single-cell error at step 1,000 is `^8` in A4-s2 (0.015328) and the smallest
`^5` in A4-s1 (0.007674); by step 6,000 every cell sits between 0.000517 and 0.001022.

Exposure per cell: `^0` 661, `^1` 595, `^2` 495, `^3` 472, `^4` 498, `^5` 450, `^6` 534, `^7` 540, `^8` 460,
`^9` 471 — an even spread, no neglected cell.

## 3. The two predeclared checks, applied literally

- **High-exposure cells rose more:** technically true in 3 of 3 seeds, but only because *both* halves fall; the
  high-exposure half falls slightly less (−0.008386 vs −0.008795; −0.007780 vs −0.010717; −0.006707 vs −0.007227).
  Calling that "overfitting" would be a misreading of falling error. **Not counted as support.**
- **Low-exposure cells had higher error at both points:** true in 2 of 3 seeds, by margins of roughly 0.001–0.002
  NLL. Again on trained rows. **Not counted as support.**

**Verdict: neither hypothesis. The measurement is dominated by memorisation, exactly as the data limit warned.**

## 4. What it does establish

1. The per-cell machinery works: a Noetic address can be extracted from gold targets, error can be attributed to
   cells, and `Λ` can be computed over the ten-cell vector.
2. On trained rows, per-cell error becomes uniformly tiny; the cell vector's lacunarity stays small (0.012–0.054),
   which is what a saturated field should look like.
3. It therefore cannot carry the scientific question. That needs a labelled **held-out** set.

## 5. Cost and artifacts

- 18 scoring runs, local GPU, **0 USD**.
- Scores: `cs_aws/notation_scores/<seed>_<checkpoint>.json`; held-out rows: `lacunarity_e1/data/notation_heldout.jsonl`.

## 6. Claim status

| Statement | Status |
|---|---|
| Per-cell Noetic error is computable from gold CAS targets | `REAL` |
| On trained notation rows every cell improves from step 1,000 to 6,000 | `REAL` |
| High-exposure cells improve slightly less; low-exposure cells are slightly worse | `REAL` but tiny and on trained rows |
| That pattern supports overfitting or neglect | `NOT SUPPORTED` — both halves improve |
| Noetic lacunarity predicts held-out failure | `NOT TESTED` |
| Claim-bearing status | **NONE** |
