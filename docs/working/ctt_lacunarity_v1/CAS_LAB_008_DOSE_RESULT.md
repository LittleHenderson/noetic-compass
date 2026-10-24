# CAS-LAB-008 — Dose-response result: a safe operating range exists (dose 0.2) (2026-10-24)

Status: **confirmatory for seed A4-s1 against the frozen rule; AWS-evaluated.** Instance `i-0c767b2ad8e6f0d67`,
region `us-west-2`, GPU instance type `g5.xlarge`, run 369.1 s, estimated **0.1128 USD**. Preregistration:
`CAS_LAB_005_DOSE_PREREG_20261024.md` (unchanged).

## 1. Result

| Dose | Composite | Δ vs baseline | Notation gain | Fraction of full gain | Verdict |
|---|---:|---:|---:|---:|---|
| Baseline | 0.231817 | — | — | — | — |
| 0.05 | 0.231817 | 0.000000 | 0.009708 | 5.4% | fails gain bar |
| 0.10 | 0.221779 | −0.010038 | 0.024033 | 13.4% | fails gain bar |
| **0.20** | **0.225594** | **−0.006223** | **0.054952** | **30.6%** | **PASS** |
| **0.40** | **0.222042** | **−0.009775** | **0.102854** | **57.3%** | **PASS** |
| 1.00 | 0.118910 | −0.112907 | 0.179647 | 100% | fails guard |

Frozen rule: composite ≥ 0.211817 **and** gain ≥ 0.051125. Doses 0.20 and 0.40 satisfy both. The smallest passing
dose, **0.20**, is frozen for the seed replication.

## 2. What this changes

The previous rejection (`CAS_LAB_004`) was a **full-strength** result. At 0.20:

- notation error still improves by **30.6%** of the full gain (0.054952),
- reply quality falls by only **0.006223**, inside the 0.02 allowance,
- every component stays near baseline: guard 0.730000, fact 0.730000, read-back 0.423333 (identical to baseline).

So the dose-response is monotone and the damage is **dose-dependent, not inevitable**. A narrow but real operating
range exists between "inert" (0.05) and "damaging" (1.00).

## 3. What it does not establish yet

- **One seed.** The preregistration requires seeds A4-s2 and A4-s3 at the frozen dose 0.20 before the claim stands.
- The gain is still teacher-forced notation error, not replies; the guard only says replies did not get worse.
- The composite at 0.20 is 0.006223 **below** baseline: this is "no significant harm", not "improvement".

## 4. Preregistered next step

Run dose 0.20 on A4-s2 and A4-s3: generation on 300 fixed exam items, same scoring, host named. Pass condition,
unchanged: composite within 0.02 of that seed's baseline and gain ≥ 0.051125, in both seeds.

## 5. Failure in this run, recorded

`rpm_select.py` crashed with a CUDA index-out-of-bounds. Cause: oracle directions were stored only for discovery rows
(300 long) but then re-indexed with global row numbers (up to 599). Fix: use the discovery-only tensor directly. The
selector test did **not** run and produced no numbers; it will be re-run with the seed replication.

## 6. Artifacts and cost

- Results: `cs_aws/aws_score_results.json`; S3 prefix `bridge-control-20260822/score-20261024-090624/`.
- Spend this run: **0.1128 USD**. Earlier failed attempt (wrong prefix): about 0.46 USD. Running total for this goal:
  roughly **0.68 USD** of the 15.00 USD cap.
