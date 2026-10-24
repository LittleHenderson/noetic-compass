# CAS-LAB-007 — RPM-guided direction: preregistration (2026-10-24)

Status: **preregistered before any run.** Second of the two approved options. It tests whether the structural labels
built in CAS-LAB-001 can pick *which* rows to learn a steering direction from, better than raw memory distance.

## 1. The hypothesis

The kNN probe works because it averages oracle directions of rows that sit near the target row in memory. The recipe
and RPM labels describe what a row *is*, not where it sits. If the label identifies the right source rows better than
distance does, a label-guided neighbourhood should capture more of the oracle gain at the same number of neighbours.

## 2. Selectors (fixed now)

For a target row, the direction is the mean oracle direction of its `k` nearest discovery rows, where "nearest" is one
of:

| Selector | Rule |
|---|---|
| **D1 unguided** | Euclidean distance in last-position memory (the current probe) |
| **D2 same-cell** | among discovery rows sharing the target's first cell (`^n^D`), nearest by memory |
| **D3 same-operator** | among discovery rows with the same operator set (`×` vs `→`), nearest by memory |
| **D4 recipe-fragility weighted** | all discovery rows, weighted by `exp(-d²/k)` × the row's recipe fragility `F` (from `lacunarity_families.py`) |
| **D5 random rows** | `k` random discovery rows (control for "any rows will do") |

`k` = 10 for every selector. No tuning of `k` in this test; the earlier sweep showed flatness between 5 and 20, so a
fixed 10 is not the variable under test.

## 3. Data and outcome

- Model: A4-s1 step 1,000 (same checkpoint as every steering result).
- Rows: `notation_new100`, split by source parity as before (discovery even, confirmation odd).
- Primary outcome: notation NLL gain on the confirmation half (mean over rows).
- Reference: the oracle gain on the same rows, so every selector is reported as a fraction of it.
- Secondary outcome: the reply guard, **only** for the winning selector, and only on AWS (no local GPU runs).

## 4. Decision rule

The structural hypothesis is supported only if **a label-guided selector (D2, D3 or D4) captures at least 1.25× the
oracle fraction of D1** on the confirmation half. Anything less is recorded as "the labels do not beat distance", and
no further label-guided variants will be tried in this programme.

D5 exists to catch the trivial case: if random rows match D1, the whole neighbourhood story is wrong and the earlier
confirmation is re-read as a magnitude effect.

## 5. Why this is a fair test

- Same rows, same split, same checkpoint, same `k`, same direction estimator.
- Only the *selection rule* changes.
- The comparison is against the strongest existing selector (D1), not against random alone.
- The bar (1.25×) is set before the numbers.

## 6. Cost

Evaluation of five selectors on 300 confirmation rows: no model forward passes beyond the oracle directions already
needed (600 per run), so this is small. It will run on AWS with the dose scoring in the same session, bounded by the
same 1.00 USD approval.

## 7. What it would change

- **Supported:** the recipe/RPM label carries steering-relevant information, and the labeller becomes part of the
  control path rather than documentation.
- **Not supported:** the neighbourhood gain is a distance effect, and labels add nothing; recorded as a clean negative
  for the second approved option.
