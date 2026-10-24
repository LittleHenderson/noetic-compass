# LAC-02 — Measurement specifications (CAS-LAC-001, Phase 1)

Status: **Phase 1 deliverable.** Every candidate is `PROPOSED` unless it says otherwise. A formula existing here does
not make it a validated measurement. Baselines are named because a measure that cannot beat them is not useful.

## 1. Noetic family

### N-1 Per-cell error lacunarity (IMPLEMENTED, EVALUATED)

```
For cells c = ^0 … ^9:
  Err_c = mean row error over held-out rows whose gold target contains c
  Exposure_c = number of TRAINING ROWS whose gold target contains c     (row count, never token count)
  Λ_err = Var_c(Err_c) / Mean_c(Err_c)^2                                  (population variance)
```

- Inputs: per-row teacher-forced error, per-row Noetic address, training addresses.
- Range: `[0, ∞)`; 0 when every cell has the same mean error.
- Normalisation: none. Comparable only between runs with the same cell set and metric.
- Baseline it must beat: the mean error alone, and exposure.
- Known limits: with ten cells the statistic is noisy; it says nothing about which cell matters.
- Status: implemented (`cas_score.py`), evaluated once; the published verdict needed correction (LAC-00 §4).

### N-2 Exposure–error gap (PROPOSED, not implemented)

```
log Err_c = a + b · log(Exposure_c) + ε_c
Gap_c = max(0, ε_c)                         (positive = worse than exposure predicts)
GapShare = Σ Gap_c / Σ Err_c
```

- Purpose: separate "this cell is hard because it is rare" from "this cell is failing beyond what its rarity
  explains". N-1 cannot do that; this can, in principle.
- Range: `Gap_c ≥ 0`; `GapShare ∈ [0, 1]` when all `Err_c > 0`.
- Baseline it must beat: raw `Err_c`, and `Err_c` rank against `Exposure_c` rank.
- Limits: ten points fit a two-parameter line poorly; report the residual pattern, not just `R²`.
- Status: `PROPOSED`.

### N-3 Forty-slot gate reading (IMPLEMENTED as a controller, not evaluated)

`Var/Mean²` on the 40 slot activations, threshold 2.0, followed by a learned rebalancing. The gate changes the
model, so its measurement and its intervention are entangled. Any diagnostic use requires reading it without the
correction active. Status: `IMPLEMENTED` (controller), `NOT EVALUATED`.

## 2. Recipe family

Existing semantics (Clarification 9): `Y_T(Ω|S) = min_i(x_i/a_i)`. A limiting reagent is a **bottleneck**, not a
lacunarity. The two candidates below are different quantities and must not be reported as "the recipe lacunarity".

### R-1 Recipe requirement dispersion (PROPOSED)

```
For a target Ω with recipes r = 1 … R:
  w_r = normalised ingredient vector of recipe r
  Λ_req = Var_r(w_r) / Mean_r(w_r)^2        (over recipes, per ingredient, then averaged)
```

- Meaning: how unevenly the same target's recipes distribute their demands. High = one recipe dominates; low = many
  equivalent routes.
- Inputs: recipe table (targets, ingredients, required quantities).
- Range: `[0, ∞)`.
- Baseline it must beat: ingredient count, and the count of distinct recipes per target.
- Limits: a target with one recipe has `Λ_req = 0` by construction; compare only within targets with `R ≥ 2`.
- Status: `PROPOSED`; no implementation exists.

### R-2 Recipe fragility (PROPOSED)

```
Y_T = min_i(x_i/a_i)
F = 1 − mean_i [ Y_T(Ω | S without ingredient i) / Y_T(Ω | S) ]
```

- Meaning: the average fractional loss of theoretical yield when each ingredient is removed in turn. A recipe with
  one critical ingredient has `F` near 1; a recipe with many substitutes has `F` near 0.
- Range: `[0, 1]`.
- Baseline it must beat: `Y_T` itself, and the number of ingredients.
- Distinct from limiting reagent: the limiting reagent is the smallest ratio at one state; `F` is a sensitivity of the
  yield to removing prerequisites.
- Status: `PROPOSED`; needs a recipe table with substitution alternatives, which the current compiler does not expose.

## 3. RPM family

Distinct quantities that must stay separate: depth, branching, unresolved prerequisites, repair cost, connectivity,
lacunarity. The existing "RPM resolution lacunarity" is only `1 − mechanisms/4`.

### P-1 Unresolved-prerequisite dispersion (PROPOSED)

```
For chain nodes n with u_n unresolved prerequisites:
  Λ_rpm = Var_n(u_n) / Mean_n(u_n)^2
```

- Meaning: whether blockers are spread across the chain or concentrated in a few nodes.
- Range: `[0, ∞)`; `0` when every node has the same blocker count.
- Baseline: total unresolved count, node count.
- Status: `PROPOSED`; the RPM engines do not expose `u_n` today.

### P-2 Chain fragility (PROPOSED)

```
Reach(n) = number of downstream nodes reachable from n
F_rpm = 1 − mean_n [ Reach(n) without n / Reach(n) ]
```

- Meaning: how much a single removed prerequisite costs downstream. A bottleneck node has high fragility.
- Range: `[0, 1]`.
- Baseline: depth, out-degree, blocker count.
- Status: `PROPOSED`; needs a dependency graph from the RPM engine.

## 4. What must not be done

- Do not sum these into one "Λ" score before each has passed its own gate (LAC-05, LAC-06).
- Do not call the limiting reagent a lacunarity.
- Do not compare `Λ` values across different cell counts, box sizes or units.
- Do not treat a learned gate's output as a measurement of the model's structure.
