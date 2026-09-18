# The decision-shape decomposition holds in all six runs, and three kinds have never been answered

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_all_runs_decomposition.py` (output `all_runs_decomposition.txt`)
**Spend:** $0.00. Pure standard library. No torch, no device, no network, no target opened.

---

## What this removes

`DECISION_STRUCTURE_RESULT.md` measured that the recorded score decomposes **exactly** by the shape of
the decision each question kind requires — and measured it on **one run**, `receipt_20260919_m`.
Every round since carried the caveat *"one arm, one seed"*.

The study ran **six** jobs — three model seeds by two arm conditions — and all six receipts are on
disk with `initial_scoring.json` and `final_scoring.json` intact. **The caveat is discharged.**

The arm and seed of each receipt were read from its own `result.json`, and the recomputed totals were
checked against the worker's own declared `initial_score` and `final_score`: **all six match exactly.**

| receipt | condition | seed | initial | final |
|---|---|---:|---:|---:|
| `receipt_20260917_a` | `ALT_COMPONENT_WHOLE` | 20260917 | 38/564 | 193/564 |
| `receipt_20260917_m` | `MIXED_SAME_ITEMS` | 20260917 | 38/564 | 192/564 |
| `receipt_20260918_a` | `ALT_COMPONENT_WHOLE` | 20260918 | 37/564 | 200/564 |
| `receipt_20260918_m` | `MIXED_SAME_ITEMS` | 20260918 | 37/564 | 203/564 |
| `receipt_20260919_a` | `ALT_COMPONENT_WHOLE` | 20260919 | 39/564 | 196/564 |
| `receipt_20260919_m` | `MIXED_SAME_ITEMS` | 20260919 | 39/564 | 189/564 |

## The decomposition, run by run

| receipt | seed | arm | **ONE DECISION** before → after | **MANY, ONE ENTITY** before → after | gap |
|---|---:|---|---:|---:|---:|
| `receipt_20260917_a` | 20260917 | ALT | 12.08% → **64.91%** | 2.01% → **7.02%** | **57.88 pp** |
| `receipt_20260917_m` | 20260917 | MIX | 12.08% → **64.15%** | 2.01% → **7.36%** | **56.79 pp** |
| `receipt_20260918_a` | 20260918 | ALT | 10.57% → **69.06%** | 3.01% → **5.69%** | **63.37 pp** |
| `receipt_20260918_m` | 20260918 | MIX | 10.57% → **68.68%** | 3.01% → **7.02%** | **61.66 pp** |
| `receipt_20260919_a` | 20260919 | ALT | 11.32% → **66.79%** | 3.01% → **6.35%** | **60.44 pp** |
| `receipt_20260919_m` | 20260919 | MIX | 11.32% → **65.66%** | 3.01% → **5.02%** | **60.64 pp** |

Across all six:

| | min | max | mean |
|---|---:|---:|---:|
| one-decision, after | 64.15% | 69.06% | **66.54%** |
| many-decision, one entity, after | 5.02% | 7.36% | **6.41%** |
| **gap** | **56.79 pp** | **63.37 pp** | **60.13 pp** |

**Six of six.** The worst case still separates the two shapes by **56.79 percentage points**, and the
arithmetic is exact in every run — for `20260917_a`, for example, `265 × 0.1208 = 32` and
`299 × 0.0201 = 6`, summing to the declared 38, and `265 × 0.6491 = 172` and `299 × 0.0702 = 21`,
summing to the declared 193.

## The per-kind table, and the fact that matters most

| kind | 17_a | 17_m | 18_a | 18_m | 19_a | 19_m | |
|---|---:|---:|---:|---:|---:|---:|---|
| `correspondence` | 96.59% | 96.59% | 93.18% | 93.18% | 94.32% | 93.18% | one decision |
| `reach` | 74.77% | 74.77% | 79.44% | 78.50% | 75.70% | 75.70% | one decision |
| `parts` | 30.19% | 32.08% | 26.42% | 33.96% | 30.19% | 22.64% | many, one entity |
| `analogy` | 10.00% | 7.14% | 22.86% | 22.86% | 18.57% | 15.71% | one decision |
| `role_set` | 13.89% | 13.89% | 8.33% | 8.33% | 8.33% | 8.33% | many, one entity |
| **`context`** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | many, one entity |
| **`definition`** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | many, one entity |
| **`edge_account`** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | **0.00%** | many, one entity |

**`context`, `definition` and `edge_account` are answered correctly exactly zero times in all six
runs.** That is 210 questions × 6 runs = **1,260 individual question-attempts, and not one correct
answer** — across two arm conditions and three independent model initialisations.

This is the strongest single fact in the record. It is not "0/70 in one arm"; it is **0 in 1,260**.

## A second finding the six runs give for free

**The study's own contrast is small next to the decision shape.**

| comparison | effect |
|---|---:|
| `ALT_COMPONENT_WHOLE` vs `MIXED_SAME_ITEMS`, one-decision half, matched seeds | **under 1.2 pp** |
| one-decision vs many-decision, worst case | **56.79 pp** |

The arm condition moves the one-decision half by less than 1.2 points on every matched pair
(64.91/64.15, 69.06/68.68, 66.79/65.66), while the shape of the decision moves it by 57 to 63 points.
**The decision shape is the dominant variable by a factor of roughly fifty**, which is consistent with
the study's own recorded finding that a learning advantage was not established between the arms.

## What this changes in the record

- **The central claim is no longer a single-run observation.** It holds in six of six with a
  worst-case margin of 56.79 pp.
- **The three never-answered kinds are 0 in 1,260 attempts**, not 0/70.
- **The "one arm, one seed" caveat still applies to everything else** — the concentration
  measurements, the stage probes, the penalty sweeps and the arm-A preparation all rest on
  `receipt_20260919_m` alone, because those need the checkpoints and the cached features, which exist
  only for that run.
- `records/MACHINE_STATE_001/STATUS.md` is updated with these figures, and section 8's caveat is
  narrowed accordingly.

## What is NOT established here

- **Nothing was scored by me.** Every number is a regrouping of the workers' own recorded
  correctness flags. The recomputation was checked against each run's declared totals and matched in
  all six.
- **This says the two shapes separate; it does not say why beyond what is already measured.** The
  composition and identification findings behind the separation are from `receipt_20260919_m`.
- **Only the exposed course and the retention panel were decomposed.** The development panel was not.
- **The six runs are not six independent studies.** They are three seeds by two arms of one study,
  and the seeds differ only in model initialisation.
- **No GPU work was launched.**
