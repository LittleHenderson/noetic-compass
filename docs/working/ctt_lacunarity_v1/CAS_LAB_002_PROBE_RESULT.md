# CAS-LAB-002 — A deployable steering probe captures 39% of the oracle gain (2026-10-24)

Status: **exploratory, local GPU, weights frozen, not claim-bearing.** Follows the Harness conditioning method
(`CAS_HARNESS_STEERING_INVENTORY_20261024.md`). Preregistration: none for this probe — it is exploratory; the
confirmation protocol below is written before it runs.

## 1. The question

The gradient direction lowers held-out error by +0.2200 mean per cell, but it needs the gold answer. Can a direction
computed **without** the answer capture that gain? Three deployable candidates, one oracle, one control.

## 2. Method

- Model: A4-s1 step 1,000, CTT A4-9.6M, weights frozen.
- Data: `notation_new100`, 600 rows; **split by source** — even source index for discovery (300 rows), odd for
  confirmation (300 rows), so no source appears in both halves.
- Oracle: `−∇_mem NLL` at the last source position, normalised, applied with scale `‖h‖`. Uses the gold target, so it
  is an upper bound.
- Deployable: same position, no target used.
  - **kNN-10:** mean oracle direction of the 10 nearest discovery rows in memory space.
  - **class mean:** mean oracle direction of the row's first cell, discovery rows only.
  - **ridge:** linear map `W` fitted from memory to oracle direction on discovery rows (`λ = 1.0`).
- Control: matched-norm random direction, seeded from `sha256(cell)`.

## 3. Result

| Direction | Held-out NLL | Change vs baseline | Fraction of oracle |
|---|---:|---:|---:|
| Baseline (no intervention) | 1.368837 | — | — |
| **Oracle gradient** (uses the answer) | 0.912078 | **+0.456759** | 1.0000 |
| **kNN-10 probe** (deployable) | 1.189190 | **+0.179647** | **0.3933** |
| Class mean (deployable) | 1.344488 | +0.024349 | 0.0533 |
| Ridge map (deployable) | 1.367664 | +0.001173 | 0.0026 |
| Random (control) | 1.368005 | +0.000832 | 0.0018 |

**Reading:** a nearest-neighbour direction, built only from rows whose answers are known, captures **39.33%** of the
oracle gain on rows whose answers are not used. Cell labels alone capture 5.33%. A linear map from memory captures
0.26% — the relation is not linear. Random captures 0.18%.

This is the first steering result with a real bar under it: it is measured against the oracle at the same position,
on rows the probe never saw, with a source-level split, and against a matched control.

## 4. Why the linear map fails and kNN works

The oracle direction is a local Jacobian effect that depends on where the row sits in memory space. A single linear
map averages that away; a neighbourhood average keeps the local structure. The practical consequence: the useful
controller is a **case-based** one, not a single steering vector per cell.

## 5. Honest limits

- **k = 10 was chosen after seeing the ridge failure.** No sensitivity sweep yet; the next run must sweep k and
  predeclare the choice.
- One checkpoint, one seed, 300 confirmation rows, no intervals.
- Outcome is teacher-forced error, not the generation composite. A gain here may not survive to replies.
- The oracle uses gold answers on **discovery** rows. That is legitimate offline training data, but it means the
  method needs a labelled set for the cells it will steer — not zero data.
- Nothing here touches weights; this is inference-time influence only.

## 6. Confirmation protocol (written before running)

1. Sweep `k ∈ {5, 10, 20, 50}` on the discovery half only; pick one by discovery performance; freeze it.
2. Run on the confirmation half across **three seeds** (A4-s1/s2/s3), same split rule.
3. Report per-seed gain, fraction of oracle, and a bootstrap interval over rows.
4. **Success bar:** fraction of oracle ≥ 0.10 in at least 2 of 3 seeds, and strictly above the random control in all
   three.
5. **Generation guard:** take the best single setting and run the 300-item generation composite; a fall of more than
   0.02 fails the run regardless of the NLL gain.
6. Only then consider making it cell-conditional (choose the neighbourhood from the recipe/RPM label rather than
   from raw memory distance).

## 7. Artifacts

- `lacunarity_e1/cell_probe.py`; results `cs_aws/probe_ridge.json.txt`, `cs_aws/probe_knn10.json.txt`.
- Spend: **0 USD**, local.
