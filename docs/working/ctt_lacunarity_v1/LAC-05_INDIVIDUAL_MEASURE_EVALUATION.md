# LAC-05 — Individual measure evaluation: Noetic family (Workstream 5, Phase 2/3)

Status: **exploratory replication, not claim-bearing.** The Recipe and RPM families are covered by their
specifications (LAC-02) and synthetic tests (LAC-03A) only; no evaluation data exists for them.

## 1. What was compared

| Source | Rows | Sources | Built from | Training overlap |
|---|---|---|---|---|
| First held-out set (`notation_dev99`) | 588 (500 distinct) | 98 | the 99 DEV SDG rows excluded from training, plus 5 noised copies | 0 |
| Second source (`notation_new100`) | 600 | 100 | **new CAS compositions written for this test**, six English phrasings each | 0 |

Both were scored on the same 18 checkpoints with the same teacher-forced error and the same ten Noetic cells.
Exposure is the preregistered **training row count** per cell: `^0` 537, `^1` 438, `^2` 368, `^3` 353, `^4` 366,
`^5` 353, `^6` 370, `^7` 403, `^8` 346, `^9` 383. The split at the median (369) is high = `^0`,`^1`,`^6`,`^7`,`^9`;
low = `^2`,`^3`,`^4`,`^5`,`^8`.

## 2. Results

### 2.1 Overall error rises in both sources

| Source | Seed | Step 1,000 | Step 6,000 | Change |
|---|---|---:|---:|---:|
| First | A4-s1 | 0.451870 | 0.458878 | +0.007008 |
| First | A4-s2 | 0.393191 | 0.491379 | +0.098188 |
| First | A4-s3 | 0.395322 | 0.448958 | +0.053636 |
| Second | A4-s1 | 1.471022 | 1.641994 | +0.170972 |
| Second | A4-s2 | 1.685291 | 2.131292 | +0.446001 |
| Second | A4-s3 | 1.651655 | 2.006977 | +0.355323 |

### 2.2 The two predeclared checks, both sources

| Source | H-overfit (high-exposure worsens more) | H-neglect (low-exposure worse at both points) |
|---|---|---|
| First (588 rows) | **1 of 3 — FAILS** | **3 of 3 — SUPPORTED** |
| Second (600 rows) | **2 of 3 — MEETS** | **3 of 3 — SUPPORTED** |

Per seed, second source:

| Seed | High-exposure Δ | Low-exposure Δ | Early low vs high | Final low vs high |
|---|---:|---:|---|---|
| A4-s1 | +0.267641 | +0.091163 | 1.568779 vs 1.357985 | 1.659942 vs 1.625626 |
| A4-s2 | +0.355732 | +0.529489 | 1.782570 vs 1.511383 | 2.312059 vs 1.867115 |
| A4-s3 | +0.363193 | +0.337460 | 1.726814 vs 1.536663 | 2.064274 vs 1.899856 |

### 2.3 The lacunarity scalar does not separate anything

`Λ` over the ten cell means:

| Source | A4-s1 | A4-s2 | A4-s3 |
|---|---|---|---|
| First, 1,000 → 6,000 | 0.015792 → 0.019795 | 0.018011 → 0.018068 | 0.009832 → 0.016672 |
| Second, 1,000 → 6,000 | 0.053447 → 0.038498 | 0.066019 → 0.070758 | 0.043385 → 0.041873 |

It moves in different directions in different seeds, and it is small in both sources. It never separates the
neglect cases from the rest.

## 3. What this establishes

1. **The exposure–error relation replicates.** In both sources, in all three seeds, the low-exposure cells carry
   higher error at both checkpoints. That is now two independent source sets.
2. **The overfitting story does not replicate.** It was 1 of 3 on the first source and 2 of 3 on the second, on
   opposite sides of the predeclared bar. It is at the noise floor and should not be claimed.
3. **The lacunarity scalar adds nothing here.** The signal is carried by the cell-level exposure split, which is a
   simpler baseline than `Λ`. This is the honest answer to Objective D for this measure: no demonstrated incremental
   value.
4. **The second source is harder.** Errors are roughly three to four times higher on the new compositions, which
   were never in training. That is expected, but it means the two sources are not comparable in absolute level — only
   in direction.

## 4. What it does not establish

- It does not show that exposure causes the error. Low-exposure cells may simply be harder cells, and the data cannot
  separate those explanations.
- It does not generalise beyond one model family, one training run configuration, and six checkpoints per seed.
- It does not validate `Λ` as a measure of anything.
- The second source was written by me from templates, not by an independent author. It is new material, but it is
  machine-authored and stylistically narrow.

## 5. Claim status

| Statement | Status |
|---|---|
| Low-exposure Noetic cells carry higher held-out error at both checkpoints, in both sources, 3 of 3 seeds | `REAL` (descriptive) |
| Held-out Noetic error rises from step 1,000 to 6,000, in both sources, 3 of 3 seeds | `REAL` |
| High-exposure cells worsen more | `NOT REPLICATED` (1/3 then 2/3) |
| `Λ` over cell means explains or separates the cases | `NOT SUPPORTED` |
| Exposure causes the error difference | `HYPOTHESIS` — not tested |
| Any measure is a validated control signal | `NO` |

## 6. Artifacts and cost

- Scores: `cs_aws\notation_new_scores\<seed>_<checkpoint>.rows.json` (18 files) and `notation_dev_scores\…`.
- Data: `lacunarity_e1\data\notation_new100.jsonl` (600 rows), `notation_dev99.jsonl` (588 rows).
- Builder: `lacunarity_e1\gen_second_source.py`.
- Cost: **0 USD** — no LLM was used; the sources are compositions written from the CAS grammar and the pinned
  compiler.
