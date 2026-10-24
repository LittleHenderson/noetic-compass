# N1 outcome — the Noetic layer cannot be measured on this data (2026-10-24)

Status: **N1 is not executable with the current splits.** No result is reported, and none is invented. This is a
data limitation, not a verdict on the lacunarity hypothesis. The predeclaration
(`PREREGISTRATION_N1_NOETIC_GAPS_20261024.md`) required per-row Noetic addresses on a held-out split. That data does
not exist.

## 1. What was checked (exact counts)

| File | Rows | Rows whose gold target contains a Noetic token `^0`…`^9` |
|---|---|---|
| `cas_val.jsonl` (the held-out CAS split) | 2,000 | **17** |
| `cas_keep.jsonl` (CAS training rows) | 20,000 | 2,034 |
| `mouth_train.jsonl` | 11,530 | 0 |
| `train_cube.jsonl` | 41,503 | 0 |
| `ear_m.jsonl` | 5,306 | 0 |

The held-out CAS split has **17 rows** with a Noetic address out of 2,000. That is not enough to estimate an error
rate per cell, let alone compare high-exposure and low-exposure cells.

The only other Noetic carrier is the mouth tone tag, and it is a single value: `^1` on all 11,530 training rows and
all 2,097 dev rows. A one-cell vector has no lacunarity (it is exactly 0 by construction), so it cannot support the
analysis either.

## 2. Why this happened

The frozen data was built to teach a translator, not to carry a cognitive address. Noetics appear in two places only:

- the notation direction's targets, which are training rows (`cas_keep`), not a held-out split;
- the mouth tone tag, which is fixed at `^1` by the data design.

So N1's joining step — per-row error to per-cell address — has no held-out rows to join to.

## 3. What the honest conclusion is

- **Noetic lacunarity remains untested.** Nothing here supports or refutes it.
- The generation result (`GENERATION_COMPARISON_RESULT_20261024.md`) stands on its own and does not depend on N1.
- The estimate in the design note that "coverage is a property of the data, not the model" is now measured: the
  data has almost no Noetic coverage on held-out rows at all.

## 4. What it would take to run N1 properly

1. **A labelled held-out Noetic set.** The notation rows already in `cas_keep` carry real addresses (2,034 of them).
   The cheapest path is to hold a portion of those rows out as a dedicated Noetic evaluation split, and to say
   plainly that they were training data, so the reading is fit rather than generalisation.
2. **Or a fresh generated split.** The notation targets are programmatic; a fresh generation of notation rows,
   never trained on, would give a clean set. That needs the generator and a short build step.
3. **Or an audited addresser.** A parser that maps an ordinary English row to a Noetic address, with a checked
   sample, would let the mouth rows be analysed — but that is a labelling project, not a quick join.

## 5. Claim status

| Statement | Status |
|---|---|
| Held-out CAS rows carry almost no Noetic addresses: 17 of 2,000 | `REAL` |
| Mouth tone tags are `^1` on every row: 11,530 of 11,530 training, 2,097 of 2,097 dev | `REAL` |
| Noetic lacunarity predicts anything about training or generation | `NOT TESTED` |
| The Noetic layer needs a labelled held-out split before any test | `REAL` conclusion from the counts |

## 6. Cost

Zero. No GPU jobs were run for N1; the counts come from reading the frozen data.
