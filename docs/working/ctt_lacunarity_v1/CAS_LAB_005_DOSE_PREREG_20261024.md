# CAS-LAB-005 — Dose-response preregistration (2026-10-24)

Status: **preregistered before the run.** Follows the rejection in `CAS_LAB_004_GUARD_RESULT.md`, where a full-strength
injection (dose 1.0) improved notation error and cost 0.112907 of reply quality. This test asks whether a smaller
dose is safe. It is written down first because choosing a dose after seeing the failure is tuning on the outcome.

## 1. Question

Is there a dose of the same steering direction that lowers notation error **without** costing reply quality?

## 2. Design

- Model: A4-s1 step 1,000 first (the seed on which the failure was measured). Seeds A4-s2 and A4-s3 only if a dose
  passes here, and then with the same frozen dose.
- Direction: the kNN-10 probe direction from the previous round, unchanged.
- Doses (fixed now): **0.05, 0.10, 0.20, 0.40, 1.00** × the row's memory norm. Dose 1.00 is the known failure and is
  included as the reference point, not as a candidate.
- Injection position: last source position, exactly as before.
- Baseline: the already-scored unsteered run (`gen_A4-s1_baseline.jsonl`, composite 0.231817). No re-run, no new
  baseline.
- Reply set: the same 300 fixed exam items, frozen decoding, same seeds.

## 3. Outcomes

1. **Primary: the reply composite** (guard × fact exactness × read-back), same scorer as every earlier run.
2. Secondary: notation teacher-forced NLL gain on the confirmation half, to confirm the direction still moves the
   internal measure at that dose.

## 4. Decision rule (fixed now)

A dose **passes** only if **both** hold:

- composite ≥ baseline − 0.02 (0.211817), and
- notation NLL gain ≥ 25% of the full-dose probe gain (0.2045 × 0.25 = 0.051125) on the confirmation half.

If any dose passes, the smallest passing dose is frozen and taken to seeds 2 and 3. If none passes, the last
inference-time steering claim is withdrawn and the direction is recorded as unsafe at every dose tested.
No dose may be added after seeing results. No retuning of the direction, the position, or the transfer rule.

## 5. What each outcome would change

- **A dose passes:** steering has a safe operating range, and the repair question reopens for training-free control.
- **No dose passes:** internal steering through memory is recorded as unusable for this task, and the repair route
  moves to RPM-guided selection of *which rows* to steer (the other approved option), not the dose.
- **NLL gain collapses before the guard is satisfied:** the direction's useful range and its safe range do not
  overlap; that is a clean negative.

## 6. Cost

Local GPU, 0 USD. One generation run per dose (~300 items each), plus scoring.
