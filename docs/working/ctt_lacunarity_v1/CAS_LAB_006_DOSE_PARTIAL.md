# CAS-LAB-006 — Partial dose curve (CPU checks only), 2026-10-24

Status: **partial result. Two of the three guard components, computed on CPU. No model inference, no GPU, no spend.**
Read-back is missing, so the composite is a **lower-bound product** (guard × fact exactness), not the frozen
composite. The preregistered decision in `CAS_LAB_005_DOSE_PREREG_20261024.md` cannot be finalised without read-back
and the notation gain; this narrows the field and is reported as such.

## 1. What was measured

`check.check` (guard) and `only_allowed_words` (fact exactness) are rule-based text checks; they need no model. They
were run over the six 300-row generation files from the dose sweep, against the same 300 exam items.

## 2. Result

| Condition | Guard | Fact exact | Guard × fact | vs baseline |
|---|---:|---:|---:|---:|
| Baseline | 0.740000 | 0.740000 | **0.547600** | — |
| Dose 0.05 | 0.740000 | 0.740000 | **0.547600** | **0.000000** |
| Dose 0.10 | 0.726667 | 0.726667 | 0.528044 | −0.019556 |
| Dose 0.20 | 0.730000 | 0.730000 | 0.532900 | −0.014700 |
| Dose 0.40 | 0.730000 | 0.730000 | 0.532900 | −0.014700 |
| Dose 1.00 | 0.603333 | 0.603333 | 0.364011 | −0.183589 |

## 3. What this narrows

- **Dose 0.05 leaves the replies exactly unchanged** on both checks: guard passes 222 of 300, identical to baseline.
  It is the only dose that is free on these two components.
- **Doses 0.10 to 0.40 cost 1.5 to 2.0 points** of the guard × fact product — inside the 0.02 allowance on this
  partial measure, but the read-back component is unknown and historically moves with the others.
- **Dose 1.00 is the known failure**: 18.4 points down on the partial product, consistent with the 0.112907 composite
  loss already recorded.

## 4. What is still needed for the preregistered decision

1. **Read-back** on each dose file (needs the ear model → GPU).
2. **Notation gain at each dose** on the confirmation half (needs the model → GPU).
3. Apply the frozen rule: composite ≥ 0.211817 **and** notation gain ≥ 0.051125.

Both are queued for the AWS run awaiting the owner's approval (bound 1.00 USD).

## 5. Honest reading

The shape is already informative: the damage is monotone in dose (0.05 none, 0.10–0.40 small, 1.00 large), which is
what a dose-response should look like. But nothing here shows a dose that *improves* replies, and the internal gain at
0.05 is likely a small fraction of the full 0.2045. The realistic expectation for the AWS stage is that 0.05 is safe
but nearly inert, and that the useful band (if any) is narrow.

## 6. Artifacts

- `lacunarity_e1/cpu_dose_guard.py`; generation files `cs_aws/guard/gen_A4-s1_*`.
- Spend: **0 USD**; no GPU used; no model inference.
