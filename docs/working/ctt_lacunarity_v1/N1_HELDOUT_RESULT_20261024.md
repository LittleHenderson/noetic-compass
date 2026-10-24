# N1 held-out result — Noetic error rises with training, and it rises more in heavily exposed cells (2026-10-24)

> **CORRECTION (2026-10-24, after independent verification; see `LAC-00_EVIDENCE_LEDGER.md` §4).**
> This report used token **occurrences** where the preregistration defines training **rows**. Re-running the
> predeclared checks with row counts (median 369; high = `^0`,`^1`,`^6`,`^7`,`^9`) gives **H-overfit 1 of 3 (FAILS)**
> and **H-neglect 3 of 3 (SUPPORTED)** — the opposite of the verdict below. Also: the set is 588 rows from
> **98 sources × 6**, not 99 × 6; there are **88 duplicate rows** (500 distinct pairs); and the run used
> `notation_dev99.jsonl`, not the preregistered `cas_val.jsonl`. The overall rise (3 of 3 seeds) is unchanged. The
> text below is kept as published and is superseded by this correction and by LAC-00 §4.

Status: **exploratory, held-out, not claim-bearing.** Numbers `REAL`. Predeclaration:
`PREREGISTRATION_N1_NOETIC_GAPS_20261024.md`. This replaces the earlier fit-only probe
(`N1_PROBE_RESULT_20261024.md`), which could not test the hypothesis.

## 1. The data (new, genuinely held out)

The 99 DEV SDG rows that the original build excluded from training were rebuilt into notation pairs with the
project's own builder (`ctt_build.notation_pairs.to_ctt`, the pinned compiler, `slots.find_slots`), plus five noised
copies each:

| Item | Value |
|---|---|
| Rows built | **588** |
| Rows carrying a Noetic token | **588** (all of them) |
| Text overlap with the training notation rows | **0** |
| Per-cell rows | `^0` 114, `^1` 162, `^2` 144, `^3` 72, `^4` 156, `^5` 132, `^6` 120, `^7` 234, `^8` 126, `^9` 120 |

Training exposure per cell (rows in `cas_keep` carrying the cell): `^0` 661, `^1` 595, `^2` 495, `^3` 472,
`^4` 498, `^5` 450, `^6` 534, `^7` 540, `^8` 460, `^9` 471.

## 2. Held-out error, step 1,000 → step 6,000

| Seed | Overall row error at 1,000 | at 6,000 | Change | Λ(error vector) |
|---|---|---|---|---|
| A4-s1 | 0.451870 | 0.458878 | **+0.007008** | 0.015792 → 0.019795 |
| A4-s2 | 0.393191 | 0.491379 | **+0.098188** | 0.018011 → 0.018068 |
| A4-s3 | 0.395322 | 0.448958 | **+0.053636** | 0.009832 → 0.016672 |

Held-out error **rises with training in all three seeds**; the rise is small in A4-s1 and clear in A4-s2 and A4-s3.

Per cell, most cells worsen. A4-s1: `^9` improves (−0.068929), `^4` (−0.016362) and `^6` (−0.003850) improve slightly,
while `^7` (+0.041304), `^1` (+0.031524) and the rest worsen. A4-s2: every cell worsens (+0.076747 to +0.160773).
A4-s3: every cell worsens (+0.010921 to +0.117632).

## 3. The two predeclared checks

**H-overfit — high-exposure cells worsen more: supported in 2 of 3 seeds.**

| Seed | High-exposure mean change | Low-exposure mean change | High worse? |
|---|---|---|---|
| A4-s1 | +0.014276 | −0.002967 | yes |
| A4-s2 | +0.110612 | +0.115985 | no |
| A4-s3 | +0.080865 | +0.054361 | yes |

**H-neglect — low-exposure cells higher at both points: 1 of 3 seeds.** Not supported.

The predeclared bar for H-overfit was 2 of 3, so it is **met**, with the caveat that the exposure range is narrow
(450–661 rows) and the A4-s2 split runs the other way.

## 4. What this means

1. **The extra 5,000 steps cost held-out Noetic accuracy.** The model that writes better replies (the generation
   result) is worse at the notation task on rows it never saw — a genuine trade-off inside one training run.
2. **The loss is not evenly distributed across cells.** In two of three seeds it is concentrated in the cells the
   model saw most, which is the overfitting pattern the predeclaration named, not the neglect pattern.
3. **The lacunarity of the error vector stays small** (0.010–0.020) and rises only slightly, so it does not by
   itself separate the two explanations; the exposure split does the work here.

## 5. Limits, stated plainly

- This is one model family, one data source (99 DEV rows with five noised copies each), three seeds.
- The exposure split has a narrow range; "high" and "low" differ by less than 50%.
- The noise copies are generated, not human; their surface forms differ but their content is the same 99 rows.
- The result is diagnostic and local; nothing here is claim-bearing.

## 6. Claim status

| Statement | Status |
|---|---|
| Held-out Noetic-labelled error rises from step 1,000 to 6,000 in 3 of 3 seeds | `REAL` |
| The rise is larger in high-exposure cells in 2 of 3 seeds | `REAL`, predeclared bar met |
| Low-exposure cells carry the higher error | `NOT SUPPORTED` (1 of 3) |
| This shows overfitting rather than a data artefact | `PROPOSED` — needs a second data source or model family |
| Noetic lacunarity alone explains the rise | `NOT SUPPORTED` — exposure split, not Λ, separates the cases |
| Claim-bearing status | **NONE** |
