# Review of the outside critique, and the checkpoint study it asked for (2026-10-23)

Status: review + a free diagnostic run. Not claim-bearing (local GPU). Numbers: `REAL`. Interpretation: `PROPOSED`.

## 1. Verdict on the critique

It gets the shape right and two facts wrong.

**Right, and already the project's position:**
- Measuring is not the mechanism. The vision was a controller, not an instrument; goal 3 (fill gaps), goal 4 (predict
  the gradient direction) and goal 5 (learn faster and generalise better) are untested. This matches the design note's
  own ranking (R1 instrument, R2 per-block, R4 global last).
- The held-out deterioration is the most important finding, more than the concentration result.
- Multi-seed replication is required before any of this is a law.
- The frozen c60 protocol must not be rewritten; checkpoint selection, if studied, belongs to a separate authorised
  experiment. That is exactly how the amendment system already works.

**Wrong:**
1. *"The training series uses the report's average surprise per token as a proxy, while the held-out series uses its
   reported error. These are different metrics."* They are the same metric: mean negative log-likelihood per target
   token under teacher forcing, with PAD masked. Same loss function the trainer optimises, same computation in the
   scoring script. The numbers are directly comparable.
2. *"The exact interpretation depends on how the trainer defines them, which is not included in the report."* The
   reports define it: gliding-box lacunarity `L(b) = 1 + Var(N_b)/E[N_b]²` over the per-token NLL vector of each row,
   with boxes 4, 8, 16 for mouth targets and 4, 16, 64 for 128-token CAS records, PAD masked, rows shorter than one
   box skipped. That is the standard Plotnick et al. (1996) estimator, not an ad-hoc invention.

**Worth adopting:** the middle step — *Predict*. Before a measurement may steer a run, test whether it predicts the
thing we care about (future held-out movement), rather than assuming a gap deserves a bigger step. That is a better
gate than the one in the amendment, and it is free to test offline. Adopted below.

**Rejected:** going back to `α(t) = α₀(1 + λL(t))`. That form was already measured to be scale-dependent (multiplier
1.504 → 651.154 on the same problem when only the loss scale changed) and unbounded. The critique calls it "a
conceptual starting point"; the measurement says it is a hazard.

## 2. The checkpoint study it recommended (run today, cost 0)

Scored all six saved checkpoints on the **full** 2,097-row held-out mouth split, same procedure for every checkpoint:

| Checkpoint | Mean token NLL | L(4) median | L(16) median |
|---|---|---|---|
| step 1,000 | **1.189868** | 1.7184 | 1.0327 |
| step 2,000 | 1.355898 | 1.9363 | 1.0411 |
| step 3,000 | 1.519506 | 2.0258 | 1.0471 |
| step 4,000 | 1.636470 | 2.0887 | 1.0503 |
| step 5,000 | 1.692508 | 2.1262 | 1.0490 |
| final (6,000) | 1.706895 | 2.1334 | 1.0498 |

Paired by row, step 1,000 versus final (10,000 bootstrap resamples, seed 20261023):

- Mean row NLL: step 1,000 **1.123029489**, final **1.589349064**; mean paired difference **+0.466319575**,
  95% CI **[0.436446804, 0.496554499]**.
- Median paired difference **+0.237172035**.
- **1,520 of 2,097 rows (0.7248) are worse at the final checkpoint**; 577 (0.2752) are better there.
- 412 rows (0.1965) are worse by more than 1.0 NLL, and those rows carry **0.6779** of the total degradation.

So the result is broader and more serious than "a few outliers": most rows degrade, and a fifth of them degrade
badly. The earlier 800-row reading (best at step 1,000) is confirmed on the full split with a tight interval.

**Why this matters for the protocol.** The frozen mouth protocol scores `final` and forbids choosing a checkpoint.
On this run that rule returns the worst checkpoint measured for unseen phrasings. That is a protocol question for the
owner, not something a diagnostic may change by itself.

## 3. What this changes in the plan

1. **Checkpoint selection becomes the first real experiment**, not the per-block arm. It is cheap (inference only on
   existing checkpoints), it has a clear decision, and it is independent of the lacunarity theory.
2. **E2 (global multiplier) stays unattractive.** The phase where `L` rises is the phase where held-out quality falls;
   a global controller would mostly act on a model that is already drifting.
3. **E2's prerequisite becomes the critique's *Predict* step:** does `L(t)` predict `held-out(t + Δ)`? With six paired
   points this cannot be answered (the two series are monotone by construction, which is consistency, not
   prediction). It needs one run that evaluates held-out every 500 steps — inference only, no extra training cost.
4. **E3 (per-block) is unchanged** and remains the only arm with a mechanism aimed at the mouth's specific weakness.

## 4. Claim status

| Statement | Status |
|---|---|
| Step 1,000 beats final by +0.466319575 mean NLL, CI [0.436446804, 0.496554499] | `REAL` (one run, local GPU) |
| 0.7248 of rows degrade at final; 0.1965 degrade by > 1.0; they carry 0.6779 of the total | `REAL` (same run) |
| The frozen final-checkpoint rule costs held-out quality on this run | `PROPOSED` — needs a second seed before it is a law |
| `L` predicts future held-out movement | `NOT TESTED` — six points cannot decide it |
| Any gain from checkpoint selection on the exam | `NOT CLAIMED` |
| Claim-bearing status | **NONE** (local diagnostic) |

## 5. Reproduction

```
# full-split scoring, all six checkpoints (row means included in each JSON)
test_c60_error_field.py --checkpoint runs/A4-s1-lac5/<ckpt>.pt --config A4_9p6M \
  --payload <payload> --rows 3000 --file mouth_dev.jsonl > runs/A4-s1-lac5/score_<ckpt>.json

# paired bootstrap, step_01000 vs final (seed 20261023, 10,000 resamples)
# result: mean +0.466319575, CI [0.436446804, 0.496554499]
```

Files: `score_step_01000.json` … `score_final.json` in `runs/A4-s1-lac5/` (each carries `row_means`).
