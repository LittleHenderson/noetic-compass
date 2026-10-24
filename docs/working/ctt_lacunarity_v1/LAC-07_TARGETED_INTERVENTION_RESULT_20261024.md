# LAC-07 — Targeted intervention trial: RESULT — the intervention fails (2026-10-24)

Status: **preregistered test, executed, failed.** Kept as a failure. Local GPU, diagnostic, not claim-bearing.
Preregistration: `LAC-07_TARGETED_INTERVENTION_PREREG_20261024.md` (frozen before the run).

## 1. What ran

Three arms, each 500 steps from the A4-s1 step-1,000 checkpoint, same optimiser, same learning-rate value (5e-4),
same batch size, same order seed. Only the extra data differed.

| Arm | Extra data | Training loss at step 500 |
|---|---|---|
| Targeted | 2× the rows for low-exposure cells (`^2`,`^3`,`^4`,`^5`,`^8`) | 0.33512 |
| Undirected | 2× random rows, same count | 0.32972 |
| Placebo | the same rows as targeted, with **random Noetic labels** | 0.33965 |

A baseline (the untouched step-1,000 checkpoint) is reported alongside.

## 2. Primary outcome — held-out Noetic error on the second source (600 rows)

| Arm | Overall | Low-exposure cells |
|---|---:|---:|
| Baseline | 1.471022 | 1.568779 |
| **Targeted** | **1.634968** | **1.715998** |
| Undirected | 1.652370 | 1.696970 |
| Placebo | 1.326175 | 1.417697 |

## 3. Secondary outcome — generation composite (300 fixed exam items)

| Arm | Guard | Fact exact | Read-back | Composite |
|---|---:|---:|---:|---:|
| Baseline | 0.740000 | 0.740000 | 0.423333 | 0.231817 |
| **Targeted** | 0.803333 | 0.803333 | 0.496667 | **0.320521** |
| Undirected | 0.816667 | 0.816667 | 0.516667 | 0.344588 |
| Placebo | 0.776667 | 0.776667 | 0.496667 | 0.299595 |

## 4. The preregistered criterion, applied literally

| Condition | Required | Observed | Verdict |
|---|---|---|---|
| 1. Targeted low-exposure error falls by ≥ 0.02 vs undirected | ≤ 1.676970 | 1.715998 (+0.019028 **worse**) | **FAIL** |
| 2. Targeted overall error does not rise vs undirected | ≤ 1.652370 | 1.634968 (−0.017402 better) | pass |
| 3. Generation composite does not fall by more than 0.02 vs undirected | ≥ 0.324588 | 0.320521 (−0.024067) | **FAIL** |

**Result: the intervention fails.** It made held-out Noetic error worse in the cells it targeted, and it cost
generation quality against the undirected control. Two of the three conditions failed.

## 5. The anomaly that must not be spun

The **placebo** arm — the same sentences with deliberately wrong Noetic labels — produced the **best** held-out
Noetic error of all four (1.326175 overall, 1.417697 on low-exposure cells), better even than the untouched baseline.
Its generation score was the worst of the three trained arms (0.299595).

I do not have an explanation. Candidate explanations, none tested:

- random labels may act as a regulariser against over-fitting the notation mapping;
- the label corruption may push the model toward a smoother output distribution that happens to lower average NLL;
- it may be noise at this sample size.

This is recorded as an unexplained anomaly, not as a result. It also means the "placebo" is not a clean control in the
sense intended: it changed the training signal in a way that improved one outcome. Any replication must treat it as a
second intervention, not a null.

## 6. What this establishes

1. **More training alone improves replies.** All three trained arms beat the untouched checkpoint on the generation
   composite (0.320521 / 0.344588 / 0.299595 vs 0.231817). That is consistent with the earlier generation finding.
2. **Targeting the weak cells did not help them.** It made them worse relative to both controls.
3. **The Noetic diagnosis did not select a useful repair.** Objective E is answered negatively for this family at this
   scale.
4. **The exposure–error association does not license a causal repair.** "Cells with fewer rows have higher error" did
   not translate into "adding rows to those cells fixes them".

## 7. Limits

- One seed, one model family, 500 steps, 300 generation items. A screening test, not a confirmation.
- The arms continued training from step 1,000 with a flat learning rate, not the original cosine schedule; the
  comparison is arm-to-arm, not against the 6,000-step final.
- The Noetic outcome used the second (machine-authored) source.
- The generation subset is 300 items, so its component rates carry roughly ±0.05 sampling noise.

## 8. Claim status

| Statement | Status |
|---|---|
| Targeted replay worsened low-exposure held-out error vs undirected (+0.019028) | `REAL` |
| Targeted replay cost generation quality vs undirected (−0.024067) | `REAL` |
| The preregistered intervention criterion failed | `REAL`, kept as a failure |
| Any training helps replies vs no training | `REAL` (all three arms beat baseline) |
| Placebo labels improve Noetic error | `UNEXPLAINED`, not a result |
| Noetic targeting is a useful repair mechanism | `NOT SUPPORTED` |

## 9. Artifacts and cost

- Arm weights: `cs_aws\arms\{targeted,undirected,placebo}.pt`; baseline is `results\out\A4-s1\step_01000.pt`.
- Scores: `cs_aws\arm_scores\*.json`, `cs_aws\arm_gen\*.jsonl`, `cs_aws\arm_scored\*.scored.jsonl`.
- Runner: `lacunarity_e1\intervene.py` (500 steps per arm, ~165 s, ~375 s, ~375 s).
- Cost: **0 USD** — local GPU diagnostic; the 1.00 USD budget was not spent.
