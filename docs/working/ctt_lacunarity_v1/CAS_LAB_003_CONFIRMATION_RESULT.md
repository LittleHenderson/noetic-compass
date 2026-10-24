# CAS-LAB-003 — Three-seed confirmation: the kNN steering probe passes its predeclared bar (2026-10-24)

Status: **confirmatory for the NLL outcome, local GPU, weights frozen, not claim-bearing.** Protocol was written in
`CAS_LAB_002_PROBE_RESULT.md` §6 before this run. The generation guard has **not** been run — that is the remaining
condition and is stated as such.

## 1. What ran

For each seed: compute the oracle direction per row; choose `k` from `{5,10,20,50}` using **discovery rows only**;
freeze that `k`; score the confirmation half. Bar fixed in advance: probe gain ≥ 10% of the oracle gain in at least
two of three seeds, and strictly above the random control in all three.

## 2. Result — all three seeds pass

| Seed | k chosen (discovery) | Conf. rows | Oracle gain [95% CI] | **Probe gain [95% CI]** | Fraction | Random gain |
|---|---|---:|---|---|---:|---:|
| A4-s1 | 5 | 300 | 0.4568 [0.4137, 0.5033] | **0.2045 [0.1635, 0.2450]** | **0.448** | 0.0008 |
| A4-s2 | 20 | 300 | 0.6485 [0.5891, 0.7171] | **0.4048 [0.3333, 0.4778]** | **0.624** | 0.0145 |
| A4-s3 | 10 | 300 | 0.4564 [0.4008, 0.5161] | **0.2217 [0.1783, 0.2657]** | **0.486** | −0.0063 |

**Verdict: 3 of 3 seeds meet the bar.** Every probe interval lies strictly above zero and above the random control.
The random control is near zero in all three seeds, as it should be.

Discovery sweeps (for the record):

| Seed | k=5 | k=10 | k=20 | k=50 |
|---|---:|---:|---:|---:|
| A4-s1 | 0.229545 | 0.228019 | 0.205812 | 0.154882 |
| A4-s2 | 0.495106 | 0.491741 | 0.517456 | 0.413637 |
| A4-s3 | 0.235889 | 0.242316 | 0.156767 | 0.111064 |

The sweep is flat between 5 and 20 and falls at 50 in two seeds; the choice is not knife-edge, which is why the
frozen-`k` confirmation is meaningful rather than a lucky pick.

Class-mean control (same rows): A4-s1 0.079535 [0.033237, 0.128959], A4-s2 0.056867 [−0.020745, 0.132216],
A4-s3 0.083643 [0.048918, 0.119615]. The neighbourhood probe beats the cell-mean by roughly 2.4× to 7× depending on
seed, and the cell-mean's interval includes zero in one seed. **The gain is not coming from the cell label.**

## 3. What this establishes

1. A direction computed **without the answer** recovers **44.8%–62.4%** of the answer-aware gradient gain, on rows the
   probe never saw, across three seeds, with intervals excluding zero.
2. The effect is **local**: the cell label alone recovers 12%–18% of the oracle; the neighbourhood carries the rest.
3. The random control is confirmed inert in all three seeds.

## 4. What it does not establish

- **Reply quality.** The outcome is teacher-forced error on notation rows. The generation composite has not been
  measured under steering, and the earlier work showed prediction and replies can move in opposite directions. The
  guard (no fall > 0.02) is still owed.
- **Generality.** One model family, one data source, one checkpoint per seed (step 1,000), 300 confirmation rows.
- **Deployability without labels.** The method still needs a labelled discovery set to compute oracle directions once;
  it does not need labels at inference, which is the practical difference.
- Claim-bearing status: **none** (local diagnostic).

## 5. The next gate (written before running)

1. Implement steered generation: encode the reply source, add the kNN direction at the last source position, decode
   with the same lock and seeds as the frozen generation test.
2. Direction for a generation item = mean oracle direction of its 10 nearest **notation discovery** rows in memory
   space (no mouth labels exist, so this is the only honest transfer).
3. Run 300 fixed exam items, baseline vs steered, three seeds, and compute the frozen composite.
4. **Pass condition:** composite does not fall by more than 0.02 in any seed, and at least one seed shows a rise.
   A fall beyond 0.02 fails the whole steering claim regardless of the NLL gain.

## 6. Artifacts

- `lacunarity_e1/probe_confirm.py`; raw results `cs_aws/confirm_results.jsonl`.
- Spend: **0 USD**, local.
