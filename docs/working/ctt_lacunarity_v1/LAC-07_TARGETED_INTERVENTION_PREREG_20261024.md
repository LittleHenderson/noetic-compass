# LAC-07 — Targeted intervention trial, preregistration (CAS-LAC-001, Workstream 7)

Status: **preregistered before any run. Not started.** Owner approved the rank and its budget (~3.5 USD upper bound);
this document fixes the protocol first.

## 1. The question

The Noetic result says low-exposure cells carry higher held-out error, on two sources. That is an association. The
intervention test asks the causal question: **if the model is given more examples of the low-exposure cells, does
held-out error in those cells fall, and does reply quality change?**

## 2. Design (three arms, one starting point)

Start from the **step-1,000 checkpoint of A4-s1** and continue training for **500 steps** in each arm. Nothing else
changes: same optimiser, same learning rate schedule continuation, same batch size, same seed.

| Arm | Extra data for the 500 steps | Purpose |
|---|---|---|
| A. Targeted | 2× the training rows whose gold target contains a low-exposure cell (`^2`,`^3`,`^4`,`^5`,`^8`) | the intervention |
| B. Undirected | 2× a random sample of training rows, same total count | controls for "more training" |
| C. Placebo | the same rows as A, but with a **random** Noetic label on each row (so the model is trained on wrong addresses) | controls for "more of these sentences" without the label |

Arm C is the one that matters: if A beats B but not C, the gain came from the sentences, not from the targeting.

## 3. Outcomes (both measured, both reported)

1. **Held-out Noetic error** on the second source (`notation_new100`, 600 rows), overall and per cell. Primary.
2. **Generation composite** (guard × fact-exactness × read-back) on a fixed 300-item subset of the 1,517 exam inputs,
   scored exactly as the earlier generation test, with the same fixed listener. Secondary.
3. **Regression guard:** if the composite falls by more than 0.02 against arm B, the intervention is a loss regardless
   of the Noetic gain.

## 4. Predeclared success criterion

The targeted arm succeeds only if **all three** hold:

1. Low-exposure-cell held-out error falls by at least **0.02** absolute versus arm B.
2. Overall held-out error does not rise versus arm B.
3. The generation composite does not fall by more than 0.02 versus arm B.

Any other pattern is reported as failure or as inconclusive, not reinterpreted.

## 5. Statistics

Per-arm point estimates with paired bootstrap intervals over rows (10,000 resamples, seed fixed in advance). Three
arms, one seed, one model — this is a **screening** test, not a confirmation. A positive result would justify a
three-seed replication, not a deployment.

## 6. Cost and stopping rules

- Compute: 3 arms × 500 steps on one g5.xlarge. At the measured rate (~1.10 USD/hour) and the earlier 6,000-step run
  time, 500 steps is about 1/12 of a run: roughly 0.10 USD per arm, ~0.30 USD total, plus instance start/stop overhead
  and storage, bounded at **1.00 USD**.
- Generation scoring: 3 arms × 300 items, local, 0 USD.
- Stop immediately if any arm diverges (loss not falling after 100 steps, or NaN).
- No second run without the owner's separate approval.

## 7. What result would change what decision

- If A beats B and C: exposure targeting is a real lever, and Rank 6 (three-seed replication, ~3 USD) follows.
- If A beats B but not C: the sentences help, the labels do not. The Noetic diagnostic loses its claim to be the
  reason, and that is recorded as a negative for the diagnostic.
- If A does not beat B: the association does not become a repair. The Noetic family stops at "diagnostically
  evaluated, not intervention validated".

## 8. Artifacts to be produced

`LAC-07_TARGETED_INTERVENTION_RESULT.md` with per-arm numbers, the three-arm table, the bootstrap intervals, the
generation composite, and every failed or diverged arm listed.
