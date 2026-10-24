# CAS-LAB-012 — Operator-gated steering, three seeds: FAILS (1 of 3) (2026-10-24)

Status: **preregistered test, executed, FAILED.** AWS instance `i-0dc888cdfc96867a2`, us-west-2, g5.xlarge, 368.8 s,
**0.1127 USD**. Preregistration: `CAS_LAB_011_OPERATOR_PREREG.md` (frozen before the run; the 1.15 bar was declared
there, including the explicit note that it is weaker than the 1.25 that already failed).

## 1. Result

| Seed | D1 unguided (fraction of oracle) | D3 same-operator (fraction) | **D3/D1** | Meets 1.15? |
|---|---|---:|---:|---:|---|
| A4-s1 | 0.179647 (0.3933) | 0.220641 (0.4831) | **1.2283** | yes |
| A4-s2 | 0.357754 (0.5517) | 0.389393 (0.6005) | **1.0885** | no |
| A4-s3 | 0.221681 (0.4858) | 0.218828 (0.4795) | **0.9870** | no |

**Verdict: 1 of 3 seeds meets the bar. The hypothesis FAILS.** The preregistered rule needed 2 of 3.

## 2. What the three seeds show

- **The 1.2283× was a single-seed fluctuation.** On the other two seeds the operator gate is +8.9% and −1.3%. There is no
  consistent benefit.
- **Cell identity is consistently terrible**, and this is now a three-seed result: D2/D1 = **0.4050, 0.1363, 0.1853**.
  Restricting the neighbourhood to one Noetic×Domain cell loses between 60% and 86% of the unguided gain every time.
  That is the most robust selection finding in the whole programme, and it is negative for the cell-based framing.
- **Random rows are far below** (0.1002, 0.1240, 0.0543), so the neighbourhood itself is doing real work; it is the
  *labels* that fail to improve the choice of neighbourhood.

## 3. Closing the selection route

This was the last approved option that was not a rescue attempt. With it:

- dose 0.20 is **safe** (3 of 3) but its efficiency bar fails on A4-s3;
- the general structural-label selector fails (1.2283× vs 1.25);
- the narrower operator-only hypothesis fails (1 of 3 at 1.15).

**Therefore: no structural label tested here reliably beats plain memory distance for choosing a steering
neighbourhood, and the Noetic cell is the worst of the labels tested.** The steering route is closed as a control
mechanism at this scale, with the safe-dose finding kept as its one durable result.

## 4. What survives the whole steering arc

1. An answer-free kNN direction captures a large share of the oracle gain (39.3%–62.4% across seeds) — `REAL`.
2. Damage is dose-dependent; 0.20 is safe on three seeds — `REAL`.
3. The efficiency of a fixed safe dose varies by seed (17.5%–30.6% of full gain) — `REAL`.
4. No structural label beats distance; cell identity is consistently harmful — `REAL` negative.
5. A validated steering control rule — **not achieved**.

## 5. Cost

- This run: **0.1127 USD**.
- Goal total: about **1.18 USD** of the 15.00 USD cap.
- All instances from this goal are terminated.

## 6. Claim status

| Statement | Status |
|---|---|
| Operator gating improves selection in ≥2 of 3 seeds | `FAILED` (1 of 3) |
| Cell-identity gating degrades selection | `REAL`, 3 of 3 seeds |
| The 1.2283× was reliable | `REJECTED` — single-seed fluctuation |
| Any structural label beats plain distance | `NO` |
| Steering is a validated control mechanism | `NO` |
